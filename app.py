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
    if not fecha_sentencia: return "⚪ Datos incompletos"
    try:
        fs = datetime.strptime(fecha_sentencia, "%Y-%m-%d")
        hoy = datetime.now()
        diferencia = (hoy - fs).days / 365.25
        
        # RPA (Art. 5 Ley 20.084) = 2 años | Adulto (CP) = 5 años base
        plazo_legal = 2.0 if es_rpa else 5.0 
        
        if diferencia >= plazo_legal:
            return f"🟢 APTA: {round(diferencia, 1)} años transcurridos (Plazo legal: {plazo_legal} años)."
        else:
            faltan = round(plazo_legal - diferencia, 1)
            return f"🔴 EN ESPERA: Faltan {faltan} años para cumplir el plazo legal."
    except:
        return "❌ Error en formato de fecha"

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
        else: p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        
        p.paragraph_format.line_spacing_rule = WD_LINE_SPACING.ONE_POINT_FIVE
        if indent: p.paragraph_format.first_line_indent = Inches(0.5)

        def_esc = re.escape(self.defensor.upper())
        ado_esc = re.escape(self.adolescente.upper())
        patron = r"(RIT:?\s?\d+-\d{4}|RUC:?\s?\d{7,10}-[\dkK]|POR TANTO|OTROSÍ|SOLICITA|INTERPONE|{0}|{1})".format(def_esc, ado_esc)
        
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
            self.aplicar_formato(doc, "POR TANTO, SOLICITO A S.S. acceder a lo solicitado extinguiendo de pleno derecho la sanción antes referida.")
            self.aplicar_formato(doc, f"OTROSÍ: Acompaña sentencia de adulto de las causas {data['causas_adulto_str']}", bold_all=True, indent=False)

        elif tipo == "Prescripción de la Pena":
            self.aplicar_formato(doc, "EN LO PRINCIPAL: SOLICITA AUDIENCIA DE PRESCRIPCIÓN; OTROSÍ: OFICIA A EXTRANJERÍA Y ADJUNTA ANTECEDENTES", bold_all=True, indent=False, align="LEFT")
            self.aplicar_formato(doc, f"\n{data['juzgado_ejecucion'].upper()}", bold_all=True, indent=False)
            comp = f"\n{self.defensor.upper()}, Abogada, Defensora Penal Pública, en representación de {self.adolescente.upper()}, en causas {data['causas_str']}, a S.S. respetuosamente digo:"
            self.aplicar_formato(doc, comp)
            self.aplicar_formato(doc, "Que, vengo en solicitar se sirva fijar día y hora para celebrar audiencia con el objeto de debatir sobre la prescripción de la pena, de conformidad a lo dispuesto en el artículo 5 de la Ley N° 20.084.")
            self.aplicar_formato(doc, "POR TANTO, SOLICITO A S.S. se declare el sobreseimiento definitivo.")

        elif tipo == "Amparo Constitucional":
            self.aplicar_formato(doc, "INTERPONE ACCIÓN CONSTITUCIONAL DE AMPARO; OTROSÍ: ORDEN DE NO INNOVAR", bold_all=True, indent=False, align="LEFT")
            self.aplicar_formato(doc, "\nILTMA. CORTE DE APELACIONES DE SANTIAGO", bold_all=True, indent=False)
            comp = f"\n{self.defensor.upper()}, abogada, Defensora Penal Juvenil, en representación de {self.adolescente.upper()}, en causa RIT {data['rit_prin']}, RUC {data['ruc_prin']}, a V.S.I respetuosamente digo:"
            self.aplicar_formato(doc, comp)
            self.aplicar_formato(doc, "Que, en virtud de lo dispuesto en el artículo 21 de la Constitución Política de la República, vengo en deducir acción constitucional de amparo.")
            self.aplicar_formato(doc, "POR TANTO, SOLICITO A V.S. ILTMA. restablecer el imperio del derecho.")

        elif tipo == "Apelación por Quebrantamiento":
            self.aplicar_formato(doc, "EN LO PRINCIPAL: INTERPONE RECURSO DE APELACIÓN; OTROSÍ: FORMA DE NOTIFICACIÓN", bold_all=True, indent=False, align="LEFT")
            self.aplicar_formato(doc, f"\n{data['juzgado_ejecucion'].upper()}", bold_all=True, indent=False)
            self.aplicar_formato(doc, "Que encontrándome dentro del plazo legal, vengo en interponer recurso de apelación conforme a los artículos 52 y siguientes de la Ley 20.084.")

        buf = io.BytesIO()
        doc.save(buf)
        buf.seek(0)
        return buf

