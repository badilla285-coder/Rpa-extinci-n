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

# --- 2. LÓGICA DE CONTADORES ---
def actualizar_cont(var, delta):
    st.session_state[var] = max(1, st.session_state[var] + delta)

# --- 3. LECTOR PDF ---
def leer_pdf(archivo):
    d = {"ruc": "", "rit": "", "juz": "", "san": "", "f_sent": "", "f_ejec": ""}
    if archivo:
        try:
            reader = PyPDF2.PdfReader(archivo)
            texto = "".join([p.extract_text() for p in reader.pages])
            r_ruc = re.search(r"RUC:\s?(\d{7,10}-[\dkK])", texto)
            if r_ruc: d["ruc"] = r_ruc.group(1)
            r_rit = re.search(r"RIT:\s?([\d\w-]+-\d{4})", texto)
            if r_rit: d["rit"] = r_rit.group(1)
            r_juz = re.search(r"(Juzgado de Garantía de\s[\w\s]+)", texto, re.I)
            if r_juz: d["juz"] = r_juz.group(1).strip()
            fechas = re.findall(r"(\d{1,2}\sde\s\w+\sde\s\d{4})", texto)
            if len(fechas) >= 1: d["f_sent"] = fechas[0]
            if len(fechas) >= 2: d["f_ejec"] = fechas[1]
        except: pass
    return d

# --- 4. MOTOR DE REDACCIÓN ---
def generar_word(tipo, gral, ejecucion, fondo):
    doc = Document()
    style = doc.styles['Normal']
    style.font.name, style.font.size = 'Cambria', Pt(12)

    p_enc = doc.add_paragraph()
    p_enc.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    if tipo == "EXTINCIÓN":
        p_enc.add_run("EN LO PRINCIPAL: SOLICITA EXTINCIÓN;\nOTROSÍ: ACOMPAÑA DOCUMENTO.").bold = True
    else:
        p_enc.add_run("EN LO PRINCIPAL: Solicita Audiencia de Prescripción;\nOTROSÍ: Oficia a extranjería y se remita extracto de filiación y antecedentes.").bold = True

    doc.add_paragraph(f"\nJUZGADO DE GARANTÍA DE {gral['juz'].upper()}").bold = True

    rits_ej = ", ".join([f"{c['rit']} (RUC: {c['ruc']})" for c in ejecucion if c['rit']])
    intro = doc.add_paragraph()
    intro.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    intro.add_run(f"\n{gral['def'].upper()}, Defensor Penal Público, por {gral['suj'].upper()}, en causas de ejecución {rits_ej}, a US. con respeto digo:")

    cuerpo = doc.add_paragraph()
    cuerpo.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    if tipo == "EXTINCIÓN":
        cuerpo.add_run("\nQue, vengo en solicitar que declare la extinción de las sanciones de la Ley de Responsabilidad Penal Adolescente, en virtud del artículo 25 ter y 25 quinquies de la Ley 20.084.")
    else:
        cuerpo.add_run("\nQue, vengo en solicitar a S.S. se sirva fijar día y hora para celebrar audiencia con el objeto de debatir sobre la prescripción de la pena, de conformidad al artículo 5 de la Ley 20.084.")

    doc.add_paragraph("\nANTECEDENTES:").bold = True
    for i, c in enumerate(fondo):
        p_c = doc.add_paragraph(style='List Bullet')
        p_c.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        p_c.add_run(f"Causa RIT {c['rit']} (RUC {c['ruc']}) del {c['juz']}: ").bold = True
        if tipo == "EXTINCIÓN":
            p_c.add_run(f"Sanción consistente en {c['detalle']}.")
        else:
            p_c.add_run(f"Sentencia de fecha {c['f_sent']}, ejecutoriada con fecha {c['f_ejec']}. Ha operado el plazo legal.")

    doc.add_paragraph("\nPOR TANTO,").bold = True
    doc.add_paragraph("A US. PIDO: Acceder a lo solicitado por encontrarse ajustado a derecho.").bold = True
    
    if tipo == "PRESCRIPCIÓN":
        doc.add_paragraph("\nOTROSÍ:").bold = True
        doc.add_paragraph("Solicito se oficie a Extranjería y se incorpore Extracto de Filiación actualizado.")
        doc.add_paragraph("\nPOR TANTO, PIDO A US. acceder.").bold = True

    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf

