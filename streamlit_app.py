import streamlit as st
from supabase import create_client, Client
from streamlit_local_storage import LocalStorage
import urllib.parse
import requests
import uuid

# Configuración de la página
st.set_page_config(page_title="Vaquita Express", page_icon="💸", layout="centered")

# Inicializar Supabase y LocalStorage
url: str = st.secrets["SUPABASE_URL"]
key: str = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)
local_storage = LocalStorage()

# Detectar parámetros en la URL
query_params = st.query_params
evento_id = query_params.get("evento")
admin_id = query_params.get("admin")

URL_BASE_APP = "https://calc-umple.streamlit.app/"

# Función para acortar links con Is.gd (rápido y sin tokens)
def acortar_link(long_url):
    try:
        shortener_url = f"https://is.gd/create.php?format=simple&url={urllib.parse.quote(long_url)}"
        response = requests.get(shortener_url, timeout=5)
        return response.text if response.status_code == 200 else long_url
    except:
        return long_url

# Función para subir imágenes al Storage público
def subir_imagen(file_buffer, file_name):
    try:
        bucket = "vaquita-comprobantes"
        supabase.storage.from_(bucket).upload(file_name, file_buffer.getvalue(), {"content-type": "image/jpeg"})
        return supabase.storage.from_(bucket).get_public_url(file_name)
    except Exception as e:
        st.error(f"Error al subir imagen: {e}")
        return None

# Helper para manejar listas en LocalStorage sin romper nada
def obtener_lista_local(key):
    lista = local_storage.get(key)
    if lista is None:
        return []
    if isinstance(lista, str):
        return [x.strip() for x in lista.split(",") if x.strip()]
    return list(lista)

def guardar_en_lista_local(key, nuevo_id):
    actual = obtener_lista_local(key)
    if nuevo_id not in actual:
        actual.append(nuevo_id)
        local_storage.set(key, actual)

# ==========================================
# VISTA 1: PANEL ADMIN
# ==========================================
if admin_id:
    # Guardamos este ID en el navegador del creador para que lo recuerde
    guardar_en_lista_local("mis_vaquitas_admin", admin_id)
    
    res_juntada = supabase.table("juntadas").select("*").eq("id", admin_id).execute()
    if not res_juntada.data:
        st.error("No se encontró esta operación.")
        st.stop()
        
    juntada = res_juntada.data[0]
    res_part = supabase.table("participantes").select("*").eq("juntada_id", admin_id).execute()
    participantes = res_part.data
    
    st.title(f"🕵️ Panel Admin: {juntada['motivo']}")
    st.write(f"**Total gastado:** ${juntada['monto_total']:,.2f} | **Alias:** `{juntada['alias']}`")
    
    if juntada['foto_ticket_url']:
        with st.expander("Ver ticket original"):
            st.image(juntada['foto_ticket_url'])
            
    st.divider()
    st.subheader("Control de pagos")
    
    for p in participantes:
        if p['pago_confirmado']:
            with st.expander(f"✅ {p['nombre']} (Pagó)"):
                if p['comentario']: st.write(f"💬 *\"{p['comentario']}\"*")
                if p['comprobante_url']:
                    st.image(p['comprobante_url'], caption=f"Comprobante de {p['nombre']}")
                else:
                    st.caption("Confirmó sin subir foto.")
        else:
            st.write(f"⏳ **{p['nombre']}** - Todavía debe")

# ==========================================
# VISTA 2: INVITADO / RENDIJO DE PAGO
# ==========================================
elif evento_id:
    # Guardamos este ID en el navegador del invitado para su historial
    guardar_en_lista_local("mis_vaquitas_invitado", evento_id)
    
    res_juntada = supabase.table("juntadas").select("*").eq("id", evento_id).execute()
    if not res_juntada.data:
        st.error("Juntada no encontrada.")
        st.stop()
        
    juntada = res_juntada.data[0]
    res_part = supabase.table("participantes").select("*").eq("juntada_id", evento_id).execute()
    participantes = res_part.data
    
    st.title(f"💸 Vaquita: {juntada['motivo']}")
    cuota = juntada['monto_total'] / len(participantes)
    
    col1, col2 = st.columns(2)
    col1.metric("Total General", f"${juntada['monto_total']:,.2f}")
    col2.metric("Tu Parte", f"${cuota:,.2f}")
    
    st.info(f"🏦 **Transferí al alias/CBU:** `{juntada['alias']}`")
    
    if juntada['foto_ticket_url']:
        with st.expander("📸 Ver Ticket de la Compra"):
            st.image(juntada['foto_ticket_url'])
            
    st.divider()
    st.subheader("¿Quién ya aportó?")
    for p in participantes:
        icon = "✅" if p['pago_confirmado'] else "⏳"
        st.write(f"{icon} **{p['nombre']}**")
        
    st.divider()
    
    # Formulario dinámico: solo deudores
    deudores = [p['nombre'] for p in participantes if not p['pago_confirmado']]
    if deudores:
        st.subheader("✍️ Informar mi pago")
        usuario_selec = st.selectbox("Seleccioná tu nombre", deudores)
        comentario = st.text_input("Comentario (opcional)", "¡Listo, transferido!")
        
        if 'cam_usuario' not in st.session_state: st.session_state.cam_usuario = False
        if st.button("📸 Adjuntar Comprobante"): st.session_state.cam_usuario = not st.session_state.cam_usuario
            
        comprobante_file = st.camera_input("Foto de la pantalla o ticket de transferencia") if st.session_state.cam_usuario else None
        
        if st.button("Confirmar Pago 🚀", type="primary"):
            url_comp = subir_imagen(comprobante_file, f"comp_{evento_id}_{uuid.uuid4().hex}.jpg") if comprobante_file else None
            
            supabase.table("participantes").update({
                "pago_confirmado": True,
                "comentario": comentario,
                "comprobante_url": url_comp
            }).eq("juntada_id", evento_id).eq("nombre", usuario_selec).execute()
            
            st.success("¡Pago registrado! Ya te tachamos de la lista.")
            st.rerun()
    else:
        st.balloons()
        st.success("🎉 ¡Espectacular! Esta vaquita ya está completamente cobrada.")

