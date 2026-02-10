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

# --- 2. LÓGICA DE ACTUALIZACIÓN DE CAUSAS (SIN WALRUS ERROR) ---
def aumentar_causa(tipo):
    st.session_state[tipo] += 1

def disminuir_causa(tipo):
    if st.session_state[tipo] > 1:
        st.session_state[tipo] -= 1

# --- 3. MOTOR MIA MEJORADO (DATOS EN PANTALLA) ---
def buscar_datos_civiles(rut_limpio):
    try:
        url = f"https://www.nombrerutyfirma.com/rut/{rut_limpio}"
        h = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        r = requests.get(url, headers=h, timeout=5)
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, 'html.parser')
            tabla = soup.find('table', {'class': 'table'})
            if tabla:
                d = tabla.find_all('tr')[1].find_all('td')
                return {
                    "nombre": d[0].text.strip(),
                    "rut": d[1].text.strip(),
                    "direccion": d[3].text.strip(),
                    "comuna": d[4].text.strip()
                }
    except: return None

# --- 4. GENERADOR DE DOCUMENTO ---
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
        if c.get('rit'):
            li = doc.add_paragraph(style='List Bullet')
            li.add_run(f"RIT {c['rit']} (RUC {c['ruc']}) de {c['juz']}: ").bold = True
            li.add_run(f"Sanción de {c['san']}.")
            
    doc.add_paragraph("\nII. FUNDAMENTO ADULTO:").bold = True
    for a in ca:
        if a.get('rit'):
            pa = doc.add_paragraph()
            pa.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            pa.add_run(f"RIT {a['rit']} (RUC {a['ruc']}) de {a['juz']}: ").bold = True
            pa.add_run(f"Condenado a {a['det']}.")
            
    doc.add_paragraph("\nPOR TANTO, PIDO A US. acceder.").bold = True
    buf = io.BytesIO(); doc.save(buf); buf.seek(0)
    return buf

# --- INTERFAZ ---
if check_auth():
    st.set_page_config(page_title="Ignacio Badilla - Suite Jurídica", layout="wide")
    
    if 'ne' not in st.session_state: st.session_state.ne = 1
    if 'nr' not in st.session_state: st.session_state.nr = 1
    if 'na' not in st.session_state: st.session_state.na = 1

    st.title("⚖️ Legal Intelligence Suite")
    tabs = st.tabs(["📄 Generador de Extinciones", "🔍 Motor MIA (Investigación)", "📅 Calculadora de Plazos"])

    # --- TAB 1: GENERADOR DE EXTINCIONES ---
    with tabs[0]:
        st.subheader("Redactor de Escritos")
        col_def, col_ado, col_juz = st.columns(3)
        d_f = col_def.text_input("Defensor Titular", value="Ignacio Badilla Lara")
        a_d = col_ado.text_input("Nombre del Adolescente")
        j_p = col_juz.text_input("Juzgado de Garantía")
        
        st.divider()
        st.markdown("### 1. Causas de Ejecución")
        ce1, ce2 = st.columns([1, 5])
        ce1.button("➕", key="add_e", on_click=aumentar_causa, args=('ne',))
        ce2.button("➖", key="rem_e", on_click=disminuir_causa, args=('ne',))
        le = []
        for i in range(st.session_state.ne):
            c_ruc, c_rit = st.columns(2)
            le.append({
                "ruc": c_ruc.text_input(f"RUC E {i+1}", key=f"re{i}"),
                "rit": c_rit.text_input(f"RIT E {i+1}", key=f"te{i}")
            })

        st.markdown("### 2. Causas RPA a Extinguir")
        cr1, cr2 = st.columns([1, 5])
        cr1.button("➕", key="add_r", on_click=aumentar_causa, args=('nr',))
        cr2.button("➖", key="rem_r", on_click=disminuir_causa, args=('nr',))
        lr = []
        for j in range(st.session_state.nr):
            c1, c2, c3 = st.columns(3)
            lr.append({
                "ruc": c1.text_input(f"RUC RPA {j+1}", key=f"rr{j}"),
                "rit": c2.text_input(f"RIT RPA {j+1}", key=f"tr{j}"),
                "juz": c3.text_input(f"Juzgado {j+1}", key=f"jr{j}"),
                "san": st.text_area(f"Sanción {j+1}", key=f"sr{j}", height=60)
            })

        if st.button("🚀 GENERAR ESCRITO ROBUSTO"):
            doc_final = generar_word_robusto({"def":d_f,"ado":a_d,"jp":j_p,"ej":le}, lr, [])
            st.download_button("📥 Descargar Word", doc_final, f"Extincion_{a_d}.docx")

    # --- TAB 2: MOTOR MIA (DATOS EN PANTALLA) ---
    with tabs[1]:
        st.subheader("🔍 Central de Investigación de Antecedentes")
        rut_q = st.text_input("Ingrese RUT para búsqueda (sin puntos ni guion)")
        
        if rut_q:
            with st.spinner("MIA extrayendo información..."):
                datos = buscar_datos_civiles(rut_q)
                if datos:
                    st.success("✅ Información detectada directamente:")
                    # Campos de salida automáticos para que sea fácil copiar
                    col_mia1, col_mia2 = st.columns(2)
                    st.session_state.temp_nom = col_mia1.text_input("Nombre Completo", value=datos['nombre'])
                    st.session_state.temp_rut = col_mia1.text_input("RUT", value=datos['rut'])
                    st.session_state.temp_dir = col_mia2.text_input("Dirección", value=datos['direccion'])
                    st.session_state.temp_com = col_mia2.text_input("Comuna", value=datos['comuna'])
                    
                    st.divider()
                    st.info("🔗 Enlaces Rápidos de Verificación:")
                    st.link_button("🌐 Ver en SERVEL", "https://consulta.servel.cl/")
                    st.link_button("🏛️ Ver en PJUD", "https://oficinajudicialvirtual.pjud.cl/")
                else:
                    st.warning("⚠️ No se pudo extraer el dato automáticamente. El sitio fuente podría estar bloqueando la IP del servidor. Intente manualmente abajo:")
                    st.link_button("Ir al Rutificador", f"https://www.nombrerutyfirma.com/rut/{rut_q}")

    # --- TAB 3: CALCULADORA DE PLAZOS ---
    with tabs[2]:
        st.subheader("Cómputo de Plazos Judiciales")
        tipo_c = st.selectbox("Resolución / Medida", [
            "Apelación Prisión Preventiva / IP (5 días)", 
            "Apelación Sentencia Definitiva (5 días)", 
            "Recurso de Nulidad (10 días)", 
            "Revisión Mensual Cautelar (30 días)"
        ])
        fecha_n = st.date_input("Fecha de Notificación")
        
        # Lógica de días
        dias_map = {"5": 5, "10": 10, "30": 30}
        dias = next((v for k, v in dias_map.items() if k in tipo_c), 0)
        
        vencimiento = fecha_n + datetime.timedelta(days=dias)
        st.error(f"🚨 El plazo fatal vence el: {vencimiento.strftime('%d/%m/%Y')}")

    st.markdown("---")
    st.caption(f"🚀 Desarrollado por Ignacio Badilla Lara | {ADMIN_EMAIL}")
