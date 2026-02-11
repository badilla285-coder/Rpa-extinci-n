      import streamlit as st
import fitz  # PyMuPDF
from docx import Document
from docx.shared import Pt, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
import io

class GeneradorJuridico:
    def __init__(self):
        self.fuente = "Century Gothic"
        self.tamaño_cuerpo = 11

    def leer_sentencia(self, archivo_pdf):
        try:
            # Importante: No cerramos el stream manualmente, dejamos que fitz lo maneje
            pdf_bytes = archivo_pdf.read()
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            texto = ""
            for pagina in doc:
                texto += f"\n--- PÁGINA {pagina.number + 1} ---\n"
                texto += pagina.get_text("text")
            doc.close()
            
            if not texto.strip():
                return None
            return texto
        except Exception as e:
            st.error(f"Error técnico al procesar el PDF: {e}")
            return None

    def crear_escrito(self, datos, texto_sentencia):
        doc = Document()
        for section in doc.sections:
            section.left_margin = Inches(1.2)
            section.right_margin = Inches(1.0)

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

        # Suma
        table = doc.add_table(rows=1, cols=2)
        cell = table.cell(0, 1)
        p_suma = cell.paragraphs[0]
        r_s = p_suma.add_run("EN LO PRINCIPAL: SOLICITA EXTINCIÓN DE SANCIONES ART. 25 TER Y QUINQUIES LEY 20.084;\nOTROSÍ: ACOMPAÑA DOCUMENTO.")
        r_s.bold = True
        r_s.font.name = self.fuente

        # Cuerpo
        aplicar_estilo(doc.add_paragraph(f"\nS.J.L. DE GARANTÍA DE {datos['tribunal'].upper()}"), negrita=True)
        
        c_text = (f"\n{datos['nombre'].upper()}, en representación de {datos['imputado'].upper()}, "
                  f"en causa RIT: {datos['rit_rpa']}, RUC: {datos['ruc_rpa']}, a S.S. con respeto digo:")
        aplicar_estilo(doc.add_paragraph(c_text))

        aplicar_estilo(doc.add_paragraph("\nI. ANTECEDENTES CAUSA RPA"), negrita=True)
        aplicar_estilo(doc.add_paragraph(f"Sancionado por el Tribunal de {datos['comuna_rpa']} a la pena de {datos['pena_rpa']}."))

        aplicar_estilo(doc.add_paragraph("\nII. SENTENCIA CAUSA ADULTO - TRANSCRIPCIÓN ÍNTEGRA:"), negrita=True)
        # Transcripción completa
        aplicar_estilo(doc.add_paragraph(texto_sentencia))

        aplicar_estilo(doc.add_paragraph("\nPOR TANTO,"))
        aplicar_estilo(doc.add_paragraph("SOLICITO A S.S. tener por interpuesta la solicitud y declarar la extinción de la sanción referida."))

        target = io.BytesIO()
        doc.save(target)
        target.seek(0)
        return target

# --- INTERFAZ ---
st.set_page_config(page_title="Generador RPA", page_icon="⚖️")

st.title("⚖️ Solicitud de Extinción RPA")

# Usamos columnas para organizar mejor y evitar saltos visuales que causen el error de Node
col1, col2 = st.columns([1, 1])

with st.sidebar:
    st.header("📋 Datos del Escrito")
    nombre = st.text_input("Nombre Abogado/Postulante", "IGNACIO BADILLA LARA", key="inp_nom")
    imputado = st.text_input("Nombre del Imputado", key="inp_imp")
    rit = st.text_input("RIT Causa RPA", key="inp_rit")
    ruc = st.text_input("RUC Causa RPA", key="inp_ruc")
    tribunal = st.text_input("Tribunal (Ej: San Bernardo)", key="inp_trib")
    comuna = st.text_input("Comuna Sentencia RPA", key="inp_com")
    pena = st.text_input("Pena RPA impuesta", key="inp_pena")

uploaded_file = st.file_uploader("Subir Sentencia de Adulto (PDF)", type="pdf", key="file_up")

if uploaded_file is not None:
    # Para evitar el error de removeChild, procesamos y guardamos el texto en el estado de la sesión
    if 'texto_pdf' not in st.session_state:
        gen = GeneradorJuridico()
        with st.spinner("Leyendo PDF..."):
            st.session_state.texto_pdf = gen.leer_sentencia(uploaded_file)

    if st.session_state.texto_pdf:
        st.success("✅ Texto extraído correctamente.")
        
        with st.expander("🔍 Ver transcripción completa"):
            st.text_area("Contenido:", st.session_state.texto_pdf, height=250, key="txt_preview")
        
        if st.button("🚀 Generar Escrito Word", key="btn_gen"):
            if imputado and rit:
                gen = GeneradorJuridico()
                datos = {
                    "nombre": nombre, "imputado": imputado, "rit_rpa": rit,
                    "ruc_rpa": ruc, "tribunal": tribunal, "comuna_rpa": comuna,
                    "pena_rpa": pena
                }
                docx_buffer = gen.crear_escrito(datos, st.session_state.texto_pdf)
                
                st.download_button(
                    label="⬇️ Descargar Escrito .docx",
                    data=docx_buffer,
                    file_name=f"Extincion_{imputado.replace(' ', '_')}.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    key="btn_dl"
                )
            else:
                st.error("Faltan datos obligatorios.")
else:
    # Si se quita el archivo, limpiamos el estado
    if 'texto_pdf' in st.session_state:
        del st.session_state.texto_pdf
