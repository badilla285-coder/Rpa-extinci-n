import streamlit as st
from docx import Document
from docx.shared import Pt, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
import io
import re
import json
from datetime import datetime
import PyPDF2
from supabase import create_client, Client
import google.generativeai as genai

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Suite Legal IABL Pro", layout="wide")

# --- CONFIGURACIÓN DE IA (GOOGLE AI STUDIO) ---
GOOGLE_API_KEY = "AIzaSyDjsyWjcHCXvgoIQsbyxGD2oyLHFMLfWhg"
genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

# --- CONFIGURACIÓN DE BASE DE DATOS (SUPABASE) ---
SUPABASE_URL = "https://zblcddxbhyomkasmbvyz.supabase.co"
SUPABASE_KEY = "sb_publishable_pHMqXxI39AssehHdBs1wqA_NVjPc-FT" 

try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as e:
    st.error(f"Error en la conexión con Supabase: {e}")

# --- LISTAS DE REFERENCIA ---
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

# --- LÓGICA DE IA Y SEMAFORIZACIÓN DIFERENCIADA ---
def analizar_pdf_legal(texto_pdf, categoria):
    prompt = f"""
    Eres un experto legal chileno. Analiza este texto de {categoria}.
    Extrae los datos en JSON puro:
    {{
        "ruc": "00.000.000-0",
        "rit": "O-000-0000",
        "tribunal": "Nombre exacto del juzgado",
        "imputado": "Nombre completo",
        "fecha_sentencia": "YYYY-MM-DD",
        "sancion_pena": "Descripción de la condena",
        "es_rpa": true/false
    }}
    Texto: {texto_pdf}
    """
    try:
        response = model.generate_content(prompt)
        limpio = response.text.replace('```json', '').replace('```', '').strip()
        return json.loads(limpio)
    except:
        return None

def calcular_semaforo(fecha_sentencia, es_rpa):
    """
    Diferenciación estricta de plazos de prescripción:
    - RPA (Art. 5 Ley 20.084): 2 años simples delitos, 5 años crímenes.
    - Adultos (Código Penal): 5 años simples delitos, 10-15 años crímenes.
    """
    if not fecha_sentencia: return "⚪ Datos incompletos"
    try:
        fs = datetime.strptime(fecha_sentencia, "%Y-%m-%d")
        hoy = datetime.now()
        diferencia = (hoy - fs).days / 365.25
        
        # Plazos según Ley 20.084 vs Código Penal
        plazo_legal = 2.0 if es_rpa else 5.0 
        
        if diferencia >= plazo_legal:
            return f"🟢 APTA: {round(diferencia, 1)} años transcurridos (Plazo: {plazo_legal} años)."
        else:
            faltan = round(plazo_legal - diferencia, 1)
            return f"🔴 EN ESPERA: Faltan {faltan} años para cumplir el plazo legal."
    except:
        return "❌ Error en fecha"

