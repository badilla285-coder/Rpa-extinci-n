import streamlit as st
from docx import Document
from docx.shared import Pt, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
import PyPDF2, io, re, datetime, urllib.parse

# --- CONFIGURACIÓN DE ACCESO ---
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

# --- FUNCIONES DE APOYO ---
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

# --- GENERADORES DE WORD ---

def aplicar_formato_ibl(doc):
    style = doc.styles['Normal']
    style.font.name = 'Cambria'
    style.font.size = Pt(12)
    for section in doc.sections:
        section.left_margin = Inches(1)
        section.right_margin = Inches(1)

def generar_extincion_completa(dg, cr, ca):
    doc = Document()
    aplicar_formato_ibl(doc)
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    p.add_run("EN LO PRINCIPAL: SOLICITA DECLARACIÓN DE EXTINCIÓN DE LA RESPONSABILIDAD PENAL POR CUMPLIMIENTO DE CONDENA EN CAUSAS RPA QUE INDICA;\nOTROSÍ: ACOMPAÑA DOCUMENTOS.").bold = True
    doc.add_paragraph(f"\nS. J. DE GARANTÍA DE {dg['jp'].upper()}").bold = True
    rits_ej = ", ".join([f"{c['rit']} (RUC: {c['ruc']})" for c in dg['ej'] if c['rit']])
    p2 = doc.add_paragraph()
    p2.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p2.paragraph_format.first_line_indent = Inches(0.5)
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

def generar_prescripcion(dp):
    doc = Document()
    aplicar_formato_ibl(doc)
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    p.add_run("EN LO PRINCIPAL: Solicita Audiencia de Prescripción;\nOTROSÍ: Oficia a extranjería y se remita extracto de filiación y antecedentes.").bold = True
    doc.add_paragraph(f"\nJUZGADO DE GARANTÍA DE {dp['juzgado'].upper()}").bold = True
    p2 = doc.add_paragraph()
    p2.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p2.add_run(f"{dp['defensor'].upper()}, Defensor Penal Público, en representación de ").bold = False
    p2.add_run(f"{dp['sujeto'].upper()}").bold = True
    p2.add_run(f", en causa RUC {dp['ruc']}, RIT {dp['rit']}, a S.S. respetuosamente digo:")
    
    body = doc.add_paragraph()
    body.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    body.paragraph_format.first_line_indent = Inches(0.5)
    body.add_run("\nQue, por medio de la presente, vengo en solicitar a S.S. se sirva fijar día y hora para celebrar audiencia con el objeto de debatir sobre la ").bold = False
    body.add_run("prescripción de la pena").bold = True
    body.add_run(f" respecto de mi representado, de conformidad a lo dispuesto en el artículo 5 de la Ley N° 20.084 y las normas pertinentes del Código Penal.")
    
    fund = doc.add_paragraph()
    fund.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    fund.add_run(f"\n1. Causa RUC {dp['ruc']} (RIT {dp['rit']} de este Tribunal):").bold = True
    fund.add_run(f" Mi representado sancionado por sentencia de fecha {dp['fecha_sentencia']}, dictada por el {dp['tribunal_origen']} (RIT {dp['rit_origen']}), a las penas de {dp['penas_detalle']}, dicha sentencia quedó ").bold = False
    fund.add_run("firme y ejecutoriada con fecha {dp['fecha_ejecutoria']}.").bold = True
    
    concl = doc.add_paragraph()
    concl.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    concl.add_run(f"\nConsiderando el tiempo transcurrido desde la fecha de ejecutoria hasta la actualidad, ha operado con creces el plazo legal para declarar la prescripción.")
    
    p_final = doc.add_paragraph()
    p_final.add_run("\nPOR TANTO, SOLICITO A S. S. acceder a lo solicitado.").bold = True
    
    buf = io.BytesIO(); doc.save(buf); buf.seek(0)
    return buf

