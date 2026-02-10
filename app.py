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

# --- FUNCIONES DE APOYO ---
def aumentar(tipo): st.session_state[tipo] += 1
def disminuir(tipo): 
    if st.session_state[tipo] > 1: st.session_state[tipo] -= 1

def extraer_info_pdf(archivo):
    d = {"ruc":"","rit":"","juz":"","san":"","f_sent":"","f_ejec":""}
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
        fechas = re.findall(r"(\d{1,2}\sde\s\w+\sde\s\d{4})", texto)
        if len(fechas) >= 1: d["f_sent"] = fechas[0]
        if len(fechas) >= 2: d["f_ejec"] = fechas[1]
    except: pass
    return d

# --- MOTOR DE REDACCIÓN ---
def generar_word_completo(tipo, dg, cr, ca_o_presc):
    doc = Document()
    style = doc.styles['Normal']
    style.font.name, style.font.size = 'Cambria', Pt(12)
    
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    if tipo == "EXTINCION":
        p.add_run("EN LO PRINCIPAL: SOLICITA DECLARACIÓN DE EXTINCIÓN DE LA RESPONSABILIDAD PENAL POR CUMPLIMIENTO DE CONDENA EN CAUSAS RPA QUE INDICA;\nOTROSÍ: ACOMPAÑA DOCUMENTOS.").bold = True
    else:
        p.add_run("EN LO PRINCIPAL: Solicita Audiencia de Prescripción;\nOTROSÍ: Oficia a extranjería y se remita extracto de filiación y antecedentes.").bold = True
    
    doc.add_paragraph(f"\nS. J. DE GARANTÍA DE {dg['jp'].upper()}").bold = True
    
    rits_ej = ", ".join([f"{c['rit']} (RUC: {c['ruc']})" for c in dg['ej'] if c['rit']])
    p2 = doc.add_paragraph()
    p2.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p2.add_run(f"\n{dg['def'].upper()}, Defensor Penal Público, por {dg['ado'].upper()}, en causas de ejecución {rits_ej}, a US. con respeto digo:")
    
    if tipo == "EXTINCION":
        doc.add_paragraph("\nI. ANTECEDENTES DE LAS CAUSAS RPA:").bold = True
        for c in cr:
            if c.get('rit'):
                p_c = doc.add_paragraph(style='List Bullet')
                p_c.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
                p_c.add_run(f"Causa RIT {c['rit']} (RUC {c['ruc']}) del {c['juz']}: ").bold = True
                p_c.add_run(f"Sanción consistente en {c['san']}.")
                
        doc.add_paragraph("\nII. FUNDAMENTO DE MAYOR GRAVEDAD (CONDENA ADULTO):").bold = True
        for a in ca_o_presc:
            if a.get('rit'):
                p_a = doc.add_paragraph()
                p_a.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
                p_a.add_run(f"Causa RIT {a['rit']} (RUC {a['ruc']}) del {a['juz']}: ").bold = True
                p_a.add_run(f"Condenado como adulto a la pena de {a['det']}.")
    else:
        doc.add_paragraph("\nANTECEDENTES DE LA PENA:").bold = True
        for c in cr:
            p_c = doc.add_paragraph(style='List Bullet')
            p_c.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            p_c.add_run(f"Causa RIT {c['rit']} (RUC {c['ruc']}) del {c['juz']}: ").bold = True
            p_c.add_run(f"Sancionada por sentencia de fecha {c['f_sent']}, ejecutoriada con fecha {c['f_ejec']}. Ha operado el plazo legal de prescripción según el Art. 5 de la Ley 20.084.")

    doc.add_paragraph("\nPOR TANTO,").bold = True
    doc.add_paragraph(f"A US. PIDO: Se sirva acceder a lo solicitado conforme a derecho.").bold = True
    
    if tipo == "PRESCRIPCION":
        doc.add_paragraph("\nOTROSÍ:").bold = True
        doc.add_paragraph("Vengo en solicitar se oficie a Extranjería y se incorpore extracto de filiación y antecedentes actualizado.")
        doc.add_paragraph("\nPOR TANTO, PIDO A US. Acceder.")

    buf = io.BytesIO(); doc.save(buf); buf.seek(0)
    return buf

