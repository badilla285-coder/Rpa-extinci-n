import streamlit as st
from docx import Document
from docx.shared import Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
import PyPDF2
import io
import re
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options

# --- 1. MOTOR SELENIUM ---
def configurar_driver():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.binary_location = "/usr/bin/chromium"
    try:
        service = Service("/usr/bin/chromedriver")
        return webdriver.Chrome(service=service, options=options)
    except Exception:
        try:
            service = Service(ChromeDriverManager().install())
            return webdriver.Chrome(service=service, options=options)
        except Exception as e:
            st.error(f"Error motor: {e}")
            return None

# --- 2. EXTRACCIÓN PDF ---
def extraer_datos_pdf(archivo):
    datos = {"ruc": "", "rit": "", "juzgado": "", "sancion": ""}
    if archivo is None: return datos
    try:
        reader = PyPDF2.PdfReader(archivo)
        texto = "".join([p.extract_text() for p in reader.pages])
        # RUC
        m_ruc = re.search(r"RUC:\s?(\d{7,10}-[\dkK])", texto)
        if m_ruc: datos["ruc"] = m_ruc.group(1)
        # RIT
        m_rit = re.search(r"RIT:\s?([\d\w-]+-\d{4})", texto)
        if m_rit: datos["rit"] = m_rit.group(1)
        # TRIBUNAL
        m_trib = re.search(r"(Juzgado de Garantía de\s[\w\s]+|Tribunal de Juicio Oral en lo Penal de\s[\w\s]+)", texto, re.I)
        if m_trib: datos["juzgado"] = m_trib.group(1).strip()
        # SANCIÓN
        m_san = re.search(r"(condena a|pena de|sanción de).*?(\d+\s(años|días|meses).*?)(?=\.|y\s|SE\sRESUELVE)", texto, re.I | re.S)
        if m_san: datos["sancion"] = m_san.group(0).replace("\n", " ").strip()
    except Exception:
        pass
    return datos

# --- 3. GENERADOR WORD ---
def generar_word(datos_g, c_rpa, c_ad):
    doc = Document()
    style = doc.styles['Normal']
    style.font.name = 'Cambria'
    style.font.size = Pt(12)
    
    # Sumilla
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    p.add_run("EN LO PRINCIPAL: SOLICITA EXTINCIÓN RPA;\nOTROSÍ: ACOMPAÑA DOCUMENTO.").bold = True
    
    doc.add_paragraph(f"\nS.J. DE GARANTÍA DE {datos_g['juzgado_p'].upper()}").bold = True
    
    rits_ej = ", ".join([c['rit'] for c in datos_g['ejecucion'] if c['rit']])
    p_comp = doc.add_paragraph()
    p_comp.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p_comp.add_run(f"\n{datos_g['defensor'].upper()}, Defensor Penal Público, por {datos_g['adolescente'].upper()}, en RIT {rits_ej}, digo:")
    
    doc.add_paragraph("\nQue, solicito extinción de sanciones RPA (Art. 25 ter Ley 20.084):")
    for c in c_rpa:
        if c['rit']:
            li = doc.add_paragraph(style='List Bullet')
            li.add_run(f"RIT {c['rit']} ({c['juzgado_causa']}): ").bold = True
            li.add_run(f"Sanción de {c['sancion']}.")
            
    doc.add_paragraph("\nFUNDAMENTO MAYOR GRAVEDAD (ADULTO):").bold = True
    for a in c_ad:
        if a['rit']:
            pa = doc.add_paragraph()
            pa.add_run(f"RIT {a['rit']} del {a['juzgado']}: ").bold = True
            pa.add_run(f"Condenado a {a['detalle']}.")
            
    doc.add_paragraph("\nPOR TANTO, PIDO A US. acceder.").bold = True
    target = io.BytesIO()
    doc.save(target)
    target.seek(0)
    return target

# --- 4. INTERFAZ ---
st.set_page_config(page_title="LegalTech Ignacio", layout="wide")

if 'n_ej' not in st.session_state: st.session_state.n_ej = 1
if 'n_rpa' not in st.session_state: st.session_state.n_rpa = 1
if 'n_ad' not in st.session_state: st.session_state.n_ad = 1

st.title("⚖️ Gestión Jurídica Pro")
t1, t2 = st.tabs(["📄 Redactor", "🔍 Inteligencia MIA"])

with t1:
    defensor = st.text_input("Defensor", value="Ignacio Badilla Lara")
    adolescente = st.text_input("Adolescente")
    juzgado_p = st.text_input("Juzgado Destino")

    st.subheader("1. Ejecución")
    if st.button("➕ Ejecución"): st.session_state.n_ej += 1
    ej_list = []
    for i in range(st.session_state.n_ej):
        ej_list.append({"rit": st.text_input(f"RIT Eje {i}", key=f"te{i}")})

    st.subheader("2. RPA")
    if st.button("➕ RPA"): st.session_state.n_rpa += 1
    rpa_list = []
    for j in range(st.session_state.n_rpa):
        f = st.file_uploader(f"Sentencia RPA {j}", type="pdf", key=f"fr{j}")
        v = extraer_datos_pdf(f)
        rpa_list.append({
            "rit": st.text_input(f"RIT R {j}", value=v["rit"], key=f"tr{j}"),
            "juzgado_causa": st.text_input(f"Juz R {j}", value=v["juzgado"], key=f"jr{j}"),
            "sancion": st.text_area(f"Sanción R {j}", value=
