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

# --- 1. CONFIGURACIÓN DEL MOTOR (SELENIUM) ---
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
            st.error(f"Error en motor: {e}")
            return None

# --- 2. EXTRACCIÓN DE DATOS PDF ---
def extraer_datos_pdf(archivo_pdf):
    if archivo_pdf is None:
        return {"ruc": "", "rit": "", "juzgado": "", "sancion": ""}
    try:
        reader = PyPDF2.PdfReader(archivo_pdf)
        texto = "".join([page.extract_text() for page in reader.pages])
        datos = {"ruc": "", "rit": "", "juzgado": "", "sancion": ""}
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
        return {"ruc": "", "rit": "", "juzgado": "", "sancion": ""}

# --- 3. GENERADOR DE WORD (CAMBRIA 12) ---
def generar_word(datos_grales, causas_rpa, condenas_ad):
    doc = Document()
    style = doc.styles['Normal']
    style.font.name = 'Cambria'
    style.font.size = Pt(12)
    p_sum = doc.add_paragraph()
    p_sum.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    p_sum.add_run("EN LO PRINCIPAL: SOLICITA EXTINCIÓN;\nOTROSÍ: ACOMPAÑA DOCUMENTO.").bold = True