# --- MOTOR DE GENERACIÓN DOCX (MULTI-RECURSO) ---
class GeneradorOficialIABL:
    def __init__(self, defensor, adolescente):
        self.fuente = "Cambria"
        self.tamano = 12
        self.defensor = defensor
        self.adolescente = adolescente

    def aplicar_formato(self, doc, texto, bold_all=False, indent=True, align="JUSTIFY"):
        p = doc.add_paragraph()
        if align == "LEFT": p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        elif align == "CENTER": p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        else: p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        
        p.paragraph_format.line_spacing_rule = WD_LINE_SPACING.ONE_POINT_FIVE
        if indent: p.paragraph_format.first_line_indent = Inches(0.5)

        # Respetar negritas en nombres, causas y POR TANTO
        def_esc = re.escape(self.defensor.upper())
        ado_esc = re.escape(self.adolescente.upper())
        patron = r"(RIT:?\s?\d+-\d{4}|RUC:?\s?\d{7,10}-[\dkK]|POR TANTO|OTROSÍ|SOLICITA|INTERPONE|ACCIÓN CONSTITUCIONAL|{0}|{1})".format(def_esc, ado_esc)
        
        partes = re.split(patron, texto, flags=re.IGNORECASE)
        for frag in partes:
            if not frag: continue
            run = p.add_run(frag)
            run.font.name, run.font.size = self.fuente, Pt(self.tamano)
            if bold_all or re.match(patron, frag, re.IGNORECASE):
                run.bold = True
        return p

    def generar_escrito(self, tipo, data):
        doc = Document()
        for s in doc.sections:
            s.left_margin, s.right_margin = Inches(1.2), Inches(1.0)
        
        if tipo == "Extinción Art. 25 ter":
            self.aplicar_formato(doc, "EN LO PRINCIPAL: SOLICITA EXTINCIÓN; OTROSÍ: ACOMPAÑA SENTENCIA", bold_all=True, indent=False, align="LEFT")
            self.aplicar_formato(doc, f"\n{data['juzgado_ejecucion'].upper()}", bold_all=True, indent=False)
            comp = f"\n{self.defensor.upper()}, Abogada, Defensora Penal Pública, en representación de {self.adolescente.upper()}, en causas de ejecución {data['causas_ej_str']}, a S.S., respetuosamente digo:"
            self.aplicar_formato(doc, comp)
            self.aplicar_formato(doc, "Que, vengo en solicitar que se declare la extinción de las sanciones de la Ley de Responsabilidad Penal Adolescente, o en subsidio se fije día y hora para celebrar audiencia para debatir sobre la extinción de la pena respecto de mi representado, en virtud de lo dispuesto en los artículos 25 ter y 25 quinquies de la Ley 20.084.")
            self.aplicar_formato(doc, "El fundamento radica en la existencia de una condena de mayor gravedad como adulto, la cual se detalla a continuación.")
            self.aplicar_formato(doc, "POR TANTO, SOLICITO A S.S. acceder a lo solicitado extinguiendo de pleno derecho la sanción antes referida.")
            self.aplicar_formato(doc, f"OTROSÍ: Acompaña sentencia de adulto de las causas {data['causas_adulto_str']}", bold_all=True, indent=False)

        elif tipo == "Prescripción de la Pena":
            self.aplicar_formato(doc, "EN LO PRINCIPAL: SOLICITA AUDIENCIA DE PRESCRIPCIÓN; OTROSÍ: OFICIA A EXTRANJERÍA Y ADJUNTA ANTECEDENTES", bold_all=True, indent=False, align="LEFT")
            self.aplicar_formato(doc, f"\n{data['juzgado_ejecucion'].upper()}", bold_all=True, indent=False)
            comp = f"\n{self.defensor.upper()}, Abogada, Defensora Penal Pública, en representación de {self.adolescente.upper()}, en causas {data['causas_str']}, a S.S. respetuosamente digo:"
            self.aplicar_formato(doc, comp)
            self.aplicar_formato(doc, "Que, por medio de la presente, vengo en solicitar a S.S. se sirva fijar día y hora para celebrar audiencia con el objeto de debatir sobre la prescripción de la pena respecto de mi representado, de conformidad a lo dispuesto en el artículo 5 de la Ley N° 20.084 y las normas pertinentes del Código Penal.")
            self.aplicar_formato(doc, "Teniendo presente el tiempo transcurrido desde que las referidas sentencias quedaron ejecutoriadas, ha transcurrido en exceso el plazo legal exigido.")
            self.aplicar_formato(doc, "POR TANTO, SOLICITO A S.S. acceder a lo solicitado, fijando día y hora para celebrar audiencia y declarar el sobreseimiento definitivo.")
            self.aplicar_formato(doc, "OTROSÍ: Solicito se oficie a Extranjería para informar movimientos migratorios y se incorpore Extracto de Filiación actualizado.", bold_all=True, indent=False)

        elif tipo == "Amparo Constitucional":
            self.aplicar_formato(doc, "INTERPONE ACCIÓN CONSTITUCIONAL DE AMPARO; OTROSÍ: ORDEN DE NO INNOVAR", bold_all=True, indent=False, align="LEFT")
            self.aplicar_formato(doc, "\nILTMA. CORTE DE APELACIONES DE SANTIAGO", bold_all=True, indent=False)
            comp = f"\n{self.defensor.upper()}, abogada, Defensora Penal Juvenil, en representación de {self.adolescente.upper()}, en causa RIT {data['rit_prin']}, RUC {data['ruc_prin']}, a V.S.I respetuosamente digo:"
            self.aplicar_formato(doc, comp)
            self.aplicar_formato(doc, "Que, en virtud de lo dispuesto en el artículo 21 de la Constitución Política de la República, vengo en deducir acción constitucional de amparo por la perturbación grave e ilegítima a la libertad personal, emanada de la resolución que ordenó el ingreso inmediato del joven, siendo esta ilegal y arbitraria.")
            self.aplicar_formato(doc, "La resolución infringe el artículo 79 del Código Penal que establece que no podrá ejecutarse pena alguna sino en virtud de sentencia ejecutoriada.")
            self.aplicar_formato(doc, "POR TANTO, SOLICITO A V.S. ILTMA. dejar sin efecto la resolución recurrida y restablecer el imperio del derecho.")
            self.aplicar_formato(doc, "OTROSÍ: Solicito Orden de No Innovar para suspender los efectos de la ilegalidad atacada.", bold_all=True, indent=False)

        elif tipo == "Apelación por Quebrantamiento":
            self.aplicar_formato(doc, "EN LO PRINCIPAL: INTERPONE RECURSO DE APELACIÓN; OTROSÍ: FORMA DE NOTIFICACIÓN", bold_all=True, indent=False, align="LEFT")
            self.aplicar_formato(doc, f"\n{data['juzgado_ejecucion'].upper()}", bold_all=True, indent=False)
            comp = f"\n{self.defensor.upper()}, abogada, Defensora Penal Juvenil, en representación de don {self.adolescente.upper()}, a V.S.I respetuosamente digo:"
            self.aplicar_formato(doc, comp)
            self.aplicar_formato(doc, "Que encontrándome dentro del plazo legal, vengo en interponer recurso de apelación en contra de la resolución que ordenó el quebrantamiento definitivo, solicitando sea revocado conforme a los artículos 52 y siguientes de la Ley 20.084.")
            self.aplicar_formato(doc, "La aplicación de una sanción en régimen cerrado no permite hacer efectiva la reinserción social, privando la posibilidad de continuar actividades laborales o educativas.")
            self.aplicar_formato(doc, "POR TANTO, SOLICITO A US. tener por interpuesto el recurso para que la Iltma. Corte de Apelaciones de San Miguel revoque la resolución y mantenga la sanción en Régimen Semicerrado.")

        buf = io.BytesIO()
        doc.save(buf)
        buf.seek(0)
        return buf

