import streamlit as st
from docx import Document
from docx.shared import Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
import PyPDF2, io, re, datetime

# --- 1. SEGURIDAD ---
ADMIN_EMAIL = "badilla285@gmail.com"
USUARIOS_AUTORIZADOS = [ADMIN_EMAIL]

def check_auth():
    if "auth" not in st.session_state: st.session_state.auth = False
    if not st.session_state.auth:
        st.title("🔐 Acceso - Generador IBL")
        u = st.text_input("Correo Autorizado")
        p = st.text_input("Contraseña", type="password")
        if st.button("Ingresar"):
            if u in USUARIOS_AUTORIZADOS and p == "nacho2026":
                st.session_state.auth = True
                st.rerun()
            else: st.error("Acceso denegado.")
        return False
    return True

# --- 2. LÓGICA DE CONTADORES ---
def cambiar_cont(var, delta):
    st.session_state[var] = max(1, st.session_state[var] + delta)

# --- 3. LECTOR PDF (AUTOMATIZACIÓN) ---
def leer_pdf(archivo):
    d = {"ruc": "", "rit": "", "juz": "", "san": "", "f_sent": "", "f_ejec": ""}
    if archivo:
        try:
            reader = PyPDF2.PdfReader(archivo)
            texto = "".join([p.extract_text() for p in reader.pages])
            r_ruc = re.search(r"RUC:\s?(\d{7,10}-[\dkK])", texto)
            if r_ruc: d["ruc"] = r_ruc.group(1)
            r_rit = re.search(r"RIT:\s?([\d\w-]+-\d{4})", texto)
            if r_rit: d["rit"] = r_rit.group(1)
            r_juz = re.search(r"(Juzgado de Garantía de\s[\w\s]+)", texto, re.I)
            if r_juz: d["juz"] = r_juz.group(1).strip()
            fechas = re.findall(r"(\d{1,2}\sde\s\w+\sde\s\d{4})", texto)
            if len(fechas) >= 1: d["f_sent"] = fechas[0]
            if len(fechas) >= 2: d["f_ejec"] = fechas[1]
        except: pass
    return d

# --- 4. MOTOR DE REDACCIÓN ---
def generar_word(tipo, gral, ejecucion
