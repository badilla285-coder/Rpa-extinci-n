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

# --- CONFIGURACIÓN DEL MOTOR (SELENIUM) ---
def configurar_driver():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.binary_location = "/usr/bin/chromium"
    try:
        # Intento directo con el driver del sistema
        service = Service("/usr/bin/chromedriver")
        return webdriver.Chrome(service=service, options=options)
    except:
        try:
            # Respaldo con manager
            return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        except Exception as e:
            st.error(f"Error en motor: {e}")
            return None

# --- EXTRACCIÓN DE DATOS PDF ---
def extraer_datos_pdf(archivo_pdf):
    if archivo_pdf is None: return {"ruc": "", "rit": "", "juzgado": "", "sancion": ""}
    try:
        reader = PyPDF2.PdfReader(archivo_pdf)
        texto = "".join([page.extract_text() for page in reader.pages])
        datos = {"ruc": "", "rit": "", "juzgado": "", "sancion": ""}
        ruc = re.search(r"RUC:\s?(\d{7,10}-[\dkK])", texto)
        if ruc: datos["ruc"] = ruc.group(1)
        rit = re.search(r"RIT:\s?([\d\w-]+-\d{4})", texto)
        if rit: datos["rit"] = rit.group(1)
        trib = re