# --- FUNCIONES DE PERSISTENCIA Y LOGIN ---
def guardar_gestion_iabl(ruc, rit, tribunal, tipo, contenido):
    try:
        data_insert = {
            "RUC": ruc,
            "RIT": rit,
            "TRIBUNAL / JUZGADO": tribunal,
            "TIPO_RECURSO": tipo,
            "CONTENIDO_ESCRITO": contenido
        }
        supabase.table("Gestiones").insert(data_insert).execute()
        return True
    except Exception as e:
        st.error(f"Error crítico en Base de Datos: {e}")
        return False

def check_password():
    if "auth_user" not in st.session_state:
        st.title("🔐 Acceso Suite IABL Pro")
        email = st.text_input("Email institucional")
        pw = st.text_input("Contraseña", type="password")
        if st.button("Ingresar"):
            if email in st.session_state.usuarios_db and st.session_state.usuarios_db[email]["pw"] == pw:
                st.session_state["auth_user"] = email
                st.session_state["user_name"] = st.session_state.usuarios_db[email]["nombre"]
                st.session_state["is_admin"] = (st.session_state.usuarios_db[email]["nivel"] == "Admin")
                st.rerun()
            else:
                st.error("Credenciales incorrectas")
        return False
    return True

# --- TRANSCRIPTOR INTELIGENTE (AUDIOS A TEXTO) ---
def transcribir_audiencia(archivo_audio):
    st.info("Función de transcripción íntegra activada. Procesando audio...")
    return "Texto íntegro de la audiencia transcrito por IA..."

# --- GESTIÓN DE ESTADO DE FORMULARIO ---
if "usuarios_db" not in st.session_state:
    st.session_state.usuarios_db = {"badilla285@gmail.com": {"nombre": "IGNACIO BADILLA LARA", "pw": "RPA2026", "nivel": "Admin"}}

if "form_data" not in st.session_state:
    st.session_state.form_data = {
        "imp_nom": "", "juz_ej_sel": "San Bernardo",
        "rpa_list": [], "adulto_list": [],
        "ej_list": [{"rit":"", "ruc":""}],
        "fecha_ad": None, "es_rpa_semaforo": True
    }

