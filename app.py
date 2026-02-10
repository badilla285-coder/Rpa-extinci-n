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

# --- 1. CONFIGURACIÓN DEL MOTOR MIA (SELENIUM) ---
def configurar_driver():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.binary_location = "/usr/bin/chromium"
    try:
        service = Service("/usr/bin/chromedriver")
        driver = webdriver.Chrome(service=service, options=options)
        return driver
    except Exception:
        try:
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=options)
            return driver
        except Exception as e:
            st.error(f"Error técnico en MIA: {e}")
            return None

# --- 2. INTELIGENCIA DE EXTRACCIÓN PDF ---
def extraer_datos_pdf(archivo_pdf):
    if archivo_pdf is None:
        return {"ruc": "", "rit": "", "juzgado": "", "sancion": "", "texto_completo": ""}
    try:
        reader = PyPDF2.PdfReader(archivo_pdf)
        texto = ""
        for page in reader.pages:
            texto += page.extract_text()
        
        datos = {"ruc": "", "rit": "", "juzgado": "", "sancion": "", "texto_completo": texto}
        ruc = re.search(r"RUC:\s?(\d{7,10}-[\dkK])", texto)
        if ruc: datos["ruc"] = ruc.group(1)
        rit = re.search(r"RIT:\s?([\d\w-]+-\d{4})", texto)
        if rit: datos["rit"] = rit.group(1)
        trib = re.search(r"(Juzgado de Garantía de\s[\w\s]+|Tribunal de Juicio Oral en lo Penal de\s[\w\s]+)", texto, re.IGNORECASE)
        if trib: datos["juzgado"] = trib.group(1).strip()
        cond = re.search(r"(condena a|pena de|sanción de|consistente en).*?(\d+\s(años|días|meses).*?)(?=\.|y\s|SE\sRESUELVE)", texto, re.IGNORECASE | re.DOTALL)
        if cond: datos["sancion"] = cond.group(0).replace("\n", " ").strip()
        
        return datos
    except Exception:
        return {"ruc": "", "rit": "", "juzgado": "", "sancion": "", "texto_completo": ""}

# --- 3. GENERADOR DE ESCRITO ROBUSTO (ESTILO DEFENSORÍA) ---
def generar_word_robusto(datos_grales, causas_rpa, condenas_ad):
    doc = Document()
    style = doc.styles['Normal']
    style.font.name = 'Cambria'
    style.font.size = Pt(12)
    
    # Sumilla
    p_sum = doc.add_paragraph()
    p_sum.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    run_sum = p_sum.add_run("EN LO PRINCIPAL: SOLICITA DECLARACIÓN DE EXTINCIÓN DE SANCIONES RPA POR ART. 25 TER Y 25 QUINQUIES LEY 20.084;\nOTROSÍ: ACOMPAÑA DOCUMENTOS.")
    run_sum.bold = True
    
    # Tribunal
    doc.add_paragraph(f"\nS. J. DE GARANTÍA DE {datos_grales['juzgado_p'].upper()}").bold = True
    
    # Comparecencia
    rits_ej = ", ".join([f"{c['rit']} (RUC: {c['ruc']})" for c in datos_grales['ejecucion'] if c['rit']])
    p_comp = doc.add_paragraph()
    p_comp.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p_comp.add_run(f"\n{datos_grales['defensor'].upper()}, Defensor Penal Público, por el adolescente ")
    p_comp.add_run(f"{datos_grales['adolescente'].upper()}, ").bold = True
    p_comp.add_run(f"en causas de ejecución {rits_ej}, a US. respetuosamente digo:")
    
    doc.add_paragraph("\nQue, de conformidad a la Ley 20.084, vengo en solicitar se declare la extinción de las sanciones impuestas a mi representado, en atención a los siguientes antecedentes:").alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    
    doc.add_paragraph("\nI. ANTECEDENTES DE LAS CAUSAS RPA:").bold = True
    for c in causas_rpa:
        if c['rit']:
            p_r = doc.add_paragraph(style='List Bullet')
            p_r.add_run(f"Causa RIT {c['rit']} (RUC {c['ruc']}) del {c['juzgado_causa']}: ").bold = True
            p_r.add_run(f"Sanción consistente en {c['sancion']}.")

    doc.add_paragraph("\nII. FUNDAMENTO DE MAYOR GRAVEDAD (CONDENA ADULTO):").bold = True
    for a in condenas_ad:
        if a['rit']:
            p_a = doc.add_paragraph()
            p_a.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            p_a.add_run(f"Causa RIT {a['rit']} (RUC {a['ruc']}) del {a['juzgado']}: ").bold = True
            p_a.add_run(f"Condenado como adulto a la pena de {a['detalle']}.")
            if a.get('texto_pdf'):
                p_cita = doc.add_paragraph()
                p_cita.add_run(f"Cita textual resolución: \"{a['texto_pdf'][:700]}...\"").italic = True

    p_pido = doc.add_paragraph("\nPOR TANTO,")
    p_pido.add_run("\nA US. PIDO: ").bold = True
    p_pido.add_run("Tener por solicitada la extinción, declarar la misma y ordenar el archivo de los antecedentes.")
    
    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf

