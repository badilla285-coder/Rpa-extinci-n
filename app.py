import streamlit as st
from docx import Document
from docx.shared import Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
import PyPDF2, io, re, datetime

# --- CONFIGURACIÓN DE ACCESO ---
ADMIN_EMAIL = "badilla285@gmail.com"
USUARIOS_AUTORIZADOS = [ADMIN_EMAIL]

def check_auth():
    if "auth" not in st.session_state: st.session_state.auth = False
    if not st.session_state.auth:
        st.title("🔐 Acceso Restringido - Suite Ignacio Badilla")
        u = st.text_input("Correo Autorizado")
        p = st.text_input("Contraseña", type="password")
        if st.button("Ingresar"):
            if u in USUARIOS_AUTORIZADOS and p == "nacho2026":
                st.session_state.auth = True
                st.rerun()
            else: st.error("Acceso denegado.")
        return False
    return True

# --- FUNCIONES DE APOYO (EXTRACCIÓN Y LÓGICA) ---
def aumentar(tipo): st.session_state[tipo] += 1
def disminuir(tipo): 
    if st.session_state[tipo] > 1: st.session_state[tipo] -= 1

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

def generar_word_completo(dg, cr, ca):
    doc = Document()
    style = doc.styles['Normal']
    style.font.name, style.font.size = 'Cambria', Pt(12)
    
    # Encabezado (SUMILLA)
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    p.add_run("EN LO PRINCIPAL: SOLICITA DECLARACIÓN DE EXTINCIÓN DE LA RESPONSABILIDAD PENAL POR CUMPLIMIENTO DE CONDENA EN CAUSAS RPA QUE INDICA;\nOTROSÍ: ACOMPAÑA DOCUMENTOS.").bold = True
    
    doc.add_paragraph(f"\nS. J. DE GARANTÍA DE {dg['jp'].upper()}").bold = True
    
    rits_ej = ", ".join([f"{c['rit']} (RUC: {c['ruc']})" for c in dg['ej'] if c['rit']])
    p2 = doc.add_paragraph()
    p2.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p2.add_run(f"\n{dg['def'].upper()}, Defensor Penal Público, por {dg['ado'].upper()}, en causas de ejecución {rits_ej}, a US. con respeto digo:")
    
    doc.add_paragraph("\nI. ANTECEDENTES DE LAS CAUSAS RPA:").bold = True
    for c in cr:
        if c.get('rit'):
            p_c = doc.add_paragraph(style='List Bullet')
            p_c.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            p_c.add_run(f"Causa RIT {c['rit']} (RUC {c['ruc']}) del {c['juz']}: ").bold = True
            p_c.add_run(f"Sanción consistente en {c['san']}.")
            
    doc.add_paragraph("\nII. FUNDAMENTO DE MAYOR GRAVEDAD (CONDENA ADULTO):").bold = True
    for a in ca:
        if a.get('rit'):
            p_a = doc.add_paragraph()
            p_a.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            p_a.add_run(f"Causa RIT {a['rit']} (RUC {a['ruc']}) del {a['juz']}: ").bold = True
            p_a.add_run(f"Condenado como adulto a la pena de {a['det']}.")
            
    doc.add_paragraph("\nPOR TANTO,").bold = True
    doc.add_paragraph("A US. PIDO: Se sirva tener por declarada la extinción de la responsabilidad penal de las causas individualizadas por cumplimiento de condena.").bold = True
    
    buf = io.BytesIO(); doc.save(buf); buf.seek(0)
    return buf

