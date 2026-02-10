import streamlit as st
from docx import Document
from docx.shared import Pt
import PyPDF2
import io

def crear_escrito(datos, info_condenas):
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
    
    p.add_run("\nCAUSAS RPA A EXTINGUIR:\n")
    for c in datos['causas_origen']:
        p.add_run(f"RIT: {c['rit']} / RUC: {c['ruc']} - JUZGADO: {c['juzgado_causa']}\n")

    doc.add_paragraph("\nEN LO PRINCIPAL: SOLICITA DECLARACIÓN DE EXTINCIÓN; OTROSÍ: ACOMPAÑA DOCUMENTOS.")
    
    p_juez = doc.add_paragraph()
    p_juez.add_run(f"\nS.J.L. DE GARANTÍA DE {datos['juzgado_presentacion'].upper()}").bold = True

    cuerpo = doc.add_paragraph()
    cuerpo.add_run(f"\n{datos['nombre_defensor']}, defensor penal público, por el adolescente {datos['nombre_adolescente']}, en las causas de ejecución ya individualizadas, a SS. con respeto digo:\n")
    
    # FUNDAMENTO
    p_fund = doc.add_paragraph()
    p_fund.add_run("\nQue, el fundamento para solicitar la extinción es que mi representado ha sido condenado como adulto en la o las siguientes causas (según archivos adjuntos):\n")
    
    # Detalle de cada condena de adulto + transcripción
    for condena in info_condenas:
        p_det = doc.add_paragraph()
        p_det.add_run(f"• Juzgado: {condena['juzgado']}, RUC: {condena['ruc']}, RIT: {condena['rit']}.\n").bold = True
        p_det.add_run(f"Condena: {condena['texto']}")
        doc.add_paragraph("-" * 20)

    cuerpo_final = doc.add_paragraph()
    cuerpo_final.add_run("\nLo anterior resulta incompatible con la ejecución de las sanciones RPA vigentes, por lo que procede declarar la extinción de la responsabilidad penal.\n")
    
    p_por_tanto = doc.add_paragraph()
    p_por_tanto.add_run("\nPOR TANTO, de acuerdo a la Ley 20.084:\n")
    p_por_tanto.add_run("SOLICITO A SS. declarar la extinción y el archivo de los antecedentes.").bold = True

    # OTROSÍ ADAPTATIVO
    doc.add_paragraph("\nOTROSÍ:").bold = True
    texto_otrosi = "Acompaña sentencia " if len(info_condenas) == 1 else "Acompaña sentencias "
    detalles_otrosi = ", ".join([f"RIT {c['rit']} del Juzgado de {c['juzgado']}" for c in info_condenas])
    
    p_otrosi = doc.add_paragraph()
    p_otrosi.add_run(f"Solicito a SS. tener por acompañada(s) sentencia(s) de adulto correspondiente(s) a: {detalles_otrosi}.")

    target = io.BytesIO()
    doc.save(target)
    target.seek(0)
    return target

st.set_page_config(page_title="Generador RPA")
st.title("⚖️ Generador de Extinciones")

nombre_defensor = st.text_input("Nombre Defensor", value="Ignacio Badilla Lara")
nombre_adolescente = st.text_input("Nombre Adolescente")
juzgado_presentacion = st.text_input("Juzgado de Ejecución (S.J.L.)")

# 1. EJECUCIÓN
st.subheader("1. Causas en Ejecución")
if 'n_e' not in st.session_state: st.session_state.n_e = 1
c1e, c2e = st.columns(2)
with c1e:
    if st.button("➕ Ejec."): st.session_state.n_e += 1
with c2e:
    if st.button("➖ Ejec.") and st.session_state.n_e > 1: st.session_state.n_e -= 1

causas_ejecucion = []
for i in range(st.session_state.n_e):
    ce1, ce2 = st.columns(2)
    with ce1: r_e = st.text_input(f"RUC Ejecución {i+1}", key=f"re_{i}")
    with ce2: t_e = st.text_input(f"RIT Ejecución {i+1}", key=f"te_{i}")
    causas_ejecucion.append({"ruc": r_e, "rit": t_e})

# 2. RPA ORIGEN
st.subheader("2. Causas RPA a Extinguir")
if 'n_o' not in st.session_state: st.session_state.n_o = 1
c1o, c2o = st.columns(2)
with c1o:
    if st.button("➕ RPA"): st.session_state.n_o += 1
with c2o:
    if st.button("➖ RPA") and st.session_state.n_o > 1: st.session_state.n_o -= 1

causas_origen = []
for j in range(st.session_state.n_o):
    co1, co2, co3 = st.columns(3)
    with co1: r_o = st.text_input(f"RUC Origen", key=f"ro_{j}")
    with co2: t_o = st.text_input(f"RIT Origen", key=f"to_{j}")
    with co3: j_o = st.text_input(f"Juzgado Origen", key=f"jo_{j}")
    causas_origen.append({"ruc": r_o, "rit": t_o, "juzgado_causa": j_o})

# 3. CONDENAS ADULTO (ARCHIVOS)
st.subheader("3. Condenas de Adulto (PDFs)")
if 'n_pdf' not in st.session_state: st.session_state.n_pdf = 1
cp1, cp2 = st.columns(2)
with cp1:
    if st.button("➕ PDF"): st.session_state.n_pdf += 1
with cp2:
    if st.button("➖ PDF") and st.session_state.n_pdf > 1: st.session_state.n_pdf -= 1

info_condenas = []
for k in range(st.session_state.n_pdf):
    st.write(f"**Datos Sentencia Adulto {k+1}**")
    p1, p2, p3 = st.columns(3)
    with p1: r_a = st.text_input(f"RUC Adulto", key=f"ra_{k}")
    with p2: t_a = st.text_input(f"RIT Adulto", key=f"ta_{k}")
    with p3: j_a = st.text_input(f"Juzgado Adulto", key=f"ja_{k}")
    f_a = st.file_uploader(f"Adjuntar PDF {k+1}", type="pdf", key=f"fa_{k}")
    
    if f_a:
        reader = PyPDF2.PdfReader(f_a)
        txt = "".join([page.extract_text() for page in reader.pages])
        info_condenas.append({"ruc": r_a, "rit": t_a, "juzgado": j_a, "texto": txt})

if st.button("Generar Escrito"):
    if not info_condenas or not juzgado_presentacion:
        st.error("Faltan datos o archivos PDF.")
    else:
        info = {
            "nombre_defensor": nombre_defensor,
            "nombre_adolescente": nombre_adolescente,
            "juzgado_presentacion": juzgado_presentacion,
            "causas_ejecucion": causas_ejecucion,
            "causas_origen": causas_origen
        }
        doc_word = crear_escrito(info, info_condenas)
        st.download_button("📥 Descargar Word", doc_word, f"Extincion_{nombre_adolescente}.docx")