# ==========================================
# VISTA 3: LOBBY PRIVADO / CREACIÓN
# ==========================================
else:
    st.title("💸 Vaquita Express")
    st.write("Gestioná tus gastos compartidos al toque.")
    
    tab_mis_cosas, tab_nueva = st.tabs(["📋 Mis Juntadas", "🚀 Crear Nueva Vaquita"])
    
    with tab_mis_cosas:
        st.subheader("Tu historial en este dispositivo")
        
        # Leemos la memoria del navegador de este usuario en particular
        admin_ids = obtener_lista_local("mis_vaquitas_admin")
        invitado_ids = obtener_lista_local("mis_vaquitas_invitado")
        
        any_data = False
        
        if admin_ids:
            any_data = True
            st.write("👑 **Vaquitas que vos armaste:**")
            res_admin = supabase.table("juntadas").select("id", "motivo").in_("id", admin_ids).execute()
            for j in res_admin.data:
                st.markdown(f"- [{j['motivo']}]({URL_BASE_APP}?admin={j['id']}) *(Panel de Control)*")
                
        if invitado_ids:
            any_data = True
            st.write("🧑‍🤝‍🧑 **Vaquitas en las que colaborás:**")
            res_inv = supabase.table("juntadas").select("id", "motivo").in_("id", invitado_ids).execute()
            for j in res_inv.data:
                st.markdown(f"- [{j['motivo']}]({URL_BASE_APP}?evento={j['id']}) *(Ver estado / Pagar)*")
                
        if not any_data:
            st.info("No tenés vaquitas registradas en este celu/navegador todavía. ¡Armá una en la otra pestaña!")
            
    with tab_nueva:
        st.subheader("Crear nueva operación")
        motivo = st.text_input("¿Qué se compró?", "Cumple Manolo")
        monto_total = st.number_input("Monto Total ($)", min_value=0.0, step=500.0)
        alias = st.text_input("Alias o CBU de destino", "JAVI.CENCO.MP")
        
        if 'cam_creador' not in st.session_state: st.session_state.cam_creador = False
        if st.button("📸 Sacar foto al ticket de compra"): st.session_state.cam_creador = not st.session_state.cam_creador
        ticket_file = st.camera_input("Enfocá la factura") if st.session_state.cam_creador else None
        
        participantes_str = st.text_area("Integrantes (separados por coma)", "Franco, Edu, Javi, Fede, JP, Caro, Mati, Andre, Anto, Vane")
        
        if st.button("🚀 Generar Vaquita", type="primary"):
            if monto_total > 0 and participantes_str:
                lista_nombres = [n.strip() for n in participantes_str.split(",") if n.strip()]
                juntada_uid = str(uuid.uuid4())
                
                # Subir ticket si se capturó
                url_ticket = subir_imagen(ticket_file, f"ticket_{juntada_uid}.jpg") if ticket_file else None
                
                # Insertar en base de datos
                supabase.table("juntadas").insert({
                    "id": juntada_uid, "motivo": motivo, "monto_total": monto_total,
                    "alias": alias, "foto_ticket_url": url_ticket
                }).execute()
                
                datos_part = [{"juntada_id": juntada_uid, "nombre": nom} for nom in lista_nombres]
                supabase.table("participantes").insert(datos_part).execute()
                
                # Generar links reales
                link_evento_largo = f"{URL_BASE_APP}?evento={juntada_uid}"
                link_admin_largo = f"{URL_BASE_APP}?admin={juntada_uid}"
                
                # Guardar en local storage del creador en el acto
                guardar_en_lista_local("mis_vaquitas_admin", juntada_uid)
                
                # Acortar link para WhatsApp
                link_evento_corto = acortar_link(link_evento_largo)
                
                # Formatear mensaje de WhatsApp
                cuota = monto_total / len(lista_nombres)
                msg_wa = f"¡Buenas! Salió vaquita para *{motivo}* 💸\n\n💰 *Cada uno pone:* ${cuota:,.2f}\n🔗 Entrá acá para ver el ticket y confirmar tu pago:\n{link_evento_corto}"
                link_wa_final = f"https://wa.me/?text={urllib.parse.quote(msg_wa)}"
                
                st.success("¡Operación creada con éxito!")
                st.markdown(f"### 📲 [Enviar al grupo de WhatsApp]({link_wa_final})")
                
                st.warning("🔒 **Tu link de Admin:** Se guardó automáticamente en la pestaña 'Mis Juntadas' de este dispositivo, pero por las dudas te lo dejo acá:")
                st.code(link_admin_largo)
            else:
                st.error("Por favor, completá el monto y poné al menos un integrante.")
