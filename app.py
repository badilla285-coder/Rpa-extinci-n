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
        u = st.text_input("Correo Autorizado")
        p = st.text_input("Contraseña", type="password")
        if st.button("Ingresar"):
            if u in USUARIOS_AUTORIZADOS and p == "nacho2026":
                st.session_state.auth = True
                st.rerun()
            else: st.error("Acceso denegado.")
        return False
    return True

# --- 2. LÓGICA DE BOTONES ---
def aumentar(tipo): st.session_state[tipo] += 1
def disminuir(tipo): 
    if st.session_state[tipo] > 1: st.session_state[tipo] -= 1

# --- 3. LECTOR PDF (AUTOMATIZACIÓN) ---
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
    except: pass
    return d

# --- 4. MOTOR DE REDACCIÓN ---
def generar_word(titulo, dg, causas_ej, causas_fondo, es_prescripcion=False):
    doc = Document()
    style = doc.styles['Normal']
    style.font.name, style.font.size = 'Cambria', Pt(12)
    
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    p.add_run(f"EN LO PRINCIPAL: {titulo};\nOTROSÍ: ACOMPAÑA DOCUMENTOS.").bold = True
    
    doc.add_paragraph(f"\nS. J. DE GARANTÍA DE {dg['jp'].upper()}").bold = True
    
    rits_ej = ", ".join([f"{c['rit']} (RUC: {c['ruc']})" for c in causas_ej if c['rit']])
    p2 = doc.add_paragraph()
    p2.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p2.add_run(f"\n{dg['def'].upper()}, Defensor Penal Público, por {dg['ado'].upper()}, en causas de ejecución {rits_ej}, a US. con respeto digo:")
    
    doc.add_paragraph("\nI. ANTECEDENTES:").bold = True
    for c in causas_fondo:
        if c.get('rit'):
            p_c = doc.add_paragraph(style='List Bullet')
            p_c.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            p_c.add_run(f"Causa RIT {c['rit']} (RUC {c['ruc']}) del {c['juz']}: ").bold = True
            
            if es_prescripcion:
                texto_p = (f"Sentencia dictada con fecha {c['f_sent']}. La resolución que la declaró ejecutoriada data de {c['f_ejec']}. "
                           f"A la fecha ha transcurrido el plazo legal sin que se haya iniciado el cumplimiento ni existan interrupciones, "
                           f"por lo que se solicita declarar la prescripción de la pena.")
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
    
    # Iniciar contadores
    for k in ['ne1', 'nr1', 'ne2', 'np2']:
        if k not in st.session_state: st.session_state[k] = 1

    st.title("⚖️ Generador IBL")
    tab1, tab2, tab3 = st.tabs(["📄 Extinción RPA", "📜 Prescripción", "📅 Plazos"])

    # --- PESTAÑA 1: EXTINCIÓN ---
    with tab1:
        st.subheader("Módulo de Extinciones")
        c1, c2, c3 = st.columns(3)
        d_f1, a_d1, j_p1 = c1.text_input("Defensor", value="Ignacio Badilla Lara", key="df1"), c2.text_input("Adolescente", key="ad1"), c3.text_input("Juzgado Destino", key="jp1")

        st.markdown("#### 1. Ejecución")
        st.button("➕ Ejecución", on_click=aumentar, args=('ne1',), key="be1")
        le1 = [{"ruc": st.columns(2)[0].text_input(f"RUC E{i}", key=f"re1{i}"), "rit": st.columns(2)[1].text_input(f"RIT E{i}", key=f"te1{i}")} for i in range(st.session_state.ne1)]

        st.markdown("#### 2. Causas RPA a Extinguir")
        st.button("➕ Causa RPA", on_click=aumentar, args=('nr1',), key="br1")
        lr1 = []
        for j in range(st.session_state.nr1):
            f1 = st.file_uploader(f"Sentencia RPA {j+1}", key=f"fr1{j}")
            v1 = extraer_info_pdf(f1)
            col1, col2, col3 = st.columns(3)
            lr1.append({
                "ruc": col1.text_input(f"RUC RPA {j}", value=v1["ruc"], key=f"rr1{j}"),
                "rit": col2.text_input(f"RIT RPA {j}", value=v1["rit"], key=f"tr1{j}"),
                "juz": col3.text_input(f"Juzgado {j}", value=v1["juz"], key=f"jr1{j}"),
                "detalle": st.text_area(f"Transcripción Sanción {j}", key=f"sr1{j}", height=100)
            })
        
        if st.button("🚀 GENERAR EXTINCIÓN"):
            doc1 = generar_word("SOLICITA DECLARACIÓN DE EXTINCIÓN RPA", {"def":d_f1, "ado":a_d1, "jp":j_p1}, le1, lr1)
            st.download_button("📥 Descargar Word", doc1, f"Extincion_{a_d1}.docx")

    # --- PESTAÑA 2: PRECRIPCIÓN (CORREGIDA) ---
    with tab2:
        st.subheader("Módulo de Prescripciones")
        c1b, c2b, c3b = st.columns(3)
        d_f2, a_d2, j_p2 = c1b.text_input("Defensor", value="Ignacio Badilla Lara", key="df2"), c2b.text_input("Sujeto", key="ad2"), c3b.text_input("Juzgado Destino", key="jp2")

        st.markdown("#### 1. Ejecución")
        st.button("➕ Ejecución ", on_click=aumentar, args=('ne2',), key="be2")
        le2 = [{"ruc": st.columns(2)[0].text_input(f"RUC E {i}", key=f"re2{i}"), "rit": st.columns(2)[1].text_input(f"RIT E {i}", key=f"te2{i}")} for i in range(st.session_state.ne2)]

        st.markdown("#### 2. Causas a Prescribir")
        st.button("➕ Causa Prescripción", on_click=aumentar, args=('np2',), key="bp2")
        lp2 = []
        for k in range(st.session_state.np2):
            f2 = st.file_uploader(f"Antecedentes {k+1}", key=f"fp2{k}")
            v2 = extraer_info_pdf(f2)
            col1, col2, col3 = st.columns(3)
            ruc_p = col1.text_input(f"RUC P {k}", value=v2["ruc"], key=f"rp2{k}")
            rit_p = col2.text_input(f"RIT P {k}", value=v2["rit"], key=f"tp2{k}")
            juz_p = col3.text_input(f"Juzgado P {k}", value=v2["juz"], key=f"jp2{k}")
            
            # Nuevos campos del formato solicitado
            col4, col5 = st.columns(2)
            f_sent = col4.text_input(f"Fecha Sentencia (DD/MM/AAAA) {k}", key=f"fs{k}")
            f_ejec = col5.text_input(f"Fecha Ejecutoriada (DD/MM/AAAA) {k}", key=f"fej{k}")
            
            lp2.append({"ruc": ruc_p, "rit": rit_p, "juz": juz_p, "f_sent": f_sent, "f_ejec": f_ejec})

        if st.button("🚀 GENERAR PRECRIPCIÓN"):
            doc2 = generar_word("SOLICITA DECLARACIÓN DE PRECRIPCIÓN", {"def":d_f2, "ado":a_d2, "jp":j_p2}, le2, lp2, es_prescripcion=True)
            st.download_button("📥 Descargar Word ", doc2, f"Prescripcion_{a_d2}.docx")

    # --- PESTAÑA 3: PLAZOS ---
    with tab3:
        st.subheader("📅 Plazos")
        f_n = st.date_input("Notificación")
        st.info(f"Vencimiento (5 días): {(f_n + datetime.timedelta(days=5)).strftime('%d/%m/%Y')}")

    st.caption("Generador IBL | Propiedad de Ignacio Badilla Lara")