# --- 5. INTERFAZ ---
if check_auth():
    st.set_page_config(page_title="Generador IBL", layout="wide")
    
    # Inicialización de contadores
    if 'ne_e' not in st.session_state: st.session_state.ne_e = 1
    if 'nf_e' not in st.session_state: st.session_state.nf_e = 1
    if 'ne_p' not in st.session_state: st.session_state.ne_p = 1
    if 'nf_p' not in st.session_state: st.session_state.nf_p = 1

    st.title("⚖️ Generador IBL")
    t1, t2 = st.tabs(["📄 Extinción", "📜 Prescripción"])

    with t1:
        st.subheader("Módulo de Extinción")
        c1, c2, c3 = st.columns(3)
        g1 = {"def": c1.text_input("Defensor", value="Ignacio Badilla Lara", key="de1"), 
              "suj": c2.text_input("Adolescente", key="se1"), 
              "juz": c3.text_input("Juzgado Destino", key="je1")}
        
        st.markdown("#### 1. Sección Ejecución")
        ca1, ca2 = st.columns([1, 10])
        ca1.button("➕", on_click=actualizar_cont, args=('ne_e', 1), key="be1")
        ca2.button("➖", on_click=actualizar_cont, args=('ne_e', -1), key="be2")
        ej_e = [{"ruc": st.columns(2)[0].text_input(f"RUC Ejecución {i+1}", key=f"re_{i}"), 
                 "rit": st.columns(2)[1].text_input(f"RIT Ejecución {i+1}", key=f"ri_{i}")} for i in range(st.session_state.ne_e)]

        st.markdown("#### 2. Causas a Extinguir")
        cb1, cb2 = st.columns([1, 10])
        cb1.button("➕ ", on_click=actualizar_cont, args=('nf_e', 1), key="bf1")
        cb2.button("➖ ", on_click=actualizar_cont, args=('nf_e', -1), key="bf2")
        fo_e = []
        for i in range(st.session_state.nf_e):
            with st.expander(f"Causa Fondo {i+1}", expanded=True):
                f = st.file_uploader(f"PDF {i+1}", key=f"f1_{i}")
                d = leer_pdf(f)
                c_1, c_2, c_3 = st.columns(3)
                fo_e.append({"ruc": c_1.text_input("RUC", value=d["ruc"], key=f"r1_{i}"), 
                             "rit": c_2.text_input("RIT", value=d["rit"], key=f"t1_{i}"), 
                             "juz": c_3.text_input("Juzgado", value=d["juz"], key=f"j1_{i}"), 
                             "detalle": st.text_area("Transcripción Sanción", key=f"d1_{i}")})
        if st.button("🚀 GENERAR EXTINCIÓN"):
            doc_ext = generar_word("EXTINCIÓN", g1, ej_e, fo_e)
            st.download_button("📥 Descargar", doc_ext, f"Extincion_{g1['suj']}.docx")

    with t2:
        st.subheader("Módulo de Prescripción")
        c1b, c2b, c3b = st.columns(3)
        g2 = {"def": c1b.text_input("Defensor ", value="Ignacio Badilla Lara", key="de2"), 
              "suj": c2b.text_input("Representado", key="se2"), 
              "juz": c3b.text_input("Juzgado Destino ", key="je2")}

        st.markdown("#### 1. Sección Ejecución")
        cc1, cc2 = st.columns([1, 10])
        cc1.button("➕  ", on_click=actualizar_cont, args=('ne_p', 1), key="be3")
        cc2.button("➖  ", on_click=actualizar_cont, args=('ne_p', -1), key="be4")
        ej_p = [{"ruc": st.columns(2)[0].text_input(f"RUC Ejecución {j+1} ", key=f"re2_{j}"), 
                 "rit": st.columns(2)[1].text_input(f"RIT Ejecución {j+1} ", key=f"ri2_{j}")} for j in range(st.session_state.ne_p)]

        st.markdown("#### 2. Causas a Prescribir")
        cd1, cd2 = st.columns([1, 10])
        cd1.button("➕   ", on_click=actualizar_cont, args=('nf_p', 1), key="bf3")
        cd2.button("➖   ", on_click=actualizar_cont, args=('nf_p', -1), key="bf4")
        fo_p = []
        for j in range(st.session_state.nf_p):
            with st.expander(f"Causa Fondo {j+1} ", expanded=True):
                fp = st.file_uploader(f"PDF {j+1} ", key=f"f2_{j}")
                dp = leer_pdf(fp)
                p_1, p_2, p_3 = st.columns(3)
                p_4, p_5 = st.columns(2)
                fo_p.append({"ruc": p_1.text_input("RUC  ", value=dp["ruc"], key=f"r2_{j}"), 
                             "rit": p_2.text_input("RIT  ", value=dp["rit"], key=f"t2_{j}"), 
                             "juz": p_3.text_input("Juzgado  ", value=dp["juz"], key=f"j2_{j}"), 
                             "f_sent": p_4.text_input("Fecha Sentencia", value=dp["f_sent"], key=f"fs_{j}"), 
                             "f_ejec": p_5.text_input("Fecha Ejecutoriada", value=dp["f_ejec"], key=f"fe_{j}")})
        if st.button("🚀 GENERAR PRECRIPCIÓN"):
            doc_pre = generar_word("PRESCRIPCIÓN", g2, ej_p, fo_p)
            st.download_button("📥 Descargar ", doc_pre, f"Prescripcion_{g2['suj']}.docx")

    st.caption("Aplicación hecha por Ignacio Badilla Lara")
