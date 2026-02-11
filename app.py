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
        """Extrae el texto íntegro para cumplir con tu instrucción de no resumir."""
        try:
            pdf_bytes = archivo_pdf.read()
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            texto = ""
            for pagina in doc:
                texto += f"\n--- PÁGINA {pagina.number + 1} ---\n"
                texto += pagina.get_text("text")
            doc.close()
            return texto if texto.strip() else None
        except Exception as e:
            st.error(f"Error técnico al procesar el PDF: {e}")
            return None

    def aplicar_estilo(self, parrafo, negrita=False, alineacion=WD_ALIGN_PARAGRAPH.JUSTIFY):
        parrafo.alignment = alineacion
        run = parrafo.add_run()
        run.font.name = self.fuente
        run.font.size = Pt(self.tamaño_cuerpo)
        run.bold = negrita
        return run

    def crear_escrito(self, datos, texto_sentencia):
        doc = Document()
        
        # Configuración de márgenes profesionales (Estándar CAJ/DPP)
        for section in doc.sections:
            section.left_margin = Inches(1.2)
            section.right_margin = Inches(1.0)

        # 1. Encabezado DPP
        h = doc.add_paragraph("Defensoría Penal Pública\nSin defensa no hay Justicia")
        self.aplicar_estilo(h, alineacion=WD_ALIGN_PARAGRAPH.LEFT)

        # 2. SUMA PROFESIONAL (Usando tabla para alinear a la derecha)
        table = doc.add_table(rows=1, cols=2)
        table.columns[0].width = Inches(3.5)
        p_suma = table.cell(0, 1).paragraphs[0]
        r_s = p_suma.add_run("EN LO PRINCIPAL: SOLICITA EXTINCIÓN DE SANCIONES ART. 25 TER Y QUINQUIES LEY 20.084;\nOTROSÍ: ACOMPAÑA DOCUMENTO.")
        r_s.bold = True
        r_s.font.name = self.fuente
        r_s.font.size = Pt(11)

        # 3. Tribunal
        t = doc.add_paragraph(f"\nS.J.L. DE GARANTÍA DE {datos.get('tribunal', 'SAN BERNARDO').upper()}")
        self.aplicar_estilo(t, negrita=True)

        # 4. Comparecencia (Datos de Ignacio Badilla)
        c = doc.add_paragraph(
            f"\n{datos.get('nombre', 'IGNACIO BADILLA LARA').upper()}, Postulante, Defensoría Penal Pública, "
            f"en representación de {datos.get('imputado', '________________')}, en causa RIT: {datos.get('rit_rpa', '____')}, "
            f"RUC: {datos.get('ruc_rpa', '____')}, a S.S., respetuosamente digo:"
        )
        self.aplicar_estilo(c)

        # 5. Solicitud Normativa
        p1 = doc.add_paragraph(
            "\nQue, vengo en solicitar que declare la extinción de las sanciones de la Ley de "
            "Responsabilidad Penal Adolescente, en virtud del artículo 25 ter y 25 quinquies de la Ley 20.084."
        )
        self.aplicar_estilo(p1)

        # 6. Antecedentes Causa RPA
        p2 = doc.add_paragraph(f"\nI. ANTECEDENTES CAUSA RPA")
        self.aplicar_estilo(p2, negrita=True)
        p2_det = doc.add_paragraph(f"Sancionado por el Juzgado de Garantía de {datos.get('comuna_rpa', '____')} a la pena de {datos.get('pena_rpa', '____')}.")
        self.aplicar_estilo(p2_det)

        # 7. Transcripción Íntegra Sentencia Adulto
        p3 = doc.add_paragraph("\nII. SENTENCIA CAUSA ADULTO (TRANSCRIPCIÓN ÍNTEGRA):")
        self.aplicar_estilo(p3, negrita=True)
        p_texto = doc.add_paragraph(texto_sentencia)
        self.aplicar_estilo(p_texto)

        # 8. Fundamento Jurídico (Modelo Alarcón)
        p4 = doc.add_paragraph("\nIII. FUNDAMENTOS JURÍDICOS")
        self.aplicar_estilo(p4, negrita=True)
        fundamento = (
            "Se hace presente que el artículo 25 ter en su inciso tercero establece que se "
            "considerará más grave el delito o conjunto de ellos que tuviere asignada en la ley una "
            "mayor pena de conformidad con las reglas generales. En el presente caso, la sanción "
            "impuesta como adulto reviste una mayor gravedad, configurándose así los presupuestos para la extinción."
        )
        self.aplicar_estilo(doc.add_paragraph(fundamento))

        # 9. Petitoria
        self.aplicar_estilo(doc.add_paragraph("\nPOR TANTO,"))
        p6 = doc.add_paragraph("SOLICITO A S.S. acceder a lo solicitado extinguiendo de pleno derecho la sanción referida.")
        self.aplicar_estilo(p6)

        target = io.BytesIO()
        doc.save(target)
        target.seek(0)
        return target

# --- INTERFAZ PRO DE STREAMLIT ---
st.set_page_config(page_title="Generador RPA Nacho", page_icon="⚖️", layout="wide")

st.title("⚖️ Generador de Escritos - Defensoría")
st.markdown("---")

with st.sidebar:
    st.header("📋 Datos de la Causa")
    nombre = st.text_input("Postulante", "IGNACIO BADILLA LARA", key="p_nom")
    imputado = st.text_input("Nombre Imputado", key="p_imp")
    rit = st.text_input("RIT Causa RPA", key="p_rit")
    ruc = st.text_input("RUC Causa RPA", key="p_ruc")
    tribunal = st.text_input("Juzgado de Garantía", "San Bernardo", key="p_tri")
    comuna_rpa = st.text_input("Comuna Sentencia RPA", key="p_com")
    pena_rpa = st.text_input("Pena RPA impuesta", key="p_pena")

uploaded_file = st.file_uploader("📂 Subir Sentencia Adulto (PDF)", type="pdf")

if uploaded_file:
    # Usamos session_state para que la previsualización no se rompa al interactuar
    if 'pdf_text' not in st.session_state:
        gen = GeneradorJuridico()
        st.session_state.pdf_text = gen.leer_sentencia(uploaded_file)

    if st.session_state.pdf_text:
        st.success("✅ Texto extraído íntegramente.")
        
        # Módulo de previsualización que pediste
        with st.expander("🔍 Revisar Transcripción Íntegra (No resumida)"):
            st.text_area("Contenido extraído:", st.session_state.pdf_text, height=300)
        
        if st.button("🚀 Generar Escrito Profesional", use_container_width=True):
            if not imputado or not rit:
                st.warning("⚠️ Debes completar al menos el Nombre del Imputado y el RIT.")
            else:
                gen = GeneradorJuridico()
                datos_form = {
                    "nombre": nombre, "imputado": imputado, "rit_rpa": rit,
                    "ruc_rpa": ruc, "tribunal": tribunal, "comuna_rpa": comuna_rpa,
                    "pena_rpa": pena_rpa
                }
                docx_file = gen.crear_escrito(datos_form, st.session_state.pdf_text)
                
                st.download_button(
                    label="⬇️ Descargar Escrito .docx",
                    data=docx_file,
                    file_name=f"Extincion_{imputado.replace(' ', '_')}.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    use_container_width=True
                )
