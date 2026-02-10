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

def actualizar_cont(var, delta):
    st.session_state[var] = max(1, st.session_state[var] + delta)

# --- 2. MOTOR DE REDACCIÓN (ESTILO ROBUSTO) ---
def generar_word_extincion(gral, ejecucion, causas_rpa, condena_adulto):
    doc = Document()
    style = doc.styles['Normal']
    style.font.name, style.font.size = 'Cambria', Pt(12)

    # SUMILLA
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    p.add_run("EN LO PRINCIPAL: SOLICITA EXTINCIÓN;\nOTROSÍ: ACOMPAÑA DOCUMENTO.").bold = True

    doc.add_paragraph(f"\nJUZGADO DE GARANTÍA DE {gral['juz'].upper()}").bold = True

    # PRESENTACIÓN
    rits_ej = ", ".join([f"{c['rit']} (RUC: {c['ruc']})" for c in ejecucion if c['rit']])
    intro = doc.add_paragraph()
    intro.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    intro.add_run(f"\n{gral['def'].upper()}, Defensor Penal Público, por {gral['suj'].upper()}, en causas de ejecución {rits_ej}, a US. con respeto digo:")

    # SOLICITUD
    doc.add_paragraph().add_run("\nQue, vengo en solicitar que declare la extinción de las sanciones de la Ley de Responsabilidad Penal Adolescente, o en subsidio se fije día y hora para celebrar audiencia para debatir sobre la extinción de la pena respecto de mi representado, en virtud del artículo 25 ter y 25 quinquies de la Ley 20.084.")

    # ANTECEDENTES RPA
    doc.add_paragraph("\nMi representado fue condenado en la siguiente causa de la Ley RPA:").bold = True
    for i, c in enumerate(causas_rpa):
        p_rpa = doc.add_paragraph()
        p_rpa.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
