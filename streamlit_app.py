import streamlit as st
from supabase import create_client, Client
from streamlit_local_storage import LocalStorage
import urllib.parse
import requests
import uuid

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Vaquita Sulleriana", page_icon="🐄", layout="centered")

st.markdown("""
    <style>
    .stApp { background: linear-gradient(135deg, #f0fdf4 0%, #ffffff 100%); }
    h1, h2, h3 { color: #00A335; }
    div.stButton > button { background-color: #00A335 !important; color: white !important; border-radius: 25px !important; border: none !important; }
    .footer { text-align: center; color: #00A335; font-size: 0.8em; font-weight: bold; margin-top: 50px; }
    </style>
""", unsafe_allow_html=True)

# --- INICIALIZACIÓN ---
url: str = st.secrets["SUPABASE_URL"]
key: str = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)
local_storage = LocalStorage()
URL_BASE_APP = "https://calc-umple.streamlit.app/"

# --- FUNCIONES ---
def acortar_link(long_url):
    try:
        r = requests.get(f"https://tinyurl.com/api-create.php?url={urllib.parse.quote(long_url)}", timeout=5)
        return r.text if r.status_code == 200 and r.text.startswith("http") else long_url
    except: return long_url

def subir_imagen(file_buffer, file_name):
    try:
        supabase.storage.from_("vaquita-comprobantes").upload(file_name, file_buffer.getvalue(), {"content-type": "image/jpeg"})
        return supabase.storage.from_("vaquita-comprobantes").get_public_url(file_name)
    except: return None

def obtener_lista_local(key):
    res = local_storage.getItem(key)
    if not res: return []
    lista = res.get(key) if isinstance(res, dict) else res
    return lista if isinstance(lista, list) else [lista]

# --- LÓGICA ---
query_params = st.query_params
admin_id = query_params.get("admin")
evento_id = query_params.get("evento")

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
    st.divider()
    admin_whatsapp = st.text_input("Tu número de WhatsApp (para que te reporten problemas)", "549299XXXXXXX")
    st.text_input("Link Invitado", value=acortar_link(f"{URL_BASE_APP}?evento={admin_id}"), disabled=True)
    if st.button("🗑️ Eliminar Vaquita"):
        supabase.table("juntadas").delete().eq("id", admin_id).execute()
        st.rerun()

elif evento_id:
    j = supabase.table("juntadas").select("*").eq("id", evento_id).execute().data[0]
    p = supabase.table("participantes").select("*").eq("juntada_id", evento_id).execute().data
    st.title(f"🐄 {j['motivo']}")
    nombre = st.selectbox("¿Quién sos?", [x['nombre'] for x in p])
    estado = next(x for x in p if x['nombre'] == nombre)
    if estado['pago_confirmado']:
        st.success("✅ ¡Pago confirmado!")
    else:
        metodo = st.radio("Carga de comprobante", ["Cámara", "Archivo"])
        foto = st.camera_input("Sacar foto") if metodo == "Cámara" else st.file_uploader("Subir archivo")
        if foto and st.button("Confirmar Pago"):
            url_img = subir_imagen(foto, f"{uuid.uuid4()}.jpg")
            supabase.table("participantes").update({"pago_confirmado": True, "comprobante_url": url_img}).eq("id", estado['id']).execute()
            st.rerun()
    st.link_button("🔙 Volver al Lobby", URL_BASE_APP)
admin_wpp = j.get('admin_whatsapp', 'tu_numero_predeterminado')
st.link_button("🆘 Reportar Problema al Admin", f"https://wa.me/{admin_wpp}?text=Hola!%20Tengo%20un%20problema%20con%20la%20vaquita:%20{j['motivo']}")
else:
    st.title("💸 Vaquita Express")
    tab1, tab2 = st.tabs(["📋 Mis Vaquitas", "🚀 Crear"])
    with tab1:
        admin_ids = obtener_lista_local("mis_vaquitas_admin")
        for i in admin_ids: st.write(f"👑 [Vaquita]({URL_BASE_APP}?admin={i})")
    with tab2:
        motivo = st.text_input("Motivo")
        monto = st.number_input("Total", step=500.0)
        nombres = st.text_area("Integrantes (separados por coma)")
        if st.button("Generar"):
            uid = str(uuid.uuid4())
            supabase.table("juntadas").insert({"id": uid, "motivo": motivo, "monto_total": monto}).execute()
            st.success("¡Creada!")

st.markdown('<div class="footer">Hecho con 💚 por Fede GC para los Sullerianos - 2026©</div>', unsafe_allow_html=True)
