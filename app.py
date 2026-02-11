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
        """Extrae el texto íntegro del buffer del PDF subido."""
        try:
            # Leemos el archivo desde el buffer de Streamlit
            doc = fitz.open(stream=archivo_pdf.read(), filetype="pdf")
            texto = ""
            for pagina in doc:
                texto += f"\n--- PÁGINA {pagina.number + 1} ---\n"
                texto += pagina.get_text("text")
            
            if not texto.strip() or len(texto) < 50:
                return None
            return texto
        except Exception as e:
            st.error(f"Error técnico al procesar el PDF: {e}")
            return None

    def crear_escrito(self, datos, texto_sentencia):
        """Genera el documento Word con formato profesional."""
        doc = Document()
        
        # Configuración de márgenes
        for section in doc.sections:
            section.left_margin = Inches(1.2)
            section.right_margin = Inches(1.0)

        def aplicar_estilo(parrafo, negrita=False, alineacion=WD_ALIGN_PARAGRAPH.JUSTIFY, size=None):
            parrafo.alignment = alineacion
            run = parrafo.add_run()
            run.font.name = self.fuente
            run.font.size = Pt(size if size else self.tamaño_cuerpo)
            run.bold = negrita
            return run

        # 1. ENCABEZADO DPP
        h = doc.add_paragraph("Defensoría Penal Pública\nSin defensa no hay Justicia")
        aplicar_estilo(h, alineacion=WD_ALIGN_PARAGRAPH.LEFT)

        # 2. SUMA (Formato tabla para alineación derecha)
        table = doc.add_table(rows=1, cols=2)
        table.columns[0].width = Inches(3.0)
        cell = table.cell(0, 1)
        p_suma = cell.paragraphs[0]
        r_s = p_suma.add_run("EN LO PRINCIPAL: SOLICITA EXTINCIÓN DE SANCIONES ART. 25 TER Y QUINQUIES LEY 20.084;\nOTROSÍ: ACOMPAÑA DOCUMENTO.")
        r_s.bold = True
        r_s.font.name = self.fuente
        r_s.font.size = Pt(11)

        # 3. TRIBUNAL
        t = doc.add_paragraph(f"\nS.J.L. DE GARANTÍA DE {datos['tribunal'].upper()}")
        aplicar_estilo(t, negrita=True)

        # 4. COMPARECENCIA
        c_text = (f"\n{datos['nombre'].upper()}, Postulante de la Corporación de Asistencia Judicial, "
                  f"en representación de {datos['imputado'].upper()}, en causa RIT: {datos['rit_rpa']}, "
                  f"RUC: {datos['ruc_rpa']}, a S.S. con respeto digo:")
        aplicar_estilo(doc.add_paragraph(c_text))

        # 5. SOLICITUD
        p1 = doc.add_paragraph("\nQue, por este acto, vengo en solicitar se declare la extinción de pleno derecho de las sanciones...")
        aplicar_estilo(p1)

        # 6. ANTECEDENTES RPA
        p2_h = doc.add_paragraph("\nI. ANTECEDENTES CAUSA RPA")
        aplicar_estilo(p2_h, negrita=True)
        p2_d = doc.add_paragraph(f"Sancionado por el Tribunal de {datos['comuna_rpa']} a la pena de {datos['pena_rpa']}.")
        aplicar_estilo(p2_d)

        # 7. TRANSCRIPCIÓN ÍNTEGRA (Lo más importante)
        p3_h = doc.add_paragraph("\nII. SENTENCIA CAUSA ADULTO - TRANSCRIPCIÓN ÍNTEGRA:")
        aplicar_estilo(p3_h, negrita=True)
        
        # Insertamos el texto completo del PDF
        p_sentencia = doc.add_paragraph(texto_sentencia)
        aplicar_estilo(p_sentencia)

        # 8. PETITORIA
        aplicar_estilo(doc.add_paragraph("\nPOR TANTO,"))
        p_fin = doc.add_paragraph("SOLICITO A S.S. tener por interpuesta la solicitud y declarar la extinción de la sanción referida.")
        aplicar_estilo(p_fin)

        # Guardar en buffer de memoria
        target = io.BytesIO()
        doc.save(target)
        target.seek(0)
        return target

# --- CONFIGURACIÓN DE LA INTERFAZ STREAMLIT ---
st.set_page_config(page_title="Generador RPA", page_icon="⚖️")

st.title("⚖️ Solicitud de Extinción RPA")
st.info("Sube la sentencia de adulto para transcribirla íntegramente en el escrito.")

# Sidebar para datos
with st.sidebar:
    st.header("📋 Datos del Escrito")
    nombre = st.text_input("Tu Nombre (Abogado/Postulante)", "IGNACIO BADILLA LARA")
    imputado = st.text_input("Nombre del Imputado")
    rit = st.text_input("RIT Causa RPA")
    ruc = st.text_input("RUC Causa RPA")
    tribunal = st.text_input("Tribunal de Garantía (Ej: San Bernardo)")
    comuna = st.text_input("Comuna Sentencia RPA")
    pena = st.text_input("Pena RPA impuesta")

# Área principal
uploaded_file = st.file_uploader("Subir Sentencia de Adulto (PDF)", type="pdf")

if uploaded_file:
    gen = GeneradorJuridico()
    texto_extraido = gen.leer_sentencia(uploaded_file)
    
    if texto_extraido:
        st.success("✅ Texto extraído correctamente.")
        
        # --- PREVISUALIZACIÓN ---
        with st.expander("🔍 Ver previsualización de la transcripción"):
            st.text_area("Contenido extraído del PDF:", texto_extraido, height=300)
        
        # Botón de generación
        if st.button("🚀 Generar Escrito Word"):
            if not imputado or not rit:
                st.error("Faltan datos obligatorios (Nombre del imputado o RIT).")
            else:
                datos = {
                    "nombre": nombre, "imputado": imputado, "rit_rpa": rit,
                    "ruc_rpa": ruc, "tribunal": tribunal, "comuna_rpa": comuna,
                    "pena_rpa": pena
                }
                docx_buffer = gen.crear_escrito(datos, texto_extraido)
                
                st.download_button(
                    label="⬇️ Descargar Escrito .docx",
                    data=docx_buffer,
                    file_name=f"Extincion_{imputado.replace(' ', '_')}.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                )
    else:
        st.error("No se pudo extraer texto. El PDF podría ser una imagen escaneada.")
