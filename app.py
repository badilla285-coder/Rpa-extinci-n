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

    # SUMILLA
    p = doc.add_paragraph()
    p.add_run("SUMILLA: SOLICITA DECLARACIÓN DE EXTINCIÓN DE RESPONSABILIDAD PENAL.\n").bold = True
    for c in datos['causas']:
        # Se incluye el juzgado específico de cada causa en la sumilla
        p.add_run(f"RIT: {c['rit']} / RUC: {c['ruc']} - JUZGADO: {c['juzgado_causa']}\n")
    p.add_run(f"TRIBUNAL DE EJECUCIÓN: {datos['juzgado_presentacion']}\n")

    doc.add_paragraph("\nEN LO PRINCIPAL: SOLICITA DECLARACIÓN DE EXTINCIÓN; OTROSÍ: ACOMPAÑA DOCUMENTO.")
    
    p_juez = doc.add_paragraph()
    p_juez.add_run(f"\nS.J.L. DE GARANTÍA DE {datos['juzgado_presentacion'].upper()}").bold = True

    cuerpo = doc.add_paragraph()
    cuerpo.add_run(f"\n{datos['nombre_defensor']}, defensor penal público, por el adolescente {datos['nombre_adolescente']}, en las causas ya individualizadas, a SS. con respeto digo:\n")
    
    # Construcción del listado de causas para el cuerpo del escrito
    texto_causas = ""
    for c in datos['causas']:
        texto_causas += f"- RIT {c['rit']}, RUC {c['ruc']} del Juzgado de Garantía de {c['juzgado_causa']}.\n"
    
    cuerpo.add_run(f"\nQue, de conformidad a la Ley 20.084, solicito se declare la extinción de la responsabilidad penal en las siguientes causas: \n{texto_causas}\nLo anterior, por haber sido mi representado condenado por un tribunal de adultos a una pena privativa de libertad, lo que resulta incompatible con la ejecución de las sanciones RPA.\n")

    # TRANSCRIPCIÓN DEL PDF
    doc.add_paragraph(texto_condena)
    
    p_final = doc.add_paragraph()
    p_final.add_run("\nPOR TANTO, de acuerdo a la Ley 20.084 y normas de extinción del Código Penal:\n")
    p_final.add_run("SOLICITO A SS. declarar la extinción y el archivo de los antecedentes.").bold = True

    target = io.BytesIO()
    doc.save(target)
    target.seek(0)
    return target

st.set_page_config(page_title="Generador RPA")
st.title("⚖️ Generador de Extinciones")

# Datos fijos arriba
nombre_defensor = st.text_input("Nombre Defensor", value="Ignacio Badilla Lara")
nombre_adolescente = st.text_input("Nombre Adolescente")
juzgado_presentacion = st.text_input("Juzgado de Ejecución (Donde se envía)")

st.markdown("---")
st.subheader("Causas RPA")

if 'n_causas' not in st.session_state:
    st.session_state.n_causas = 1

col_btn1, col_btn2 = st.columns([0.2, 0.8])
with col_btn1:
    if st.button("➕"):
        st.session_state.n_causas += 1
with col_btn2:
    if st.button("➖") and st.session_state.n_causas > 1:
        st.session_state.n_causas -= 1

causas_lista = []

# Bucle para generar los campos de cada causa
for i in range(st.session_state.n_causas):
    st.write(f"### Causa {i+1}")
    ruc_v = st.text_input(f"RUC de la causa {i+1}", key=f"ruc_{i}")
    rit_v = st.text_input(f"RIT de la causa {i+1}", key=f"rit_{i}")
    juz_v = st.text_input(f"Juzgado donde fue sancionado (Causa {i+1})", key=f"juz_{i}")
    
    causas_lista.append({
        "ruc": ruc_v, 
        "rit": rit_v, 
        "juzgado_causa": juz_v
    })
    st.markdown("---") # Línea divisoria para separar visualmente cada bloque de causa

# Carga de archivo
pdf_file = st.file_uploader("Adjuntar PDF Condena Adulto", type="pdf")

if st.button("Generar Escrito"):
    if not pdf_file or not nombre_defensor:
        st.error("Faltan datos obligatorios o el PDF.")
    else:
        try:
            reader = PyPDF2.PdfReader(pdf_file)
            txt_pdf = ""
            for page in reader.pages:
                txt_pdf += page.extract_text() + "\n"
            
            info = {
                "nombre_defensor": nombre_defensor,
                "nombre_adolescente": nombre_adolescente,
                "juzgado_presentacion": juzgado_presentacion,
                "causas": causas_lista
            }
            
            doc_word = crear_escrito(info, txt_pdf)
            st.success("Escrito generado correctamente.")
            st.download_button(
                "📥 Descargar Word", 
                doc_word, 
                f"Extincion_{nombre_adolescente.replace(' ', '_')}.docx"
            )
        except Exception as e:
            st.error(f"Error: {e}")

st.caption("Aplicación hecha por Ignacio Badilla Lara")
