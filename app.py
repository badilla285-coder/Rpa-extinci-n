import streamlit as st
from docx import Document
from docx.shared import Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
import PyPDF2, io, re, datetime

# --- CONFIGURACIÓN DE ACCESO ---
ADMIN_EMAIL = "badilla285@gmail.com"
USUARIOS_AUTORIZADOS = [ADMIN_EMAIL]

def check_auth():
    if "auth" not in st.session_state: st.session_state.auth = False
    if not st.session_state.auth:
        st.title("🔐 Acceso Restringido - Suite Ignacio Badilla")
        u = st.text_input("Correo Autorizado")
        p = st.text_input("Contraseña", type="password")
        if st.button("Ingresar"):
            if u in USUARIOS_AUTORIZADOS and p == "nacho2026":
                st.session_state.auth = True
                st.rerun()
            else: st.error("Acceso denegado.")
        return False
    return True

# --- FUNCIONES DE APOYO ---
def aumentar(tipo): st.session_state[tipo] += 1
def disminuir(tipo): 
    if st.session_state[tipo] > 1: st.session_state[tipo] -= 1

def extraer_info_pdf(archivo):
    d = {"ruc":"","rit":"","juz":"","san":"","f_sent":"","f_ejec":""}
    if archivo is None: return d
    try:
        reader = PyPDF2.PdfReader(archivo)
        texto = "".join([p.extract_text() for p in reader.pages])
        r_ruc = re.search(r"RUC:\s?(\d{7,10}-[\dkK])", texto)
        if r_ruc: d["ruc"] = r_ruc.group(1)
        r_rit = re.search(r"RIT:\s?([\d\w-]+-\d{4})", texto)
        if r_rit: d["rit"] = r_rit.group(1)
        r_juz = re.search(r"(Juzgado de Garantía de\s[\w\s]+)", texto, re.I)
        if r_juz: d["juz"] = r_juz.group(1).strip()
        r_san = re.search(r"(condena a|pena de|sanción de).*?(\d+\s(años|días|meses).*?)(?=\.)", texto, re.I|re.S)
        if r_san: d["san"] = r_san.group(0).replace("\n", " ").strip()
        fechas = re.findall(r"(\d{1,2}\sde\s\w+\sde\s\d{4})", texto)
        if len(fechas) >= 1: d["f_sent"] = fechas[0]
        if len(fechas) >= 2: d["f_ejec"] = fechas[1]
    except: pass
    return d

# --- MOTOR DE REDACCIÓN ---
def generar_word_completo(tipo, dg, cr, ca_o_presc):
    doc = Document()
    style = doc.styles['Normal']
    style.font.name, style.font.size = 'Cambria', Pt(12)
    
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    if tipo == "EXTINCION":
        p.add_run("EN LO PRINCIPAL: SOLICITA DECLARACIÓN DE EXTINCIÓN DE LA RESPONSABILIDAD PENAL POR CUMPLIMIENTO DE CONDENA EN CAUSAS RPA QUE INDICA;\nOTROSÍ: ACOMPAÑA DOCUMENTOS.").bold = True
    else:
        p.add_run("EN LO PRINCIPAL: Solicita Audiencia de Prescripción;\nOTROSÍ: Oficia a extranjería y se remita extracto de filiación y antecedentes.").bold = True
    
    doc.add_paragraph(f"\nS. J. DE GARANTÍA DE {dg['jp'].upper()}").bold = True
    
    rits_ej = ", ".join([f"{c['rit']} (RUC: {c['ruc']})" for c in dg['ej'] if c['rit']])
    p2 = doc.add_paragraph()
    p2.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p2.add_run(f"\n{dg['def'].upper()}, Defensor Penal Público, por {dg['ado'].upper()}, en causas de ejecución {rits_ej}, a US. con respeto digo:")
    
    if tipo == "EXTINCION":
        doc.add_paragraph("\nI. ANTECEDENTES DE LAS CAUSAS RPA:").bold = True
        for c in cr:
            if c.get('rit'):
                p_c = doc.add_paragraph(style='List Bullet')
                p_c.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
                p_c.add_run(f"Causa RIT {c['rit']} (RUC {c['ruc']}) del {c['juz']}: ").bold = True
                p_c.add_