# --- INTERFAZ ---
if check_auth():
    st.set_page_config(page_title="Ignacio Badilla - Suite Legal", layout="wide")
    
    # Estados
    for k in ['ne', 'nr', 'na', 'ne_p', 'nr_p']:
        if k not in st.session_state: st.session_state[k] = 1

    st.title("⚖️ Legal Intelligence Suite")
    t1, t2 = st.tabs(["📄 Generador de Extinciones", "📜 Generador de Prescripción"])

    with t1:
        st.subheader("Redactor de Extinción (Art. 25 ter)")
        c_def, c_ado, c_juz = st.columns(3)
        d_f = c_def.text_input("Defensor Titular", value="Ignacio Badilla Lara", key="def_ext")
        a_d = c_ado.text_input("Nombre del Adolescente", key="ado_ext")
        j_p = c_juz.text_input("Juzgado Destino", key="juz_ext")

        st.markdown("#### 1. Causas de Ejecución")
        col_e1, col_e2 = st.columns([1, 6])
        col_e1.button("➕", key="ae_e", on_click=aumentar, args=('ne',))
        col_e2.button("➖", key="de_e", on_click=disminuir, args=('ne',))
        le = []
        for i in range(st.session_state.ne):
            c1, c2 = st.columns(2)
            le.append({"ruc": c1.text_input(f"RUC Ejecución {i+1}", key=f"re{i}"), "rit": c2.text_input(f"RIT Ejecución {i+1}", key=f"te{i}")})

        st.markdown("#### 2. Causas RPA")
        col_r1, col_r2 = st.columns([1, 6])
        col_r1.button("➕", key="ar_e", on_click=aumentar, args=('nr',))
        col_r2.button("➖", key="dr_e", on_click=disminuir, args=('nr',))
        lr = []
        for j in range(st.session_state.nr):
            f_rpa = st.file_uploader(f"Sentencia RPA {j+1}", key=f"fr{j}")
            v = extraer_info_pdf(f_rpa)
            c1, c2, c3 = st.columns(3)
            lr.append({"ruc": c1.text_input(f"RUC RPA {j+1}", value=v["ruc"], key=f"rr{j}"), "rit": c2.text_input(f"RIT RPA {j+1}", value=v["rit"], key=f"tr{j}"), "juz": c3.text_input(f"Juzgado RPA {j+1}", value=v["juz"], key=f"jr{j}"), "san": st.text_area(f"Sanción {j+1}", value=v["san"], key=f"sr{j}")})

        st.markdown("#### 3. Causas Adulto")
        col_a1, col_a2 = st.columns([1, 6])
        col_a1.button("➕", key="aa_e", on_click=aumentar, args=('na',))
        col_a2.button("➖", key="da_e", on_click=disminuir, args=('na',))
        la = []
        for k in range(st.session_state.na):
            f_ad = st.file_uploader(f"Sentencia Adulto {k+1}", key=f"fa{k}")
            va = extraer_info_pdf(f_ad)
            c1, c2, c3 = st.columns(3)
            la.append({"ruc": c1.text_input(f"RUC Adulto {k+1}", value=va["ruc"], key=f"ra{k}"), "rit": c2.text_input(f"RIT Adulto {k+1}", value=va["rit"], key=f"ta{k}"), "juz": c3.text_input(f"Juzgado Adulto {k+1}", value=va["juz"], key=f"ja{k}"), "det": st.text_area(f"Pena Adulto {k+1}", value=va["san"], key=f"da{k}")})

        if st.button("🚀 GENERAR EXTINCIÓN"):
            doc_ext = generar_word_completo("EXTINCION", {"def":d_f,"ado":a_d,"jp":j_p,"ej":le}, lr, la)
            st.download_button("📥 Descargar", doc_ext, f"Extincion_{a_d}.docx")

    with t2:
        st.subheader("Redactor de Prescripción (Art. 5)")
        cp_def, cp_ado, cp_juz = st.columns(3)
        dp_f = cp_def.text_input("Defensor Titular", value="Ignacio Badilla Lara", key="def_pre")
        ap_d = cp_ado.text_input("Nombre del Adolescente", key="ado_pre")
        jp_p = cp_juz.text_input("Juzgado Destino", key="juz_pre")

        st.markdown("#### 1. Causas de Ejecución")
        col_pe1, col_pe2 = st.columns([1, 6])
        col_pe1.button("➕", key="ae_p", on_click=aumentar, args=('ne_p',))
        col_pe2.button("➖", key="de_p", on_click=disminuir, args=('ne_p',))
        le_p = []
        for i in range(st.session_state.ne_p):
            c1, c2 = st.columns(2)
            le_p.append({"ruc": c1.text_input(f"RUC Ejecución {i+1} ", key=f"re_p{i}"), "rit": c2.text_input(f"RIT Ejecución {i+1} ", key=f"te_p{i}")})

        st.markdown("#### 2. Causas a Prescribir")
        col_pr1, col_pr2 = st.columns([1, 6])
        col_pr1.button("➕", key="ar_p", on_click=aumentar, args=('nr_p',))
        col_pr2.button("➖", key="dr_p", on_click=disminuir, args=('nr_p',))
        lr_p = []
        for j in range(st.session_state.nr_p):
            f_pre = st.file_uploader(f"Sentencia a Prescribir {j+1}", key=f"f_pre{j}")
            vp = extraer_info_pdf(f_pre)
            c1, c2, c3 = st.columns(3)
            c4, c5 = st.columns(2)
            lr_p.append({
                "ruc": c1.text_input(f"RUC {j+1}", value=vp["ruc"], key=f"rp_p{j}"),
                "rit": c2.text_input(f"RIT {j+1}", value=vp["rit"], key=f"tp_p{j}"),
                "juz": c3.text_input(f"Juzgado {j+1}", value=vp["juz"], key=f"jp_p{j}"),
                "f_sent": c4.text_input(f"F. Sentencia {j+1}", value=vp["f_sent"], key=f"fs_p{j}"),
                "f_ejec": c5.text_input(f"F. Ejecutoria {j+1}", value=vp["f_ejec"], key=f"fe_p{j}")
            })

        if st.button("🚀 GENERAR PRESCRIPCIÓN"):
            doc_pre = generar_word_completo("PRESCRIPCION", {"def":dp_f,"ado":ap_d,"jp":jp_p,"ej":le_p}, lr_p, [])
            st.download_button("📥 Descargar ", doc_pre, f"Prescripcion_{ap_d}.docx")

    st.caption(f"Aplicación hecha por Ignacio Badilla Lara | {ADMIN_EMAIL}")
