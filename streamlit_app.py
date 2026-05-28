import streamlit as st
from supabase import create_client, Client
from streamlit_local_storage import LocalStorage
import urllib.parse
import requests
import uuid
import base64

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Vaquita Sulleriana", page_icon="🐄", layout="centered")

# Función para convertir la imagen local vq_slr.png a Base64 e inyectarla como fondo mosaico
def cargar_fondo_mosaico():
    try:
        with open("vq_slr.png", "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode()
        return f"""
        <style>
        /* Fondo principal */
        .stApp {{
            background-image: url("data:image/png;base64,{encoded_string}");
            background-repeat: repeat;
            background-size: 400px; 
            background-attachment: fixed;
        }}
        
        /* HACEMOS TRANSPARENTE EL BLOQUE CENTRAL */
        section[data-testid="stSidebar"] {{
            background-color: rgba(255, 255, 255, 0.8);
        }}
        
        .block-container {{
            background-color: rgba(255, 255, 255, 0.85); /* Un poquito transparente para que se vean las vaquitas atrás */
            padding: 2rem !important;
            border-radius: 20px;
            border: 1px solid #00A335;
        }}
        </style>
        """
    except:
        return ""

st.markdown(cargar_fondo_mosaico(), unsafe_allow_html=True)

# --- INICIALIZAR SUPABASE Y LOCALSTORAGE ---
url: str = st.secrets["SUPABASE_URL"]
key: str = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)
local_storage = LocalStorage()

# Detectar parámetros en la URL
query_params = st.query_params
evento_id = query_params.get("evento")
admin_id = query_params.get("admin")

URL_BASE_APP = "https://calc-umple.streamlit.app/"

# --- FUNCIONES AUXILIARES ---
def acortar_link(long_url):
    try:
        shortener_url = f"https://tinyurl.com/api-create.php?url={urllib.parse.quote(long_url)}"
        response = requests.get(shortener_url, timeout=5)
        if response.status_code == 200 and response.text.startswith("http"):
            return response.text
        return long_url
    except:
        return long_url

def subir_imagen(file_buffer, file_name):
    try:
        bucket = "vaquita-comprobantes"
        supabase.storage.from_(bucket).upload(file_name, file_buffer.getvalue(), {"content-type": "image/jpeg"})
        return supabase.storage.from_(bucket).get_public_url(file_name)
    except Exception as e:
        st.error(f"Error al subir imagen: {e}")
        return None

def obtener_lista_local(key):
    resultado = local_storage.getItem(key)
    if not resultado:
        return []
    if isinstance(resultado, dict) and key in resultado:
        lista = resultado[key]
    else:
        lista = resultado
    if isinstance(lista, str):
        return [x.strip() for x in lista.split(",") if x.strip()]
    elif isinstance(lista, list):
        return lista
    return [lista]

def guardar_en_lista_local(key, nuevo_id):
    actual = obtener_lista_local(key)
    if nuevo_id not in actual:
        actual.append(nuevo_id)
        local_storage.setItem(key, actual)


# ==========================================
# VISTA 1: PANEL ADMIN
# ==========================================
if admin_id:
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
                
                # BOTÓN DE RECHAZO (Para volverlo a poner como deudor)
                if st.button(f"❌ Rechazar Pago de {p['nombre']}", key=f"rech_{p['id']}"):
                    supabase.table("participantes").update({
                        "pago_confirmado": False, 
                        "comprobante_url": None,
                        "comentario": "Rechazado por el Admin"
                    }).eq("id", p['id']).execute()
                    st.success(f"Pago de {p['nombre']} rechazado.")
                    st.rerun()
        else:
            st.write(f"⏳ **{p['nombre']}** - Todavía debe")
    
    st.divider()
    st.subheader("🔗 Gestión y Reenvío de Links")
    link_invitado_corto = acortar_link(f"{URL_BASE_APP}?evento={admin_id}")
    st.text_input("Link de Admin (Para seguirlo desde la PC - ¡No compartir!)", value=f"{URL_BASE_APP}?admin={admin_id}", disabled=True)
    st.text_input("Link de Invitados (Para pasar por el grupo)", value=link_invitado_corto, disabled=True)
    
    st.divider()
    st.subheader("⚠️ Zona de Peligro")
    if st.button("🗑========= ELIMINAR ESTA VAQUITA =========", type="primary", use_container_width=True):
        supabase.table("juntadas").delete().eq("id", admin_id).execute()
        mis_v = obtener_lista_local("mis_vaquitas_admin")
        if admin_id in mis_v:
            mis_v.remove(admin_id)
            local_storage.setItem("mis_vaquitas_admin", mis_v)
        st.success("¡Vaquita eliminada con éxito!")
        st.stop()