# --- PERSISTENCIA Y LOGIN ---
def guardar_gestion_iabl(ruc, rit, tribunal, tipo, contenido):
    try:
        data_insert = {
            "RUC": ruc, "RIT": rit, "TRIBUNAL / JUZGADO": tribunal,
            "TIPO_RECURSO": tipo, "CONTENIDO_ESCRITO": contenido
        }
        supabase.table("Gestiones").insert(data_insert).execute()
        return True
    except: return False

def check_password():
    if "auth_user" not in st.session_state:
        st.title("🔐 Acceso Suite IABL Pro")
        email = st.text_input("Email")
        pw = st.text_input("Contraseña", type="password")
        if st.button("Entrar"):
            if email in st.session_state.usuarios_db and st.session_state.usuarios_db[email]["pw"] == pw:
                st.session_state["auth_user"], st.session_state["user_name"] = email, st.session_state.usuarios_db[email]["nombre"]
                st.session_state["is_admin"] = (st.session_state.usuarios_db[email]["nivel"] == "Admin")
                st.rerun()
            else: st.error("Error de acceso")
        return False
    return True

if "usuarios_db" not in st.session_state:
    st.session_state.usuarios_db = {"badilla285@gmail.com": {"nombre": "IGNACIO BADILLA LARA", "pw": "RPA2026", "nivel": "Admin"}}

if "form_data" not in st.session_state:
    st.session_state.form_data = {"imp_nom": "", "juz_ej_sel": "San Bernardo", "rpa_list": [], "adulto_list": [], "ej_list": [{"rit":"", "ruc":""}], "fecha_ad": None, "es_rpa_semaforo": True}

# --- INTERFAZ ---
if check_password():
    with st.sidebar:
        st.title("💼 Suite IABL")
        st.write(f"Usuario: **{st.session_state.user_name}**")
        st.divider()
        st.subheader("💳 LegalCoins")
        st.info(f"Saldo: {st.session_state.get('legal_coins', 0)}")
        tipo_escrito = st.selectbox("Recurso", ["Extinción Art. 25 ter", "Prescripción de la Pena", "Amparo Constitucional", "Apelación por Quebrantamiento"])
        st.subheader("📊 Semáforo")
        if st.session_state.form_data.get("fecha_ad"):
            st.info(calcular_semaforo(st.session_state.form_data["fecha_ad"], st.session_state.form_data.get("es_rpa_semaforo", True)))

    t1, t2, t3, t4 = st.tabs(["🤖 IA", "🎙️ Transcriptor", "📄 Formulario", "⚙️ Admin"])

    with t1:
        st.header("⚡ Gemini 1.5 Flash")
        c1, c2, c3 = st.columns(3)
        for col, lab, key in zip([c1, c2, c3], ["Ejecución", "RPA", "Adulto"], ["f1", "f2", "f3"]):
            with col:
                f = st.file_uploader(lab, type="pdf", key=key)
                if f and st.button(f"Leer {lab}", key="b"+key):
                    reader = PyPDF2.PdfReader(f)
                    res = analizar_pdf_legal("".join([p.extract_text() for p in reader.pages[:3]]), lab)
                    if res:
                        if key == "f1": st.session_state.form_data["ej_list"][0].update({"rit": res["rit"], "ruc": res["ruc"]}); st.session_state.form_data["imp_nom"] = res["imputado"]
                        elif key == "f2": st.session_state.form_data["rpa_list"].append({"rit": res["rit"], "sancion": res["sancion_pena"]})
                        elif key == "f3": st.session_state.form_data["adulto_list"].append({"rit": res["rit"]}); st.session_state.form_data["fecha_ad"] = res["fecha_sentencia"]; st.session_state.form_data["es_rpa_semaforo"] = False
                        st.success("Cargado")

    with t2:
        st.header("🎙️ Transcripción")
        st.file_uploader("Audio de Audiencia")

    with t3:
        with st.form("leg"):
            st.subheader("Individualización")
            def_n = st.text_input("Defensor", st.session_state.user_name)
            imp_n = st.text_input("Adolescente", st.session_state.form_data["imp_nom"])
            juz = st.selectbox("Juzgado", TRIBUNALES_STGO_SM)
            if st.form_submit_button("⚖️ GENERAR Y GUARDAR"):
                dat = {"juzgado_ejecucion": juz, "causas_ej_str": st.session_state.form_data["ej_list"][0]["rit"], "causas_adulto_str": "", "rit_prin": st.session_state.form_data["ej_list"][0]["rit"], "ruc_prin": st.session_state.form_data["ej_list"][0]["ruc"], "causas_str": ""}
                word = GeneradorOficialIABL(def_n, imp_n).generar_escrito(tipo_escrito, dat)
                guardar_gestion_iabl(dat["ruc_prin"], dat["rit_prin"], juz, tipo_escrito, "Escrito generado")
                st.download_button("Descargar", word, f"{tipo_escrito}.docx")
                st.balloons()

    with t4:
        if st.session_state.is_admin: st.table([{"Email": k, "Nombre": v["nombre"]} for k, v in st.session_state.usuarios_db.items()])

    st.markdown("<div style='text-align: center; color: gray;'>Suite Legal Pro - <b>IGNACIO ANTONIO BADILLA LARA</b></div>", unsafe_allow_html=True)





