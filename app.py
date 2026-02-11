import streamlit as st
import fitz  # PyMuPDF
from docx import Document
from docx.shared import Pt, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
import io
import re

class GeneradorJuridico:
    def __init__(self):
        self.fuente = "Century Gothic"
        self.tamaño_cuerpo = 11

    def extraer_datos_inteligente(self, texto):
        """Intenta encontrar RIT, RUC y Tribunal automáticamente en el texto."""
        datos = {
            "rit": "",
            "ruc": "",
            "tribunal": "San Bernardo",
            "imputado": ""
        }
        # Patrón RIT: números - año
        rit_match = re.search(r"\b(\d+-\d{4})\b", texto)
        if rit_match: datos["rit"] = rit_match.group(1)
        
        # Patrón RUC: números - dígito
        ruc_match = re.search(r"\b(\d{10}-\w)\b", texto)
        if ruc_match: datos["ruc"] = ruc_match.group(1)
        
        # Intento de Tribunal
        if "GARANTIA DE" in texto.upper():
            trib_match = re.search(r"GARANTIA DE\s+([A-Z\sáéíóúÁÉÍÓÚ]+)", texto.upper())
            if trib_match: datos["tribunal"] = trib_match.group(1).strip()
            
        return datos

    def leer_sentencia(self, archivo_pdf):
        try:
            pdf_bytes = archivo_pdf.read()
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            texto = ""
            for pagina in doc:
                texto += f"\n--- PÁGINA {pagina.number + 1} ---\n"
                texto += pagina.get_text("text")
            doc.close()
            return texto
        except Exception as e:
            st.error(f"Error al leer el PDF: {e}")
            return None

    def crear_escrito(self, datos, texto_sentencia):
        doc = Document()
        for section in doc.sections:
            section.left_margin, section.right_margin = Inches(1.2), Inches(1.0)

        def aplicar_estilo(parrafo, negrita=False, alineacion=WD_ALIGN_PARAGRAPH.JUSTIFY):
            parrafo.alignment = alineacion
            run = parrafo.add_run()
            run.font.name = self.fuente
            run.font.size = Pt(self.tamaño_cuerpo)
            run.bold = negrita
            return run

        # Encabezado
        h = doc.add_paragraph("Defensoría Penal Pública\nSin defensa no hay Justicia")
        aplicar_estilo(h, alineacion=WD_ALIGN_PARAGRAPH.LEFT)

        # SUMA PROFESIONAL (Alineada a la derecha)
        table = doc.add_table(rows=1, cols=2)
        table.columns[0].width = Inches(3.5)
        p_suma = table.cell(0, 1).paragraphs[0]
        r_s = p_suma.add_run("EN LO PRINCIPAL: SOLICITA EXTINCIÓN DE SANCIONES ART. 25 TER Y QUINQUIES LEY 20.084;\nOTROSÍ: ACOMPAÑA DOCUMENTO.")
        r_s.bold, r_s.font.name, r_s.font.size = True, self.fuente, Pt(11)

        # Tribunal y Comparecencia
        aplicar_estilo(doc.add_paragraph(f"\nS.J.L. DE GARANTÍA DE {datos['tribunal'].upper()}"), negrita=True)
        
        c_text = (f"\n{datos['nombre'].upper()}, Postulante, Defensoría Penal Pública San Bernardo, "
                  f"en representación de {datos['imputado'].upper()}, en causa RIT: {datos['rit_rpa']}, "
                  f"RUC: {datos['ruc_rpa']}, a S.S., respetuosamente digo:")
        aplicar_estilo(doc.add_paragraph(c_text))

        # Cuerpo
        aplicar_estilo(doc.add_paragraph("\nQue, vengo en solicitar que declare la extinción de las sanciones de la Ley 20.084..."))
        
        aplicar_estilo(doc.add_paragraph(f"\nI. ANTECEDENTES CAUSA RPA"), negrita=True)
        aplicar_estilo(doc.add_paragraph(f"Sancionado por el Juzgado de Garantía de {datos['comuna_rpa']} a la pena de {datos['pena_rpa']}."))

        aplicar_estilo(doc.add_paragraph("\nII. SENTENCIA CAUSA ADULTO - TRANSCRIPCIÓN ÍNTEGRA:"), negrita=True)
        aplicar_estilo(doc.add_paragraph(texto_sentencia))

        aplicar_estilo(doc.add_paragraph("\nIII. FUNDAMENTOS JURÍDICOS"), negrita=True)
        fundamento = ("Se hace presente que el artículo 25 ter en su inciso tercero establece que se considerará más grave "
                      "el delito que tuviere asignada una mayor pena... configurándose los presupuestos para la extinción.")
        aplicar_estilo(doc.add_paragraph(fundamento))

        aplicar_estilo(doc.add_paragraph("\nPOR TANTO,"))
        aplicar_estilo(doc.add_paragraph("SOLICITO A S.S. acceder a lo solicitado extinguiendo de pleno derecho la sanción referida."))

        target = io.BytesIO()
        doc.save(target)
        target.seek(0)
        return target

