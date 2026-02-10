import streamlit as st
from docx import Document
from docx.shared import Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
import PyPDF2, io, re, datetime, requests
from bs4 import BeautifulSoup

# --- CONFIGURACIÓN DE ACCESO ---
ADMIN_EMAIL = "badilla285@gmail.com"
USUARIOS_AUTORIZADOS = [ADMIN_EMAIL]

def check_auth():
    if "auth" not in st.session_state:
        st.session_state.auth = False
    if not st.session_state.auth:
        st.title("🔐 Acceso Restringido - Suite Ignacio Badilla")
        col1, col2 = st.columns(2)
        with col1:
            u = st.text_input("Correo electrónico")
            p = st.text_input("Contraseña", type="password")
            if st.button("Ingresar"):
                if u in USUARIOS_AUTORIZADOS and p == "nacho2026":
                    st.session_state.auth = True
                    st.rerun()
                else:
                    st.error("Credenciales no autorizadas.")
        return False
    return True

# --- FUNCIONES CORE (REDACTOR ORIGINAL) ---
def extraer_pdf(f):
    d = {"ruc":"","rit":"","juz":"","san":""}
    if f is None: return d
    try:
        reader = PyPDF2.PdfReader(f)
        txt = "".join([p.extract_text() for p in reader.pages])
        r_ruc = re.search(r"RUC:\s?(\d{7,10}-[\dkK])", txt)
        if r_ruc: d["ruc"] = r_ruc.group(1)
        r_rit = re.search(r"RIT:\s?([\d\w-]+-\d{4})", txt)
        if r_rit: d["rit"] = r_rit.group(1)
        r_juz = re.search(r"(Juzgado de Garantía de\s[\w\s]+)", txt, re.I)
        if r_juz: d["juz"] = r_juz.group(1).strip()
        r_san = re.search(r"(condena a|pena de|sanción de).*?(\d+\s(años|días|meses).*?)(?=\.)", txt, re.I|re.S)
        if r_san: d["san"] = r_san.group(0).replace("\n", " ").strip()
    except: pass
    return d

def generar_escrito(dg, cr, ca):
    doc = Document()
    s = doc.styles['Normal']
    s.font.name, s.font.size = 'Cambria', Pt(12)
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    p.add_run("EN LO PRINCIPAL: SOLICITA DECLARACIÓN DE EXTINCIÓN RPA;\nOTROSÍ: ACOMPAÑA DOCUMENTOS.").bold = True
    doc.add_paragraph(f"\nS. J. DE GARANTÍA DE {dg['jp'].upper()}").bold = True
    rits = ", ".join([f"{c['rit']} (RUC: {c['ruc']})" for c in dg['ej'] if c['rit']])
    p2 = doc.add_paragraph()
    p2.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p2.add_run(f"\n{dg['def'].upper()}, Defensor Penal Público, por {dg['ado'].upper()}, en causas {rits}, digo:")
    doc.add_paragraph("\nI. ANTECEDENTES RPA:").bold = True
    for c in cr:
        if c['rit']:
            li = doc.add_paragraph(style='List Bullet')
            li.add_run(f"RIT {c['rit']} (RUC {c['ruc']}) de {c['juz']}: ").bold = True
            li.add_run(f"{c['san']}.")
    doc.add_paragraph("\nII. FUNDAMENTO ADULTO:").bold = True
    for a in ca:
        if a['rit']:
            pa = doc.add_paragraph()
            pa.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            pa.add_run(f"RIT {a['rit']} (RUC {a['ruc']}) de {a['juz']}: ").bold = True
            pa.add_run(f"Condenado como adulto a {a['det']}.")
    doc.add_paragraph("\nPOR TANTO, PIDO A US. acceder.").bold = True
    buf = io.BytesIO(); doc.save(buf); buf.seek(0)
    return buf

# --- LÓGICA DE PLAZOS AMPLIADA ---
def calcular_plazos_legales(tipo, fecha):
    # Definición de plazos según CPP y Ley RPA
    plazos = {
        "Apelación Sentencia Definitiva": 5,
        "Recurso de Nulidad": 10,
        "Reposición (en audiencia)": 0,
        "Reposición (fuera de audiencia)": 3,
        "Revisión Prisión Preventiva (Plazo sugerido)": 30, # Días para pedir revisión periódica
        "Apelación Prisión Preventiva / IP": 5,
        "Apelación por Cautelar de Menor Intensidad": 5
    }
    dias = plazos.get(tipo, 0)
    vence = fecha + datetime.timedelta(days=dias)
    return vence

