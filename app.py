import streamlit as st
from docx import Document
from docx.shared import Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
import PyPDF2, io, re, time, requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options

# --- CONFIGURACIÓN MOTOR ---
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
        try: return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=o)
        except: return None

def extraer_rutificador(rut_num):
    try:
        url = f"https://www.nombrerutyfirma.com/rut/{rut_num}"
        h = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url, headers=h, timeout=10)
        if r.status_code == 200:
            s = BeautifulSoup(r.text, 'html.parser')
            t = s.find('table', {'class': 'table'})
            if t:
                d = t.find_all('tr')[1].find_all('td')
                return {"nom": d[0].text.strip(), "dir": d[3].text.strip(), "com": d[4].text.strip()}
        return None
    except: return None

def extraer(f):
    d = {"ruc":"","rit":"","juz":"","san":"","txt":""}
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
    buf = io.BytesIO(); doc.save(buf); buf.seek(0)
    return buf

# --- INTERFAZ ---
st.set_page_config(page_title="Generador de Extinciones - Ignacio Badilla", layout="wide")
for k in ['ne','nr','na']:
    if k not in st.session_state: st.session_state[k] = 1

st.title("⚖️ Generador de Extinciones")
t1, t2 = st.tabs(["📄 Redactor de Escritos", "🔍 Módulo MIA"])

with t1:
    d_f = st.text_input("Defensor Titular", value="Ignacio Badilla Lara")
    a_d = st.text_input("Nombre del Adolescente")
    j_p = st.text_input("Juzgado de Garantía Destino")
    
    st.subheader("1. Causas de Ejecución")
    e1, e2 = st.columns(2)
    if e1.button("➕ Añadir Causa Ejecución"): st.session_state.ne += 1
    if e2.button("➖ Quitar Causa Ejecución") and st.session_state.ne > 1: st.session_state.ne -= 1
    le = []
    for i in range(st.session_state.ne):
        c1, c2 = st.columns(2)
        le.append({"ruc": c1.text_input(f"RUC Ejecución {i+1}", key=f"re{i}"), "rit": c2.text_input(f"RIT Ejecución {i+1}", key=f"te{i}")})

    st.subheader("2. Causas RPA (A extinguir)")
    r1, r2 = st.columns(2)
    if r1.button("➕ Añadir Causa RPA"): st.session_state.nr += 1
    if r2.button("➖ Quitar Causa RPA") and st.session_state.nr > 1: st.session_state.nr -= 1
    lr = []
    for j in range(st.session_state.nr):
        f = st.file_uploader(f"Sentencia RPA {j+1}", key=f"fr{j}")
        v = extraer(f); c1, c2, c3 = st.columns(3)
        lr.append({"ruc":c1.text_input(f"RUC RPA {j+1}",value=v["ruc"],key=f"rr{j}"),"rit":c2.text_input(f"RIT RPA {j+1}",value=v["rit"],key=f"tr{j}"),"juz":c3.text_input(f"Tribunal RPA {j+1}",value=v["juz"],key=f"jr{j}"),"san":st.text_area(f"Sanción RPA {j+1}",value=v["san"],key=f"sr{j}")})

    st.subheader("3. Condenas Adulto (Fundamento)")
    a1, a2 = st.columns(2)
    if a1.button("➕ Añadir Causa Adulto"): st.session_state.na += 1
    if a2.button("➖ Quitar Causa Adulto") and st.session_state.na > 1: st.session_state.na -= 1
    la = []
    for k in range(st.session_state.na):
        fa = st.file_uploader(f"Sentencia Adulto {k+1}", key=f"fa{k}")
        va = extraer(fa); cl1, cl2, cl3 = st.columns(3)
        la.append({"ruc":cl1.text_input(f"RUC Adulto {k+1}",value=va["ruc"],key=f"ra{k}"),"rit":cl2.text_input(f"RIT Adulto {k+1}",value=va["rit"],key=f"ta{k}"),"juz":cl3.text_input(f"Tribunal Adulto {k+1}",value=va["juz"],key=f"ja{k}"),"det":st.text_area(f"Pena Adulto {k+1}",value=va["san"],key=f"da{k}")})

    if st.button("🚀 GENERAR ESCRITO ROBUSTO"):
        res = gen_doc({"def":d_f,"ado":a_d,"jp":j_p,"ej":le}, lr, la)
        st.download_button("📥 Descargar Escrito Word", res, f"Extincion_{a_d}.docx")

with t2:
    st.header("🔍 Módulo MIA: Inteligencia")
    r_m = st.text_input("RUT a investigar (Ej: 12345678-9)")
    if r_m:
        r_l = r_m.replace(".","").replace("-",""); r_n = r_l[:-1]
        if st.button("⚡ ESCANEO PROFUNDO"):
            with st.status("MIA Rastreando...") as s:
                d_c = extraer_rutificador(r_n)
                if d_c:
                    st.success(f"**Nombre:** {d_c['nom']}")
                    st.info(f"**Dirección:** {d_c['dir']}, {d_c['com']}")
                else: st.warning("No se hallaron datos automáticos.")
                dr = configurar_driver()
                if dr:
                    dr.get(f"https://www.google.com/search?q={r_m}"); time.sleep(1); dr.quit()
                    s.update(label="Escaneo Finalizado", state="complete")
        st.divider()
        ca, cb = st.columns(2)
        with ca:
            st.link_button("⚖️ PJUD", "https://oficinajudicialvirtual.pjud.cl/")
            st.link_button("👤 Rutificador", f"https://www.nombrerutyfirma.com/rut/{r_n}")
        with cb:
            st.link_button("🗳️ SERVEL", "https://consulta.servel.cl/")
            st.link_button("📱 Redes Sociales", f"https://www.google.com/search?q={r_m}+facebook+instagram")

st.markdown("---")
st.caption("🚀 Aplicación hecha por Ignacio Badilla Lara")
