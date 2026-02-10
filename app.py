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

# --- 1. CONFIGURACIÓN DEL MOTOR MIA ---
def configurar_driver():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.binary_location = "/usr/bin/chromium"
    try:
        service = Service("/usr/bin/chromedriver")
        return webdriver.Chrome(service=service, options=options)
    except Exception:
        try:
            return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        except Exception as e:
            st.error(f"Error motor: {e}")
            return None

# --- 2. EXTRACCIÓN PDF ---
def extraer_datos_pdf(archivo_pdf):
    if archivo_pdf is None:
        return {"ruc": "", "rit": "", "juzgado": "", "sancion": "", "texto_completo": ""}
    try:
        reader = PyPDF2.PdfReader(archivo_pdf)
        texto = "".join([page.extract_text() for page in reader.pages])
        datos = {"ruc": "", "rit": "", "juzgado": "", "sancion": "", "texto_completo": texto}
        ruc = re.search(r"RUC:\s?(\d{7,10}-[\dkK])", texto)
        if ruc: datos["ruc"] = ruc.group(1)
        rit = re.search(r"RIT:\s?([\d\w-]+-\d{4})", texto)
        if rit: datos["rit"] = rit.group(1)
        trib = re.search(r"(Juzgado de Garantía de\s[\w\s]+|Tribunal de Juicio Oral en lo Penal de\s[\w\s]+)", texto, re.IGNORECASE)
        if trib: datos["juzgado"] = trib.group(1).strip()
        cond = re.search(r"(condena a|pena de|sanción de|consistente en).*?(\d+\s(años|días|meses).*?)(?=\.|y\s|SE\sRESUELVE)", texto, re.IGNORECASE | re.DOTALL)
        if cond: datos["sancion"] = cond.group(0).replace("\n", " ").strip()
        return datos
    except:
        return {"ruc": "", "rit": "", "juzgado": "", "sancion": "", "texto_completo": ""}

# --- 3. GENERADOR DE ESCRITO ---
def generar_word_robusto(dg, cr, ca):
    doc = Document()
    style = doc.styles['Normal']
    style.font.name, style.font.size = 'Cambria', Pt(12)
    
    p_sum = doc.add_paragraph()
    p_sum.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    p_sum.add_run("EN LO PRINCIPAL: SOLICITA DECLARACIÓN DE EXTINCIÓN DE SANCIONES RPA POR ART. 25 TER Y 25 QUINQUIES LEY 20.084;\nOTROSÍ: ACOMPAÑA DOCUMENTOS.").bold = True
    
    doc.add_paragraph(f"\nS. J. DE GARANTÍA DE {dg['jp'].upper()}").bold = True
    
    rits_ej = ", ".join([f"{c['rit']} (RUC: {c['ruc']})" for c in dg['ejecucion'] if c['rit']])
    p_comp = doc.add_paragraph()
    p_comp.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p_comp.add_run(f"\n{dg['def'].upper()}, Defensor Penal Público, por el adolescente ")
    p_comp.add_run(f"{dg['ado'].upper()}, ").bold = True
    p_comp.add_run(f"en causas de ejecución {rits_ej}, a US. respetuosamente digo:")
    
    doc.add_paragraph("\nQue, de conformidad a la Ley 20.084, vengo en solicitar se declare la extinción de las sanciones impuestas a mi representado, en atención a los siguientes antecedentes:").alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    
    doc.add_paragraph("\nI. ANTECEDENTES DE LAS CAUSAS RPA:").bold = True
    for c in cr:
        if c['rit']:
            li = doc.add_paragraph(style='List Bullet')
            li.add_run(f"Causa RIT {c['rit']} (RUC {c['ruc']}) del {c['juz']}: ").bold = True
            li.add_run(f"Sanción consistente en {c['san']}.")

    doc.add_paragraph("\nII. FUNDAMENTO DE MAYOR GRAVEDAD (CONDENA ADULTO):").bold = True
    for a in ca:
        if a['rit']:
            pa = doc.add_paragraph()
            pa.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            pa.add_run(f"Causa RIT
