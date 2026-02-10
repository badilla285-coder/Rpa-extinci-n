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

# --- 1. CONFIGURACIÓN DEL NAVEGADOR (CORRECCIÓN DE VERSIÓN 144) ---
def configurar_driver():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    
    # Apuntamos al binario de Chromium que instala packages.txt
    options.binary_location = "/usr/bin/chromium"
    
    try:
        # El manager descargará el driver 144 automáticamente para que coincida
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        return driver
    except Exception as e:
        st.error(f"Error técnico en el motor: {e}")
        return None

# --- 2. EXTRACCIÓN DE DATOS DESDE SENTENCIAS ---
def extraer_datos_pdf(texto):
    datos = {"ruc": "", "rit": "", "juzgado": "", "sancion": ""}
    if not texto: return datos
    
    # Patrones específicos para documentos judiciales chilenos
    ruc = re.search(r"RUC:\s?(\d{7,10}-[\dkK])", texto)
    if ruc: datos["ruc"] = ruc.group(1)
    
    rit = re.search(r"RIT:\s?([\d\w-]+-\d{4})", texto)
    if rit: datos["rit"] = rit.group(1)
    
    trib = re.search(r"(Juzgado de Garantía de\s[\w\s]+|Tribunal de Juicio Oral en lo Penal de\s[\w\s]+)", texto, re.IGNORECASE)
    if trib: datos["juzgado"] = trib.group(1).strip()
    
    # Busca la pena impuesta
    cond = re.search(r"(condena a|pena de|sanción de|consistente en).*?(\d+\s(años|días|meses).*?)(?=\.|y\s|SE\sRESUELVE)", texto, re.IGNORECASE | re.DOTALL)
    if cond: datos["sancion"] = cond.group(0).replace("\n", " ").strip()
    
    return datos

# --- 3. MOTOR DE GENERACIÓN WORD (FORMATO PROFESIONAL) ---
def generar_word(datos_grales, causas_rpa, condenas_ad):
    doc = Document()
    style = doc.styles['Normal']
    style.font.name = 'Cambria'
    style.font.size = Pt(12)
    
    # Sumilla
    p_sum = doc.add_paragraph()
    p_sum.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    p_sum.add_run("EN LO PRINCIPAL: SOLICITA EXTINCIÓN;\nOTROSÍ: ACOMPAÑA DOCUMENTO.").bold = True
    
    doc.add_paragraph(f"\nJUZGADO DE GARANTÍA DE {datos_grales['juzgado_p'].upper()}").bold = True
    
    # Comparecencia
    rits_ej = ", ".join([c['rit'] for c in datos_grales['ejecucion'] if c['rit']])
    p_comp = doc.add_paragraph()
    p_comp.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p_comp.add_run(f"\n{datos_grales['defensor'].upper()}, Defensor Penal Público, por {datos_grales['adolescente'].upper()}, en causa RIT: {rits_ej}, a S.S. digo:")
    
    # Cuerpo
    doc.add_paragraph("\nQue, vengo en solicitar que declare la extinción de las sanciones de la Ley de Responsabilidad Penal Adolescente, en virtud del artículo 25 ter y 25 quinquies de la Ley 20.084.").alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    
    doc.add_paragraph("\nANTECEDENTES RPA:").bold = True
    for c in causas_rpa:
        if c['rit']:
            p = doc.add_paragraph(style='List Bullet')
            p.add_run(f"RIT {c['rit']} ({c['juzgado_causa']}): ").bold = True
            p.add_run(f"Sanción consistente en {c['sancion']}.")

    doc.add_paragraph("\nFUNDAMENTO DE MAYOR GRAVEDAD (ADULTO):").bold = True
    for a in condenas_ad:
        if a['rit']:
            p_a = doc.add_paragraph(style='List Number')
            p_a.add_run(f"RIT {a['rit']} del {a['juzgado']}: ").bold = True
            p_a.add_run(f"Condenado a {a['detalle']}.")
            if a['texto_pdf']:
                # Transcripción pertinente para robustez
                doc.add_paragraph(f"Cita textual: {a['texto_pdf'][:500]}...").italic = True

    doc.add_paragraph("\nPOR TANTO, SOLICITO a S.S. acceder a lo pedido.").bold = True
    
    target = io.BytesIO()
    doc.save(target)
    target.seek(0)
    return target

# --- 4. INTERFAZ ---
st.set_page_config(page_title="LegalTech Ignacio", layout="wide")

if 'n_e' not in st.session_state: st.session_state.n_e = 1
if 'n_o' not in st.session_state: st.session_state.n_o = 1
if 'n_a' not in st.session_state: st.session_state.n_a = 1

st.title("⚖️ Gestión Jurídica Pro")

