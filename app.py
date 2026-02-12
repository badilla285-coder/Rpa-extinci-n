import streamlit as st
from docx import Document
from docx.shared import Pt, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
import io
import re
from datetime import datetime, timedelta
import PyPDF2

# --- CONFIGURACIÓN Y LISTAS ---
TRIBUNALES_STGO_SM = [
    "1° Juzgado de Garantía de Santiago", "2° Juzgado de Garantía de Santiago",
    "3° Juzgado de Garantía de Santiago", "4° Juzgado de Garantía de Santiago",
    "5° Juzgado de Garantía de Santiago", "6° Juzgado de Garantía de Santiago",
    "7° Juzgado de Garantía de Santiago", "8° Juzgado de Garantía de Santiago",
    "9° Juzgado de Garantía de Santiago", "10° Juzgado de Garantía de Santiago",
    "11° Juzgado de Garantía de Santiago", "12° Juzgado de Garantía de Santiago",
    "13° Juzgado de Garantía de Santiago", "14° Juzgado de Garantía de Santiago",
    "15° Juzgado de Garantía de Santiago", "16° Juzgado de Garantía de Santiago",
    "Juzgado de Garantía de San Bernardo", "Juzgado de Garantía de Puente Alto",
    "Juzgado de Garantía de Talagante", "Juzgado de Garantía de Melipilla",
    "Juzgado de Garantía de Curacaví", "Juzgado de Garantía de Colina"
]

# --- SEGURIDAD ---
def check_password():
    if "password_correct" not in st.session_state:
        st.title("🔐 Acceso Sistema Judicial")
        email = st.text_input("Correo electrónico")
        pw = st.text_input("Contraseña", type="password")
        if st.button("Ingresar"):
            if email == "badilla285@gmail.com" and pw == "RPA2026":
                st.session_state["password_correct"] = True
                st.session_state["legal_coins"] = 0
                st.rerun()
            else: st.error("Credenciales incorrectas")
        return False
    return True

class GeneradorOficial:
    def __init__(self, defensor, adolescente):
        self.fuente = "Cambria"
        self.tamano = 12
        self.defensor = defensor
        self.adolescente = adolescente

    def limpiar_tribunal(self, nombre):
        if not nombre: return ""
        # Evita el error de "Juzgado de Juzgado de..."
        nombre = nombre.upper()
        if nombre.startswith("JUZGADO DE"): return nombre
        return f"JUZGADO DE GARANTÍA DE {nombre}"

    def generar_docx(self, data):
        doc = Document()
        for s in doc.sections:
            s.left_margin, s.right_margin = Inches(1.2), Inches(1.0)

        def add_p(texto_base, bold_all=False, indent=True):
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            p.paragraph_format.line_spacing_rule = WD_LINE_SPACING.ONE_POINT_FIVE
            if indent: p.paragraph_format.first_line_indent = Inches(0.5)
            
            # Corrección punto 8: Regex preciso para evitar negritas erróneas en "mérito"
            def_esc = re.escape(self.defensor.upper())
            ado_esc = re.escape(self.adolescente.upper())
            patron = f"(RIT|RUC|{def_esc}|{ado_esc}|JUZGADO DE [A-ZÁÉÍÓÚÑ\s]+|\d+-\d{{4}}|\d{{7,10}}-[\dkK])"
            
            partes = re.split(patron, texto_base, flags=re.IGNORECASE)
            for fragmento in partes:
                if not fragmento: continue
                run = p.add_run(fragmento)
                run.font.name, run.font.size = self.fuente, Pt(self.tamano)
                if bold_all or (re.match(patron, fragmento, re.IGNORECASE) and fragmento.lower() != "mérito"):
                    run.bold = True
            return p

        # 1. SUMA
        suma = doc.add_paragraph()
        r_suma = suma.add_run("EN LO PRINCIPAL: SOLICITA EXTINCIÓN;\nOTROSÍ: ACOMPAÑA DOCUMENTO.")
        r_suma.bold = True
        r_suma.font.name, r_suma.font.size = self.fuente, Pt(self.tamano)

        # 2. TRIBUNAL (Corrección punto 7)
        add_p(f"\n{self.limpiar_tribunal(data['juzgado_ejecucion'])}", bold_all=True, indent=False)
        
        # 3. COMPARECENCIA
        # Punto 3: Unir múltiples causas de ejecución en el encabezado
        causas_str = ", ".join([f"RIT: {c['rit']} (RUC: {c['ruc']})" for c in data['causas_ej_principales'] if c['rit']])
        comp = (f"\n{self.defensor.upper()}, Abogada, Defensora Penal Pública, en representación de "
                f"{self.adolescente.upper()}, en causas de ejecución {causas_str}, a S.S., respetuosamente digo:")
        add_p(comp, indent=True)

        # 4. CUERPO
        add_p("\nQue, vengo en solicitar que declare la extinción de las sanciones de la Ley RPA, en virtud del artículo 25 ter y 25 quinquies de la Ley 20.084.")
        
        for i, c in enumerate(data['causas_rpa'], 1):
            add_p(f"{i}. RIT: {c['rit']}, RUC: {c['ruc']}: Condenado por el {self.limpiar_tribunal(c['juzgado'])} a la pena de {c['sancion']}.")

        add_p("\nEl fundamento para solicitar la discusión radica en una condena de mayor gravedad como adulto:")
        for i, c in enumerate(data['causas_adulto'], 1):
            idx = i + len(data['causas_rpa'])
            add_p(f"{idx}. RIT: {c['rit']}, RUC: {c['ruc']}: Condenado por el {self.limpiar_tribunal(c['juzgado'])}, con fecha {c['fecha']}, a la pena de {c['pena']}.")

        add_p("\nPOR TANTO,", indent=False)
        add_p("En mérito de lo expuesto, SOLICITO A S.S. acceder a lo solicitado extinguiendo de pleno derecho la sanción antes referida.")

        add_p("\nOTROSÍ: Acompaña sentencia de adulto.", bold_all=True, indent=False)
        add_p("POR TANTO, SOLICITO A S.S. se tenga por acompañada.", indent=False)

        buf = io.BytesIO()
        doc.save(buf)
        buf.seek(0)
        return buf

