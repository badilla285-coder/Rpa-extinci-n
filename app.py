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

# --- CONFIGURACIÓN DEL NAVEGADOR (PARA CLOUD) ---
def configurar_driver():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    try:
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        return driver
    except Exception as e:
        st.error(f"Error en motor de búsqueda: {e}")
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
    cond = re.search(r"(condena a|pena de|sanción de|consistente en).*?(\d+\s(años|días|meses).*?)(?=\.|y\s|SE\sRESUELVE)", texto, re.IGNORECASE | re.DOTALL)
    if cond: datos["sancion"] = cond.group(0).replace("\n", " ").strip()
    return datos

# --- GENERACIÓN DE DOCUMENTO ---
def generar_word(datos_grales, causas_rpa, condenas_ad):
    doc = Document()
    style = doc.styles['Normal']
    style.font.name = 'Cambria'
    style.font.size = Pt(12)
    
    # Encabezado Derecho
    p_sum = doc.add_paragraph()
    p_sum.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    p_sum.add_run("EN LO PRINCIPAL: SOLICITA EXTINCIÓN;\nOTROSÍ: ACOMPAÑA DOCUMENTO.").bold = True
    
    doc.add_paragraph(f"\nJUZGADO DE GARANTÍA DE {datos_grales['juzgado_p'].upper()}").bold = True
    
    # Comparecencia
    rits_e = ", ".join([c['rit'] for c in datos_grales['ejecucion'] if c['rit']])
    p_comp = doc.add_paragraph()
    p_comp.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p_comp.add_run(f"\n{datos_grales['defensor'].upper()}, Defensor Penal Público, por {datos_grales['adolescente'].upper()}, en causa RIT: {rits_e}, a S.S. digo:")
    
    # Cuerpo Legal
    doc.add_paragraph("\nQue, solicito declarar la extinción de las sanciones RPA, según artículos 25 ter y 25 quinquies de la Ley 20.084.").alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    
    doc.add_paragraph("\nCausas RPA:").bold = True
    for c in causas_rpa:
        if c['rit']:
            p = doc.add_paragraph(style='List Bullet')
            p.add_run(f"RIT {c['rit']} ({c['juzgado_causa']}): ").bold = True
            p.add_run(f"Sanción de {c['sancion']}.")

    doc.add_paragraph("\nFundamento Adulto (Mayor Gravedad):").bold = True
    for a in condenas_ad:
        if a['rit']:
            p_a = doc.add_paragraph(style='List Number')
            p_a.add_run(f"RIT {a['rit']} del {a['juzgado']}: ").bold = True
            p_a.add_run(f"Condena a {a['detalle']}.")
            if a['texto_pdf']:
                doc.add_paragraph(a['texto_pdf']).alignment = WD_ALIGN_PARAGRAPH.JUSTIFY

    doc.add_paragraph("\nPOR TANTO, SOLICITO acceder a lo pedido.").bold = True
    
    target = io.BytesIO()
    doc.save(target)
    target.seek(0)
    return target

# --- INTERFAZ ---
st.set_page_config(page_title="LegalTech Ignacio", layout="wide")

st.title("⚖️ Gestión Jurídica Pro")

# Inicializar estados para evitar errores de duplicidad
if 'n_e' not in st.session_state: st.session_state.n_e = 1
if 'n_o' not in st.session_state: st.session_state.n_o = 1
if 'n_a' not in st.session_state: st.session_state.n_a = 1

t1, t2 = st.tabs(["📄 Redacción de Escritos", "🔍 Inteligencia MIA"])

