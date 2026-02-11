import streamlit as st
import fitz  # PyMuPDF
from docx import Document
from docx.shared import Pt, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
import io

# --- SEGURIDAD Y ACCESO ---
def check_password():
    if "password_correct" not in st.session_state:
        st.title("🔐 Acceso Sistema Judicial")
        c1, c2 = st.columns(2)
        email = c1.text_input("Correo electrónico")
        pw = c2.text_input("Contraseña", type="password")
        if st.button("Ingresar"):
            if email == "badilla285@gmail.com" and pw == "nacho2026":
                st.session_state["password_correct"] = True
                st.rerun()
            else:
                st.error("Credenciales incorrectas")
        return False
    return True

class GeneradorOficial:
    def __init__(self):
        self.fuente = "Cambria"
        self.tamano = 12

    def generar_docx(self, data):
        """Genera el Word con el formato Cambria 12, interlineado 1.5 y sangría."""
        doc = Document()
        for s in doc.sections:
            s.left_margin, s.right_margin = Inches(1.2), Inches(1.0)

        def add_p(texto, bold=False, indent=True):
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            p.paragraph_format.line_spacing_rule = WD_LINE_SPACING.ONE_POINT_FIVE
            if indent: p.paragraph_format.first_line_indent = Inches(0.5)
            run = p.add_run(texto)
            run.font.name, run.font.size, run.bold = self.fuente, Pt(self.tamano), bold
            return p

        # 1. SUMA (Izquierda)
        suma = doc.add_paragraph()
        suma.alignment = WD_ALIGN_PARAGRAPH.LEFT
        r = suma.add_run("EN LO PRINCIPAL: SOLICITA EXTINCIÓN;\nOTROSÍ: ACOMPAÑA DOCUMENTO.")
        r.bold, r.font.name, r.font.size = True, self.fuente, Pt(self.tamano)

        # 2. TRIBUNAL Y COMPARECENCIA
        add_p(f"\nJUZGADO DE GARANTÍA DE {data['juzgado_ejecucion'].upper()}", bold=True, indent=False)
        
        comp = (f"\n{data['defensor'].upper()}, Abogada, Defensora Penal Pública, en representación de "
                f"{data['adolescente'].upper()}, en causa RIT: {data['rit_principal']}, "
                f"RUC: {data['ruc_principal']}, a S.S., respetuosamente digo:")
        add_p(comp, indent=False)

        # 3. CUERPO LEGAL
        add_p("\nQue, vengo en solicitar que declare la extinción de las sanciones de la Ley de "
                "Responsabilidad Penal Adolescente, o en subsidio se fije día y hora para celebrar "
                "audiencia para debatir sobre la extinción de la pena respecto de mi representado, en "
                "virtud del artículo 25 ter y 25 quinquies de la Ley 20.084.")

        add_p("Mi representado fue condenado en la siguiente causa de la Ley RPA:")
        for i, c in enumerate(data['causas_rpa'], 1):
            add_p(f"{i}. RIT: {c['rit']}, RUC: {c['ruc']}: Condenado por el Juzgado de Garantía de "
                  f"{c['juzgado']} a la pena de {c['sancion']}. Cabe señalar que dicha pena no se encuentra cumplida.")

        add_p("El fundamento para solicitar la discusión radica en una condena de mayor gravedad como adulto:")
        for i, c in enumerate(data['causas_adulto'], 1):
            idx = i + len(data['causas_rpa'])
            add_p(f"{idx}. RIT: {c['rit']}, RUC: {c['ruc']}: Condenado por el {c['juzgado']}, "
                  f"con fecha {c['fecha']}, a la pena de {c['pena']}. Esta sanción reviste mayor gravedad, configurándose los presupuestos legales.")

        add_p("Se hace presente que el artículo 25 ter en su inciso tercero establece que se considerará más grave el delito o conjunto de ellos "
              "que tuviere asignada en la ley una mayor pena de conformidad con las reglas generales.")

        add_p("\nPOR TANTO,", indent=False)
        add_p("En mérito de lo expuesto, SOLICITO A S.S. acceder a lo solicitado extinguiendo de pleno derecho la sanción antes referida.")

        add_p("\nOTROSÍ: Acompaña sentencia de adulto.", bold=True, indent=False)
        add_p("POR TANTO, SOLICITO A S.S. se tenga por acompañada.", indent=False)

        buf = io.BytesIO(); doc.save(buf); buf.seek(0)
        return buf

