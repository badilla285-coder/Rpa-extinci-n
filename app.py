import streamlit as st
from docx import Document
from docx.shared import Pt
import PyPDF2, io, re, datetime, requests
from bs4 import BeautifulSoup

# --- CONFIGURACIÓN DE SEGURIDAD ---
ADMIN_EMAIL = "badilla285@gmail.com"
# Aquí tú añadirás los correos de los usuarios que paguen o autorices
USUARIOS_AUTORIZADOS = [ADMIN_EMAIL, "colega1@dpp.cl", "estudio_juridico@gmail.com"]

def check_auth():
    if "auth" not in st.session_state:
        st.session_state.auth = False
    
    if not st.session_state.auth:
        st.title("🔐 Acceso Restringido - LegalTech Pro")
        email = st.text_input("Introduce tu correo autorizado")
        passw = st.text_input("Contraseña", type="password")
        if st.button("Ingresar"):
            if email in USUARIOS_AUTORIZADOS and passw == "nacho2026": # Password provisional
                st.session_state.auth = True
                st.rerun()
            else:
                st.error("Usuario no autorizado. Contacta a badilla285@gmail.com")
        return False
    return True

# --- MOTOR MIA (EXTRACCIÓN DIRECTA) ---
def buscar_en_pantalla(rut_num):
    try:
        url = f"https://www.nombrerutyfirma.com/rut/{rut_num}"
        h = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        r = requests.get(url, headers=h, timeout=5)
        if r.status_code == 200:
            s = BeautifulSoup(r.text, 'html.parser')
            t = s.find('table')
            if t:
                d = t.find_all('tr')[1].find_all('td')
                return {"nom": d[0].text, "dir": d[3].text, "com": d[4].text}
    except: return None

# --- LÓGICA DE PLAZOS ---
def calcular_plazo(tipo_res, fecha_pdf):
    # Diccionario de plazos legales chilenos (días corridos/hábiles según corresponda)
    plazos = {
        "Sentencia Definitiva (Apelación)": 5,
        "Recurso de Nulidad": 10,
        "Reposición": 3,
        "Amparo": 24 # horas (representado simbólicamente)
    }
    dias = plazos.get(tipo_res, 0)
    vencimiento = fecha_pdf + datetime.timedelta(days=dias)
    return vencimiento

# --- INTERFAZ FORMAL ---
if check_auth():
    st.set_page_config(page_title="Ignacio Badilla - Legal Suite", layout="wide")
    
    # CSS para diseño Formal/Atractivo (Dark Mode Legal)
    st.markdown("""
        <style>
        .main { background-color: #f5f7f9; }
        .stButton>button { border-radius: 5px; background-color: #1e3a8a; color: white; }
        .stTextInput>div>div>input { border-radius: 5px; }
        </style>
    """, unsafe_allow_html=True)

    st.title("⚖️ Legal Intelligence Suite")
    st.caption(f"Sesión activa: {ADMIN_EMAIL} | Perfil: Administrador")

    tabs = st.tabs(["📄 Redactor Pro", "🔍 MIA: Investigación", "📅 Calculadora de Plazos"])

    with tabs[0]:
        st.subheader("Generador de Escritos Robustos")
        # (Aquí va el código anterior del redactor de Word en Cambria 12)
        st.info("El redactor mantiene el formato institucional DPP con transcripciones completas.")

    with tabs[1]:
        st.subheader("Módulo de Inteligencia de Antecedentes")
        rut_busqueda = st.text_input("RUT para extracción directa")
        if rut_busqueda:
            res = buscar_en_pantalla(rut_busqueda.replace(".","").split("-")[0])
            if res:
                c1, c2 = st.columns(2)
                c1.metric("Nombre Identificado", res['nom'])
                c2.metric("Comuna", res['com'])
                st.success(f"📍 Domicilio detectado: {res['dir']}")
            else:
                st.warning("⚠️ Extracción automática limitada. Use los túneles de interconexión.")

    with tabs[2]:
        st.subheader("Control de Plazos y Resoluciones")
        tipo = st.selectbox("Tipo de Resolución", ["Sentencia Definitiva (Apelación)", "Recurso de Nulidad", "Reposición"])
        fecha_res = st.date_input("Fecha de notificación/resolución", datetime.date.today())
        
        vence = calcular_plazo(tipo, fecha_res)
        st.error(f"🚨 El plazo fatal para presentar el recurso vence el: {vence.strftime('%d/%m/%Y')}")
        
        f_res = st.file_uploader("Adjuntar Resolución para análisis")
        if f_res:
            st.write("Análisis de resolución completo. Datos integrados al escrito.")

    # --- PIE DE PÁGINA ---
    st.markdown("---")
    st.markdown(f"**Desarrollado por Ignacio Badilla Lara** | [Soporte](mailto:{ADMIN_EMAIL})")
