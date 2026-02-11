import streamlit as st
import fitz  # PyMuPDF
from docx import Document
from docx.shared import Pt, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
import io
import re

# --- SEGURIDAD ---
def check_password():
    if "password_correct" not in st.session_state:
        st.title("🔐 Acceso Sistema Judicial")
        col1, col2 = st.columns(2)
        email = col1.text_input("Correo")
        pw = col2.text_input("Clave", type="password")
        if st.button("Ingresar"):
            if email == "badilla285@gmail.com" and pw == "nacho2026":
                st.session_state["password_correct"] = True
                st.rerun()
            else:
                st.error("Credenciales incorrectas")
        return False
    return True

class GeneradorJuridicoPro:
    def __init__(self):
        self.fuente = "Cambria"
        self.tamano = 12

    def extraer_datos_flexible(self, file):
        """Motor de extracción corregido para evitar KeyError."""
        file.seek(0)
        texto = ""
        with fitz.open(stream=file.read(), filetype="pdf") as doc:
            for pagina in doc:
                texto += pagina.get_text()
        
        rit = re.search(r"RIT[:\s]*(\d+-\d{4})", texto, re.I)
        ruc = re.search(r"RUC[:\s]*(\d{8,12}-[\dkK])", texto, re.I)
        trib = re.search(r"(?:Juzgado de Garantía de|Tribunal de|TOP de)\s+([a-zA-ZáéíóúÁÉÍÓÚ\s]+)", texto, re.I)
        
        return {
            "rit": rit.group(1) if rit else "",
            "ruc": ruc.group(1) if ruc else "",
            "juzgado": trib.group(1).split('\n')[0].strip() if trib else ""
        }

    def crear_escrito(self, data):
        doc = Document()
        
        # Configuración de página
        for section in doc.sections:
            section.left_margin = Inches(1.2)
            section.right_margin = Inches(1.0)

        def agregar_parrafo(texto, bold=False, sin_sangria=False):
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            p.paragraph_format.line_spacing_rule = WD_LINE_SPACING.ONE_POINT_FIVE
            if not sin_sangria:
                p.paragraph_format.first_line_indent = Inches(0.5)
            
            run = p.add_run(texto)
            run.font.name = self.fuente
            run.font.size = Pt(self.tamano)
            run.bold = bold
            return p

        # 1. SUMA (IZQUIERDA)
        suma = doc.add_paragraph()
        suma.alignment = WD_ALIGN_PARAGRAPH.LEFT
        r_suma = suma.add_run("EN LO PRINCIPAL: SOLICITA EXTINCIÓN;\nOTROSÍ: ACOMPAÑA DOCUMENTO.")
        r_suma.bold = True
        r_suma.font.name = self.fuente
        r_suma.font.size = Pt(self.tamano)

        # 2. TRIBUNAL
        agregar_parrafo(f"\nJUZGADO DE GARANTÍA DE {data['juzgado_ejecucion'].upper()}", bold=True, sin_sangria=True)

        # 3. COMPARECENCIA
        comp = (f"\n{data['defensor'].upper()}, Abogada, Defensora Penal Pública, en representación de "
                f"{data['adolescente'].upper()}, en causa RIT: {data['rit_principal']}, "
                f"RUC: {data['ruc_principal']}, a S.S., respetuosamente digo:")
        agregar_parrafo(comp, sin_sangria=True)

        # 4. CUERPO FIJO
        agregar_parrafo("\nQue, vengo en solicitar que declare la extinción de las sanciones de la Ley de "
                        "Responsabilidad Penal Adolescente, o en subsidio se fije día y hora para celebrar "
                        "audiencia para debatir sobre la extinción de la pena respecto de mi representado, en "
                        "virtud del artículo 25 ter y 25 quinquies de la Ley 20.084.")

        agregar_parrafo("Mi representado fue condenado en la siguiente causa de la Ley RPA:")

        # 5. CAUSAS RPA (DINÁMICAS)
        for i, c in enumerate(data['causas_rpa'], 1):
            txt_causa = (f"{i}. RIT: {c['rit']}, RUC: {c['ruc']}: En la cual fue condenado por el Juzgado de Garantía de "
                         f"{c['juzgado']} a una sanción consistente en {c['sancion']}. Cabe señalar que dicha pena no se encuentra cumplida.")
            agregar_parrafo(txt_causa)

        agregar_parrafo("El fundamento para solicitar la discusión respecto de la extinción de responsabilidad "
                        "penal radica en la existencia de una condena de mayor gravedad como adulto, la cual paso a detallar:")

        # 6. CAUSAS ADULTO (DINÁMICAS)
        for i, c in enumerate(data['causas_adulto'], 1):
            idx = i + len(data['causas_rpa'])
            txt_adulto = (f"{idx}. RIT: {c['rit']}, RUC: {c['ruc']}: En la cual fue condenado por el {c['juzgado']}, "
                          f"con fecha {c['fecha']}, a sufrir la pena de {c['pena']}. Atendido que dicha sanción reviste una mayor gravedad, "
                          "tanto por la naturaleza del ilícito como por la cuantía de la pena impuesta, configurándose así los presupuestos para la extinción.")
            agregar_parrafo(txt_adulto)

        # 7. CIERRE JURÍDICO
        agregar_parrafo("Se hace presente que el artículo 25 ter en su inciso tercero establece que se considerará más grave el delito o conjunto de ellos "
                        "que tuviere asignada en la ley una mayor pena de conformidad con las reglas generales.")

        agregar_parrafo("\nPOR TANTO,", sin_sangria=True)
        agregar_parrafo("En mérito de lo expuesto, SOLICITO A S.S. acceder a lo solicitado extinguiendo de pleno derecho la sanción antes referida, "
                        "o en subsidio se fije día y hora para celebrar audiencia para que se abra debate sobre la extinción de responsabilidad penal en la presente causa.")

        # 8. OTROSÍ
        agregar_parrafo("\nOTROSÍ: Acompaña sentencia de adulto de mi representado.", bold=True, sin_sangria=True)
        agregar_parrafo("POR TANTO,", sin_sangria=True)
        agregar_parrafo("SOLICITO A S.S. se tenga por acompañada sentencia", sin_sangria=True)

        buffer = io.BytesIO()
        doc.save(buffer)
        buffer.seek(0)
        return buffer

