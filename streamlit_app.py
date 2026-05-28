import streamlit as st
from supabase import create_client, Client
from streamlit_local_storage import LocalStorage
import urllib.parse
import requests
import uuid

# Configuración de página
st.set_page_config(page_title="Vaquita Sullair", page_icon="🐄", layout="centered")

# CSS "Sullair Style"
st.markdown("""
    <style>
    .stApp { background: linear-gradient(135deg, #f0fdf4 0%, #ffffff 100%); }
    h1, h2, h3 { color: #00A335; }
    div.stButton > button { 
        background-color: #00A335 !important; color: white !important; 
        border-radius: 25px !important; border: none !important;
    }
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
        shortener_url = f"https://tinyurl.com/api-create.php?url={urllib.parse.quote(long_url)}"
        response = requests.get(shortener_url, timeout=5)
        return response.text if response.status_code == 200 and response.text.startswith("http") else long_url
    except: return long_url

def obtener_lista_local(key):
    res = local_storage.getItem(key)
    if not res: return []
    lista = res[key] if isinstance(res, dict) and key in res else res
    return [x.strip() for x in lista.split(",")] if isinstance(lista, str) else (lista if isinstance(lista, list) else [lista])

def guardar_en_lista_local(key, nuevo_id):
    actual = obtener_lista_local(key)
    if nuevo_id not in actual:
        actual.append(nuevo_id)
        local_storage.setItem(key, actual)

# Lógica principal
query_params = st.query_params
admin_id = query_params.get("admin")
evento_id = query_params.get("evento")

# --- VISTA 1: ADMIN ---
if admin_id:
    guardar_en_lista_local("mis_vaquitas_admin", admin_id)
    j = supabase.table("juntadas").select("*").eq("id", admin_id).execute().data[0]
    participantes = supabase.table("participantes").select("*").eq("juntada_id", admin_id).execute().data
    
    st.title("🐄 Panel Admin Sullair")
    st.info(f"💰 {j['motivo']} | Total: ${j['monto_total']:,.2f}")
    
    for p in participantes:
        if p['pago_confirmado']:
            with st.expander(f"✅ {p['nombre']}"):
                if p['comprobante_url']: st.image(p['comprobante_url'])
                if st.button(f"❌ Rechazar {p['nombre']}", key=f"rech_{p['id']}"):
                    supabase.table("participantes").update({"pago_confirmado": False, "comprobante_url": None}).eq("id", p['id']).execute()
                    st.rerun()
        else:
            st.write(f"⏳ {p['nombre']} (Debe)")
            
    st.divider()
    st.text_input("Link Invitado", value=acortar_link(f"{URL_BASE_APP}?evento={admin_id}"), disabled=True)
    if st.button("🗑️ Eliminar Vaquita"):
        supabase.table("juntadas").delete().eq("id", admin_id).execute()
        st.rerun()

# --- VISTA 2: INVITADO ---
elif evento_id:
    guardar_en_lista_local("mis_vaquitas_invitado", evento_id)
    j = supabase.table("juntadas").select("*").eq("id", evento_id).execute().data[0]
    p = supabase.table("participantes").select("*").eq("juntada_id", evento_id).execute().data
    
    st.title("🐄 Vaquita Sullair")
    nombre_user = st.selectbox("¿Quién sos?", [x['nombre'] for x in p])
    estado = next(item for item in p if item['nombre'] == nombre_user)
    
    if estado['pago_confirmado']:
        st.success("✅ ¡Gracias! Tu pago está confirmado.")
    else:
        comprobante = st.camera_input("Sacale foto al comprobante")
        if comprobante and st.button("Confirmar Pago"):
            supabase.table("participantes").update({"pago_confirmado": True}).eq("id", estado['id']).execute()
            st.rerun()

# --- VISTA 3: LOBBY ---
else:
    st.title("💸 Vaquita Express")
    tab1, tab2 = st.tabs(["📋 Mis Vaquitas", "🚀 Crear"])
    with tab1:
        admin_ids = obtener_lista_local("mis_vaquitas_admin")
        for j_id in admin_ids:
            st.write(f"👑 [Admin] Vaquita: {j_id}")
    with tab2:
        if st.button("Crear"): st.write("Lógica de creación...")