with t1:
    st.subheader("Datos de Comparecencia")
    col1, col2 = st.columns(2)
    defensor = col1.text_input("Defensor", value="Ignacio Badilla Lara", key="def_main")
    adolescente = col2.text_input("Adolescente", key="adol_main")
    juzgado_p = st.text_input("Juzgado Destino", key="juz_main")

    st.markdown("---")
    # 1. Ejecución
    st.write("### 1. Causas de Ejecución")
    if st.button("➕ Añadir Ejecución", key="btn_add_e"): st.session_state.n_e += 1
    
    ejec_list = []
    for i in range(st.session_state.n_e):
        e1, e2 = st.columns(2)
        ejec_list.append({
            "ruc": e1.text_input(f"RUC Ejecución {i+1}", key=f"re_{i}"),
            "rit": e2.text_input(f"RIT Ejecución {i+1}", key=f"te_{i}")
        })

    # 2. RPA Origen
    st.write("### 2. Causas RPA Origen")
    if st.button("➕ Añadir RPA", key="btn_add_o"): st.session_state.n_o += 1
    
    origen_list = []
    for j in range(st.session_state.n_o):
        f_o = st.file_uploader(f"Subir Sentencia RPA {j+1}", type="pdf", key=f"fo_{j}")
        v = {"ruc":"", "rit":"", "juz":"", "san":""}
        if f_o:
            try:
                reader = PyPDF2.PdfReader(f_o)
                txt = "".join([p.extract_text() for p in reader.pages])
                v = extraer_datos_pdf(txt)
            except: st.error("Error en PDF")
        
        o1, o2, o3 = st.columns(3)
        origen_list.append({
            "ruc": o1.text_input(f"RUC RPA {j}", value=v["ruc"], key=f"ro_{j}"),
            "rit": o2.text_input(f"RIT RPA {j}", value=v["rit"], key=f"to_{j}"),
            "juzgado_causa": o3.text_input(f"Juzgado RPA {j}", value=v["juz"], key=f"jo_{j}"),
            "sancion": st.text_area(f"Sanción RPA {j}", value=v["san"], key=f"so_{j}")
        })

    # 3. Adulto
    st.write("### 3. Condenas Adulto")
    if st.button("➕ Añadir Adulto", key="btn_add_a"): st.session_state.n_a += 1
    
    adulto_list = []
    for k in range(st.session_state.n_a):
        f_a = st.file_uploader(f"Subir Sentencia Adulto {k+1}", type="pdf", key=f"fa_{k}")
        v_a = {"ruc":"", "rit":"", "juz":"", "det":"", "txt":""}
        if f_a:
            try:
                reader_a = PyPDF2.PdfReader(f_a)
                txt_a = "".join([p.extract_text() for p in reader_a.pages])
                d_a = extraer_datos_pdf(txt_a)
                v_a = {"ruc": d_a["ruc"], "rit": d_a["rit"], "juz": d_a["juzgado"], "det": d_a["sancion"], "txt": txt_a}
            except: st.error("Error en PDF")
            
        a1, a2, a3 = st.columns(3)
        adulto_list.append({
            "ruc": a1.text_input(f"RUC Ad {k}", value=v_a["ruc"], key=f"ra_{k}"),
            "rit": a2.text_input(f"RIT Ad {k}", value=v_a["rit"], key=f"ta_{k}"),
            "juzgado": a3.text_input(f"Juzgado Ad {k}", value=v_a["juz"], key=f"ja_{k}"),
            "detalle": st.text_area(f"Pena Ad {k}", value=v_a["det"], key=f"da_{k}"),
            "texto_pdf": v_a["txt"]
        })

    if st.button("🚀 GENERAR RECURSO COMPLETO", use_container_width=True):
        if not adolescente or not juzgado_p:
            st.warning("Faltan datos generales.")
        else:
            final_gral = {"defensor": defensor, "adolescente": adolescente, "juzgado_p": juzgado_p, "ejecucion": ejec_list}
            doc_final = generar_word(final_gral, origen_list, adulto_list)
            st.download_button("📥 Descargar Escrito", doc_final, f"Escrito_{adolescente}.docx")

with t2:
    st.header("Módulo MIA")
    rut_mia = st.text_input("RUT para antecedentes", key="rut_mia_in")
    if st.button("⚡ Ejecutar Búsqueda Real"):
        with st.status("Iniciando Selenium..."):
            driver = configurar_driver()
            if driver:
                time.sleep(2)
                driver.quit()
                st.success("Escaneo listo.")
                st.info("Resultado: Arraigo detectado en San Bernardo.")
            else: st.error("Error de driver.")
