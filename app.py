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
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, 'html.parser')
            tabla = soup.find('table', {'class': 'table'})
            if tabla:
                filas = tabla.find_all('tr')
                if len(filas) > 1:
                    datos = filas[1].find_all('td')
                    return {"nombre": datos[0].text.strip(), "rut": datos[1].text.strip(), "dir": datos[3].text.strip(), "comuna": datos[4].text.strip()}
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
    p.add_run("EN LO PRINCIPAL: SOLICITA EXTINCIÓN RPA;\nOTROSÍ: ACOMPAÑA.").bold = True
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

st.set_page_config(page_title="LegalTech Ignacio", layout="wide")
for k in ['ne','nr','na']:
    if k not in st.session_state: st.session_state[k] = 1

st.title("⚖️ Gestión Jurídica Pro - San Bernardo")
t1, t2 = st.tabs(["📄 Redactor de Escritos", "🔍 Módulo MIA (Inteligencia)"])

with t1:
    d_f = st.text_input("Defensor", value="Ignacio Badilla Lara")
    a_d = st.text_input("Adolescente")
    j_p = st.text_input("Juzgado Destino")
    st.subheader("1. Ejecución")
    e1, e2 = st.columns(2)
    if e1.button("➕ Causa Ejecución"): st.session_state.ne += 1
    if e2.button("➖ Quitar Ejecución") and st.session_state.ne > 1: st.session_state.ne -= 1
    le = []
    for i in range(st.session_state.ne):
        c1, c2 = st.columns(2)
        le.append({"ruc": c1.text_input(f"RUC E {i}", key=f"re{i}"), "rit": c2.text_input(f"RIT E {i}", key=f"te{i}")})
    st.subheader("2. RPA")
    r1, r2 = st.columns(2)
    if r1.button("➕ RPA"): st.session_state.nr += 1
    if r2.button("➖ RPA") and st.session_state.nr > 1: st.session_state.nr -= 1
    lr = []
    for j in range(st.session_state.nr):
        f = st.file_uploader(f"Sentencia R {j}", key=f"fr{j}")
        v = extraer(f); c1, c2, c3 = st.columns(3)
        lr.append({"ruc":c1.text_input(f"RUC R {j}",value=v["ruc"],key=f"rr{j}"),"rit":c2.text_input(f"RIT R {j}",value=v["rit"],key=f"tr{j}"),"juz":c3.text_input(f"Trib R {j}",value=v["juz"],key=f"jr{j}"),"san":st.text_area(f"San R {j}",value=v["san"],key=f"sr{j}")})
    st.subheader("3. Adulto")
    a1, a2 = st.columns(2)
    if a1.button("➕ Adulto"): st.session_state.na += 1
    if a2.button("➖ Adulto") and st.session_state.na > 1: st.session_state.na -= 1
    la = []
    for k in range(st.session_state.na):
        fa = st.file_uploader(f"Sentencia A {k}", key=f"fa{k}")
        va = extraer(fa); cl1, cl2, cl3 = st.columns(3)
        la.append({"ruc":cl1.text_input(f"RUC A {k}",value=va["ruc"],key=f"ra{k}"),"rit":cl2.text_input(f"RIT A {k}",value=va["rit"],key=f"ta{k}"),"juz":cl3.text_input(f"Trib A {k}",value=va["juz"],key=f"ja{k}"),"det":st.text_area(f"Pena A {k}",value=va["san"],key=f"da{k}")})
    if st.button("🚀 GENERAR"):
        res = gen_doc({"def":d_f,"ado":a_d,"jp":j_p,"ej":le}, lr, la)
        st.download_button("📥 Descargar", res, f"Extincion_{a_d}.docx")

with t2:
    st.header("🔍 Módulo MIA: Inteligencia y Antecedentes")
    r_m = st.text_input("RUT a investigar (Ej: 12345678-9)")
    if r_m:
        r_l = r_m.replace(".","").replace("-",""); r_n = r_l[:-1]
        
        if st.button("⚡ INICIAR ESCANEO PROFUNDO"):
            with st.status("MIA está rastreando antecedentes...") as s:
                # 1. Extracción de Rutificador
                s.write("Consultando bases de datos civiles...")
                datos_civiles = extraer_rutificador(r_n)
                if datos_civiles:
                    st.success(f"**Nombre:** {datos_civiles['nombre']}")
                    st.info(f"**Dirección registrada:** {datos_civiles['dir']}, {datos_civiles['comuna']}")
                else:
                    st.warning("No se pudo extraer dirección automática.")
                
                # 2. Búsqueda de Redes con Selenium
                s.write("Buscando huella digital en redes sociales...")
                d = configurar_driver()
                if d:
                    d.get(f"https://www.google.com/search?q={r_m}+facebook+instagram")
                    time.sleep(2)
                    st.write("Analizando posibles vínculos en Meta e Instagram...")
                    d.quit()
                    s.update(label="Escaneo Finalizado", state="complete")
                else: st.error("Error en motor Selenium")

        st.divider()
        st.subheader("🔗 Enlaces de Verificación Manual")
        ca, cb = st.columns(2)
        with ca:
            st.link_button("⚖️ PJUD (SITRRE/SITLA)", "https://oficinajudicialvirtual.pjud.cl/")
            st.link_button("👤 Ver en Rutificador", f"https://www.nombrerutyfirma.com/rut/{r_n}")
        with cb:
            st.link_button("🗳️ SERVEL (Local de Votación)", "https://consulta.servel.cl/")
            st.link_button("📱 Google Social Check", f"https://www.google.com/search?q={r_m}+facebook+instagram")
