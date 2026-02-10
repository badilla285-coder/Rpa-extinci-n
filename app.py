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

# --- 1. CONFIGURACIÓN DEL MOTOR DE BÚSQUEDA (SELENIUM) ---
def configurar_driver():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    # Forzamos la ruta del binario instalado por packages.txt
    options.binary_location = "/usr/bin/chromium"
    
    try:
        # Intento A: Usar el driver del sistema (Garantiza misma versión que navegador)
        service = Service("/usr/bin/chromedriver")
        driver = webdriver.Chrome(service=service, options=options)
        return driver
    except Exception:
        try:
            # Intento B: Webdriver Manager como respaldo
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=options)
            return driver
        except Exception as e:
            st.error(f"Error crítico en el motor: {e}")
            return None

# --- 2. PROCESAMIENTO DE DOCUMENTOS (IA DE EXTRACCIÓN) ---
def extraer_datos_pdf(archivo_pdf):
    if archivo_pdf is None:
        return {"ruc": "", "rit": "", "juzgado": "", "sancion": ""}
    
    try:
        reader = PyPDF2.PdfReader(archivo_pdf)
        texto = ""
        for page in reader.pages:
            texto += page.extract_text()
        
        datos = {"ruc": "", "rit": "", "juzgado": "", "sancion": ""}
        
        # Búsqueda de RUC (Ej: 21.000.123-4)
        ruc = re.search(r"RUC:\s?(\d{1,2}\.?\d{3}\.?\d{3}-[\dkK])", texto)
        if ruc: datos["ruc"] = ruc.group(1)
        
        # Búsqueda de RIT (Ej: O-1234-2021)
        rit = re.search(r"RIT:\s?([A-Z]-\d{1,5}-\d{4})", texto)
        if rit: datos["rit"] = rit.group(1)
        
        # Búsqueda de Tribunal
        trib = re.search(r"(Juzgado de Garantía de\s[\w\s]+|Tribunal de Juicio Oral en lo Penal de\s[\w\s]+)", texto, re.IGNORECASE)
        if trib: datos["juzgado"] = trib.group(1).strip()
        
        # Búsqueda de Sanción/Pena
        cond = re.search(r"(condena a|pena de|sanción de|consistente en).*?(\d+\s(años|días|meses).*?)(?=\.|y\s|SE\sRESUELVE)", texto, re.IGNORECASE | re.DOTALL)
        if cond: datos["sancion"] = cond.group(0).replace("\n", " ").strip()
        
        return datos
    except Exception as e:
        st.error(f"Error leyendo PDF: {e}")
        return {"ruc": "", "rit": "", "juzgado": "", "sancion": ""}

