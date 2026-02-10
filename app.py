import streamlit as st
from docx import Document
from docx.shared import Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
import PyPDF2, io, re, datetime

# --- 1. SEGURIDAD Y ACCESO ---
ADMIN_EMAIL = "badilla285@gmail.com"
USUARIOS_AUTORIZADOS = [ADMIN_EMAIL]

def check_auth():
    if "auth" not in st.session_state: st.session_state.auth = False
    if not st.session_state.auth:
        st.title("🔐 Acceso Restringido - Generador IBL")
        u = st.text_input("Correo Autorizado")
        p = st.text_input("Contraseña", type="password")
        if st.button("Ingresar"):
            if u in USUARIOS_AUTORIZADOS and p == "nacho2026":
                st.session_state.auth = True
                st.rerun()
            else: st.error("Acceso denegado.")
        return False
    return True

# --- 2. LÓGICA DE ACTUALIZACIÓN (MULTICAUSA) ---
def aumentar(tipo): st.session_state[tipo] += 1
def disminuir(tipo): 
    if st.session_state[tipo] > 1: st.session_state[tipo] -= 1

# --- 3. LECTOR AUTOMÁTICO DE PDF ---
def extraer_info_pdf(archivo):
    d = {"ruc":"","rit":"","juz":"","san":""}
    if archivo is None: return d
    try:
        reader = PyPDF2.PdfReader(archivo)
        texto = "".join([p.extract_text() for p in reader.pages])
        r_ruc = re.search(r"RUC:\s?(\d{7,10}-[\dkK])", texto)
        if r_ruc: d["ruc"] = r_ruc.group(1)
        r_rit = re.search(r"RIT:\s?([\d\w-]+-\d{4})", texto)
        if r_rit: d["rit"] = r_rit.group(1)
        r_juz = re.search(r"(Juzgado de Garantía de\s[\w\s]+)", texto, re.I)
        if r_juz: d["juz"] = r_juz.group(1).strip()
        r_san = re.search(r"(condena a|pena de|sanción de).*?(\d+\s(años|días|meses).*?)(?=\.)", texto, re.I|re.S)
        if r_san: d["san"] = r_san.group(0).replace("\n", " ").strip()
    except: pass
    return d

# --- 4. MOTOR DE REDACCIÓN ROBUSTA ---
def generar_word_ibl(titulo, dg, causas_ej, causas_fondo, es_prescripcion=False):
    doc = Document()
    style = doc.styles['Normal']
    style.font.name, style.font.size = 'Cambria', Pt(12)
    
    # SUMILLA PROFESIONAL
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    p.add_run(f"EN LO PRINCIPAL: {titulo};\nOTROSÍ: ACOMPAÑA DOCUMENTOS.").bold = True
    
    doc.add_paragraph(f"\nS. J. DE GARANTÍA DE {dg['jp'].upper()}").bold = True
    
    rits_ej = ", ".join([f"{c['rit']} (RUC: {c['ruc']})" for c in causas_ej if c['rit']])
    p2 = doc.add_paragraph()
    p2.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p2.add_run(f"\n{dg['def'].upper()}, Defensor Penal Público, por {dg['ado'].upper()}, en causas de ejecución {rits_ej}, a US. con respeto digo:")
    
    doc.add_paragraph("\nI. ANTECEDENTES Y FUNDAMENTOS:").bold = True
    for c in causas_fondo:
        if c.get('rit'):
            p_c = doc.add_paragraph(style='List Bullet')
            p_c.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            p_c.add_run(f"Causa RIT {c['rit']} (RUC {c['ruc']}) del {c['juz']}: ").bold = True
            
            if es_prescripcion:
                texto_p = (f"Sentencia dictada con fecha {c['f_sent']}. La resolución que la declaró ejecutoriada data de {c['f_ejec']}. "
                           f"A la fecha ha transcurrido el plazo legal sin que se haya iniciado el cumplimiento ni existan interrupciones.")
                p_c.add_run(texto_p)
            else:
                p_c.add_run(f"Sanción consistente en: {c['detalle']}")
            
    doc.add_paragraph("\nPOR TANTO,").bold = True
    doc.add_paragraph("A US. PIDO: Acceder a lo solicitado en lo principal por encontrarse ajustado a derecho.").bold = True
    
    buf = io.BytesIO(); doc.save(buf); buf.seek(0)
    return buf

