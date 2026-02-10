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

    p = doc.add_paragraph()
    p.add_run("SUMILLA: SOLICITA DECLARACIÓN DE EXTINCIÓN DE RESPONSABILIDAD PENAL.\n").bold = True
    for c in datos['causas']:
        p.add_run(f"RIT: {c['rit']} / RUC: {c['ruc']}\n")
    p.add_run(f"TRIBUNAL: {datos['juzgado']}\n")

    doc.add_paragraph("\nEN LO PRINCIPAL: SOLICITA DECLARACIÓN DE EXTINCIÓN; OTROSÍ: ACOMPAÑA DOCUMENTO.")
    
    p_juez = doc.add_paragraph()
    p_juez.add_run(f"\nS.J.L. DE GARANTÍA DE {datos['juzgado'].upper()}").bold = True

    cuerpo = doc.add_paragraph()
    cuerpo.add_run(f"\n{datos['nombre_defensor']}, defensor penal público, por el adolescente {datos['nombre_adolescente']}, en las causas ya individualizadas, a SS. con respeto digo:\n")
    
    rits = [f"RIT {c['rit']}" for c in datos['causas']]
    texto_rits = ", ".join(rits)
    
    cuerpo.add_run(f"\nQue, de conformidad a la Ley 20.084, solicito se declare la extinción de la responsabilidad penal en las causas {texto_rits}, por haber sido mi representado condenado por un tribunal de adultos a una pena privativa de libertad, lo que resulta incompatible con la ejecución de las sanciones RPA.\n")

    doc.add_paragraph("\nFUNDAMENTOS DE LA CONDENA DE ADULTO:").bold = True
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

nombre_defensor = st.text_input("Nombre Defensor")
nombre_adolescente = st.text_input("Nombre Adolescente")
juzgado = st.text_input("Juzgado (Ej: San Bernardo)")

st.subheader("Causas RPA")
if 'n_causas' not in st.session_state:
    st.session_state.n_causas = 1

col_btn1, col_btn2 = st.columns([0.1, 0.9])
with col_btn1:
    if st.button("➕"):
        st.session_state.n_causas += 1
with col_btn2:
    if st.button("➖") and st.session_state.n_causas > 1:
        st.session_state.n_causas -= 1

causas_lista = []
for i in range(st.session_state.n_causas):
    c1, c2 = st.columns(2)
    with c1:
        ruc_v = st.text_input(f"RUC {i+1}", key=f"ruc_{i}")
    with c2:
        rit_v = st.text_input(f"RIT {i+1}", key=f"rit_{i}")
    causas_lista.append
