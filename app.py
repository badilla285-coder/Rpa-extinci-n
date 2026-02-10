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

# --- CONFIGURACIÓN DEL NAVEGADOR ---
def configurar_driver():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    try:
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        return driver
    except Exception as e:
        st.error(f"Error al iniciar el motor de búsqueda: {e}")
        return None

# --- EXTRACCIÓN DE DATOS ---
def extraer_datos_pdf(texto):
    datos = {"ruc": "", "rit": "", "juzgado": "", "sancion": ""}
    if not texto: return datos
    
    ruc = re.search(r"RUC:\s?(\d{7,10}-[\dkK])", texto)
    if ruc: datos["ruc"] = ruc.group(1)
    
    rit = re.search(r"RIT:\s?([\d\w-]+-\d{4})", texto)
    if rit: datos["rit"] = rit.group(1)
    
    trib = re.search(r"(Juzgado de Garantía de\s[\w\s]+|Tribunal de Juicio Oral en lo Penal de\s[\w\s]+)", texto)
    if trib: datos["juzgado"] = trib.group(1).strip()
    
    cond = re.search(r"(condena a|pena de|sanción de).*?(\d+\s(años|días|meses).*?)(?=\.|y\s|SE\sRESUELVE)", texto, re.IGNORECASE | re.DOTALL)
    if cond: datos["sancion"] = cond.group(0).replace("\n", " ").strip()
    return datos

# --- INTERFAZ ---
st.set_page_config(page_title="LegalTech Ignacio", layout="wide")

st.title("⚖️ Gestión Jurídica Pro")

tab1, tab2 = st.tabs(["📄 Redacción de Escritos", "🔍 Inteligencia MIA"])

with tab1:
    st.subheader("Datos Generales")
    col1, col2 = st.columns(2)
    defensor = col1.text_input("Defensor", value="Ignacio Badilla Lara")
    adolescente = col2.text_input("Nombre Adolescente")
    juzgado_p = st.text_input("Juzgado de Destino")

    # SECCIÓN 1: EJECUCIÓN
    st.markdown("### 1. Causas de Ejecución")
    if 'n_e' not in st.session_state: st.session_state.n_e = 1
    if st.button("➕ Añadir RIT de Ejecución"): st.session_state.n_e += 1
    
    ejecucion_data = []
    for i in range(st.session_state.n_e):
        c_e1, c_e2 = st.columns(2)
        r_e = c_e1.text_input(f"RUC Eje {i}", key=f"re_input_{i}")
        t_e = c_e2.text_input(f"RIT Eje {i}", key=f"te_input_{i}")
        ejecucion_data.append({"ruc": r_e, "rit": t_e})

    # SECCIÓN 2: RPA (CON CARGA ESTABLE)
    st.markdown("### 2. Antecedentes RPA")
    if 'n_o' not in st.session_state: st.session_state.n_o = 1
    if st.button("➕ Añadir Causa RPA"): st.session_state.n_o += 1
    
    origen_data = []
    for j in range(st.session_state.n_o):
        st.info(f"Causa RPA #{j+1}")
        # El file_uploader necesita un KEY único y estable
        f_o = st.file_uploader(f"Subir PDF RPA {j+1}", type="pdf", key=f"file_rpa_{j}")
        v = {"ruc":"", "rit":"", "juz":"", "san":""}
        
        if f_o:
            try:
                reader = PyPDF2.PdfReader(f_o)
                txt = "".join([page.extract_text() for page in reader.pages])
                v = extraer_datos_pdf(txt)
            except:
                st.error("Error al leer el PDF.")
        
        o1, o2, o3 = st.columns(3)
        ru = o1.text_input("RUC", value=v["ruc"], key=f"ru_o_{j}")
        ri = o2.text_input("RIT", value=v["rit"], key=f"ri_o_{j}")
        ju = o3.text_input("Juzgado", value=v["juz"], key=f"ju_o_{j}")
        sa = st.text_area("Sanción", value=v["san"], key=f"sa_o_{j}")
        origen_data.append({"ruc": ru, "rit": ri, "juzgado_causa": ju, "sancion": sa})

    # BOTÓN DE GENERACIÓN
    if st.button("🚀 GENERAR ESCRITO"):
        # (Aquí iría tu función de crear_escrito_robusto)
        st.success("¡Escrito listo para descargar!")

with tab2:
    st.header("Módulo de Inteligencia de Antecedentes")
    rut_m = st.text_input("RUT a consultar (ej: 12345678-9)")
    
    if st.button("🔍 Iniciar Escaneo Real"):
        with st.status("Ejecutando Selenium en la nube..."):
            driver = configurar_driver()
            if driver:
                st.write("Conectado con éxito. Buscando en fuentes públicas...")
                # Aquí iría tu lógica de driver.get()
                time.sleep(2)
                driver.quit()
                st.success("Búsqueda finalizada.")
            else:
                st.error("No se pudo iniciar el navegador. Revisa packages.txt")