# --- 4. INTERFAZ ---
st.set_page_config(page_title="LegalTech Ignacio", layout="wide")

for key in ['n_e', 'n_r', 'n_a']:
    if key not in st.session_state: st.session_state[key] = 1

st.title("⚖️ Gestión Jurídica Pro")

t1, t2 = st.tabs(["📄 Redactor de Escritos", "🔍 Inteligencia MIA"])

with t1:
    with st.expander("👤 DATOS DE COMPARECENCIA", expanded=True):
        c_d1, c_d2 = st.columns(2)
        defensor = c_d1.text_input("Defensor Titular", value="Ignacio Badilla Lara")
        adolescente = c_d2.text_input("Nombre Adolescente")
        juzgado_p = st.text_input("Juzgado Destino")

    st.subheader("1. Causas de Ejecución")
    if st.button("➕ Añadir RIT Ejecución"): st.session_state.n_e += 1
    ej_list = []
    for i in range(st.session_state.n_e):
        col1, col2 = st.columns(2)
        ej_list.append({
            "ruc": col1.text_input(f"RUC Ejecución {i+1}", key=f"re{i}"),
            "rit": col2.text_input(f"RIT Ejecución {i+1}", key=f"te{i}")
        })

    st.subheader("2. Causas RPA (A extinguir)")
    if st.button("➕ Añadir Causa RPA"): st.session_state.n_r += 1
    rpa_list = []
    for j in range(st.session_state.n_r):
        f = st.file_uploader(f"Subir Sentencia RPA {j+1}", type="pdf", key=f"fr{j}")
        v = extraer_datos_pdf(f)
        c1, c2, c3 = st.columns(3)
        rpa_list.append({
            "ruc": c1.text_input(f"RUC RPA {j+1}", value=v["ruc"], key=f"r_r{j}"),
            "rit": c2.text_input(f"RIT RPA {j+1}", value=v["rit"], key=f"t_r{j}"),
            "juzgado_causa": c3.text_input(f"Tribunal RPA {j+1}", value=v["juzgado"], key=f"j_r{j}"),
            "sancion": st.text_area(f"Sanción RPA {j+1}", value=v["sancion"], key=f"s_r{j}")
        })

    st.subheader("3. Condenas Adulto (Fundamento)")
    if st.button("➕ Añadir Condena Adulto"): st.session_state.n_a += 1
    ad_list = []
    for k in range(st.session_state.n_a):
        fa = st.file_uploader(f"Subir Sentencia Adulto {k+1}", type="pdf", key=f"fa{k}")
        va = extraer_datos_pdf(fa)
        c4, c5, c6 = st.columns(3)
        ad_list.append({
            "ruc": c4.text_input(f"RUC Adulto {k+1}", value=va["ruc"], key=f"r_a{k}"),
            "rit": c5.text_input(f"RIT Adulto {k+1}", value=va["rit"], key=f"t_a{k}"),
            "juzgado": c6.text_input(f"Tribunal Adulto {k+1}", value=va["juzgado"], key=f"j_a{k