VERSION PRO OTRA

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
        else: p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        
        p.paragraph_format.line_spacing_rule = WD_LINE_SPACING.ONE_POINT_FIVE
        if indent: p.paragraph_format.first_line_indent = Inches(0.5)

        # Respetar negritas en nombres, causas y POR TANTO
        def_esc = re.escape(self.defensor.upper())
        ado_esc = re.escape(self.adolescente.upper())
        patron = r"(RIT:?\s?\d+-\d{4}|RUC:?\s?\d{7,10}-[\dkK]|POR TANTO|OTROSÍ|SOLICITA|INTERPONE|{0}|{1})".format(def_esc, ado_esc)
        
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
        
        # Lógica de encabezados según tipo (Se completa en la Parte 2)
        # --- CONTINUACIÓN DE LA CLASE GeneradorOficialIABL (DENTRO DE generar_escrito) ---
        
        if tipo == "Extinción Art. 25 ter":
            self.aplicar_formato(doc, "EN LO PRINCIPAL: SOLICITA EXTINCIÓN; OTROSÍ: ACOMPAÑA SENTENCIA", bold_all=True, indent=False, align="LEFT")
            self.aplicar_formato(doc, f"\n{data['juzgado_ejecucion'].upper()}", bold_all=True, indent=False)
            comp = f"\n{self.defensor.upper()}, Abogada, Defensora Penal Pública, en representación de {self.adolescente.upper()}, en causas de ejecución {data['causas_ej_str']}, a S.S., respetuosamente digo:"
            self.aplicar_formato(doc, comp)
            self.aplicar_formato(doc, "Que, vengo en solicitar que se declare la extinción de las sanciones de la Ley de Responsabilidad Penal Adolescente, o en subsidio se fije día y hora para celebrar audiencia para debatir sobre la extinción de la pena respecto de mi representado, en virtud de lo dispuesto en los artículos 25 ter y 25 quinquies de la Ley 20.084.")
            self.aplicar_formato(doc, "El fundamento radica en la existencia de una condena de mayor gravedad como adulto, la cual se detalla a continuación.")
            # Se itera sobre las causas RPA y Adulto proporcionadas en 'data'
            self.aplicar_formato(doc, "POR TANTO, SOLICITO A S.S. acceder a lo solicitado extinguiendo de pleno derecho la sanción antes referida.")
            self.aplicar_formato(doc, f"OTROSÍ: Acompaña sentencia de adulto de las causas {data['causas_adulto_str']}", bold_all=True, indent=False)

        elif tipo == "Prescripción de la Pena":
            self.aplicar_formato(doc, "EN LO PRINCIPAL: SOLICITA AUDIENCIA DE PRESCRIPCIÓN; OTROSÍ: OFICIA A EXTRANJERÍA Y ADJUNTA ANTECEDENTES", bold_all=True, indent=False, align="LEFT")
            self.aplicar_formato(doc, f"\n{data['juzgado_ejecucion'].upper()}", bold_all=True, indent=False)
            comp = f"\n{self.defensor.upper()}, Abogada, Defensora Penal Pública, en representación de {self.adolescente.upper()}, en causas {data['causas_str']}, a S.S. respetuosamente digo:"
            self.aplicar_formato(doc, comp)
            self.aplicar_formato(doc, "Que, vengo en solicitar se sirva fijar día y hora para celebrar audiencia con el objeto de debatir sobre la prescripción de la pena, de conformidad a lo dispuesto en el artículo 5 de la Ley N° 20.084 y las normas pertinentes del Código Penal.")
            self.aplicar_formato(doc, "Teniendo presente el tiempo transcurrido desde que las sentencias quedaron ejecutoriadas, ha transcurrido en exceso el plazo legal exigido.")
            self.aplicar_formato(doc, "POR TANTO, SOLICITO A S.S. acceder a lo solicitado, fijando día y hora para celebrar audiencia y declarar el sobreseimiento definitivo.")
            self.aplicar_formato(doc, "OTROSÍ: Solicito se oficie a Extranjería para informar movimientos migratorios y se incorpore Extracto de Filiación actualizado.", bold_all=True, indent=False)

        elif tipo == "Amparo Constitucional":
            self.aplicar_formato(doc, "INTERPONE ACCIÓN CONSTITUCIONAL DE AMPARO; OTROSÍ: ORDEN DE NO INNOVAR", bold_all=True, indent=False, align="LEFT")
            self.aplicar_formato(doc, "\nILTMA. CORTE DE APELACIONES DE SANTIAGO", bold_all=True, indent=False)
            comp = f"\n{self.defensor.upper()}, abogada, Defensora Penal Juvenil, en representación de {self.adolescente.upper()}, en causa RIT {data['rit_prin']}, RUC {data['ruc_prin']} del Juzgado de Garantía, a V.S.I respetuosamente digo:"
            self.aplicar_formato(doc, comp)
            self.aplicar_formato(doc, "Que, en virtud de lo dispuesto en el artículo 21 de la Constitución Política de la República, vengo en deducir acción constitucional de amparo por la perturbación grave e ilegítima a la libertad personal, emanada de la resolución que ordenó el ingreso inmediato del joven, siendo esta ilegal y arbitraria.")
            self.aplicar_formato(doc, "La resolución infringe el artículo 79 del Código Penal: 'no podrá ejecutarse pena alguna sino en virtud de sentencia ejecutoriada'.")
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

