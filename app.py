import streamlit as st
from docx import Document
from docx.shared import Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
import PyPDF2, io, re, datetime

# --- 1. SEGURIDAD ---
ADMIN_EMAIL = "badilla285@gmail.com"
USUARIOS_AUTORIZADOS = [ADMIN_EMAIL]

def check_auth():
    if "auth" not in st.session_state: st.session_state.auth = False
    if not st.session_state.auth:
        st.title("🔐 Acceso - Generador IBL")
        u = st.text_input("Correo")
        p = st.text_input("Contraseña", type="password")
        if st.button("Ingresar"):
            if u in USUARIOS_AUTORIZADOS and p == "nacho2026":
                st.session_state.auth = True
                st.rerun()
            else: st.error("Acceso denegado.")
        return False
    return True

# --- 2. LÓGICA DE CONTADORES ---
def cambiar_contador(variable, delta):
    st.session_state[variable] = max(1, st.session_state[variable] + delta)

# --- 3. LECTOR PDF (AUTOMATIZACIÓN) ---
def extraer_datos(archivo):
    datos = {"ruc": "", "rit": "", "juz": "", "san": "", "f_sent": ""}
    if archivo:
        try:
            reader = PyPDF2.PdfReader(archivo)
            texto = "".join([p.extract_text() for p in reader.pages])
            r_ruc = re.search(r"RUC:\s?(\d{7,10}-[\dkK])", texto)
            if r_ruc: datos["ruc"] = r_ruc.group(1)
            r_rit = re.search(r"RIT:\s?([\d\w-]+-\d{4})", texto)
            if r_rit: datos["rit"] = r_rit.group(1)
            r_juz = re.search(r"(Juzgado de Garantía de\s[\w\s]+)", texto, re.I)
            if r_juz: datos["juz"] = r_juz.group(1).strip()
            r_san = re.search(r"(condena a|pena de|sanción de).*?(\d+\s(años|días|meses).*?)(?=\.)", texto, re.I|re.S)
            if r_san: datos["san"] = r_san.group(0).replace("\n", " ").strip()
            fechas = re.findall(r"(\d{1,2}\sde\s\w+\sde\s\d{4})", texto)
            if fechas: datos["f_sent"] = fechas[0]
        except: pass
    return datos

# --- 4. MOTOR DE REDACCIÓN (ESTILO MODELOS IBL) ---
def generar_word_final(tipo, info, causas):
    doc = Document()
    style = doc.styles['Normal']
    style.font.name, style.font.size = 'Cambria', Pt(12)

    p_enc = doc.add_paragraph()
    p_enc.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    if tipo == "EXTINCIÓN":
        p_enc.add_run("EN LO PRINCIPAL: SOLICITA EXTINCIÓN;\nOTROSÍ: ACOMPAÑA DOCUMENTO.").bold = True
    else:
        p_enc.add_run("EN LO PRINCIPAL: Solicita Audiencia de Prescripción;\nOTROSÍ: Oficia a extranjería y se remita extracto de filiación y antecedentes.").bold = True

    doc.add_paragraph(f"\nJUZGADO DE GARANTÍA DE {info['juzgado'].upper()}").bold = True

    intro = doc.add_paragraph()
    intro.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    intro.add_run(f"\n{info['defensor'].upper()}, Abogado, Defensor Penal Público, en representación de {info['sujeto'].upper()}, a S.S. respetuosamente digo:")

    cuerpo = doc.add_paragraph()
    cuerpo.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    if tipo == "EXTINCIÓN":
        cuerpo.add_run(f"\nQue, vengo en solicitar que declare la extinción de las sanciones de la Ley de Responsabilidad Penal Adolescente, en virtud del artículo 25 ter y 25 quinquies de la Ley 20.084.")
    else:
        cuerpo.add_run(f"\nQue, por medio de la presente, vengo en solicitar a S.S. se sirva fijar día y hora para celebrar audiencia con el objeto de debatir sobre la prescripción de la pena, de conformidad a lo dispuesto en el artículo 5 de la Ley N° 20.084.")

    doc.add_paragraph("\nANTECEDENTES:").bold = True
    for i, c in enumerate(causas):
        p_c = doc.add_paragraph()
        p_c.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        p_c.add_run(f"{i+1}. RIT: {c['rit']}, RUC: {c['ruc']} ({c['juz']}): ").bold = True
        if tipo == "EXTINCIÓN":
            p_c.add_run(f"Condenado a sanción de {c['detalle']}.")
        else:
            p_c.add_run(f"Sentencia de fecha {c['f_sent']}, la cual quedó firme y ejecutoriada con fecha {c['f_ejec']}. Ha operado el plazo legal del Art. 5 Ley 20.084.")

    doc.add_paragraph("\nPOR TANTO,").bold = True
    final = doc.add_paragraph()
    if tipo == "EXTINCIÓN":
        final.add_run("SOLICITO A S.S. acceder a lo solicitado extinguiendo de pleno derecho la sanción antes referida.")
    else:
        final.add_run("SOLICITO A S.S. acceder a lo solicitado, fijando día y hora para celebrar audiencia.")
        doc.add_paragraph("\nOTROSÍ:").bold = True
        doc.add_paragraph("Vengo en solicitar se oficie a Extranjería y se incorpore Extracto de Filiación actualizado.")
        doc.add_paragraph("\nPOR TANTO, SOLICITO A S.S. acceder a lo solicitado.")

    buf = io.BytesIO(); doc.save(buf); buf.seek(0)
    return buf

