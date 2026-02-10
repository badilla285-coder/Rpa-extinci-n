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
    
    p.add_run(f"TRIBUNAL DE EJECUCIÓN: {datos['juzgado_presentacion']}\n")
    for c in datos['causas_ejecucion']:
        p.add_run(f"RIT: {c['rit']} / RUC: {c['ruc']} (Ejecución)\n")
    
    p.add_run("\nCAUSAS A EXTINGUIR:\n")
    for c in datos['causas_origen']:
        p.add_run(f"RIT: {c['rit']} / RUC: {c['ruc']} - JUZGADO: {c['juzgado_causa']}\n")

    doc.add_paragraph("\nEN LO PRINCIPAL: SOLICITA DECLARACIÓN DE EXTINCIÓN; OTROSÍ: ACOMPAÑA DOCUMENTO.")
    
    p_juez = doc.add_paragraph()
    p_juez.add_run(f"\nS.J.L. DE GARANTÍA DE {datos['juzgado_presentacion'].upper()}").bold = True

    cuerpo = doc.add_paragraph()
    cuerpo.add_run(f"\n{datos['nombre_defensor']}, defensor penal público, por el adolescente {datos['nombre_adolescente']}, en las causas de ejecución ya individualizadas, a SS. con respeto digo:\n")
    
    # Listado para el cuerpo
    texto_origen = "\n".join([f"- RIT {c['rit']} del Juzgado de {c['juzgado_causa']} (RUC {c['ruc']})" for c in datos['causas_origen']])
    
    cuerpo.add_run(f"\nQue, de conformidad a la Ley 20.084, solicito se declare la extinción de la responsabilidad penal respecto de las siguientes sanciones sancionadas originalmente en:\n{texto_origen}\n\nLo anterior, por haber sido mi representado condenado por un tribunal de adultos a una pena privativa de libertad, según se acredita en documento adjunto.\n")

    # TRANSCRIPCIÓN PDF
    doc.add_paragraph(texto_condena)
    
    p_final = doc.add_paragraph()
    p_final.add_run("\nPOR TANTO, de acuerdo a la Ley 20.084:\n")
    p_final.add_run("SOLICITO A SS. declarar la extinción y el archivo de los antecedentes.").bold = True

    target = io.BytesIO()
    doc.save(target)
    target.seek(0)
    return target

st.set_page_config(page_title="Generador RPA")
st.title("⚖️ Generador de Extinciones")

# Datos Personales
nombre_defensor = st.text_input("Nombre Defensor", value="Ignacio Badilla Lara")
nombre_adolescente = st.text_input("Nombre Adolescente")
juzgado_presentacion = st.text_input("Juzgado de Ejecución (S.J.L.)")

# SECCIÓN 1: CAUSAS EN EJECUCIÓN (ARRIBA)
st.markdown("### 1. Causas en el Tribunal de Ejecución")
if 'n_ejecucion' not in st.session_state: st.session_state.n_ejecucion = 1

c_ej1, c_ej2 = st.columns(2)
with c_ej1:
    if st.button("➕ Ejecución"): st.session_state.n_ejecucion += 1
with c_ej2:
    if st.button("➖ Ejecución") and st.session_state.n_ejecucion > 1: st.session_state.n_ejecucion -= 1

causas_ejecucion = []
for i in range(st.session_state.n_ejecucion):
    col1, col2 = st.columns(2)
    with col1: ruc_e = st.text_input(f"RUC Ejecución {i+1}", key=f"ruce_{i}")
    with col2: rit_e = st.text_input(f"RIT Ejecución {i+1}", key=f"rite_{i}")
    causas_ejecucion.append({"ruc": ruc_e, "rit": rit_e})

st.markdown("---")

# SECCIÓN 2: CAUSAS DE ORIGEN (DONDE FUE SANCIONADO)
st.markdown("### 2. Causas de Origen (A extinguir)")
if 'n_origen' not in st.session_state: st.session_state.n_origen = 1

c_or1, c_or2 = st.columns(2)
with c_or1:
    if st.button("➕ Origen"): st.session_state.n_origen += 1
with c_or2:
    if st.button("➖ Origen") and st.session_state.n_origen > 1: st.session_state.n_origen -= 1

causas_origen = []
for j in range(st.session_state.n_origen):
    st.write(f"**Causa de Origen {j+1}**")
    o1, o2, o3 = st.columns(3)
    with o1: ruc_o = st.text_input(f"RUC", key=f"ruco_{j}")
    with o2: rit_o = st.text_input(f"RIT", key=f"rito_{j}")
    with o3: juz_o = st.text_input(f"Juzgado Sanción", key=f"juzo_{j}")
    causas_origen.append({"ruc": ruc_o, "rit": rit_o, "juzgado_causa": juz_o})

st.markdown("---")
pdf_file = st.file_uploader("Adjuntar PDF Condena Adulto", type="pdf")

if st.button("Generar Escrito"):
    if not pdf_file or not nombre_defensor or not juzgado_presentacion:
        st.error("Faltan datos críticos.")
    else:
        reader = PyPDF2.PdfReader(pdf_file)
        txt_pdf = "".join([page.extract_text() for page in reader.pages])
        
        info = {
            "nombre_defensor": nombre_defensor,
            "nombre_adolescente": nombre_adolescente,
            "juzgado_presentacion": juzgado_presentacion,
            "causas_ejecucion": causas_ejecucion,
            "causas_origen": causas_origen
        }
        
        doc_word = crear_escrito(info, txt_pdf)
        st.download_button("📥 Descargar Word", doc_word, f"Extincion_{nombre_adolescente}.docx")

st.caption("Aplicación hecha por Ignacio Badilla Lara")
