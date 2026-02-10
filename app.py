import streamlit as st
from docx import Document
from docx.shared import Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
import PyPDF2, io, re, time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options

def configurar_driver():
    o = Options()
    o.add_argument("--headless")
    o.add_argument("--no-sandbox")
    o.add_argument("--disable-dev-shm-usage")
    o.binary_location = "/usr/bin/chromium"
    try:
        s = Service("/usr/bin/chromedriver")
        return webdriver.Chrome(service=s, options=o)
    except:
        try:
            return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=o)
        except: return None

def extraer(f):
    d = {"ruc": "", "rit": "", "juz": "", "san": "", "txt": ""}
    if f is None: return d
    try:
        pdf = PyPDF2.PdfReader(f)
        t = "".join([p.extract_text() for p in pdf.pages])
        d["txt"] = t
        ruc = re.search(r"RUC:\s?(\d{7,10}-[\dkK])", t)
        if ruc: d["ruc"] = ruc.group(1)
        rit = re.search(r"RIT:\s?([\d\w-]+-\d{4})", t)
        if rit: d["rit"] = rit.group(1)
        juz = re.search(r"(Juzgado de Garantía de\s[\w\s]+)", t, re.I)
        if juz: d["juz"] = juz.group(1).strip()
        san = re.search(r"(condena a|pena de|sanción de).*?(\d+\s(años|días|meses).*?)(?=\.|y\s|SE\sRESUELVE)", t, re.I|re.S)
        if san: d["san"] = san.group(0).replace("\n", " ").strip()
    except: pass
    return d

def gen_doc(dg, cr, ca):
    doc = Document()
    s = doc.styles['Normal']
    s.font.name, s.font.size = 'Cambria', Pt(12)
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    p.add_run("EN LO PRINCIPAL: SOLICITA DECLARACIÓN DE EXTINCIÓN RPA;\nOTROSÍ: ACOMPAÑA DOCUMENTOS.").bold = True
    doc.add_paragraph(f"\nS. J. DE GARANTÍA DE {dg['jp'].upper()}").bold = True
    rits = ", ".join([f"{c['rit']} (RUC: {c['ruc']})" for c in dg['ej'] if c['rit']])
    p2 = doc.add_paragraph()
    p2.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p2.add_run(f"\n{dg['def'].upper()}, DPP, por {dg['ado'].upper()}, en causas {rits}, digo:")
    doc.add_paragraph("\nI. ANTECEDENTES RPA:").bold = True
    for c in cr:
        if c['rit']:
            li = doc.add_paragraph(style='List Bullet')
            li.add_run(f"RIT {c['rit']} (RUC {c['ruc']}) de {c['juz']}: ").bold = True
            li.add_run(f"{c['san']}.")
    doc.add_paragraph("\nII. FUNDAMENTO ADULTO:").bold = True
    for a in ca:
        if a['rit']:
            pa = doc.add_paragraph()
            pa.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            pa.add_run(f"RIT {a['rit']} (RUC {a['ruc']}) de {a['juz']}: ").bold = True
            pa.add_run(f"Condenado a {a['det']}.")
    doc.add_paragraph("\nPOR TANTO, PIDO A US. acceder.").bold = True
    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf

st.set_page_config(page_title="LegalTech Ignacio", layout="wide")
for k in ['ne', 'nr', 'na']:
    if k not in st.session_state: st.session_state[k] = 1

st.title("⚖️ Gestión Jurídica Pro")
t1, t2 = st.tabs(["📄 Redactor de Escritos", "🔍 Inteligencia MIA"])

with t1:
    d_f = st.text_input("Defensor", value="Ignacio Badilla Lara")
    a_d = st.text_input("Adolescente")
    j_p = st.text_input("Juzgado Destino")
    
    st.subheader("1. Causas de Ejecución")
    c_e1, c_e2 = st.columns(2)
    if c_e1.button("➕ Añadir Causa Ejecución"): st.session_state.ne += 1
    if c_e2.button("➖ Quitar Causa Ejecución") and st.session_state.ne > 1: st.session_state.ne -= 1
    le = []
    for i in range(st.session_state.ne):
        col1, col2 = st.columns(2)
        le.append({"ruc": col1.text_input(f"RUC E {i+1}", key=f"re{i}"), "rit": col2.text_input(f"RIT E {i+1}", key=f"te{i}")})

    st.subheader("2. Causas RPA (A extinguir)")
    c_r1, c_r2 = st.columns(2)
    if c_r1.button("➕ Añadir RPA"): st.session_state.nr += 1
    if c_r2.button("➖ Quitar RPA") and st.session_state.nr > 1: st.session_state.nr -= 1
    lr = []
    for j in range(st.session_state.nr):
        f = st.file_uploader(f"Sentencia RPA {j+1}", key=f"fr{j}")
        v = extraer(f); c1, c2, c3 = st.columns(3)
        lr.append({"ruc": c1.text_input(f"RUC R {j}", value=v["ruc"], key=f"rr{j}"), "rit": c2.text_input(f"RIT R {j}", value=v["rit"], key=f"tr{j}"), "juz": c3.text_input