# --- 5. INTERFAZ ---
if check_auth():
    st.set_page_config(page_title="Generador IBL", layout="wide")
    
    # Inicialización de contadores
    for k in ['ne_ext', 'nr_ext', 'ne_pre', 'np_pre']:
        if k not in st.session_state: st.session_state[k] = 1

    st.title("⚖️ Generador IBL")
    tab1, tab2 = st.tabs(["📄 Generador de Extinciones", "📜 Generador de Prescripciones"])

    # --- PESTAÑA 1: EXTINCIÓN (LA MEJOR VERSIÓN) ---
    with tab1:
        st.subheader("Módulo de Extinción de Responsabilidad")
        c1, c2, c3 = st.columns(3)
        def1 = c1.text_input("Defensor Titular", value="Ignacio Badilla Lara", key="def1")
        ado1 = c2.text_input("Nombre del Adolescente", key="ado1")
        juz1 = c3.text_input("Juzgado de Garantía", key="juz1")

        st.markdown("#### 1. Causas de Ejecución")
        st.button("➕ Ejecución", on_click=aumentar, args=('ne_ext',), key="btn_ae1")
        le1 = [{"ruc": st.columns(2)[0].text_input(f"RUC E{i}", key=f"re1_{i}"), "rit": st.columns(2)[1].text_input(f"RIT E{i}", key=f"te1_{i}")} for i in range(st.session_state.ne_ext)]

        st.markdown("#### 2. Causas RPA (Subir para Transcribir)")
        st.button("➕ Causa RPA", on_click=aumentar, args=('nr_ext',), key="btn_ar1")
        lr1 = []
        for j in range(st.session_state.nr_ext):
            f1 = st.file_uploader(f"Sentencia RPA {j+1}", key=f"fr1_{j}")
            v1 = extraer_info_pdf(f1)
            col1, col2, col3 = st.columns(3)
            lr1.append({
                "ruc": col1.text_input(f"RUC RPA {j}", value=v1["ruc"], key=f"rr1_{j}"),
                "rit": col2.text_input(f"RIT RPA {j}", value=v1["rit"], key=f"tr1_{j}"),
                "juz": col3.text_input(f"Juzgado {j}", value=v1["juz"], key=f"jr1_{j}"),
                "detalle": st.text_area(f"Transcripción de Sanción {j}", value=v1["san"], key=f"sr1_{j}", height=100)
            })

        if st.button("🚀 GENERAR EXTINCIÓN ROBUSTA"):
            doc_ext = generar_word_ibl("SOLICITA DECLARACIÓN DE EXTINCIÓN RPA", {"def":def1, "ado":ado1, "jp":juz1}, le1, lr1)
            st.download_button("📥 Descargar Escrito", doc_ext, f"Extincion_{ado1}.docx")

    # --- PESTAÑA 2: PRECRIPCIÓN (FORMATO TÉCNICO) ---
    with tab2:
        st.subheader("Módulo de Prescripción de la Acción/Pena")
        c1b, c2b, c3b = st.columns(3)
        def2 = c1b.text_input("Defensor Titular", value="Ignacio Badilla Lara", key="def2")
        ado2 = c2b.text_input("Sujeto de la Causa", key="ado2")
        juz2 = c3b.text_input("Juzgado de Garantía ", key="juz2")

        st.markdown("#### 1. Causas de Ejecución")
        st.button("➕ Ejecución ", on_click=aumentar, args=('ne_pre',), key="btn_ae2")
        le2 = [{"ruc": st.columns(2)[0].text_input(f"RUC E {i}", key=f"re2_{i}"), "rit": st.columns(2)[1].text_input(f"RIT E {i}", key=f"te2_{i}")} for i in range(st.session_state.ne_pre)]

        st.markdown("#### 2. Causas para Prescribir")
        st.button("➕ Causa Prescripción", on_click=aumentar, args=('np_pre',), key="btn_ap2")
        lp2 = []
        for k in range(st.session_state.np_pre):
            f2 = st.file_uploader(f"Documento Causa {k+1}", key=f"fp2_{k}")
            v2 = extraer_info_pdf(f2)
            col1, col2, col3 = st.columns(3)
            rp, tp, jp = col1.text_input(f"RUC P{k}", value=v2["ruc"], key=f"rp_{k}"), col2.text_input(f"RIT P{k}", value=v2["rit"], key=f"tp_{k}"), col3.text_input(f"Juzgado P{k}", value=v2["juz"], key=f"jp_{k}")
            
            c4, c5 = st.columns(2)
            fs = c4.text_input(f"Fecha de Sentencia {k+1}", placeholder="DD/MM/AAAA", key=f"fs_{k}")
            fe = c5.text_input(f"Fecha Ejecutoriada {k+1}", placeholder="DD/MM/AAAA", key=f"fe_{k}")
            
            lp2.append({"ruc": rp, "rit": tp, "juz": jp, "f_sent": fs, "f_ejec": fe})

        if st.button("🚀 GENERAR PRECRIPCIÓN ROBUSTA"):
            doc_pre = generar_word_ibl("SOLICITA DECLARACIÓN DE PRECRIPCIÓN", {"def":def2, "ado":ado2, "jp":juz2}, le2, lp2, es_prescripcion=True)
            st.download_button("📥 Descargar Escrito ", doc_pre, f"Prescripcion_{ado2}.docx")

    st.markdown("---")
    st.caption("Generador IBL | Ignacio Badilla Lara - Defensoría Penal Pública")
