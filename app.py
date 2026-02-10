import streamlit as st
from docx import Document
from docx.shared import Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
import PyPDF2
import io
import re

# Función para extraer datos automáticamente del PDF (RPA y Adulto)
def extraer_datos_pdf(texto):
    datos = {"ruc": "", "rit": "", "juzgado": "", "sancion": ""}
    # RUC: 12345678-9
    ruc = re.search(r"RUC:\s?(\d{7,10}-[\dkK])", texto)
    if ruc: datos["ruc"] = ruc.group(1)
    # RIT: 123-2024 o O-123-2024
    rit = re.search(r"RIT:\s?([\d\w-]+-\d{4})", texto)
    if rit: datos["rit"] = rit.group(1)
    # Tribunal
    trib = re.search(r"(Juzgado de Garantía de\s[\w\s]+|Tribunal de Juicio Oral en lo Penal de\s[\w\s]+)", texto)
    if trib: datos["juzgado"] = trib.group(1).strip()
    # Sanción / Condena
    cond = re.search(r"(condena a|pena de|sanción de|consistente en).*?(\d+\s(años|días|meses).*?)(?=\.|y\s|SE\sRESUELVE)", texto, re.IGNORECASE | re.DOTALL)
    if cond: datos["sancion"] = cond.group(0).replace("\n", " ").strip()
    return datos

def crear_escrito(datos, info_condenas):
    doc = Document()
    style = doc.styles['Normal']
    style.font.name = 'Cambria'
    style.font.size = Pt(12)

    # SUMILLA
    p_sumilla = doc.add_paragraph()
    p_sumilla.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    run_sum = p_sumilla.add_run("EN LO PRINCIPAL: SOLICITA EXTINCIÓN;\nOTROSÍ: ACOMPAÑA DOCUMENTO.")
    run_sum.bold = True

    # TRIBUNAL
    doc.add_paragraph(f"\nJUZGADO DE GARANTÍA DE {datos['juzgado_presentacion'].upper()}").bold = True

    # COMPARECENCIA
    rits_ej = ", ".join([f"RIT: {c['rit']}" for c in datos['causas_ejecucion']])
    rucs_ej = ", ".join([f"RUC: {c['ruc']}" for c in datos['causas_ejecucion']])
    p_comp = doc.add_paragraph()
    p_comp.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p_comp.add_run(f"\n{datos['nombre_defensor'].upper()}, Abogado, Defensor Penal Público, en representación de {datos['nombre_adolescente'].upper()}, en causa {rits_ej}, {rucs_ej}, a S.S., respetuosamente digo:")

    # CUERPO
    p_sol = doc.add_paragraph()
    p_sol.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p_sol.add_run(f"\nQue, vengo en solicitar que declare la extinción de las sanciones de la Ley de Responsabilidad Penal Adolescente, o en subsidio se fije día y hora para celebrar audiencia para debatir sobre la extinción de la pena respecto de mi representado, en virtud del artículo 25 ter y 25 quinquies de la Ley 20.084.")

    doc.add_paragraph("\nMi representado fue condenado en la siguiente causa de la Ley RPA:").bold = True
    
    idx = 1
    for c in datos['causas_origen']:
        p_rpa = doc.add_paragraph()
        p_rpa.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        p_rpa.add_run(f"{idx}. RIT: {c['rit']}, RUC: {c['ruc']}: ").bold = True
        p_rpa.add_run(f"En la cual fue condenado por el Juzgado de Garantía de {c['juzgado_causa']} a una sanción consistente en {c['sancion']}. Cabe señalar que dicha pena no se encuentra cumplida.")
        idx += 1

    doc.add_paragraph("\nEl fundamento para solicitar la discusión respecto de la extinción de responsabilidad penal radica en la existencia de una condena de mayor gravedad como adulto, la cual paso a detallar:").alignment = WD_ALIGN_PARAGRAPH.JUSTIFY

    for condena in info_condenas:
        p_cond = doc.add_paragraph()
        p_cond.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        p_cond.add_run(f"{idx}. RIT: {condena['rit']}, RUC: {condena['ruc']}: ").bold = True
        p_cond.add_run(f"En la cual fue condenado por el {condena['juzgado']}, {condena['detalle']}.\n")
        doc.add_paragraph(condena['texto_pdf']).alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        idx += 1

    doc.add_paragraph("\nSe hace presente que el artículo 25 ter en su inciso tercero establece que se considerará más grave el delito o conjunto de ellos que tuviere asignada en la ley una mayor pena de conformidad con las reglas generales. En el presente caso, la sanción impuesta como adulto reviste una mayor gravedad, configurándose así los presupuestos para la extinción.").alignment = WD_ALIGN_PARAGRAPH.JUSTIFY

    doc.add_paragraph("\nPOR TANTO,").bold = True
    doc.add_paragraph("En mérito de lo expuesto, SOLICITO A S.S. acceder a lo solicitado extinguiendo de pleno derecho la sanción antes referida, o en subsidio se fije día y hora para celebrar audiencia para que se abra debate sobre la extinción de responsabilidad penal en la presente causa.").alignment = WD_ALIGN_PARAGRAPH.JUSTIFY

    # OTROSÍ
    doc.add_paragraph("\nOTROSÍ: ").bold = True
    doc.add_paragraph("Acompaña sentencia de adulto.")
    doc.add_paragraph("\nPOR TANTO,").bold = True
    det_rit = ", ".join([c['rit'] for c in info_condenas])
    doc.add_paragraph(f"SOLICITO A S.S. se tenga por acompañada sentencia de adulto de mi representado de la causa RIT: {det_rit}.").alignment = WD_ALIGN_PARAGRAPH.JUSTIFY

    target = io.BytesIO()
    doc.save(target)
    target.seek(0)
    return target

