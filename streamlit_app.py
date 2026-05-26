import streamlit as st
import urllib.parse

# Configuración básica de la página
st.set_page_config(page_title="Vaquita Express", page_icon="💸", layout="centered")

st.title("💸 Vaquita Express")
st.write("Calculá y repartí los gastos al toque.")

st.divider()

# Sección 1: Datos de la compra
st.subheader("1. El Ticket")
monto_total = st.number_input("Monto Total ($)", min_value=0.0, step=1000.0, format="%.2f")
motivo = st.text_input("¿Qué compramos?", "Ej: Cumple Manolo")
alias = st.text_input("Alias o CBU para transferir", "JAVI.CENCO.MP")

# Cámara nativa (en Android te va a abrir la cámara del celu directamente)
foto_ticket = st.camera_input("Sacale foto al comprobante (opcional)")

st.divider()

# Sección 2: Participantes
st.subheader("2. Los Integrantes")
participantes_str = st.text_area(
    "Nombres (separalos por coma)", 
    "Franco, Edu, Javi, Fede, JP, Caro, Mati, Andre, Anto, Vane"
)

# Limpiamos la lista sacando espacios vacíos
participantes = [p.strip() for p in participantes_str.split(",") if p.strip()]

st.divider()

# Sección 3: Cálculo y Compartir
if st.button("Calcular y armar mensaje", type="primary"):
    if len(participantes) > 0 and monto_total > 0:
        cuota = monto_total / len(participantes)
        
        st.success(f"Total: ${monto_total:,.2f} | Cada uno pone: **${cuota:,.2f}**")
        
        # Armamos el texto para WhatsApp
        mensaje = f"¡Buenas! Hicimos la vaquita para: *{motivo}* 💸\n\n"
        mensaje += f"💰 *Total gastado:* ${monto_total:,.2f}\n"
        mensaje += f"🧑‍🤝‍🧑 *Somos {len(participantes)}:* nos toca poner *${cuota:,.2f}* a cada uno.\n"
        mensaje += f"🏦 *Transfieran al alias:* {alias}\n\n"
        mensaje += "Integrantes:\n" + ", ".join(participantes)
        
        # Generamos el link con el texto encodeado para la URL
        mensaje_url = urllib.parse.quote(mensaje)
        link_wa = f"https://wa.me/?text={mensaje_url}"
        
        # Botón estilo enlace para abrir WhatsApp directo
        st.markdown(f"### [📲 Compartir por WhatsApp]({link_wa})")
        
    else:
        st.error("Che, poné un monto mayor a 0 y al menos un participante.")
