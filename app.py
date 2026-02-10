import streamlit as st
from docx import Document
from docx.shared import Pt, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
import PyPDF2
import io

def crear_escrito(datos, info_condenas):
    doc = Document()
    
    # Configuración de fuente Cambria 12
    style = doc.styles['Normal']
    font = style.font
    font.name = 'Cambria'
    font.size = Pt(12)

    # --- SUMILLA (Derecha, Negrita, Cambria) ---
    p_sumilla = doc.add_paragraph()
    p_sumilla.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    run_sumilla = p_sumilla.add_run("EN LO PRINCIPAL: SOLICITA EXTINCIÓN;\nOTROSÍ: ACOMPAÑA DOCUMENTO.")
    run_sumilla.bold = True

    # --- TRIBUNAL ---
    p_tribunal = doc.add_paragraph()
    p_tribunal.add_run(f"\nJUZGADO DE GARANTÍA DE {datos['juzgado_presentacion'].upper()}").bold = True

    # --- COMPARECENCIA ---
    p_comp = doc.add_paragraph()
    p_comp.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    # Se genera el texto de las causas de ejecución
    rits_ej = ", ".join([f"RIT: {c['rit']}" for c in datos['causas_ejecucion']])
    rucs_ej = ", ".join([f"RUC: {c['ruc']}" for c in datos['causas_ejecucion']])
    
    p_comp.add_run(f"\n{datos['nombre_defensor'].upper()}, Abogado, Defensor Penal Público, en representación de {datos['nombre_adolescente'].upper()}, en causa {rits_ej}, {rucs_ej}, a S.S., respetuosamente digo:")

    # --- SOLICITUD PRINCIPAL ---
    p_cuerpo = doc.add_paragraph()
    p_cuerpo.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p_cuerpo.add_run(f"\nQue, vengo en solicitar que declare la extinción de las sanciones de la Ley de Responsabilidad Penal Adolescente, o en subsidio se fije día y hora para celebrar audiencia para debatir sobre la extinción de la pena respecto de mi representado, en virtud del artículo 25 ter y 25 quinquies de la Ley 20.084.")

    p_rpa_tit = doc.add_paragraph()
    p_rpa_tit.add_run("\nMi representado fue condenado en la siguiente causa de la Ley RPA:").bold = True
    
    for i, c in enumerate(datos['causas_origen'], 1):
        p_rpa = doc.add_paragraph()
        p_rpa.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        p_rpa.add_run(f"{i}. RIT: {c['rit']}, RUC: {c['ruc']}: ").bold = True
        p_rpa.add_run(f"En la cual fue condenado por el Juzgado de Garantía de {c['juzgado_causa']} a una sanción consistente en {c['sancion']}. Cabe señalar que dicha pena no se encuentra cumplida.")

    # --- FUNDAMENTO CONDENA ADULTO ---
    p_fund_tit = doc.add_paragraph()
    p_fund_tit.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p_fund_tit.add_run("\nEl fundamento para solicitar la discusión respecto de la extinción de responsabilidad penal radica en la existencia de una condena de mayor gravedad como adulto, la cual paso a detallar:")

    for k, condena in enumerate(info_condenas, 1):
        p_cond = doc.add_paragraph()
        p_cond.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        # El número sigue el orden después de las RPA (usualmente empieza en 2 si hay una RPA)
        p_cond.add_run(f"{k+1}. RIT: {condena['rit']}, RUC: {condena['ruc']}: ").bold = True
        p_cond.add_run(f"En la cual fue condenado por el {condena['juzgado']}, {condena['detalle_sentencia']}.\n")
        
        # Transcripción íntegra del PDF
        p_trans = doc.add_paragraph()
        p_trans.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        p_trans.add_run(condena['texto'])

    # --- ANÁLISIS JURÍDICO ---
    p_analisis = doc.add_paragraph()
    p_analisis.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p_analisis.add_run("\nSe hace presente que el artículo 25 ter en su inciso tercero establece que se considerará más grave el delito o conjunto de ellos que tuviere asignada en la ley una mayor pena de conformidad con las reglas generales. En el presente caso, la sanción impuesta como adulto reviste una mayor gravedad, configurándose así los presupuestos para la extinción.")

    p_tanto = doc.add_paragraph()
    p_tanto.add_run("\nPOR TANTO,").bold = True
    
    p_petitorio = doc.add_paragraph()
    p_petitorio.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p_petitorio.add_run("En mérito de lo expuesto, SOLICITO A S.S. acceder a lo solicitado extinguiendo de pleno derecho la sanción antes referida, o en subsidio se fije día y hora para celebrar audiencia para que se abra debate sobre la extinción de responsabilidad penal en la presente causa.")

    # --- OTROSÍ ---
    p_otro_enc = doc.add_paragraph()
    p_otro_enc.add_run("\nOTROSÍ: ").bold = True
    p_otro_enc.add_run("Acompaña sentencia de adulto.")
    
    p_otro_tanto = doc.add_paragraph()
    p_otro_tanto.add_run("\nPOR TANTO,").bold = True
    
    p_otro_pet = doc.add_paragraph()
    p_otro_pet.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    detalle_rit = ", ".join([c['rit'] for c in info_condenas])
    p_otro_pet.add_run(f"SOLICITO A S.S. se tenga por acompañada sentencia de adulto de mi representado de la causa RIT: {detalle_rit}.")

    target = io.BytesIO()
    doc.save(target)
    target.seek(0)
    return target