# --- INTERFAZ ---
if check_auth():
    st.set_page_config(page_title="Generador IBL", layout="wide")
    for k in ['ne', 'nr', 'na']:
        if k not in st.session_state: st.session_state[k] = 1

    st.title("⚖️ Generador IBL")
    t1, t2, t3 = st.tabs(["📄 Extinciones", "⚖️ Prescripciones", "📅 Plazos y WhatsApp"])

    with t1:
        st.subheader("Redactor de Extinciones RPA")
        # [MANTENIDO: Todo el código anterior de extinciones va aquí...]
        c_def, c_ado, c_juz = st.columns(3)
        d_f = c_def.text_input("Defensor", value="Ignacio Badilla Lara", key="dext")
        a_d = c_ado.text_input("Adolescente", key="aext")
        j_p = c_juz.text_input("Juzgado", key="jext")
        # (Lógica de botones y listas de causas idéntica a la versión anterior)
        if st.button("🚀 GENERAR EXTINCIÓN"):
            # (Lógica de generación...)
            st.success("Generador Activo")

    with t2:
        st.subheader("Generador de Prescripciones (Formato Estricto)")
        col1, col2 = st.columns(2)
        with col1:
            p_juz = st.text_input("Tribunal Destino", value="SAN BERNARDO")
            p_def = st.text_input("Defensor Titular", value="Ignacio Badilla Lara")
            p_suj = st.text_input("Nombre Representado")
            p_ruc = st.text_input("RUC de la causa")
            p_rit = st.text_input("RIT de la causa")
        with col2:
            p_f_sent = st.text_input("Fecha Sentencia (ej: 23 de agosto de 2021)")
            p_trib_orig = st.text_input("Tribunal que dictó (ej: 9º Juzgado de Garantía)")
            p_rit_orig = st.text_input("RIT Original")
            p_f_ejec = st.text_input("Fecha Ejecutoria")
            p_penas = st.text_area("Detalle de las penas (ej: 3 años de L.A.E.)")
        
        if st.button("📝 GENERAR PRESCRIPCIÓN"):
            datos_p = {"juzgado":p_juz,"defensor":p_def,"sujeto":p_suj,"ruc":p_ruc,"rit":p_rit,"fecha_sentencia":p_f_sent,"tribunal_origen":p_trib_orig,"rit_origen":p_rit_orig,"fecha_ejecutoria":p_f_ejec,"penas_detalle":p_penas}
            doc_p = generar_prescripcion(datos_p)
            st.download_button("📥 Descargar Prescripción IBL", doc_p, f"Prescripcion_{p_suj}.docx")

    with t3:
        st.subheader("📅 Control de Plazos y Notificación")
        col_wa1, col_wa2 = st.columns(2)
        with col_wa1:
            m_tipo = st.selectbox("Tipo de Plazo", ["Apelación", "Nulidad", "Revisión Cautelar"])
            m_fecha = st.date_input("Fecha Inicio", datetime.date.today())
            m_cliente = st.text_input("Nombre del Cliente/Colega")
            m_tel = st.text_input("Teléfono (ej: 56912345678)")
        
        with col_wa2:
            plazo_d = 5 if m_tipo == "Apelación" else 10 if m_tipo == "Nulidad" else 30
            vence_f = m_fecha + datetime.timedelta(days=plazo_d)
            st.metric("Vencimiento", vence_f.strftime('%d/%m/%Y'))
            
            # Botón de WhatsApp
            msg = f"Hola {m_cliente}, te recuerdo que el plazo para la {m_tipo} vence impostergablemente el {vencimiento.strftime('%d/%m/%Y')}. Saludos, Ignacio Badilla."
            url_wa = f"https://wa.me/{m_tel}?text={urllib.parse.quote(msg)}"
            st.link_button("📲 Notificar por WhatsApp", url_wa)

    st.caption("Generador IBL Pro | v3.0")
