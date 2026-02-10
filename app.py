import streamlit as st
from docx import Document
from docx.shared import Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
import PyPDF2, io, re

# --- 1. SEGURIDAD ---
ADMIN_EMAIL = "badilla285@gmail.com"
USUARIOS_AUTORIZADOS = [ADMIN_EMAIL]

def check_auth():
    if "auth" not in st.session_state: st.session_state.auth = False
    if not st.session_state.auth:
        st.title("🔐 Acceso - Generador IBL")
        u = st.text_input("Correo Autorizado")
        p = st.text_input("Contraseña", type="password")
        if st.button("Ingresar"):
            if u in USUARIOS_AUTORIZADOS and p == "nacho2026":
                st.session_state.auth = True
                st.rerun()
            else: st.error("Acceso denegado.")
        return False
    return True

# --- 2. LÓGICA DE ESTADO ---
def inicializar_estados():
    keys = ['ne_e', 'nr_e', 'ne_p', 'nf_p']
    for k in keys:
        if k not in st.session_state:
            st.session_state[k] = 1

def cambiar_cont(var, delta):
    st.session_state[var] = max(1, st.session_state[var] + delta)

# --- 3. MOTOR DE REDACCIÓN (FORMATO ROBUSTO IBL) ---
def generar_word_extincion(gral, ejecucion, causas_rpa, condena_adulto):
    doc = Document()
    style = doc.styles['Normal']
    style.font.name, style.font.size = 'Cambria', Pt(12)

    # SUMILLA
    p_sumilla = doc.add_paragraph()
    p_sumilla.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    p_sumilla.add_run("EN LO PRINCIPAL: SOLICITA EXTINCIÓN;\nOTROSÍ: ACOMPAÑA DOCUMENTO.").bold = True

    doc.add_paragraph(f"\nJUZGADO DE GARANTÍA DE {gral['juz'].upper()}").bold = True

    # PRESENTACIÓN
    rits_ej = ", ".join([f"{c['rit']} (RUC: {c['ruc']})" for c in ejecucion if c['rit']])
    intro = doc.add_paragraph()
    intro.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    intro.add_run(f"\n{gral['def'].upper()}, Defensor Penal Público, por {gral['suj'].upper()}, en causas de ejecución {rits_ej}, a US. con respeto digo:")

    # CUERPO LEGAL
    doc.add_paragraph().add_run("\nQue, vengo en solicitar que declare la extinción de las sanciones de la Ley de Responsabilidad Penal Adolescente, o en subsidio se fije día y hora para celebrar audiencia para debatir sobre la extinción de la pena respecto de mi representado, en virtud del artículo 25 ter y 25 quinquies de la Ley 20.084.")

    # ANTECEDENTES RPA
    doc.add_paragraph("\nMi representado fue condenado en la siguiente causa de la Ley RPA:").bold = True
    for i, c in enumerate(causas_rpa):
        p_c = doc.add_paragraph()
        p_c.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        p_c.add_run(f"{i+1}. RIT: {c['rit']}, RUC: {c['ruc']}: ").bold = True
        p_c.add_run(f"Condenado por el {c['juz']} a una sanción consistente en {c['detalle']}.")

    # FUNDAMENTO CONDENA ADULTO
    doc.add_paragraph("\nEl fundamento para solicitar la discusión respecto de la extinción de responsabilidad penal radica en la existencia de una condena de mayor gravedad como adulto, la cual paso a detallar:").bold = True
    p_a = doc.add_paragraph()
    p_a.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p_a.add_run(f"2. RIT: {condena_adulto['rit']}, RUC: {condena_adulto['ruc']}: ").bold = True
    p_a.add_run(f"Condenado por el {condena_adulto['juz']}, con fecha {condena_adulto['fecha']}, a la pena de {condena_adulto['pena']}.")
    
    doc.add_paragraph("\nSe hace presente que el artículo 25 ter en su inciso tercero establece que se considerará más grave el delito que tuviere asignada una mayor pena. En el presente caso, la sanción impuesta como adulto reviste mayor gravedad, configurándose los presupuestos para la extinción.")

    doc.add_paragraph("\nPOR TANTO,").bold = True
    doc.add_paragraph("SOLICITO A S.S. acceder a lo solicitado extinguiendo de pleno derecho la sanción antes referida.").bold = True
    
    # OTROSÍ
    doc.add_paragraph("\nOTROSÍ: ACOMPAÑA DOCUMENTO.").bold = True
    doc.add_paragraph(f"Vengo en acompañar sentencia de adulto de mi representado de la causa RIT: {condena_adulto['rit']} del {condena_adulto['juz']}.")
    doc.add_paragraph("\nPOR TANTO, SOLICITO A S.S. Tenerlo por acompañado.").bold = True

    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf

# --- 4. INTERFAZ STREAMLIT ---
if check_auth():
    st.set_page_config(page_title="Generador IBL", layout="wide")
    inicializar_estados()
    
    st.title("⚖️ Generador IBL - Defensoría")
    tab1, tab2 = st.tabs(["📄 Extinción (Art. 25 ter)", "📜 Prescripción (Art. 5)"])

    with tab1:
        st.subheader("Módulo de Extinción por Condena de Adulto")
        c1, c2, c3 = st.columns(3)
        g = {"def": c1.text_