# --- INTERFAZ STREAMLIT ---
st.set_page_config(page_title="Generador RPA Nacho", page_icon="⚖️", layout="centered")

st.title("⚖️ Generador Inteligente RPA")
st.write("Sube la sentencia y el sistema rellenará los campos automáticamente.")

# 1. Carga de Archivo
archivo = st.file_uploader("📂 Primero, sube la Sentencia de Adulto (PDF)", type="pdf")

# Inicializar estados para los campos
if "datos_extraidos" not in st.session_state:
    st.session_state.datos_extraidos = {"rit": "", "ruc": "", "tribunal": "San Bernardo", "texto": ""}

if archivo:
    gen = GeneradorJuridico()
    texto = gen.leer_sentencia(archivo)
    if texto:
        st.session_state.datos_extraidos["texto"] = texto
        auto = gen.extraer_datos_inteligente(texto)
        st.session_state.datos_extraidos["rit"] = auto["rit"]
        st.session_state.datos_extraidos["ruc"] = auto["ruc"]
        st.session_state.datos_extraidos["tribunal"] = auto["tribunal"]
        st.success("✅ Datos sugeridos extraídos del PDF")

st.markdown("---")

# 2. Formulario Principal (Sin pestañas)
col1, col2 = st.columns(2)

with col1:
    nombre_post = st.text_input("Postulante", "IGNACIO BADILLA LARA")
    imputado = st.text_input("Nombre Imputado", placeholder="Ej: JUAN PEREZ")
    rit = st.text_input("RIT Causa RPA", value=st.session_state.datos_extraidos["rit"])
    ruc = st.text_input("RUC Causa RPA", value=st.session_state.datos_extraidos["ruc"])

with col2:
    tribunal = st.text_input("Juzgado de Garantía", value=st.session_state.datos_extraidos["tribunal"])
    comuna_rpa = st.text_input("Comuna Sentencia RPA", placeholder="Ej: San Bernardo")
    pena_rpa = st.text_input("Pena RPA impuesta", placeholder="Ej: 2 años de libertad asistida")

st.markdown("---")

# 3. Acciones Finales
if st.session_state.datos_extraidos["texto"]:
    with st.expander("🔍 Revisar Texto del PDF que se incluirá"):
        st.text_area("Transcripción:", st.session_state.datos_extraidos["texto"], height=200)

    if st.button("🚀 GENERAR ESCRITO COMPLETO", use_container_width=True):
        if not imputado or not rit:
            st.warning("⚠️ Completa el nombre del imputado y el RIT antes de continuar.")
        else:
            gen = GeneradorJuridico()
            datos_finales = {
                "nombre": nombre_post, "imputado": imputado, "rit_rpa": rit,
                "ruc_rpa": ruc, "tribunal": tribunal, "comuna_rpa": comuna_rpa,
                "pena_rpa": pena_rpa
            }
            docx = gen.crear_escrito(datos_finales, st.session_state.datos_extraidos["texto"])
            
            st.download_button(
                label="⬇️ DESCARGAR DOCUMENTO WORD",
                data=docx,
                file_name=f"Extincion_{imputado.replace(' ', '_')}.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                use_container_width=True
            )