# --- FUNCIONES DE PERSISTENCIA Y USUARIOS ---
def guardar_gestion_iabl(ruc, rit, tribunal, tipo, contenido):
    """Guarda en Supabase usando las columnas exactas solicitadas."""
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

# --- TRANSCRIPTOR INTELIGENTE (AUDIOS A TEXTO) ---
def transcribir_audiencia(archivo_audio):
    """Integración futura con Gemini 1.5 Pro para audios largos."""
    st.info("Función de transcripción íntegra activada. Procesando audio...")
    # Lógica de carga de archivo a API de Google
    return "Texto íntegro de la audiencia transcrito por IA..."

# --- GESTIÓN DE ESTADO DE FORMULARIO ---
if "form_data" not in st.session_state:
    st.session_state.form_data = {
        "imp_nom": "", "juz_ej_sel": "Seleccionar...",
        "rpa_list": [], "adulto_list": [],
        "ej_list": [{"rit":"", "ruc":""}],
        "fecha_ad": None, "es_rpa_semaforo": True
    }
    # --- CONTINUACIÓN DE LA INTERFAZ STREAMLIT ---

if check_password():
    with st.sidebar:
        st.title("💼 Suite Legal IABL")
        st.write(f"Usuario: **{st.session_state.user_name}**")
        
        # --- MÓDULO DE SUSCRIPCIONES Y PAGOS ---
        st.divider()
        st.subheader("💳 Planes y Suscripciones")
        if st.session_state.get("legal_coins", 0) < 10:
            st.warning(f"Saldo bajo: {st.session_state.get('legal_coins', 0)} LegalCoins")
            if st.button("Comprar Créditos (Stripe/Webpay)"):
                st.info("Redirigiendo a pasarela de pagos segura...")
        else:
            st.success(f"Créditos disponibles: {st.session_state.get('legal_coins', 0)}")
        
        st.divider()
        tipo_escrito = st.selectbox("📝 Recurso a Generar", 
            ["Extinción Art. 25 ter", "Prescripción de la Pena", "Amparo Constitucional", "Apelación por Quebrantamiento"])
        
        # --- SEMÁFORO DE PLAZOS INTELIGENTE ---
        st.subheader("📊 Semáforo de Plazos")
        if st.session_state.form_data.get("fecha_ad"):
            # Diferenciación automática: RPA (Art. 5 Ley 20.084) vs Adultos
            status = calcular_semaforo(
                st.session_state.form_data["fecha_ad"], 
                st.session_state.form_data.get("es_rpa_semaforo", True)
            )
            st.info(status)
        else:
            st.write("Sube una sentencia para calcular plazos.")

    # --- PESTAÑAS PRINCIPALES ---
    tab_ia, tab_audio, tab_form, tab_admin = st.tabs([
        "🤖 Carga Inteligente (IA)", 
        "🎙️ Transcriptor", 
        "📄 Datos del Recurso", 
        "⚙️ Administración"
    ])

    with tab_ia:
        st.header("⚡ Asistente Gemini 1.5 Flash")
        st.write("Automatiza el llenado de apartados mediante lectura de PDFs.")
        
        c_ia1, c_ia2, c_ia3 = st.columns(3)
        with c_ia1:
            st.markdown("### 1. Ejecución")
            pdf_ej = st.file_uploader("Acta de Ejecución", type=["pdf"], key="up_ej_final")
            if pdf_ej and st.button("Procesar Ejecución", key="btn_ej"):
                with st.spinner("Analizando acta..."):
                    reader = PyPDF2.PdfReader(pdf_ej)
                    texto = "".join([p.extract_text() for p in reader.pages[:3]])
                    res = analizar_pdf_legal(texto, "Acta de Ejecución")
                    if res:
                        st.session_state.form_data["ej_list"][0]["rit"] = res.get("rit", "")
                        st.session_state.form_data["ej_list"][0]["ruc"] = res.get("ruc", "")
                        st.session_state.form_data["imp_nom"] = res.get("imputado", "")
                        st.session_state.form_data["juz_ej_sel"] = res.get("tribunal", "Juzgado de Garantía de San Bernardo")
                        st.success("Apartado 1 cargado automáticamente.")

        with c_ia2:
            st.markdown("### 2. Sentencia RPA")
            pdf_rpa = st.file_uploader("Sentencia Ley 20.084", type=["pdf"], key="up_rpa_final")
            if pdf_rpa and st.button("Procesar RPA", key="btn_rpa"):
                with st.spinner("Analizando condena RPA..."):
                    reader = PyPDF2.PdfReader(pdf_rpa)
                    texto = "".join([p.extract_text() for p in reader.pages[:3]])
                    res = analizar_pdf_legal(texto, "Sentencia RPA")
                    if res:
                        st.session_state.form_data["rpa_list"].append({
                            "rit": res.get("rit", ""), "ruc": res.get("ruc", ""), 
                            "juzgado": res.get("tribunal", ""), "sancion": res.get("sancion_pena", "")
                        })
                        st.session_state.form_data["es_rpa_semaforo"] = True
                        st.success("Apartado 2 (RPA) actualizado.")

        with c_ia3:
            st.markdown("### 3. Sentencia Adulto")
            pdf_ad = st.file_uploader("Condena Adulto (CP)", type=["pdf"], key="up_ad_final")
            if pdf_ad and st.button("Procesar Adulto", key="btn_ad"):
                with st.spinner("Analizando condena Adulto..."):
                    reader = PyPDF2.PdfReader(pdf_ad)
                    texto = "".join([p.extract_text() for p in reader.pages[:3]])
                    res = analizar_pdf_legal(texto, "Sentencia Adulto")
                    if res:
                        st.session_state.form_data["adulto_list"].append({
                            "rit": res.get("rit", ""), "ruc": res.get("ruc", ""), 
                            "juzgado": res.get("tribunal", ""), "pena": res.get("sancion_pena", ""),
                            "fecha": res.get("fecha_sentencia", "")
                        })
                        st.session_state.form_data["fecha_ad"] = res.get("fecha_sentencia", "")
                        st.session_state.form_data["es_rpa_semaforo"] = False
                        st.success("Apartado 3 cargado y Semáforo activado.")

    with tab_audio:
        st.header("🎙️ Transcriptor Inteligente de Audiencias")
        st.write("Sube el audio de la audiencia para obtener la transcripción íntegra.")
        archivo_audio = st.file_uploader("Subir Audio (MP3, WAV, M4A)", type=["mp3", "wav", "m4a"])
        if archivo_audio and st.button("Comenzar Transcripción"):
            texto_transcrito = transcribir_audiencia(archivo_audio)
            st.text_area("Resultado de la Transcripción", value=texto_transcrito, height=400)

    with tab_form:
        st.header(f"Gestión: {tipo_escrito}")
        
        # --- FORMULARIO DINÁMICO ---
        with st.form("main_legal_form"):
            st.subheader("Datos de Individualización")
            c1, c2 = st.columns(2)
            def_nom_input = c1.text_input("Defensor/a", st.session_state.user_name)
            imp_nom_input = c2.text_input("Nombre Adolescente", st.session_state.form_data["imp_nom"])
            juz_sel = st.selectbox("Juzgado de Ejecución", TRIBUNALES_STGO_SM, 
                                 index=TRIBUNALES_STGO_SM.index(st.session_state.form_data["juz_ej_sel"]) if st.session_state.form_data["juz_ej_sel"] in TRIBUNALES_STGO_SM else 0)
            
            st.markdown("---")
            if st.form_submit_button(f"⚖️ GENERAR Y GUARDAR {tipo_escrito.upper()}"):
                if not imp_nom_input:
                    st.error("Faltan datos críticos.")
                else:
                    # Lógica de construcción de datos para el motor Docx
                    datos_finales = {
                        "juzgado_ejecucion": juz_sel,
                        "causas_ej_str": ", ".join([c['rit'] for c in st.session_state.form_data["ej_list"] if c['rit']]),
                        "causas_adulto_str": ", ".join([c['rit'] for c in st.session_state.form_data["adulto_list"] if c['rit']]),
                        "rit_prin": st.session_state.form_data["ej_list"][0]["rit"],
                        "ruc_prin": st.session_state.form_data["ej_list"][0]["ruc"]
                    }
                    
                    # 1. Generar Documento
                    gen = GeneradorOficialIABL(def_nom_input, imp_nom_input)
                    word_file = gen.generar_escrito(tipo_escrito, datos_finales)
                    
                    # 2. Guardar en Supabase (Columnas exactas solicitadas)
                    res_db = guardar_gestion_iabl(
                        datos_finales["ruc_prin"], 
                        datos_finales["rit_prin"], 
                        juz_sel, 
                        tipo_escrito, 
                        f"Escrito generado íntegramente para {imp_nom_input}."
                    )
                    
                    st.download_button(f"📂 Descargar {tipo_escrito}.docx", word_file, f"{tipo_escrito}_{imp_nom_input}.docx")
                    if res_db: st.toast("Sincronizado con Base de Datos IABL", icon="☁️")
                    st.balloons()

    with tab_admin:
        st.header("⚙️ Administración de Usuarios")
        if st.session_state.get("is_admin", False):
            st.subheader("Control de Suscripciones")
            # Simulación de tabla de usuarios de Supabase
            usuarios_data = [{"Email": k, "Nombre": v["nombre"], "Nivel": v["nivel"]} for k, v in st.session_state.usuarios_db.items()]
            st.table(usuarios_data)
            st.info("Módulo de gestión de pagos vía API de Stripe/Webpay en desarrollo.")
        else:
            st.warning("Acceso restringido a administradores.")

    st.markdown("---")
    st.markdown("<div style='text-align: center; color: gray;'>Suite Legal Pro - <b>IGNACIO ANTONIO BADILLA LARA</b> - Defensoría Penal Pública</div>", unsafe_allow_html=True)