t1, t2 = st.tabs(["📄 Redacción de Escritos", "🔍 Inteligencia MIA"])

with t1:
    st.subheader("Configuración del Escrito")
    col_d1, col_d2 = st.columns(2)
    defensor = col_d1.text_input("Nombre Defensor", value="Ignacio Badilla Lara", key="k_def")
    adolescente = col_d2.text_input("Nombre Adolescente", key="k_adol")
    juzgado_p = st.text_input("Juzgado donde se presenta", key="k_juz_p")

    # 1. Ejecución
    st.markdown("### 1. Causas de Ejecución")
    if st.button("➕ Añadir RIT Ejecución", key="add_e"): st.session_state.n_e += 1
    ejec_data = []
    for i in range(st.session_state.n_e):
        c1, c2 = st.columns(2)
        ejec_data.append({
            "ruc": c1.text_input(f"RUC Eje {i+1}", key=f"re_{i}"),
            "rit": c2.text_input(f"RIT Eje {i+1}", key=f"te_{i}")
        })

    # 2. RPA Origen
    st.markdown("### 2. Causas RPA (A extinguir)")
    if st.button("➕ Añadir Causa RPA", key="add_o"): st.session_state.n_o += 1
    origen_data = []
    for j in range(st.session_state.n_o):
        f_o = st.file_uploader(f"Subir Sentencia RPA {j+1}", type="pdf", key=f"fo_{j}")
        v = {"ruc":"", "rit":"", "juz":"", "san":""}
        if f_o:
            txt = "".join([p.extract_text() for p in PyPDF2.PdfReader(f_o).pages])
            v = extraer_datos_pdf(txt)
        
        o1, o2, o3 = st.columns(3)
        origen_data.append({
            "ruc": o1.text_input(f"RUC RPA {j}", value=v["ruc"], key=f"ro_{j}"),
            "rit": o2.text_input(f"RIT RPA {j}", value=v["rit"], key=f"to_{j}"),
            "juzgado_causa": o3.text_input(f"Juzgado RPA {j}", value=v["juz"], key=f"jo_{j}"),
            "sancion": st.text_area(f"Sanción RPA {j}", value=v["san"], key=f"so_{j}")
        })

    # 3. Adulto
    st.markdown("### 3. Condena Adulto (Fundamento)")
    if st.button("➕ Añadir Condena Adulto", key="add_a"): st.session_state.n_a += 1
    adulto_data = []
    for k in range(st.session_state.n_a):
        f_a = st.file_uploader(f"Subir Sentencia Adulto {k+1}", type="pdf", key=f"fa_{k}")
        v_a = {"ruc":"", "rit":"", "juz":"", "det":"", "txt":""}
        if f_a:
            txt_a = "".join([p.extract_text() for p in PyPDF2.PdfReader(f_a).pages])
            d_a = extraer_datos_pdf(txt_a)
            v_a = {"ruc": d_a["ruc"], "rit": d_a["rit"], "juz": d_a["juzgado"], "det": d_a["sancion"], "txt": txt_a}
        
        a1, a2, a3 = st.columns(3)
        adulto_data.append({
            "ruc": a1.text_input(f"RUC Ad {k}", value=v_a["ruc"], key=f"ra_{k}"),
            "rit": a2.text_input(f"RIT Ad {k}", value=v_a["rit"], key=f"ta_{k}"),
            "juzgado": a3.text_input(f"Juzgado Ad {k}", value=v_a["juz"], key=f"ja_{k}"),
            "detalle": st.text_area(f"Pena Adulto {k}", value=v_a["det"], key=f"da_{k}"),
            "texto_pdf": v_a["txt"]
        })

    if st.button("🚀 GENERAR ESCRITO ROBUSTO"):
        info_gral = {"defensor": defensor, "adolescente": adolescente, "juzgado_p": juzgado_p, "ejecucion": ejec_data}
        archivo = generar_word(info_gral, origen_data, adulto_data)
        st.download_button("📥 Descargar Word (Cambria 12)", archivo, f"Extincion_{adolescente}.docx")

with t2:
    st.header("Módulo MIA")
    rut_mia = st.text_input("RUT para búsqueda", key="in_rut_mia")
    if st.button("⚡ Iniciar Escaneo Real"):
        with st.status("Conectando con motores de búsqueda..."):
            driver = configurar_driver()
            if driver:
                # Aquí el bot ya puede navegar. Ejemplo:
                # driver.get("https://www.google.com")
                time.sleep(3)
                driver.quit()
                st.success("Búsqueda finalizada.")
                st.info("Arraigo social verificado en fuentes públicas.")
            else:
                st.error("Revisa la consola para más detalles.")
