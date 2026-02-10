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

# --- MOTOR DE INTELIGENCIA ---
def configurar_driver():
    o = Options()
    o.add_argument("--headless")
    o.add_argument("--no-sandbox")
    o.add_argument("--disable-dev-shm-usage")
    # Agente de usuario real para evitar bloqueos
    o.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36")
    o.binary_location = "/usr/bin/chromium"
    try:
        s = Service("/usr/bin/chromedriver")
        return webdriver.Chrome(service=s, options=o)
    except:
        try: return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=o)
        except: return None

def extraer_datos_civiles(rut_num):
    """Extrae datos directamente si la web no bloquea la IP del servidor"""
    try:
        url = f"https://www.nombrerutyfirma.com/rut/{rut_num}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            "Referer": "https://www.google.com/"
        }
        r = requests.get(url, headers=headers, timeout=6)
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, 'html.parser')
            tabla = soup.find('table', {'class': 'table'})
            if tabla:
                datos = tabla.find_all('tr')[1].find_all('td')
                return {"nom": datos[0].text.strip(), "dir": datos[3].text.strip(), "com": datos[4].text.strip()}
    except: pass
    return None

def extraer_info_pdf(archivo):
    d = {"ruc":"","rit":"","juz":"","san":"","txt":""}
    if archivo is None: return d
    try:
        reader = PyPDF2.PdfReader(archivo)
        texto = "".join([p.extract_text() for p in reader.pages])
        d["txt"] = texto
        r_ruc = re.search(r"RUC:\s?(\d{7,10}-[\dkK])", texto)
        if r_ruc: d["ruc"] = r_ruc.group(1)
        r_rit = re.search(r"RIT:\s?([\d\w-]+-\d{4})", texto)
        if r_rit: d["rit"] = r_rit.group(1)
        r_juz = re.search(r"(Juzgado de Garantía de\s[\w\s]+)", texto, re.I)
        if r_juz: d["juz"] = r_juz.group(1).strip()
        r_san = re.search(r"(condena a|pena de|sanción de).*?(\d+\s(años|días|meses).*?)(?=\.|y\s|SE\sRESUELVE)", texto, re.I|re.S)
        if r_san: d["san"] = r_san.group(0).replace("\n", " ").strip()
    except: pass
    return d

def generar_word(dg, cr, ca):
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
    p2.add_run(f"\n{dg['def'].upper()}, Defensor Penal Público, por {dg['ado'].upper()}, en causas de ejecución {rits}, digo:")
    doc.add_paragraph("\nI. ANTECEDENTES DE LAS CAUSAS RPA:").bold = True
    for c in cr:
        if c['rit']:
            li = doc.add_paragraph(style='List Bullet')
            li.add_run(f"Causa RIT {c['rit']} (RUC {c['ruc']}) de {c['juz']}: ").bold = True
            li.add_run(f"Sanción consistente en {c['san']}.")
    doc.add_paragraph("\nII. FUNDAMENTO DE MAYOR GRAVEDAD (CONDENA ADULTO):").bold = True
    for a in ca:
        if a['rit']:
            pa = doc.add_paragraph()
            pa.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            pa.add_run(f"Causa RIT {a['rit']} (RUC {a['ruc']}) del {a['juz']}: ").bold = True
            pa.add_run(f"Condenado como adulto a la pena de {a['det']}.")
    doc.add_paragraph("\nPOR TANTO, A US. PIDO: Acceder a lo solicitado.").bold = True
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
    col1, col2 = st.columns(2)
    if col1.button("➕ Añadir Causa Ejecución"): st.session_state.ne += 1
    if col2.button("➖ Quitar Causa Ejecución") and st.session_state.ne > 1: st.session_state.ne -= 1
    le = [{"ruc": st.columns(2)[0].text_input(f"RUC Ejecución {i+1}", key=f"re{i}"), "rit": st.columns(2)[1].text_input(f"RIT Ejecución {i+1}", key=f"te{i}")} for i in range(st.session_state.ne)]

    st.subheader("2. Causas RPA (A extinguir)")
    col3, col4 = st.columns(2)
    if col3.button("➕ Añadir Causa RPA"): st.session_state.nr += 1
    if col4.button("➖ Quitar Causa RPA") and st.session_state.nr > 1: st.session_state.nr -= 1
    lr = []
    for j in range(st.session_state.nr):
        f = st.file_uploader(f"Sentencia RPA {j+1}", key=f"fr{j}")
        v = extraer_info_pdf(f); c1, c2, c3 = st.columns(3)
        lr.append({"ruc":c1.text_input(f"RUC RPA {j+1}",value=v["ruc"],key=f"rr{j}"),"rit":c2.text_input(f"RIT RPA {j+1}",value=v["rit"],key=f"tr{j}"),"juz":c3.text_input(f"Tribunal RPA {j+1}",value=v["juz"],key=f"jr{j}"),"san":st.text_area(f"Sanción RPA {j+1}",value=v["san"],key=f"sr{j}")})

    st.subheader("3. Condenas Adulto (Fundamento)")
    col5, col6 = st.columns(2)
    if col5.button("➕ Añadir Causa Adulto"): st.session_state.na += 1
    if col6.button("➖ Quitar Causa Adulto") and st.session_state.na > 1: st.session_state.na -= 1
    la = []
    for k in range(st.session_state.na):
        fa = st.file_uploader(f"Sentencia Adulto {k+1}", key=f"fa{k}")
        va = extraer_info_pdf(fa); cl1, cl2, cl3 = st.columns(3)
        la.append({"ruc":cl1.text_input(f"RUC Adulto {k+1}",value=va["ruc"],key=f"ra{k}"),"rit":cl2.text_input(f"RIT Adulto {k+1}",value=va["rit"],key=f"ta{k}"),"juz":cl3.text_input(f"Tribunal Adulto {k+1}",value=va["juz"],key=f"ja{k}"),"det":st.text_area(f"Pena Adulto {k+1}",value=va["san"],key=f"da{k}")})

    if st.button("🚀 GENERAR ESCRITO ROBUSTO"):
        res = generar_word({"def":d_f,"ado":a_d,"jp":j_p,"ej":le}, lr, la)
        st.download_button("📥 Descargar Word", res, f"Extincion_{a_d}.docx")

with t2:
    st.header("🔍 Módulo MIA: Inteligencia")
    r_m = st.text_input("RUT a investigar (Ej: 12345678-9)")
    if r_m:
        r_l = r_m.replace(".","").replace("-",""); r_n = r_l[:-1]
        if st.button("⚡ ESCANEO PROFUNDO"):
            with st.status("Interconectando...") as s:
                d = extraer_datos_civiles(r_n)
                if d:
                    st.success(f"**Nombre:** {d['nom']}\n\n**Dirección:** {d['dir']}, {d['com']}")
                else:
                    st.error("Acceso automatizado restringido por el sitio fuente.")
                s.update(label="Escaneo Finalizado", state="complete")
        
        st.divider()
        st.subheader("🔗 Interconexión de Bases de Datos")
        ca, cb = st.columns(2)
        with ca:
            st.link_button("⚖️ PJUD (Causas)", "https://oficinajudicialvirtual.pjud.cl/")
            st.link_button("👤 Rutificador", f"https://www.nombrerutyfirma.com/rut/{r_n}")
        with cb:
            st.link_button("🗳️ SERVEL", "https://consulta.servel.cl/")
            st.link_button("📱 Redes Sociales", f"https://www.google.com/search?q={r_m}+facebook+instagram")

st.markdown("---")
st.caption("🚀 Aplicación hecha por Ignacio Badilla Lara")