# --- INTERFAZ ---
if check_password():
    st.set_page_config(page_title="Generador de Escritos", layout="wide")
    
    # Inicialización de estados
    if "rpa_list" not in st.session_state: st.session_state.rpa_list = []
    if "adulto_list" not in st.session_state: st.session_state.adulto_list = []
    if "ej_list" not in st.session_state: st.session_state.ej_list = [{"rit":"", "ruc":""}]

    # SIDEBAR
    with st.sidebar:
        # Punto 9: Reloj digital elegante
        st.markdown(f"#### 🕒 {datetime.now().strftime('%H:%M:%S')}")
        st.header("🎮 Perfil Judicial")
        st.info(f"LegalCoins: {st.session_state.legal_coins} 🪙")
        if st.session_state.legal_coins >= 50:
            st.success("🔓 ¡Nivel Desbloqueado: Defensor Senior!")
        
        st.markdown("---")
        st.header("⏳ Calculadora")
        tipo_res = st.selectbox("Tipo", ["Amparo", "Apelación (5d)", "Nulidad (10d)"])
        fecha_not = st.date_input("Notificación")
        if st.button("Ver Vencimiento"):
            d = 1 if "Amparo" in tipo_res else 5 if "5d" in tipo_res else 10
            st.error(f"Vence: {(fecha_not + timedelta(days=d)).strftime('%d-%m-%Y')}")
        
        st.markdown("---")
        # Punto 6: Unir PDFs
        st.header("📂 Unir Documentos")
        files = st.file_uploader("Adjuntar archivos a unir", accept_multiple_files=True, type="pdf")
        if st.button("Unir PDFs"):
            if files:
                merger = PyPDF2.PdfMerger()
                for f in files: merger.append(f)
                out = io.BytesIO()
                merger.write(out)
                st.download_button("⬇️ Descargar PDF Unido", out.getvalue(), "Causa_Unida.pdf")

    st.title("⚖️ Generador de Escritos IBL")

    # 1. INDIVIDUALIZACIÓN
    st.header("1. Individualización")
    c1, c2, c3 = st.columns(3)
    def_nom = c1.text_input("Defensor/a", "IGNACIO BADILLA LARA")
    imp_nom = c2.text_input("Nombre Adolescente")
    
    # Punto 2 y 7: Selector de Juzgado
    juz_ej = c3.selectbox("Juzgado Ejecución", ["Escribir manual..."] + TRIBUNALES_STGO_SM)
    if juz_ej == "Escribir manual...":
        juz_ej = c3.text_input("Indique Juzgado manualmente", key="juz_manual")

    # Punto 3: Multiples causas de ejecución
    st.markdown("#### Causas que conoce el Tribunal de Ejecución")
    for i, item in enumerate(st.session_state.ej_list):
        col_r1, col_r2, col_r3 = st.columns([4, 4, 1])
        item['rit'] = col_r1.text_input(f"RIT Ejecución {i+1}", item['rit'], key=f"ej_rit_{i}")
        item['ruc'] = col_r2.text_input(f"RUC Ejecución {i+1}", item['ruc'], key=f"ej_ruc_{i}")
        if col_r3.button("❌", key=f"del_ej_{i}"):
            st.session_state.ej_list.pop(i); st.rerun()
    if st.button("➕ Agregar Causa de Ejecución"): st.session_state.ej_list.append({"rit":"", "ruc":""}); st.rerun()

    # 2. CAUSAS RPA
    st.header("2. Causas RPA")
    for i, item in enumerate(st.session_state.rpa_list):
        cols = st.columns([2, 2, 3, 3, 0.5])
        item['rit'] = cols[0].text_input("RIT", item['rit'], key=f"r_rit_{i}")
        item['ruc'] = cols[1].text_input("RUC", item['ruc'], key=f"r_ruc_{i}")
        item['juzgado'] = cols[2].selectbox("Juzgado", TRIBUNALES_STGO_SM, key=f"r_juz_{i}")
        item['sancion'] = cols[3].text_input("Sanción", item['sancion'], key=f"r_san_{i}")
        if cols[4].button("❌", key=f"del_rpa_{i}"): 
            st.session_state.rpa_list.pop(i); st.rerun()
    if st.button("➕ Agregar Causa RPA"): st.session_state.rpa_list.append({"rit":"", "ruc":"", "juzgado":"", "sancion":""}); st.rerun()

    # 3. CONDENAS ADULTO
    st.header("3. Condenas Adulto")
    for i, item in enumerate(st.session_state.adulto_list):
        cols = st.columns([2, 2, 3, 2, 2, 0.5])
        item['rit'] = cols[0].text_input("RIT Ad", item['rit'], key=f"a_rit_{i}")
        item['ruc'] = cols[1].text_input("RUC Ad", item['ruc'], key=f"a_ruc_{i}")
        item['juzgado'] = cols[2].selectbox("Juzgado Ad", TRIBUNALES_STGO_SM, key=f"a_juz_{i}")
        item['pena'] = cols[3].text_input("Pena", item['pena'], key=f"a_pen_{i}")
        item['fecha'] = cols[4].text_input("Fecha", item['fecha'], key=f"a_fec_{i}")
        if cols[5].button("❌", key=f"del_ad_{i}"): 
            st.session_state.adulto_list.pop(i); st.rerun()
    if st.button("➕ Agregar Condena Adulto"): st.session_state.adulto_list.append({"rit":"", "ruc":"", "juzgado":"", "pena":"", "fecha":""}); st.rerun()

    # 4. GENERACIÓN
    if st.button("🚀 GENERAR ESCRITO ROBUSTO", use_container_width=True):
        if not imp_nom or not st.session_state.ej_list[0]['rit']:
            st.error("⚠️ Faltan datos críticos.")
        else:
            # Punto 5: Sumar LegalCoins al generar
            st.session_state.legal_coins += 10
            datos = {
                "defensor": def_nom, "adolescente": imp_nom, "juzgado_ejecucion": juz_ej, 
                "causas_ej_principales": st.session_state.ej_list,
                "causas_rpa": st.session_state.rpa_list, "causas_adulto": st.session_state.adulto_list
            }
            gen = GeneradorOficial(def_nom, imp_nom)
            st.download_button("⬇️ Descargar Escrito Cambria 12", gen.generar_docx(datos), f"Extincion_{imp_nom}.docx", use_container_width=True)
            st.balloons()