# --- INTERFAZ ---
st.set_page_config(page_title="Generador RPA")
st.title("⚖️ Generador de Extinciones")

nombre_defensor = st.text_input("Defensor/a", value="Ignacio Badilla Lara")
nombre_adolescente = st.text_input("Nombre Adolescente")
juzgado_p = st.text_input("Juzgado de Garantía de...")

st.markdown("---")
col1, col2 = st.columns(2)

with col1:
    st.subheader("1. Ejecución")
    if 'n_e' not in st.session_state: st.session_state.n_e = 1
    if st.button("➕ Ejec"): st.session_state.n_e += 1
    c_ejec = []
    for i in range(st.session_state.n_e):
        e1, e2 = st.columns(2)
        with e1: re = st.text_input(f"RUC Ejec {i+1}", key=f"re_{i}")
        with e2: te = st.text_input(f"RIT Ejec {i+1}", key=f"te_{i}")
        c_ejec.append({"ruc": re, "rit": te})

with col2:
    st.subheader("2. RPA Origen")
    if 'n_o' not in st.session_state: st.session_state.n_o = 1
    if st.button("➕ RPA"): st.session_state.n_o += 1
    c_orig = []
    for j in range(st.session_state.n_o):
        st.write(f"Causa {j+1}")
        o1, o2 = st.columns(2)
        with o1: ro = st.text_input(f"RUC", key=f"ro_{j}")
        with o2: to = st.text_input(f"RIT", key=f"to_{j}")
        jo = st.text_input(f"Juzgado Origen", key=f"jo_{j}")
        sa = st.text_area(f"Sanción impuesta", placeholder="Ej: dos años de libertad asistida...", key=f"sa_{j}")
        c_orig.append({"ruc": ro, "rit": to, "juzgado_causa": jo, "sancion": sa})

st.markdown("---")
st.subheader("3. Condenas Adulto")
if 'n_a' not in st.session_state: st.session_state.n_a = 1
if st.button("➕ Adulto"): st.session_state.n_a += 1

inf_cond = []
for k in range(st.session_state.n_a):
    st.write(f"Condena {k+1}")
    a1, a2 = st.columns(2)
    with a1: ra = st.text_input(f"RUC Adulto", key=f"ra_{k}")
    with a2: ta = st.text_input(f"RIT Adulto", key=f"ta_{k}")
    ja = st.text_input(f"Juzgado", key=f"ja_{k}")
    det = st.text_area(f"Detalle (Fecha, pena, delito...)", key=f"det_{k}")
    fa = st.file_uploader(f"PDF Sentencia {k+1}", type="pdf", key=f"fa_{k}")
    if fa:
        reader = PyPDF2.PdfReader(fa)
        txt = "".join([p.extract_text() for p in reader.pages])
        inf_cond.append({"ruc": ra, "rit": ta, "juzgado": ja, "detalle_sentencia": det, "texto": txt})

if st.button("Generar Escrito"):
    if not inf_cond or not nombre_adolescente:
        st.error("Faltan datos o archivos.")
    else:
        info = {
            "nombre_defensor": nombre_defensor,
            "nombre_adolescente": nombre_adolescente,
            "juzgado_presentacion": juzgado_p,
            "causas_ejecucion": c_ejec,
            "causas_origen": c_orig
        }
        doc = crear_escrito(info, inf_cond)
        st.download_button("📥 Descargar Word", doc, f"Extincion_{nombre_adolescente}.docx")