# --- 3. GENERADOR DE ESCRITOS (FORMATO DEFENSORÍA) ---
def generar_escrito_word(datos_grales, causas_rpa, condenas_ad):
    doc = Document()
    
    # Configuración de fuente Cambria 12 (Estándar Poder Judicial)
    style = doc.styles['Normal']
    font = style.font
    font.name = 'Cambria'
    font.size = Pt(12)

    # SUMILLA (Derecha)
    p_sum = doc.add_paragraph()
    p_sum.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    run_sum = p_sum.add_run("EN LO PRINCIPAL: SOLICITA DECLARACIÓN DE\nEXTINCIÓN DE SANCIONES RPA POR ART. 25 TER Y\n25 QUINQUIES LEY 20.084.\nOTROSÍ: ACOMPAÑA DOCUMENTOS.")
    run_sum.bold = True

    # TRIBUNAL
    p_trib = doc.add_paragraph()
    p_trib.add_run(f"\nS. J. DE GARANTÍA DE {datos_grales['juzgado_p'].upper()}").bold = True

    # COMPARECENCIA
    rits_ej = ", ".join([c['rit'] for c in datos_grales['ejecucion'] if c['rit']])
    p_comp = doc.add_paragraph()
    p_comp.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p_comp.add_run(f"\n{datos_grales['defensor'].upper()}, Defensor Penal Público, por el adolescente ")
    p_comp.add_run(f"{datos_grales['adolescente'].upper()}, ").bold = True
    p_comp.add_run(f"en causas RIT de ejecución {rits_ej}, a US. respetuosamente digo:")

    # CUERPO LEGAL
    p1 = doc.add_paragraph("\nQue, por este acto y de conformidad a lo dispuesto en el artículo 25 ter y 25 quinquies de la Ley 20.084, vengo en solicitar que US. declare la extinción de las sanciones impuestas a mi representado, en atención a los antecedentes de hecho y de derecho que paso a exponer:")
    p1.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY

    # SECCIÓN RPA
    doc.add_paragraph("\nI. ANTECEDENTES DE LAS CAUSAS RPA").bold = True
    for c in causas_rpa:
        if c['rit']:
            p_c = doc.add_paragraph(style='List Bullet')
            p_c.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            p_c.add_run(f"Causa RIT {c['rit']} del {c['juzgado_causa']}: ").bold = True
            p_c.add_run(f"Se impuso la sanción de {c['sancion']}.")

    # SECCIÓN ADULTO (FUNDAMENTO)
    doc.add_paragraph("\nII. FUNDAMENTO DE MAYOR GRAVEDAD (CONDENA ADULTO)").bold = True
    for a in condenas_ad:
        if a['rit']:
            p_a = doc.add_paragraph()
            p_a.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            p_a.add_run(f"Con fecha posterior, mi representado fue condenado como adulto en la causa ").bold = False
            p_a.add_run(f"RIT {a['rit']} del {a['juzgado']} ").bold = True
            p_a.add_run(f"a la pena de {a['detalle']}, la cual resulta de mayor gravedad que las sanciones RPA anteriormente señaladas, operando de pleno derecho la causal de extinción.")

    # PETITORIO
    p_final = doc.add_paragraph("\nPOR TANTO,")
    p_final.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p_final.add_run("\nA US. PIDO: ").bold = True
    p_final.add_run("Tener por solicitada la extinción de las sanciones RPA señaladas, declarar la misma y ordenar el archivo de los antecedentes y el cese de toda medida cautelar o de ejecución vigente.")

    # Guardado en buffer
    target = io.BytesIO()
    doc.save(target)
    target.seek(0)
    return target

# --- 4. INTERFAZ DE USUARIO (STREAMLIT) ---
st.set_page_config(page_title="LegalTech Ignacio - RPA", layout="wide", page_icon="⚖️")

# Inyectar CSS para mejorar visualización en móviles
st.markdown("""<style> .stButton>button { width: 100%; border-radius: 10px; height: 3em; background-color: #004a99; color: white; } </style>""", unsafe_allow_html=True)

st.title("⚖️ Gestión Jurídica Pro (V2026)")
st.caption("Desarrollado para Defensoría Penal Pública por Ignacio Badilla")

# Manejo de estados para añadir filas dinámicamente sin errores
if 'n_ej' not in st.session_state: st.session_state.n_ej = 1
if 'n_rpa' not in st.session_state: st.session_state.n_rpa = 1
if 'n_ad' not in st.session_state: st.session_state.n_ad = 1

tab_escrito, tab_mia = st.tabs(["📄 Redactor de Escritos", "🔍 Inteligencia MIA"])

with tab_escrito:
    with st.expander("👤 DATOS DE COMPARECENCIA", expanded=True):
        c1, c2 = st.columns(2)
        nombre_defensor = c1.text_input("Defensor Titular", value="Ignacio Badilla Lara")
        nombre_adolescente = c2.text_input("Nombre del Adolescente (Completo)")
        tribunal_destino = st.text_input("Juzgado de Garantía de Destino (Ej: San Bernardo)")

    st.divider()
    
    # 1. EJECUCIÓN
    st.subheader("1. Causas de
