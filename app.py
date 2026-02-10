import streamlit as st
from docx import Document
from docx.shared import Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
import PyPDF2
import io
import re

def extraer_datos_sentencia(texto):
    """Busca patrones comunes en sentencias chilenas para auto-rellenar."""
    datos = {"ruc": "", "rit": "", "juzgado": "", "condena": ""}
    
    # RUC: Busca patrones como 2000951562-4
    ruc_match = re.search(r"RUC:\s?(\d{8,10}-\d|[\d\.-]+)", texto, re.IGNORECASE)
    if ruc_match: datos["ruc"] = ruc_match.group(1)
    
    # RIT: Busca patrones como 3639-2020 o O-123-2022
    rit_match = re.search(r"RIT:\s?([\d\w-]+-\d{4})", texto, re.IGNORECASE)
    if rit_match: datos["rit"] = rit_match.group(1)
    
    # Juzgado: Busca "Juzgado de Garantía de [Ciudad]"
    juzgado_match = re.search(r"(Juzgado de Garantía de\s[\w\s]+|Tribunal de Juicio Oral en lo Penal de\s[\w\s]+)", texto, re.IGNORECASE)
    if juzgado_match: datos["juzgado"] = juzgado_match.group(1).strip()
    
    # Condena (Extracto): Busca palabras clave para capturar el párrafo de la pena
    condena_match = re.search(r"(condena a|pena de|sanción de).*?(\d+\s(años|días|meses).*?)(?=\.|y\s)", texto, re.IGNORECASE | re.DOTALL)
    if condena_match: 
        datos["condena"] = condena_match.group(0).replace("\n", " ").strip()
    
    return datos

def crear_escrito(datos, info_condenas):
    doc = Document()
    
    # Estilo base: Cambria 12
    style = doc.styles['Normal']
    font = style.font
    font.name = 'Cambria'
    font.size = Pt(12)

    # --- SUMILLA ---
    p_sumilla = doc.add_paragraph()
    p_sumilla.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    run_sum = p_sumilla.add_run("EN LO PRINCIPAL: SOLICITA EXTINCIÓN;\nOTROSÍ: ACOMPAÑA DOCUMENTO.")
    run_sum.bold = True

    # --- TRIBUNAL ---
    doc.add_paragraph(f"\nJUZGADO DE GARANTÍA DE {datos['juzgado_presentacion'].upper()}").bold = True

    # --- COMPARECENCIA ---
    rits_ej = ", ".join([f"RIT: {c['rit']}" for c in datos['causas_ejecucion']])
    rucs_ej = ", ".join([f"RUC: {c['ruc']}" for c in datos['causas_ejecucion']])
    p_comp = doc.add_paragraph()
    p_comp.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p_comp.add_run(f"\n{datos['nombre_defensor'].upper()}, Abogado, Defensor Penal Público, en representación de {datos['nombre_adolescente'].upper()}, en causa {rits_ej}, {rucs_ej}, a S.S., respetuosamente digo:")

    # --- SOLICITUD ---
    p_sol = doc.add_paragraph()
    p_sol.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p_sol.add_run(f"\nQue, vengo en solicitar que declare la extinción de las sanciones de la Ley de Responsabilidad Penal Adolescente, o en subsidio se fije día y hora para celebrar audiencia para debatir sobre la extinción de la pena respecto de mi representado, en virtud del artículo 25 ter y 25 quinquies de la Ley 20.084.")

    doc.add_paragraph("\nMi representado fue condenado en la siguiente causa de la Ley RPA:").bold = True
    
    for i, c in enumerate(datos['causas_origen'], 1):
        p_rpa = doc.add_paragraph()
        p_rpa.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        p_rpa.add_run(f"{i}. RIT: {c['rit']}, RUC: {c['ruc']}: ").bold = True
        p_rpa.add_run(f"En la cual fue condenado por el Juzgado de Garantía de {c['juzgado_causa']} a una sanción consistente en {c['sancion']}. Cabe señalar que dicha pena no se encuentra cumplida.")

    # --- FUNDAMENTO ADULTO ---
    doc.add_paragraph("\nEl fundamento para solicitar la discusión respecto de la extinción de responsabilidad penal radica en la existencia de una condena de mayor gravedad como adulto, la cual paso a detallar:").alignment = WD_ALIGN_PARAGRAPH.JUSTIFY

    for k, condena in enumerate(info_condenas, 2): # Empieza en 2 siguiendo el modelo
        p_cond = doc.add_paragraph()
        p_cond.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        p_cond.add_run(f"{k}. RIT: {condena['rit']}, RUC: {condena['ruc']}: ").bold = True
        p_cond.add_run(f"En la cual fue condenado por el {condena['juzgado']}, {condena['detalle_sentencia']}.\n")
        
        # Transcripción (Se adjunta al final o como bloque según el modelo)
        p_trans = doc.add_paragraph()
        p_trans.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        p_trans.add_run(condena['texto_pdf'])

    # --- CIERRE ---
    doc.add_paragraph("\nSe hace presente que el artículo 25 ter en su inciso tercero establece que se considerará más grave el delito o conjunto de ellos que tuviere asignada en la ley una mayor pena de conformidad con las reglas generales. En el presente caso, la sanción impuesta como adulto reviste una mayor gravedad, configurándose así los presupuestos para la extinción.").alignment = WD_ALIGN_PARAGRAPH.JUSTIFY

    doc.add_paragraph("\nPOR TANTO,").bold = True
    doc.add_paragraph("En mérito de lo expuesto, SOLICITO A S.S. acceder a lo solicitado extinguiendo de pleno derecho la sanción antes referida, o en subsidio se fije día y hora para celebrar audiencia para que se abra debate sobre la extinción de responsabilidad penal en la presente causa.").alignment = WD_ALIGN_PARAGRAPH.JUSTIFY

    # --- OTROSÍ ---
    doc.add_paragraph("\nOTROSÍ: ").bold = True
    doc.add_paragraph("Acompaña sentencia de adulto.")
    doc.add_paragraph("\nPOR TANTO,").bold = True
    detalle_rit = ", ".join([c['rit'] for c in info_condenas])
    doc.add_paragraph(f"SOLICITO A S.S. se tenga por acompañada sentencia de adulto de mi representado de la causa RIT: {detalle_rit}.").alignment = WD_ALIGN_PARAGRAPH.JUSTIFY

    target = io.BytesIO()
    doc.save(target)
    target.seek(0)
    return target