# --- INTERFAZ ---
if check_auth():
    st.set_page_config(page_title="Ignacio Badilla - Legal Suite", layout="wide")
    
    if 'ne' not in st.session_state: st.session_state.ne = 1
    if 'nr' not in st.session_state: st.session_state.nr = 1
    if 'na' not in st.session_state: st.session_state.na = 1

    st.title("⚖️ Legal Intelligence Suite")
    tabs = st.tabs(["📄 Generador de Extinciones", "📅 Calculadora de Plazos & Cautelares", "🔍 Módulo MIA"])

    with tabs[0]:
        st.subheader("Redactor de Escritos de Extinción RPA")
        d_f = st.text_input("Defensor Titular", value="Ignacio Badilla Lara")
        a_d = st.text_input("Nombre del Adolescente")
        j_p = st.text_input("Juzgado de Garantía Destino")
        
        st.write("---")
        st.markdown("### 1. Causas de Ejecución")
        ce1, ce2 = st.columns(2)
        if ce1.button("➕ Añadir Ejecución"): st.session_state.ne += 1
        if ce2.button("➖ Quitar Ejecución") and st.session_state.ne > 1: st.session_state.ne -= 1
        le = [{"ruc": st.columns(2)[0].text_input(f"RUC E {i+1}", key=f"re{i}"), "rit": st.columns(2)[1].text_input(f"RIT E {i+1}", key=f"te{i}")} for i in range(st.session_state.ne)]

        st.markdown("### 2. Causas RPA")
        cr1, cr2 = st.columns(2)
        if cr1.button("➕ Añadir RPA"): st.session_state.nr += 1
        if cr2.button("➖ Quitar RPA") and st.session_state.nr > 1: st.session_state.nr -= 1
        lr = []
        for j in range(st.session_state.nr):
            f = st.file_uploader(f"Sentencia RPA {j+1}", key=f"fr{j}")
            v = extraer_pdf(f); col1, col2, col3 = st.columns(3)
            lr.append({"ruc":col1.text_input(f"RUC RPA {j+1}",value=v["ruc"],key=f"rr{j}"),"rit":col2.text_input(f"RIT RPA {j+1}",value=v["rit"],key=f"tr{j}"),"juz":col3.text_input(f"Tribunal RPA {j+1}",value=v["juz"],key=f"jr{j}"),"san":st.text_area(f"Sanción {j+1}",value=v["san"],key=f"sr{j}")})

        st.markdown("### 3. Causas Adulto")
        ca1, ca2 = st.columns(2)
        if ca1.button("➕ Añadir Adulto"): st.session_state.na += 1
        if ca2.button("➖ Quitar Adulto") and st.session_state.na > 1: st.session_state.na -= 1
        la = []
        for k in range(st.session_state.na):
            fa = st.file_uploader(f"Sentencia Adulto {k+1}", key=f"fa{k}")
            va = extraer_pdf(fa); cl1, cl2, cl3 = st.columns(3)
            la.append({"ruc":cl1.text_input(f"RUC Adulto {k+1}",value=va["ruc"],key=f"ra{k}"),"rit":cl2.text_input(f"RIT Adulto {k+1}",value=va["rit"],key=f"ta{k}"),"juz":cl3.text_input(f"Tribunal Adulto {k+1}",value=va["juz"],key=f"ja{k}"),"det":st.text_area(f"Pena {k+1}",value=va["san"],key=f"da{k}")})

        if st.button("🚀 GENERAR ESCRITO"):
            res = generar_escrito({"def":d_f,"ado":a_d,"jp":j_p,"ej":le}, lr, la)
            st.download_button("📥 Descargar Word", res, f"Extincion_{a_d}.docx")

    with tabs[1]:
        st.subheader("Cómputo de Plazos Judiciales")
        col_res, col_f = st.columns(2)
        with col_res:
            res_tipo = st.selectbox("Resolución / Medida", [
                "Apelación Prisión Preventiva / IP",
                "Apelación Sentencia Definitiva",
                "Recurso de Nulidad",
                "Reposición (fuera de audiencia)",
                "Revisión Prisión Preventiva (Plazo sugerido)"
            ])
        with col_f:
            f_inicio = st.date_input("Fecha de Resolución/Notificación", datetime.date.today())
        
        vencimiento = calcular_plazos_legales(res_tipo, f_inicio)
        st.error(f"📅 El plazo vence el: {vencimiento.strftime('%d/%m/%Y')}")
        
        st.divider()
        st.info("💡 **Nota Legal:** Los plazos de apelación en el proceso penal son generalmente de días corridos. Para la Internación Provisoria (IP) y Prisión Preventiva, la apelación debe interponerse dentro de los 5 días.")

    with tabs[2]:
        st.subheader("Módulo de Inteligencia MIA")
        rut_i = st.text_input("RUT a investigar")
        if rut_i:
            r_limpio = rut_i.replace(".","").split("-")[0]
            st.link_button(f"👤 Abrir Datos Civiles de {rut_i}", f"https://www.nombrerutyfirma.com/rut/{r_limpio}")
            st.link_button("⚖️ Consultar PJUD", "https://oficinajudicialvirtual.pjud.cl/")

    st.markdown("---")
    st.caption("🚀 Aplicación hecha por Ignacio Badilla Lara | Propiedad Intelectual Protegida")