# --- 5. INTERFAZ ---
if check_auth():
    st.set_page_config(page_title="Generador IBL", layout="wide")
    
    if 'n_ext' not in st.session_state: st.session_state.n_ext = 1
    if 'n_pre' not in st.session_state: st.session_state.n_pre = 1

    st.title("⚖️ Generador IBL")
    t1, t2 = st.tabs(["📄 Extinción RPA", "📜 Prescripción"])

    with t1:
        st.subheader("Generador de Extinciones (Modelo Alarcón)")
        c1, c2, c3 = st.columns(3)
        gral1 = {"defensor": c1.text_input("Defensor", value="Ignacio Badilla Lara", key="d1"), "sujeto": c2.text_input("Adolescente", key="s1"), "juzgado": c3.text_input("Juzgado Destino", key="j1")}
        
        st.button("➕ Añadir Causa", on_click=cambiar_contador, args=('n_ext', 1), key="a1")
        st.button("➖ Quitar Causa", on_click=cambiar_contador, args=('n_ext', -1), key="q1")
        
        causas_ext = []
        for i in range(st.session_state.n_ext):
            with st.expander(f"Causa Extinción {i+1}", expanded=True):
                f = st.file_uploader(f"PDF Extinción {i+1}", key=f"f_ext_{i}")
                d = extraer_datos(f)
                cx1, cx2, cx3 = st.columns(3)
                causas_ext.append({
                    "ruc": cx1.text_input("RUC", value=d["ruc"], key=f"re1_{i}"),
                    "rit": cx2.text_input("RIT", value=d["rit"], key=f"te1_{i}"),
                    "juz": cx3.text_input("Juzgado", value=d["juz"], key=f"je1_{i}"),
                    "detalle": st.text_area("Sanción Transcrita", value=d["san"], key=f"de1_{i}")
                })
        if st.button("🚀 GENERAR EXTINCIÓN"):
            doc_e = generar_word_final("EXTINCIÓN", gral1, causas_ext)
            st.download_button("📥 Descargar Word", doc_e, f"Extincion_{gral1['sujeto']}.docx")

    with t2:
        st.subheader("Generador de Prescripciones (Modelo Acevedo)")
        c1b, c2b, c3b = st.columns(3)
        gral2 = {"defensor": c1b.text_input("Defensor", value="Ignacio Badilla Lara", key="d2"), "sujeto": c2b.text_input("Representado", key="s2"), "juzgado": c3b.text_input("Juzgado Destino ", key="j2")}
        
        st.button("➕ Añadir Causa ", on_click=cambiar_contador, args=('n_pre', 1), key="a2")
        st.button("➖ Quitar Causa ", on_click=cambiar_contador, args=('n_pre', -1), key="q2")
        
        causas_pre = []
        for j in range(st.session_state.n_pre):
            with st.expander(f"Causa Prescripción {j+1}", expanded=True):
                f_p = st.file_uploader(f"PDF Prescripción {j+1}", key=f"f_pre_{j}")
                dp = extraer_datos(f_p)
                px1, px2, px3 = st.columns(3)
                px4, px5 = st.columns(2)
                causas_pre.append({
                    "ruc": px1.text_input("RUC ", value=dp["ruc"], key=f"re2_{j}"),
                    "rit": px2.text_input("RIT ", value=dp["rit"], key=f"te2_{j}"),
                    "juz": px3.text_input("Juzgado ", value=dp["juz"], key=f"je2_{j}"),
                    "f_sent": px4.text_input("Fecha Sentencia", value=dp["f_sent"], key=f"fs2_{j}"),
                    "f_ejec": px5.text_input("Fecha Ejecutoriada", key=f"fe2_{j}")
                })
        if st.button("🚀 GENERAR PRECRIPCIÓN"):
            doc_p = generar_word_final("PRECRIPCIÓN", gral2, causas_pre)
            st.download_button("📥 Descargar Word ", doc_p, f"Prescripcion_{gral2['sujeto']}.docx")

    st.caption("Aplicación hecha por Ignacio Badilla Lara")