# --- INTERFAZ ---
if check_auth():
    st.set_page_config(page_title="Ignacio Badilla - Legal Suite", layout="wide")
    
    # Inicializar contadores si no existen
    for k in ['ne', 'nr', 'na']:
        if k not in st.session_state: st.session_state[k] = 1

    st.title("⚖️ Legal Intelligence Suite")
    t1, t2 = st.tabs(["📄 Generador de Extinciones", "📅 Calculadora de Plazos"])

    with t1:
        st.subheader("Redactor de Escritos de Extinción RPA")
        c_def, c_ado, c_juz = st.columns(3)
        d_f = c_def.text_input("Defensor Titular", value="Ignacio Badilla Lara")
        a_d = c_ado.text_input("Nombre del Adolescente")
        j_p = c_juz.text_input("Juzgado de Garantía Destino")

        # 1. Ejecución
        st.markdown("#### 1. Causas de Ejecución Actuales")
        col_e1, col_e2 = st.columns([1, 6])
        col_e1.button("➕", key="ae", on_click=aumentar, args=('ne',))
        col_e2.button("➖", key="de", on_click=disminuir, args=('ne',))
        le = []
        for i in range(st.session_state.ne):
            c1, c2 = st.columns(2)
            le.append({"ruc": c1.text_input(f"RUC Ejecución {i+1}", key=f"re{i}"), "rit": c2.text_input(f"RIT Ejecución {i+1}", key=f"te{i}")})

        # 2. RPA a extinguir
        st.markdown("#### 2. Causas RPA (Subir Sentencias)")
        col_r1, col_r2 = st.columns([1, 6])
        col_r1.button("➕", key="ar", on_click=aumentar, args=('nr',))
        col_r2.button("➖", key="dr", on_click=disminuir, args=('nr',))
        lr = []
        for j in range(st.session_state.nr):
            f_rpa = st.file_uploader(f"Adjuntar Sentencia RPA {j+1}", key=f"fr{j}")
            v = extraer_info_pdf(f_rpa)
            c1, c2, c3 = st.columns(3)
            lr.append({
                "ruc": c1.text_input(f"RUC RPA {j+1}", value=v["ruc"], key=f"rr{j}"),
                "rit": c2.text_input(f"RIT RPA {j+1}", value=v["rit"], key=f"tr{j}"),
                "juz": c3.text_input(f"Juzgado RPA {j+1}", value=v["juz"], key=f"jr{j}"),
                "san": st.text_area(f"Sanción Transcrita {j+1}", value=v["san"], key=f"sr{j}")
            })

        # 3. Adulto fundamento
        st.markdown("#### 3. Causas Adulto (Fundamento de Extinción)")
        col_a1, col_a2 = st.columns([1, 6])
        col_a1.button("➕", key="aa", on_click=aumentar, args=('na',))
        col_a2.button("➖", key="da", on_click=disminuir, args=('na',))
        la = []
        for k in range(st.session_state.na):
            f_ad = st.file_uploader(f"Adjuntar Sentencia Adulto {k+1}", key=f"fa{k}")
            va = extraer_info_pdf(f_ad)
            c1, c2, c3 = st.columns(3)
            la.append({
                "ruc": c1.text_input(f"RUC Adulto {k+1}", value=va["ruc"], key=f"ra{k}"),
                "rit": c2.text_input(f"RIT Adulto {k+1}", value=va["rit"], key=f"ta{k}"),
                "juz": c3.text_input(f"Juzgado Adulto {k+1}", value=va["juz"], key=f"ja{k}"),
                "det": st.text_area(f"Pena Adulto {k+1}", value=va["san"], key=f"da{k}")
            })

        if st.button("🚀 GENERAR ESCRITO ROBUSTO"):
            doc_final = generar_word_completo({"def":d_f,"ado":a_d,"jp":j_p,"ej":le}, lr, la)
            st.download_button("📥 Descargar Escrito Cambria 12", doc_final, f"Extincion_{a_d}.docx")

    with t2:
        st.subheader("Cómputo de Plazos Críticos")
        tipo_res = st.selectbox("Resolución/Medida", [
            "Apelación Prisión Preventiva / IP (5 días)",
            "Apelación Sentencia Definitiva (5 días)",
            "Recurso de Nulidad (10 días)",
            "Revisión Mensual Cautelar (30 días)"
        ])
        fecha_not = st.date_input("Fecha Notificación")
        dias = 5 if "5" in tipo_res else 10 if "10" in tipo_res else 30
        st.error(f"🚨 El plazo fatal vence el: {(fecha_not + datetime.timedelta(days=dias)).strftime('%d/%m/%Y')}")

    st.markdown("---")
    st.caption(f"Aplicación hecha por Ignacio Badilla Lara | {ADMIN_EMAIL}")