# --- INTERFAZ ---
st.set_page_config(page_title="Generador de Escritos RPA", layout="centered")

st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stButton>button { border-radius: 20px; }
    </style>
    """, unsafe_allow_html=True)

st.title("⚖️ Generador de Extinciones")

st.markdown("### Individualización")
nombre_defensor = st.text_input("Nombre Defensor/a", value="Ignacio Badilla Lara")
nombre_adolescente = st.text_input("Nombre Adolescente")
juzgado_p = st.text_input("Juzgado de Garantía de Presentación")

st.divider()

# SECCIÓN 1: EJECUCIÓN
st.subheader("1. Causas en el Tribunal de Ejecución")
if 'n_e' not in st.session_state: st.session_state.n_e = 1
col_be = st.columns([0.1, 0.1, 0.8])
if col_be[0].button("➕", key="ae"): st.session_state.n_e += 1
if col_be[1].button("➖", key="re") and st.session_state.n_e > 1: st.session_state.n_e -= 1

causas_ejec = []
for i in range(st.session_state.n_e):
    c1, c2 = st.columns(2)
    with c1: re = st.text_input(f"RUC Ejecución {i+1}", key=f"re_{i}")
    with c2: te = st.text_input(f"RIT Ejecución {i+1}", key=f"te_{i}")
    causas_ejec.append({"ruc": re, "rit": te})

st.divider()

# SECCIÓN 2: RPA ORIGEN (CON LECTURA INTELIGENTE OPCIONAL)
st.subheader("2. Causas RPA a Extinguir (Carga opcional)")
if 'n_o' not in st.session_state: st.session_state.n_o = 1
col_bo = st.columns([0.1, 0.1, 0.8])
if col_bo[0].button("➕", key="ao"): st.session_state.n_o += 1
if col_bo[1].button("➖", key="ro") and st.session_state.n_o > 1: st.session_state.n_o -= 1

causas_orig = []
for j in range(st.session_state.n_o):
    st.markdown(f"*Causa RPA {j+1}*")
    f_o = st.file_uploader(f"Cargar PDF RPA {j+1} (Opcional)", type="pdf", key=f"fo_{j}")
    
    vals_o = {"ruc": "", "rit": "", "juz": "", "san": ""}
    if f_o:
        reader_o = PyPDF2.PdfReader(f_o)
        txt_o = "".join([p.extract_text() for p in reader_o.pages])
        datos_o = extraer_datos_pdf(txt_o)
        vals_o = {"ruc": datos_o["ruc"], "rit": datos_o["rit"], "juz": datos_o["juzgado"], "san": datos_o["sancion"]}

    o1, o2, o3 = st.columns(3)
    with o1: ro = st.text_input(f"RUC", value=vals_o["ruc"], key=f"ro_{j}")
    with o2: to = st.text_input(f"RIT", value=vals_o["rit"], key=f"to_{j}")
    with o3: jo = st.text_input(f"Juzgado Origen", value=vals_o["juz"], key=f"jo_{j}")
    so = st.text_area(f"Sanción impuesta", value=vals_o["san"], key=f"so_{j}", height=80)
    causas_orig.append({"ruc": ro, "rit": to, "juzgado_causa": jo, "sancion": so})

st.divider()

# SECCIÓN 3: CONDENAS ADULTO
st.subheader("3. Condenas Adulto (Carga PDF)")
if 'n_a' not in st.session_state: st.session_state.n_a = 1
col_ba = st.columns([0.1, 0.1, 0.8])
if col_ba[0].button("➕", key="aa"): st.session_state.n_a += 1
if col_ba[1].button("➖", key="ra") and st.session_state.n_a > 1: st.session_state.n_a -= 1

inf_cond = []
for k in range(st.session_state.n_a):
    st.markdown(f"**Sentencia Adulto {k+1}**")
    f_a = st.file_uploader(f"Cargar Sentencia Adulto {k+1}", type="pdf", key=f"fa_{k}")
    
    vals_a = {"ruc": "", "rit": "", "juz": "", "det": "", "txt": ""}
    if f_a:
        reader_a = PyPDF2.PdfReader(f_a)
        txt_a = "".join([p.extract_text() for p in reader_a.pages])
        datos_a = extraer_datos_pdf(txt_a)
        vals_a = {"ruc": datos_a["ruc"], "rit": datos_a["rit"], "juz": datos_a["juzgado"], "det": datos_a["sancion"], "txt": txt_a}

    a1, a2, a3 = st.columns(3)
    with a1: ra = st.text_input("RUC Adulto", value=vals_a["ruc"], key=f"ra_{k}")
    with a2: ta = st.text_input("RIT Adulto", value=vals_a["rit"], key=f"ta_{k}")
    with a3: ja = st.text_input("Juzgado Adulto", value=vals_a["juz"], key=f"ja_{k}")
    da = st.text_area("Detalle de la Pena", value=vals_a["det"], key=f"da_{k}")
    inf_cond.append({"ruc": ra, "rit": ta, "juzgado": ja, "detalle": da, "texto_pdf": vals_a["txt"]})

if st.button("🚀 GENERAR ESCRITO ROBUSTO", use_container_width=True):
    if not nombre_adolescente or not juzgado_p:
        st.error("Faltan datos de individualización.")
    elif not inf_cond:
        st.error("Debe existir al menos una condena de adulto.")
    else:
        info = {"nombre_defensor": nombre_defensor, "nombre_adolescente": nombre_adolescente, 
                "juzgado_presentacion": juzgado_p, "causas_ejecucion": causas_ejec, "causas_origen": causas_orig}
        word_out = crear_escrito(info, inf_cond)
        st.download_button("📥 Descargar Word (Cambria 12)", word_out, f"Extincion_{nombre_adolescente}.docx")
