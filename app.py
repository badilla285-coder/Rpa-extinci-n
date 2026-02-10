import streamlit as st
from docx import Document
from docx.shared import Pt
import PyPDF2
import io

def crear_escrito(datos, texto_condena):
    doc = Document()
    style = doc.styles['Normal']
    style.font.name = 'Arial'
    style.font.size = Pt(12)

    # 1. ENCABEZADO Y SUMILLA
    p = doc.add_paragraph()
    p.add_run("SUMILLA: SOLICITA DECLARACIÓN DE EXTINCIÓN DE RESPONSABILIDAD PENAL POR CONDENA DE ADULTO.\n").bold = True
    
    # Listado de causas en el encabezado
    for causa in datos['causas']:
        p.add_run(f"RIT: {causa['rit']} / RUC: {causa['ruc']}\n")
    p.add_run(f"TRIBUNAL: {datos['juzgado']}\n")

    doc.add_paragraph("\nEN LO PRINCIPAL: SOLICITA DECLARACIÓN DE EXTINCIÓN DE RESPONSABILIDAD PENAL; OTROSÍ: ACOMPAÑA DOCUMENTO.")
    
    p_juez = doc.add_paragraph()
    p_juez.add_run(f"\nS.J.L. DE GARANTÍA DE {datos['juzgado'].upper()}").bold = True

    cuerpo = doc.add_paragraph()
    cuerpo.add_run(f"\n{datos['nombre_defensor']}, abogado de la Defensoría Penal Pública, en representación del adolescente {datos['nombre_adolescente']}, en las causas ya individualizadas, a SS. con respeto digo:\n")
    
    # Redacción para múltiples causas
    texto_causas = ", ".join([f"RIT {c['rit']}" for c in datos['causas']])
    cuerpo.add_run(f"\nQue, por este acto y conforme a lo previsto en la Ley 20.084, vengo en solicitar se declare la extinción de la responsabilidad penal de mi representado en las causas {texto_causas}. ")
    cuerpo.add_run("Esta solicitud se funda en que el adolescente ha sido condenado por un tribunal de adultos a una pena privativa de libertad, circunstancia que genera una incompatibilidad material y jurídica con la ejecución de las sanciones impuestas en el sistema de responsabilidad penal adolescente, operando la extinción de conformidad a los principios de proporcionalidad y coherencia punitiva.\n")

    # 2. FUNDAMENTOS TRANSCRITOS (Transcripción completa de la resolución)
    doc.add_paragraph("\nFUNDAMENTOS DE LA O LAS CONDENAS DE ADULTO QUE SE ADJUNTAN:").bold = True
    doc.add_paragraph(texto_condena)
    
    # 3. PETITORIO
    p_final = doc.add_paragraph()
    p_final.add_run("\nPOR TANTO, de acuerdo a lo dispuesto en la Ley 20.084 y las normas generales sobre extinción de responsabilidad penal del Código Penal:\n")
    p_final.add_run("SOLICITO A SS. tener por solicitada la extinción de las causas señaladas, declarar la misma y ordenar el archivo definitivo de los antecedentes.").bold = True

    target = io.BytesIO()
    doc.save(target)
    target.seek(0)
    return target

# --- INTERFAZ STREAMLIT ---
st.set_page_config(page_title="Generador RPA Multi-Causa", layout="wide")
st.title("⚖️ Generador de Extinciones (Múltiples Causas)")

with st.sidebar:
    st.header("Datos del Defensor")
    nombre_defensor = st.text_input("Nombre y Apellido")
    nombre_adolescente = st.text_input("Nombre del Adolescente")
    juzgado = st.text_input("Juzgado de Ejecución (Ej: San Bernardo)")

st.subheader("Causas RPA a Extinguir")
# Usamos el estado de la sesión para manejar múltiples causas
if 'num_causas' not in st.session_state:
    st.session_state.num_causas = 1

col_btn1, col_btn2 = st.columns(2)
with col_btn1:
    if st.button("➕ Añadir otra causa"):
        st.session_state.num_causas += 1
with col_btn2:
    if st.button("➖ Quitar última causa") and st.session_state.num_causas > 1:
        st.session_state.num_causas -= 1

causas_data = []
for i in range(st.session_state.num_causas):
    c1, c2 = st.columns(2)
    with c1:
        ruc_i = st.text_input(f"RUC causa {i+1}", key=f"ruc_{i}")
    with c2:
        rit_i = st.text_input(f"RIT causa {i+1}", key=f"rit_{i}")
    causas_data.append({"ruc": ruc_i, "rit": rit_i})

st.divider()
pdf_file = st.file_uploader("Insertar PDF con condena(s) de adulto", type="pdf")

if st.button("Generar Escrito Robusto"):
    if not pdf_file or not nombre_defensor or not causas_data[0]['rit']:
        st.error("Por favor complete los datos del defensor y al menos una causa.")
    else:
        try:
            reader = PyPDF2.PdfReader(pdf_file)
            texto_pdf = ""
            for page in reader.pages:
                texto_pdf += page.extract_text() + "\n"

            datos_finales = {
                "nombre_defensor": nombre_defensor,
                "nombre_adolescente": nombre_adolescente,
                "juzgado": juzgado,
                "causas": causas_data
            }

            archivo = crear_escrito(datos_finales, texto_pdf)
            st.success("✅ Escrito para múltiples causas generado correctamente.")
            st.download_button(
                label="📥 Descargar Escrito Word",
                data=archivo,
                file_name=f"Extincion_Multiple_{nombre_adolescente}.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )
        except Exception as e:
            st.error(f"Error al procesar: {e}")
