import streamlit as st
from docx import Document
from docx.shared import Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
import PyPDF2, io, re

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
def actualizar_cont(var, delta):
    st.session_state[var] = max(1, st.session_state[var] + delta)

# --- 3. LECTOR PDF ---
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

# --- 4. MOTOR DE REDACCIÓN (SINTAXIS CORREGIDA) ---
def generar_word(tipo, gral, ejecucion, fondo):
    doc = Document()
    style = doc.styles['Normal']
    style.font.name, style.font.size = 'Cambria', Pt(12)

    p_enc = doc.add_paragraph()
    p_enc.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    if tipo == "EXTINCIÓN":
        p_enc.add_run("EN LO PRINCIPAL: SOLICITA EXTINCIÓN;\nOTROSÍ: ACOMPAÑA DOCUMENTO.").bold = True
    else:
        p_enc.add_run("EN LO PRINCIPAL: Solicita Audiencia de Prescripción;\nOTROSÍ: Oficia a extranjería y se remita extracto de filiación y antecedentes.").bold = True

    doc.add_paragraph(f"\nJUZGADO DE GARANTÍA DE {gral['juz'].upper()}").bold = True

    rits_ej = ", ".join([f"{c['rit']} (RUC: {c['ruc']})" for c in ejecucion if c['rit']])
    intro = doc.add_paragraph()
    intro.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    intro.add_run(f"\n{gral['def'].upper()}, Defensor Penal Público, por {gral['suj'].upper()}, en causas de ejecución {rits_ej}, a US. con respeto digo:")

    cuerpo = doc.add_paragraph()
    cuerpo.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    if tipo == "EXTINCIÓN":
        cuerpo.add_run("\nQue, vengo en solicitar que declare la extinción de las sanciones de la Ley de Responsabilidad Penal Adolescente, en virtud del artículo 25 ter y 25 quinquies de la Ley 20.084.")
    else:
        cuerpo.add_run("\nQue, vengo en solicitar a S.S. se sirva fijar día y hora para celebrar audiencia con el objeto de debatir sobre la prescripción de la pena, de conformidad al artículo 5 de la Ley 20.084.")

    doc.add_paragraph("\nANTECEDENTES:").bold = True
    for i, c in enumerate(fondo):
        p_c = doc.add_paragraph(style='List Bullet')
        p_c.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        p_c.add_run(f"Causa RIT {c['rit']} (RUC {c['ruc']}) del {c['juz']}: ").bold = True
        if tipo == "EXTINCIÓN":
            p_c.add_run(f"Sanción consistente en {c['detalle']}.")
        else:
            p_c.add_run(f"Sentencia de fecha {c['f_sent']}, ejecutoriada con fecha {c['f_ejec']}. Ha operado el plazo legal.")

    doc.add_paragraph("\nPOR TANTO,").bold = True
    doc.add_paragraph("A US. PIDO: Acceder a lo solicitado por encontrarse ajustado a derecho.").bold = True
    
    if tipo == "PRESCRIPCIÓN":
        doc.add_paragraph("\nOTROSÍ:").bold = True
        doc.add_paragraph("Solicito se oficie a Extranjería y se incorpore Extracto de Filiación actualizado.")
        doc.add_paragraph("\nPOR TANTO, PIDO A US. acceder.").bold = True

    buf = io.BytesIO(); doc.save(buf); buf.seek(0)
    return buf

# --- 5. INTERFAZ ---
if check_auth():
    st.set_page_config(page_title="Generador IBL", layout="wide")
    
    if 'ne_e' not in st.session_state: st.session_state.ne_e = 1
    if 'nf_e' not in st.session_state: st.session_state.nf_e = 1
    if 'ne_p' not in st.session_state: st.session_state.ne_p = 1
    if 'nf_p' not in st