# --- INTERFAZ STREAMLIT ---
st.set_page_config(page_title="Generador RPA - Automático")
st.title("⚖️ Generador de Extinciones (Auto-rellenado)")

nombre_defensor = st.text_input("Defensor/a", value="Ignacio Badilla Lara")
nombre_adolescente = st.text_input("Nombre Adolescente")
juzgado_p = st.text_input("Juzgado de Garantía (Destino)")

# --- 1. EJECUCIÓN ---
st.subheader("1. Causas en Ejecución")
if 'n_e' not in st.session_state: st.session_state.n_e = 1
causas_ejecucion = []
for i in range(st.session_state.n_e):
    c1, c2 = st.columns(2)
    with c1: re = st.text_input(f"RUC Ejecución {i+1}", key=f"re_{i}")
    with c2: te = st.text_input(f"RIT Ejecución {i+1}", key=f"te_{i}")
    causas_ejecucion.append({"ruc": re, "rit": te})

# --- 2. RPA ORIGEN ---
st.subheader("2. Causas RPA (A extinguir)")
if 'n_o' not in st.session_state: st.session_state.n_o = 1
causas_origen = []
for j in range(st.session_state.n_o):
    o1, o2 = st.columns(2)
    with o1: ro = st.text_input(f"RUC RPA {j+1}", key=f"ro_{j}")
    with o2: to = st.text_input(f"RIT RPA {j+1}", key=f"to_{j}")
    jo = st.text_input(f"Juzgado Origen {j+1}", key=f"jo_{j}")
    sa = st.text_area(f"Sanción impuesta {j+1}", key=f"sa_{j}")
    causas_origen.append({"ruc": ro, "rit": to, "juzgado_causa": jo, "sancion": sa})

# --- 3. CONDENAS ADULTO (INTELIGENTE) ---
st.markdown("---")
st.subheader("🔞 Condenas Adulto (Suba el PDF para rellenar)")
if 'n_a' not in st.session_state: st.session_state.n_a = 1

inf_cond = []
for k in range(st.session_state.n_a):
    st.write(f"### Condena Adulto {k+1}")
    fa = st.file_uploader(f"Subir PDF {k+1}", type="pdf", key=f"fa_{k}")
    
    # Lógica de auto-rellenado
    default_vals = {"ruc": "", "rit": "", "juzgado": "", "condena": "", "texto_completo": ""}
    if fa:
        reader = PyPDF2.PdfReader(fa)
        texto_extraido = "".join([p.extract_text() for p in reader.pages])
        datos_extraidos = extraer_datos_sentencia(texto_extraido)
        default_vals.update(datos_extraidos)
        default_vals["texto_completo"] = texto_extraido

    a1, a2 = st.columns(2)
    with a1: ra = st.text_input("RUC", value=default_vals["ruc"], key=f"ra_{k}")
    with a2: ta = st.text_input("RIT", value=default_vals["rit"], key=f"ta_{k}")
    ja = st.text_input("Juzgado", value=default_vals["juzgado"], key=f"ja_{k}")
    det = st.text_area("Detalle de condena", value=default_vals["condena"], key=f"det_{k}", help="Ej: Fecha, pena, delito...")
    
    inf_cond.append({"ruc": ra, "rit": ta, "juzgado": ja, "detalle_sentencia": det, "texto_pdf": default_vals["texto_completo"]})

if st.button("🚀 GENERAR ESCRITO CAMBRIA 12"):
    if not nombre_adolescente or not inf_cond:
        st.error("Faltan datos obligatorios.")
    else:
        info = {
            "nombre_defensor": nombre_defensor,
            "nombre_adolescente": nombre_adolescente,
            "juzgado_presentacion": juzgado_p,
            "causas_ejecucion": causas_ejecucion,
            "causas_origen": causas_origen
        }
        doc = crear_escrito(info, inf_cond)
        st.download_button("📥 Descargar Escrito", doc, f"Extincion_{nombre_adolescente}.docx")

if st.button("➕ Añadir otra condena adulto"):
    st.session_state.n_a += 1
    st.rerun()