# --- INTERFAZ ---
if check_password():
    st.set_page_config(page_title="Generador Judicial Pro", layout="wide")
    
    if "rpa_list" not in st.session_state: st.session_state.rpa_list = []
    if "adulto_list" not in st.session_state: st.session_state.adulto_list = []

    st.title("⚖️ Generador de Extinciones con Adjuntos")
    st.sidebar.button("🧹 Reiniciar Caso", on_click=lambda: st.session_state.update({"rpa_list":[], "adulto_list":[]}))

    # 1. INDIVIDUALIZACIÓN
    st.header("1. Individualización")
    c1, c2, c3 = st.columns(3)
    def_nom = c1.text_input("Defensor/a", "IGNACIO BADILLA LARA")
    imp_nom = c2.text_input("Nombre Adolescente")
    juz_ej = c3.text_input("Juzgado Ejecución")
    
    c4, c5 = st.columns(2)
    rit_pr = c4.text_input("RIT Principal")
    ruc_pr = c5.text_input("RUC Principal")

    # 2. CAUSAS RPA (Solo Manual)
    st.header("2. Causas RPA")
    for i, item in enumerate(st.session_state.rpa_list):
        cols = st.columns([2, 2, 2, 3, 0.5])
        item['rit'] = cols[0].text_input("RIT RPA", item['rit'], key=f"r_rit_{i}")
        item['ruc'] = cols[1].text_input("RUC RPA", item['ruc'], key=f"r_ruc_{i}")
        item['juzgado'] = cols[2].text_input("Juzgado", item['juzgado'], key=f"r_juz_{i}")
        item['sancion'] = cols[3].text_input("Sanción", item['sancion'], key=f"r_san_{i}")
        if cols[4].button("❌", key=f"del_rpa_{i}"): st.session_state.rpa_list.pop(i); st.rerun()
    
    if st.button("➕ Añadir Causa RPA"):
        st.session_state.rpa_list.append({"rit":"", "ruc":"", "juzgado":"", "sancion":""}); st.rerun()

    # 3. CONDENAS ADULTO (Manual + Adjuntos para Unión)
    st.header("3. Condenas Adulto y Sentencias para Adjuntar")
    sentencias_adulto = st.file_uploader("Adjuntar sentencias de Adulto (PDF)", type="pdf", accept_multiple_files=True)
    
    for i, item in enumerate(st.session_state.adulto_list):
        cols = st.columns([2, 2, 2, 2, 2, 0.5])
        item['rit'] = cols[0].text_input("RIT Adulto", item['rit'], key=f"ad_rit_{i}")
        item['ruc'] = cols[1].text_input("RUC Adulto", item['ruc'], key=f"ad_ruc_{i}")
        item['juzgado'] = cols[2].text_input("Juzgado", item['juzgado'], key=f"ad_juz_{i}")
        item['pena'] = cols[3].text_input("Pena", item['pena'], key=f"ad_pen_{i}")
        item['fecha'] = cols[4].text_input("Fecha", item['fecha'], key=f"ad_fec_{i}")
        if cols[5].button("❌", key=f"del_ad_{i}"): st.session_state.adulto_list.pop(i); st.rerun()
    
    if st.button("➕ Añadir Campo de Condena Adulto"):
        st.session_state.adulto_list.append({"rit":"", "ruc":"", "juzgado":"", "pena":"", "fecha":""}); st.rerun()

    # 4. GENERACIÓN
    st.markdown("---")
    if st.button("🚀 GENERAR PAQUETE FINAL", use_container_width=True):
        datos = {
            "defensor": def_nom, "adolescente": imp_nom, "juzgado_ejecucion": juz_ej,
            "rit_principal": rit_pr, "ruc_principal": ruc_pr,
            "causas_rpa": st.session_state.rpa_list, "causas_adulto": st.session_state.adulto_list
        }
        word_buf = GeneradorOficial().generar_docx(datos)
        st.success("✅ Escrito de Extinción generado.")
        st.download_button("⬇️ Descargar Escrito (Word)", word_buf, f"Extincion_{imp_nom}.docx", use_container_width=True)
        
        if sentencias_adulto:
            merged = fitz.open()
            for pdf in sentencias_adulto:
                merged.insert_pdf(fitz.open(stream=pdf.read(), filetype="pdf"))
            pdf_buf = io.BytesIO(merged.tobytes())
            st.download_button("⬇️ Descargar Sentencias Adjuntas Unidas (PDF)", pdf_buf, "Sentencias_Acompanadas.pdf", use_container_width=True)