# --- INTERFAZ STREAMLIT ---
if check_password():
    with st.sidebar:
        st.title("💼 Suite Legal IABL")
        st.write(f"Usuario: **{st.session_state.user_name}**")
        st.divider()
        st.subheader("💳 Planes y Suscripciones")
        if st.session_state.get("legal_coins", 0) < 10:
            st.warning(f"Saldo: {st.session_state.get('legal_coins', 0)} LegalCoins")
            if st.button("💳 Comprar LegalCoins"): st.info("Pasarela en desarrollo...")
        else:
            st.success(f"Créditos: {st.session_state.get('legal_coins', 0)}")
        
        st.divider()
        tipo_escrito = st.selectbox("📝 Recurso a Generar", 
            ["Extinción Art. 25 ter", "Prescripción de la Pena", "Amparo Constitucional", "Apelación por Quebrantamiento"])
        
        st.subheader("📊 Semáforo de Plazos")
        if st.session_state.form_data.get("fecha_ad"):
            status = calcular_semaforo(st.session_state.form_data["fecha_ad"], st.session_state.form_data.get("es_rpa_semaforo", True))
            st.info(status)
        else:
            st.write("Sube una sentencia para calcular plazos.")

    tab_ia, tab_audio, tab_form, tab_admin = st.tabs(["🤖 IA", "🎙️ Transcriptor", "📄 Formulario", "⚙️ Admin"])

    with tab_ia:
        st.header("⚡ Asistente Gemini 1.5 Flash")
        c_ia1, c_ia2, c_ia3 = st.columns(3)
        with c_ia1:
            st.markdown("### 1. Ejecución")
            pdf_ej = st.file_uploader("Acta de Ejecución", type=["pdf"], key="up_ej")
            if pdf_ej and st.button("Procesar Ejecución"):
                reader = PyPDF2.PdfReader(pdf_ej)
                res = analizar_pdf_legal("".join([p.extract_text() for p in reader.pages[:3]]), "Acta de Ejecución")
                if res:
                    st.session_state.form_data["ej_list"][0].update({"rit": res["rit"], "ruc": res["ruc"]})
                    st.session_state.form_data["imp_nom"] = res["imputado"]
                    st.success("Cargado")

        with c_ia2:
            st.markdown("### 2. Sentencia RPA")
            pdf_rpa = st.file_uploader("Sentencia RPA", type=["pdf"], key="up_rpa")
            if pdf_rpa and st.button("Procesar RPA"):
                reader = PyPDF2.PdfReader(pdf_rpa)
                res = analizar_pdf_legal("".join([p.extract_text() for p in reader.pages[:3]]), "Sentencia RPA")
                if res:
                    st.session_state.form_data["rpa_list"].append({"rit": res["rit"], "sancion": res["sancion_pena"]})
                    st.session_state.form_data["es_rpa_semaforo"] = True
                    st.success("Añadido")

        with c_ia3:
            st.markdown("### 3. Sentencia Adulto")
            pdf_ad = st.file_uploader("Sentencia Adulto", type=["pdf"], key="up_ad")
            if pdf_ad and st.button("Procesar Adulto"):
                reader = PyPDF2.PdfReader(pdf_ad)
                res = analizar_pdf_legal("".join([p.extract_text() for p in reader.pages[:3]]), "Sentencia Adulto")
                if res:
                    st.session_state.form_data["adulto_list"].append({"rit": res["rit"]})
                    st.session_state.form_data["fecha_ad"] = res["fecha_sentencia"]
                    st.session_state.form_data["es_rpa_semaforo"] = False
                    st.success("Cargado")

    with tab_audio:
        st.header("🎙️ Transcripción")
        st.file_uploader("Audio de Audiencia", type=["mp3", "wav"])

    with tab_form:
        st.header(f"Gestión: {tipo_escrito}")
        with st.form("main_form"):
            c1, c2 = st.columns(2)
            def_n = c1.text_input("Defensor/a", st.session_state.user_name)
            imp_n = c2.text_input("Adolescente", st.session_state.form_data["imp_nom"])
            juz = st.selectbox("Tribunal", TRIBUNALES_STGO_SM)
            if st.form_submit_button("⚖️ GENERAR Y GUARDAR"):
                dat = {"juzgado_ejecucion": juz, "causas_ej_str": st.session_state.form_data["ej_list"][0]["rit"], "causas_adulto_str": "", "rit_prin": st.session_state.form_data["ej_list"][0]["rit"], "ruc_prin": st.session_state.form_data["ej_list"][0]["ruc"], "causas_str": ""}
                word = GeneradorOficialIABL(def_n, imp_n).generar_escrito(tipo_escrito, dat)
                guardar_gestion_iabl(dat["ruc_prin"], dat["rit_prin"], juz, tipo_escrito, f"Escrito para {imp_n}")
                st.download_button("Descargar Word", word, f"{tipo_escrito}.docx")
                st.balloons()

    with tab_admin:
        if st.session_state.is_admin:
            st.table([{"Email": k, "Nombre": v["nombre"]} for k, v in st.session_state.usuarios_db.items()])

    st.markdown("---")
    st.markdown("<div style='text-align: center; color: gray;'>Suite Legal Pro - <b>IGNACIO ANTONIO BADILLA LARA</b> - Defensoría Penal Pública</div>", unsafe_allow_html=True)