# --- INTERFAZ ---
if check_password():
    st.set_page_config(page_title="Generador Judicial Nacho", layout="wide")
    
    # Inicialización de listas en sesión para evitar borrado de campos
    if "rpa_list" not in st.session_state: st.session_state.rpa_list = []
    if "adulto_list" not in st.session_state: st.session_state.adulto_list = []

    st.title("⚖️ Generador de Escritos de Extinción")

    # SECCIÓN 1: INDIVIDUALIZACIÓN
    st.header("1. Individualización")
    c1, c2, c3 = st.columns(3)
    defensor = c1.text_input("Abogado/a Defensor/a", "VIVIANA MORENO HERMAN")
    adolescente = c2.text_input("Nombre Adolescente", "CARLOS MANUEL ALARCÓN CANDIA")
    juzgado_e = c3.text_input("Juzgado Ejecución", "SAN BERNARDO")
    
    c4, c5 = st.columns(2)
    rit_p = c4.text_input("RIT Principal (Ejecución)", "1587-2018")
    ruc_p = c5.text_input("RUC Principal (Ejecución)", "1800174694-0")

    # SECCIÓN 2: CAUSAS RPA
    st.header("2. Causas RPA (Sanciones)")
    up_rpa = st.file_uploader("Adjuntar PDF RPA para auto-relleno", type="pdf", accept_multiple_files=True, key="up_rpa")
    
    if up_rpa:
        for f in up_rpa:
            if f.name not in [x.get('fn') for x in st.session_state.rpa_list]:
                d = GeneradorJuridicoPro().extraer_datos_flexible(f)
                st.session_state.rpa_list.append({"rit": d['rit'], "ruc": d['ruc'], "juzgado": d['juzgado'], "sancion": "", "fn": f.name})

    for i, item in enumerate(st.session_state.rpa_list):
        cols = st.columns([2, 2, 2, 3, 0.5])
        item['rit'] = cols[0].text_input("RIT", item['rit'], key=f"rpat_{i}")
        item['ruc'] = cols[1].text_input("RUC", item['ruc'], key=f"rpau_{i}")
        item['juzgado'] = cols[2].text_input("Juzgado", item['juzgado'], key=f"rpaj_{i}")
        item['sancion'] = cols[3].text_input("Sanción", item['sancion'], key=f"rpas_{i}")
        if cols[4].button("❌", key=f"rpad_{i}"):
            st.session_state.rpa_list.pop(i)
            st.rerun()

    if st.button("➕ Añadir Causa RPA Manual"):
        st.session_state.rpa_list.append({"rit": "", "ruc": "", "juzgado": "", "sancion": "", "fn": "manual"})
        st.rerun()

    # SECCIÓN 3: CAUSAS ADULTO
    st.header("3. Causas Adulto (Fundamento)")
    up_ad = st.file_uploader("Adjuntar PDF Adulto para auto-relleno", type="pdf", accept_multiple_files=True, key="up_ad")
    
    if up_ad:
        for f in up_ad:
            if f.name not in [x.get('fn') for x in st.session_state.adulto_list]:
                d = GeneradorJuridicoPro().extraer_datos_flexible(f)
                # AQUÍ ESTABA EL ERROR: Clave 'juzgado' corregida
                st.session_state.adulto_list.append({"rit": d['rit'], "ruc": d['ruc'], "juzgado": d['juzgado'], "pena": "", "fecha": "", "fn": f.name, "bytes": f.getvalue()})

    for i, item in enumerate(st.session_state.adulto_list):
        cols = st.columns([2, 2, 2, 2, 2, 0.5])
        item['rit'] = cols[0].text_input("RIT Adulto", item['rit'], key=f"adt_{i}")
        item['ruc'] = cols[1].text_input("RUC Adulto", item['ruc'], key=f"adu_{i}")
        item['juzgado'] = cols[2].text_input("Juzgado Adulto", item['juzgado'], key=f"adj_{i}")
        item['pena'] = cols[3].text_input("Pena", item['pena'], key=f"adp_{i}")
        item['fecha'] = cols[4].text_input("Fecha", item['fecha'], key=f"adf_{i}")
        if cols[5].button("❌", key=f"add_{i}"):
            st.session_state.adulto_list.pop(i)
            st.rerun()

    if st.button("➕ Añadir Causa Adulto Manual"):
        st.session_state.adulto_list.append({"rit": "", "ruc": "", "juzgado": "", "pena": "", "fecha": "", "fn": "manual"})
        st.rerun()

    # BOTÓN FINAL
    st.markdown("---")
    if st.button("🚀 GENERAR ESCRITO COMPLETO", use_container_width=True):
        datos_finales = {
            "defensor": defensor, "adolescente": adolescente, "juzgado_ejecucion": juzgado_e,
            "rit_principal": rit_p, "ruc_principal": ruc_p,
            "causas_rpa": st.session_state.rpa_list,
            "causas_adulto": st.session_state.adulto_list
        }
        
        gen = GeneradorJuridicoPro()
        word_doc = gen.crear_escrito(datos_finales)
        
        st.success("✅ Escrito generado con éxito.")
        st.download_button("⬇️ Descargar Escrito (Word)", word_doc, f"Extincion_{adolescente}.docx", use_container_width=True)
        
        if st.session_state.adulto_list:
            pdf_merged = fitz.open()
            for item in st.session_state.adulto_list:
                if "bytes" in item:
                    doc_ad = fitz.open(stream=item['bytes'], filetype="pdf")
                    pdf_merged.insert_pdf(doc_ad)
            pdf_buf = io.BytesIO(pdf_merged.tobytes())
            st.download_button("⬇️ Descargar Sentencias Unidas (PDF)", pdf_buf, "Sentencias_Adjuntas.pdf", use_container_width=True)
