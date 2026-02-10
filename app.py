import streamlit as st
from docx import Document
from docx.shared import Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
import PyPDF2, io, re, datetime, requests
from bs4 import BeautifulSoup

# --- 1. SEGURIDAD Y ACCESO ---
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
            else: st.error("Acceso no autorizado.")
        return False
    return True

# --- 2. MOTOR MIA MEJORADO (EXTRACCIÓN EN PANTALLA) ---
def buscar_datos_civiles(rut_limpio):
    try:
        url = f"https://www.nombrerutyfirma.com/rut/{rut_limpio}"
        # Disfrazamos la petición para que el sitio crea que es un humano
        h = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        r = requests.get(url, headers=h, timeout=5)
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, 'html.parser')
            tabla = soup.find('table', {'class': 'table'})
            if tabla:
                d = tabla.find_all('tr')[1].find_all('td')
                return {"nombre": d[0].text.strip(), "rut": d[1].text.strip(), "direccion": d[3].text.strip(), "comuna": d[4].text.strip()}
    except: return None

# --- 3. LÓGICA DE DOCUMENTOS (REDACTOR ORIGINAL) ---
def generar_word_robusto(dg, cr, ca):
    doc = Document()
    style = doc.styles['Normal']
    style.font.name, style.font.size = 'Cambria', Pt(12)
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
            li.add_run(f"Sanción de {c['san']}.")
    doc.add_paragraph("\nII. FUNDAMENTO ADULTO:").bold = True
    for a in ca:
        if a['rit']:
            pa = doc.add_paragraph()
            pa.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            pa.add_run(f"RIT {a['rit']} (RUC {a['ruc']}) de {a['juz']}: ").bold = True
            pa.add_run(f"Condenado a {a['det']}.")
    doc.add_paragraph("\nPOR TANTO, PIDO A US. acceder.").bold = True
    buf = io.BytesIO(); doc.save(buf); buf.seek(0)
    return buf

# --- INTERFAZ PRINCIPAL ---
if check_auth():
    st.set_page_config(page_title="Ignacio Badilla - Suite Jurídica", layout="wide")
    
    # Mantener contadores
    for k in ['ne', 'nr', 'na']:
        if k not in st.session_state: st.session_state[k] = 1

    st.title("⚖️ Legal Intelligence Suite")
    tabs = st.tabs(["📄 Generador de Extinciones", "🔍 Motor MIA (Investigación)", "📅 Calculadora de Plazos"])

    # --- PESTAÑA 1: TU GENERADOR ---
    with tabs[0]:
        st.subheader("Redactor de Escritos de Extinción")
        d_f = st.text_input("Defensor Titular", value="Ignacio Badilla Lara")
        a_d = st.text_input("Nombre del Adolescente")
        j_p = st.text_input("Juzgado de Garantía")
        
        st.write("---")
        st.markdown("### 1. Causas de Ejecución")
        e1, e2 = st.columns(2); (st.session_state.ne := st.session_state.ne + 1) if e1.button("➕ Ejecución") else None; (st.session_state.ne := max(1, st.session_state.ne - 1)) if e2.button("➖ Ejecución") else None
        le = [{"ruc": st.columns(2)[0].text_input(f"RUC E {i}", key=f"re{i}"), "rit": st.columns(2)[1].text_input(f"RIT E {i}", key=f"te{i}")} for i in range(st.session_state.ne)]

        st.markdown("### 2. Causas RPA")
        r1, r2 = st.columns(2); (st.session_state.nr := st.session_state.nr + 1) if r1.button("➕ RPA") else None; (st.session_state.nr := max(1, st.session_state.nr - 1)) if r2.button("➖ RPA") else None
        lr = []
        for j in range(st.session_state.nr):
            col1, col2, col3 = st.columns(3)
            lr.append({"ruc": col1.text_input(f"RUC RPA {j}", key=f"rr{j}"), "rit": col2.text_input(f"RIT RPA {j}", key=f"tr{j}"), "juz": col3.text_input(f"Juzgado {j}", key=f"jr{j}"), "san": st.text_area(f"Sanción {j}", key=f"sr{j}")})

        if st.button("🚀 GENERAR ESCRITO"):
            doc_final = generar_word_robusto({"def":d_f,"ado":a_d,"jp":j_p,"ej":le}, lr, [])
            st.download_button("📥 Descargar Word", doc_final, f"Extincion_{a_d}.docx")

    # --- PESTAÑA 2: MOTOR MIA MEJORADO ---
    with tabs[1]:
        st.subheader("🔍 Módulo de Extracción Directa")
        rut_q = st.text_input("Ingrese RUT para búsqueda automática (sin puntos)")
        
        if rut_q:
            rut_limpio = rut_q.replace(".","").split("-")[0]
            with st.spinner("MIA consultando bases de datos..."):
                datos = buscar_datos_civiles(rut_limpio)
                if datos:
                    st.success("✅ Datos encontrados en pantalla:")
                    c1, c2 = st.columns(2)
                    c1.text_input("Nombre Completo", value=datos['nombre'], key="mia_nom")
                    c1.text_input("RUT", value=datos['rut'], key="mia_rut")
                    c2.text_input("Dirección", value=datos['direccion'], key="mia_dir")
                    c2.text_input("Comuna", value=datos['comuna'], key="mia_com")
                else:
                    st.error("Acceso restringido por el sitio. Use los enlaces de respaldo:")
                    st.link_button("Ir al Rutificador", f"https://www.nombrerutyfirma.com/rut/{rut_limpio}")

    # --- PESTAÑA 3: CALCULADORA ---
    with tabs[2]:
        st.subheader("Cómputo de Plazos de Cautelares")
        tipo_c = st.selectbox("Medida / Recurso", ["Apelación Prisión Preventiva / IP (5 días)", "Recurso de Nulidad (10 días)", "Revisión Mensual Cautelar (30 días)"])
        fecha_n = st.date_input("Fecha de Resolución")
        plazo = 5 if "5" in tipo_c else 10 if "10" in tipo_c else 30
        st.error(f"📅 Vence el: {(fecha_n + datetime.timedelta(days=plazo)).strftime('%d/%m/%Y')}")

    st.markdown("---")
    st.caption("🚀 Desarrollado por Ignacio Badilla Lara | Administrador")