# ==========================================
# VISTA 2: INVITADO / RENDIJO DE PAGO
# ==========================================
elif evento_id:
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
    
    # Comprobar estado dinámico según el nombre seleccionado
    st.subheader("✍️ Informar mi pago")
    todos_nombres = [p['nombre'] for p in participantes]
    usuario_selec = st.selectbox("Seleccioná tu nombre", todos_nombres)
    estado_usuario = next(p for p in participantes if p['nombre'] == usuario_selec)
    
    if estado_usuario['pago_confirmado']:
        st.success("✅ ¡Tu pago ya fue registrado y confirmado para este evento!")
    else:
        comentario = st.text_input("Comentario (opcional)", "¡Listo, transferido!")
        
        # CHICHE: Elegir entre cámara o archivo local de galería
        origen_comp = st.radio("¿Cómo vas a subir el comprobante?", ["📁 Subir Archivo / Captura", "📸 Sacar Foto en Vivo"])
        
        comprobante_file = None
        if origen_comp == "📸 Sacar Foto en Vivo":
            comprobante_file = st.camera_input("Foto de la pantalla o ticket")
        else:
            comprobante_file = st.file_uploader("Elegí el comprobante desde tus archivos", type=["jpg", "jpeg", "png"])
        
        if st.button("Confirmar Pago 🚀", type="primary"):
            url_comp = subir_imagen(comprobante_file, f"comp_{evento_id}_{uuid.uuid4().hex}.jpg") if comprobante_file else None
            
            supabase.table("participantes").update({
                "pago_confirmado": True,
                "comentario": comentario,
                "comprobante_url": url_comp
            }).eq("id", estado_usuario['id']).execute()
            
            st.success("¡Pago registrado! El Administrador ya puede auditarlo.")
            st.rerun()
            
    # BOTONES DE SOPORTE Y NAVEGACIÓN
    st.divider()
    col_back, col_report = st.columns(2)
    with col_back:
        st.link_button("Toque acá para ir al lobby principal", URL_BASE_APP)
    with col_report:
        admin_wpp = juntada.get('admin_whatsapp', '549299000000') # Respaldo por si viene vacío
        msg_wpp = f"Hola! Tengo un problema para rendir el pago en la vaquita *{juntada['motivo']}*."
        link_soporte = f"https://wa.me/{admin_wpp}?text={urllib.parse.quote(msg_wpp)}"
        st.link_button("Avisarle al Admin por un problema", link_soporte)


# ==========================================
# VISTA 3: LOBBY PRIVADO / CREACIÓN
# ==========================================
else:
    st.title("💸 Vaquita Express")
    st.write("Gestioná tus gastos compartidos al toque.")
    
    tab_mis_cosas, tab_nueva = st.tabs(["📋 Mis Vaquitas", "🚀 Crear Nueva Vaquita"])
    
    with tab_mis_cosas:
        st.subheader("Tu historial en este dispositivo")
        
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
        motivo = st.text_input("¿Qué se compró?", "Cumple/Morfi/Cosa para repartir")
        monto_total = st.number_input("Monto Total ($)", min_value=0.0, step=500.0)
        alias = st.text_input("Alias o CBU de destino", "TU.ALIAS.MP")
        wpp_admin = st.text_input("Tu Nro WhatsApp (Ej: 5492994123456 - Clave para reportes)", "549")
        
        if 'cam_creador' not in st.session_state: st.session_state.cam_creador = False
        if st.button("📸 Sacar foto al ticket de compra"): st.session_state.cam_creador = not st.session_state.cam_creador
        ticket_file = st.camera_input("Enfocá la factura") if st.session_state.cam_creador else None
        
        participantes_str = st.text_area("Integrantes (separados por coma)", "Sullerio, Sullerita, Sullerión")
        
        if st.button("🚀 Generar Vaquita", type="primary"):
            if monto_total > 0 and participantes_str and wpp_admin != "549":
                lista_nombres = [n.strip() for n in participantes_str.split(",") if n.strip()]
                juntada_uid = str(uuid.uuid4())
                
                url_ticket = subir_imagen(ticket_file, f"ticket_{juntada_uid}.jpg") if ticket_file else None
                
                supabase.table("juntadas").insert({
                    "id": juntada_uid, "motivo": motivo, "monto_total": monto_total,
                    "alias": alias, "foto_ticket_url": url_ticket, "admin_whatsapp": wpp_admin
                }).execute()
                
                datos_part = [{"juntada_id": juntada_uid, "nombre": nom} for nom in lista_nombres]
                supabase.table("participantes").insert(datos_part).execute()
                
                link_evento_largo = f"{URL_BASE_APP}?evento={juntada_uid}"
                link_admin_largo = f"{URL_BASE_APP}?admin={juntada_uid}"
                
                guardar_en_lista_local("mis_vaquitas_admin", juntada_uid)
                link_evento_corto = acortar_link(link_evento_largo)
                
                cuota = monto_total / len(lista_nombres)
                msg_wa = f"¡Buenas! Salió vaquita para *{motivo}* 💸\n\n💰 *Cada uno pone:* ${cuota:,.2f}\n🔗 Entrá acá para ver el ticket y confirmar tu pago:\n{link_evento_corto}"
                link_wa_final = f"https://wa.me/?text={urllib.parse.quote(msg_wa)}"
                
                st.success("¡Operación creada con éxito!")
                st.markdown(f"### 📲 [Enviar al grupo de WhatsApp]({link_wa_final})")
                
                st.warning("🔒 **Tu link de Admin:** Se guardó en la pestaña 'Mis Vaquitas', pero agendalo por seguridad:")
                st.code(link_admin_largo)
            else:
                st.error("Che, completá el monto, integrantes y poné tu número de WhatsApp válido.")

# --- PIE DE PÁGINA ---
st.markdown('<div class="footer">Hecho con 💚 por Fede GC para los Sullerianos - 2026©</div>', unsafe_allow_html=True)
