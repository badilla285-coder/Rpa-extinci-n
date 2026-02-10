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
    d = {"rit": "", "juz": "", "san": ""}
    if f is None: return d
    try:
        pdf = PyPDF2.PdfReader(f)
        t = "".join([p.extract_text() for p in pdf.pages])
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
    p.add_run("SOLICITA EXTINCIÓN RPA;\nOTROSÍ: ACOMPAÑA.").bold = True
    doc.add_paragraph(f"\nJUZGADO DE GARANTÍA DE {dg['jp'].upper()}").bold = True
    p2 = doc.add_paragraph()
    p2.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p2.add_run(f"\n{dg['def'].upper()}, DPP, por {dg['ado'].upper()}, digo:")
    doc.add_paragraph("\nSolicito extinción RPA (Art. 25 ter Ley 20.084):")
    for c in cr:
        if c['rit']:
            li = doc.add_paragraph(style='List Bullet')
            li.add_run(f"RIT {c['rit']} ({c['juz']}): ").bold = True
            li.add_run(f"{c['san']}.")
    doc.add_paragraph("\nFUNDAMENTO ADULTO:").bold = True
    for a in ca:
        if a['rit']:
            pa = doc.add_paragraph()
            pa.add_run(f"RIT {a['rit']} ({a['juz']}): ").bold = True
            pa.add_run(f"Pena: {a['det']}.")
    doc.add_paragraph("\nPOR TANTO, PIDO A US. acceder.").bold = True
    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf

st.set_page_config(page_title="LegalTech")
if 'n_e' not in st.session_state: st.session_state.n_e = 1
if 'n_r' not in st.session_state: st.session_state.n_r = 1
if 'n_a' not in st.session_state: st.session_state.n_a = 1

st.title("⚖️ Gestión Jurídica Pro")
t1, t2 = st.tabs(["📄 Redactor", "🔍 MIA"])

with t1:
    df = st.text_input("Defensor", value="Ignacio Badilla Lara")
    ad = st.text_input("Adolescente")
    jp = st.text_input("Juzgado Destino")
    st.subheader("1. Ejecución")
    if st.button("+ Eje"): st.session_state.n_e += 1
    le = [{"rit": st.text_input(f"RIT E {i}", key=f"e{i}")} for i in range(st.session_state.n_e)]
    st.subheader("2. RPA")
    if st.button("+ RPA"): st.session_state.n_r += 1
    lr = []
    for j in range(st.session_state.n_r):
        f = st.file_uploader(f"PDF R {j}", key=f"fr{j}")
        v = extraer(f)
        lr.append({"rit": st.text_input(f"RIT R {j}", value=v["rit"], key=f"tr{j}"), "juz": st.text_input(f"Juz R {j}", value=v["juz"], key=f"jr{j}"), "san": st.text_area(f"San R {j}", value=v["san"], key=f"sr{j}")})
    st.subheader("3. Adulto")
    if st.button("+ Adulto"): st.session_state.n_a += 1
    la = []
    for k in range(st.session_state.n_a):
        fa = st.file_uploader(f"PDF A {k}", key=f"fa{k}")
        va = extraer(fa)
        la.append({"rit": st.text_input(f"RIT A {k}", value=va["rit"], key=f"ta{k}"), "juz": st.text_input(f"Juz A {k}", value=va["juz"], key=f"ja{k}"), "det": st.text_area(f"Pena A {k}", value=va["san"], key=f"da{k}")})
    if st.button("🚀 GENERAR"):
        res = gen_doc({"def": df, "ado": ad, "jp": jp, "ejecucion": le}, lr, la)
        st.download_button("📥 Descargar", res, f"Escrito_{ad}.docx")

with t2:
    if st.button("🔍 Motor"):
        with st.status("Test..."):
            d = configurar_driver()
            if d:
                d.quit()
                st.success("OK")
            else: st.error("Error")
