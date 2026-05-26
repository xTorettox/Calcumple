import streamlit as st
from supabase import create_client, Client
import urllib.parse
import uuid

# Configuración de página
st.set_page_config(page_title="Vaquita Express", page_icon="💸", layout="centered")

# Inicializar Supabase (usa los mismos secretos que el Hopper)
url: str = st.secrets["SUPABASE_URL"]
key: str = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

# Detectar si venimos de un link compartido (?evento=UUID)
query_params = st.query_params
evento_id = query_params.get("evento")

# Función auxiliar para subir imágenes al Storage
def subir_imagen(file_buffer, file_name):
    try:
        bucket = "vaquita-comprobantes"
        supabase.storage.from_(bucket).upload(file_name, file_buffer.getvalue(), {"content-type": "image/jpeg"})
        return supabase.storage.from_(bucket).get_public_url(file_name)
    except Exception as e:
        st.error(f"Error al subir imagen: {e}")
        return None

# ==========================================
# VISTA 1: DETALLE Y PAGO (Para los invitados)
# ==========================================
if evento_id:
    # Traer datos de la juntada
    res_juntada = supabase.table("juntadas").select("*").eq("id", evento_id).execute()
    
    if not res_juntada.data:
        st.error("¡Ufa! No encontramos esa juntada. Capaz el link está mal.")
        st.stop()
        
    juntada = res_juntada.data[0]
    
    # Traer participantes
    res_part = supabase.table("participantes").select("*").eq("juntada_id", evento_id).execute()
    participantes = res_part.data
    
    st.title(f"💸 Vaquita: {juntada['motivo']}")
    cuota = juntada['monto_total'] / len(participantes)
    
    # Datos clave expuestos
    col1, col2 = st.columns(2)
    col1.metric("Total Gastado", f"${juntada['monto_total']:,.2f}")
    col2.metric("Tu Parte", f"${cuota:,.2f}")
    
    st.info(f"🏦 **Alias/CBU para transferir:** `{juntada['alias']}`")
    
    if juntada['foto_ticket_url']:
        with st.expander("📸 Ver Ticket Original"):
            st.image(juntada['foto_ticket_url'])
            
    st.divider()
    
    # Lista de control / Quién pagó y quién no
    st.subheader("🧑‍🤝‍🧑 ¿Quién ya puso la tarasca?")
    
    for p in participantes:
        check = "✅" if p['pago_confirmado'] else "⏳"
        coment = f" - *\"{p['comentario']}\"*" if p['comentario'] else ""
        st.write(f"{check} **{p['nombre']}** {coment}")
        if p['comprobante_url'] and not p['pago_confirmado']:
            st.caption(f"[Ver comprobante enviado]({p['comprobante_url']})")

    st.divider()
    
    # Formulario para que el usuario rinda su pago
    st.subheader("✍️ Rendir mi pago")
    usuario_selec = st.selectbox("Seleccioná tu nombre", [p['nombre'] for p in participantes if not p['pago_confirmado']])
    
    if usuario_selec:
        comentario = st.text_input("Dejá un comentario (opcional)", "¡Ya transferí!")
        
        # Botón para activar cámara
        if 'cam_usuario' not in st.session_state:
            st.session_state.cam_usuario = False
        if st.button("📸 Sacar foto al comprobante"):
            st.session_state.cam_usuario = not st.session_state.cam_usuario
            
        comprobante_file = None
        if st.session_state.cam_usuario:
            comprobante_file = st.camera_input("Capturá el comprobante de transferencia")
            
        if st.button("Enviar Confirmación", type="primary"):
            url_comp = None
            if comprobante_file:
                fname = f"comprobante_{evento_id}_{uuid.uuid4().hex}.jpg"
                url_comp = subir_imagen(comprobante_file, fname)
            
            # Actualizar en Supabase (lo dejamos como rendido, podés elegir si se tacha automático o no)
            supabase.table("participantes").update({
                "pago_confirmado": True, # Se tacha al toque
                "comentario": comentario,
                "comprobante_url": url_comp
            }).eq("juntada_id", evento_id).eq("nombre", usuario_selec).execute()
            
            st.success("¡Buenísimo! Pago cargado. Refrescando...")
            st.rerun()
    else:
        st.balloons()
        st.success("¡Qué equipo! Ya pagaron todos.")

# ==========================================
# VISTA 2: CREACIÓN (Para Fede)
# ==========================================
else:
    st.title("💸 Creador de Vaquitas")
    st.write("Armá la juntada y compartí el link interactivo.")
    
    motivo = st.text_input("¿Qué compramos? (Motivo)", "Cumple Manolo")
    monto_total = st.number_input("Monto Total ($)", min_value=0.0, step=100.0)
    alias = st.text_input("Alias / CBU para recibir el pago", "JAVI.CENCO.MP")
    
    # Manejo del botón de la cámara para que no quede siempre abierto
    if 'cam_creador' not in st.session_state:
        st.session_state.cam_creador = False
        
    if st.button("📸 Adjuntar foto del ticket"):
        st.session_state.cam_creador = not st.session_state.cam_creador
        
    ticket_file = None
    if st.session_state.cam_creador:
        ticket_file = st.camera_input("Enfocá el ticket")
        
    participantes_str = st.text_area("Integrantes (separados por coma)", "Franco, Edu, Javi, Fede, JP, Caro, Mati, Andre, Anto, Vane")
    
    if st.button("🚀 Crear Evento y Generar Link", type="primary"):
        if monto_total > 0 and participantes_str:
            lista_nombres = [n.strip() for n in participantes_str.split(",") if n.strip()]
            
            # Subir ticket si existe
            url_ticket = None
            juntada_uid = str(uuid.uuid4())
            if ticket_file:
                fname = f"ticket_{juntada_uid}.jpg"
                url_ticket = subir_imagen(ticket_file, fname)
                
            # Insertar Juntada
            supabase.table("juntadas").insert({
                "id": juntada_uid,
                "motivo": motivo,
                "monto_total": monto_total,
                "alias": alias,
                "foto_ticket_url": url_ticket
            }).execute()
            
            # Insertar Participantes
            datos_part = [{"juntada_id": juntada_uid, "nombre": nom} for nom in lista_nombres]
            supabase.table("participantes").insert(datos_part).execute()
            
            # Construir URL dinámica (reemplazar con tu URL real de Streamlit Cloud)
            # Ej: https://vaquita-express.streamlit.app/
            url_app_base = "https://tu-app-de-vaquitas.streamlit.app/" 
            link_compartir = f"{url_app_base}?evento={juntada_uid}"
            
            # Armar mensaje para WhatsApp
            cuota_individual = monto_total / len(lista_nombres)
            msg_wa = f"¡Buenas! Salió vaquita para *{motivo}* 💸\n\n"
            msg_wa += f"💰 *Cada uno pone:* ${cuota_individual:,.2f}\n"
            msg_wa += f"🔗 Entrá acá para ver el ticket, confirmar tu pago y subir el comprobante:\n{link_compartir}"
            
            msg_url = urllib.parse.quote(msg_wa)
            link_final_wa = f"https://wa.me/?text={msg_url}"
            
            st.success("¡Juntada guardada en Supabase con éxito!")
            st.markdown(f"### [📲 Compartir por WhatsApp]({link_final_wa})")
        else:
            st.error("Completá los montos y los integrantes de la juntada.")
