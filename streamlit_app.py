import streamlit as st
from supabase import create_client, Client
from streamlit_local_storage import LocalStorage
import urllib.parse
import requests
import uuid

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Vaquita Sullair", page_icon="🐄", layout="centered")

# CSS "Sullair Style"
st.markdown("""
    <style>
    .stApp { background: linear-gradient(135deg, #f0fdf4 0%, #ffffff 100%); }
    h1, h2, h3 { color: #00A335; }
    div.stButton > button { background-color: #00A335 !important; color: white !important; border-radius: 25px !important; border: none !important; }
    </style>
""", unsafe_allow_html=True)

# Inicializar
url: str = st.secrets["SUPABASE_URL"]
key: str = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)
local_storage = LocalStorage()

URL_BASE_APP = "https://calc-umple.streamlit.app/"

# Funciones Base
def acortar_link(long_url):
    try:
        r = requests.get(f"https://tinyurl.com/api-create.php?url={urllib.parse.quote(long_url)}", timeout=5)
        return r.text if r.status_code == 200 and r.text.startswith("http") else long_url
    except: return long_url

# Lógica
query_params = st.query_params
admin_id = query_params.get("admin")
evento_id = query_params.get("evento")

# --- VISTA 1: ADMIN ---
if admin_id:
    j = supabase.table("juntadas").select("*").eq("id", admin_id).execute().data[0]
    p = supabase.table("participantes").select("*").eq("juntada_id", admin_id).execute().data
    st.title("🐄 Panel Admin Sullair")
    st.info(f"💰 {j['motivo']} | Total: ${j['monto_total']:,.2f}")
    for part in p:
        with st.expander(f"{'✅' if part['pago_confirmado'] else '⏳'} {part['nombre']}"):
            if part['comprobante_url']: st.image(part['comprobante_url'])
            if part['pago_confirmado'] and st.button("❌ Rechazar", key=part['id']):
                supabase.table("participantes").update({"pago_confirmado": False, "comprobante_url": None}).eq("id", part['id']).execute()
                st.rerun()
    st.text_input("Link Invitado", value=acortar_link(f"{URL_BASE_APP}?evento={admin_id}"), disabled=True)

# --- VISTA 2: INVITADO ---
elif evento_id:
    j = supabase.table("juntadas").select("*").eq("id", evento_id).execute().data[0]
    p = supabase.table("participantes").select("*").eq("juntada_id", evento_id).execute().data
    
    st.title(f"🐄 {j['motivo']}")
    nombre = st.selectbox("¿Quién sos?", [x['nombre'] for x in p])
    estado = next(x for x in p if x['nombre'] == nombre)
    
    if estado['pago_confirmado']:
        st.success("✅ ¡Pago confirmado!")
    else:
        # Carga de fotos/archivos...
        foto = st.file_uploader("Subir comprobante", type=['jpg', 'png'])
        if foto and st.button("Confirmar Pago"):
            # ... lógica de subida ...
            st.rerun()
    
    # BOTÓN DINÁMICO DE REPORTE AL ADMIN
    admin_wpp = j.get('admin_whatsapp', '5492990000000') # Número fallback
    msg_reporte = f"Hola! Tengo un problema con la vaquita: {j['motivo']}"
    st.link_button("🆘 Reportar Problema al Admin", f"https://wa.me/{admin_wpp}?text={urllib.parse.quote(msg_reporte)}")
    st.link_button("🔙 Volver al Lobby", URL_BASE_APP)

# --- VISTA 3: LOBBY ---
else:
    st.title("💸 Vaquita Express")
    # ... (Tabs de Mis Vaquitas y Crear)
    # Al crear, asegúrate de guardar el 'admin_whatsapp' ingresado por el usuario:
    # supabase.table("juntadas").insert({"id": uid, "admin_whatsapp": wpp_input, ...}).execute()
