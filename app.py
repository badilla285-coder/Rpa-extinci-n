import streamlit as st
import streamlit_antd_components as sac
import streamlit_shadcn_ui as ui
from streamlit_extras.colored_header import colored_header
from streamlit_extras.add_vertical_space import add_vertical_space
from streamlit_extras.card import card
from docx import Document
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
import io
import re
import json
from datetime import datetime
import PyPDF2
from supabase import create_client
import google.generativeai as genai
import time
import random
import tempfile
import os
import numpy as np 

# --- INTEGRACIÓN LANGCHAIN ---
# Fundamental para la integridad de los textos legales al indexar
from langchain.text_splitter import RecursiveCharacterTextSplitter

# =============================================================================
# 1. CONFIGURACIÓN Y ESTILOS (DISEÑO LEGAL TECH PRO)
# =============================================================================
st.set_page_config(
    page_title="Sistema Jurídico Avanzado IABL",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS Profesional: Diseño "Nórdico Legal" (Navy/Slate/Beige)
st.markdown("""
    <style>
    /* Ocultar elementos base */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    /* Animación de entrada */
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(20px); }
        to { opacity: 1; transform: translateY(0); }
    }
    
    /* Tipografía y Fondo */
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 5rem;
    }
    
    .stApp {
        background-color: #f8fafc;
        font-family: 'Segoe UI', 'Roboto', sans-serif;
        color: #333333;
    }
    
    /* Encabezados */
    h1 { 
        color: #1e293b !important; 
        font-weight: 800; 
        border-bottom: 2px solid #cbd5e1;
        padding-bottom: 15px; 
        letter-spacing: -0.5px;
        text-transform: uppercase;
        font-size: 1.8rem;
    }
    h2, h3 { color: #334155 !important; font-weight: 600; }
    
    /* Botones Premium */
    .stButton>button {
        background-color: #0f172a !important;
        color: white !important;
        border-radius: 8px;
        font-weight: 600;
        border: none;
        padding: 0.6rem 1.2rem;
        transition: all 0.3s ease;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        width: 100%;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    .stButton>button:hover {
        background-color: #334155 !important;
        transform: translateY(-2px);
    }
    
    /* Inputs Modernos */
    .stTextInput > div > div > input, .stSelectbox > div > div > div {
        border-radius: 8px !important;
        border: 1px solid #e2e8f0 !important;
        background-color: white;
    }
    
    /* Text Area para Copiar (Estilo Sigilo/Sistema) */
    .copy-area textarea {
        background-color: #f1f5f9;
        border: 1px dashed #94a3b8;
        font-family: 'Courier New', monospace;
        font-size: 0.9rem;
        color: #0f172a;
    }

    /* Badges */
    .status-badge {
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 600;
        text-transform: uppercase;
        border: 1px solid #e2e8f0;
        background-color: white;
        color: #475569;
    }

    /* Footer */
    .custom-footer {
        position: fixed;
        left: 0;
        bottom: 0;
        width: 100%;
        background-color: #ffffff;
        color: #94a3b8;
        text-align: center;
        padding: 15px;
        border-top: 1px solid #e2e8f0;
        font-size: 0.8rem;
        z-index: 999;
        font-family: 'Segoe UI', sans-serif;
    }
    </style>
""", unsafe_allow_html=True)

# =============================================================================
# 2. SERVICIOS Y API (SEGURIDAD REFORZADA)
# =============================================================================

try:
    if "GOOGLE_API_KEY" in st.secrets:
        genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
except Exception as e:
    st.error(f"⚠️ Error configurando API Key: {e}")

def get_generative_model_dinamico():
    """Busca modelo disponible priorizando Flash 1.5 para velocidad/costo."""
    try:
        modelos = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        mejor = next((m for m in modelos if 'gemini-1.5-flash' in m), None)
        if not mejor:
            mejor = next((m for m in modelos if 'gemini-1.5-pro' in m), modelos[0])
        return genai.GenerativeModel(mejor)
    except:
        return genai.GenerativeModel('models/gemini-1.5-flash-latest')

model_ia = get_generative_model_dinamico()

MODELO_EMBEDDING_ACTUAL = None
def get_embedding_model():
    """Busca modelo de embedding disponible."""
    global MODELO_EMBEDDING_ACTUAL
    if MODELO_EMBEDDING_ACTUAL: return MODELO_EMBEDDING_ACTUAL
    try:
        modelos = list(genai.list_models())
        for m in modelos:
            if 'embedContent' in m.supported_generation_methods and 'text-embedding-004' in m.name:
                MODELO_EMBEDDING_ACTUAL = m.name
                return m.name
        return 'models/text-embedding-004'
    except:
        return 'models/text-embedding-004'

def analizar_metadata_profunda(texto_completo):
    """Extracción precisa de metadata jurídica."""
    try:
        prompt = f"""
        Actuario Judicial Experto. Lee este documento legal COMPLETO. 
        Extrae JSON válido:
        {{
            "tribunal": "Nombre exacto del tribunal",
            "rol": "RIT o Rol",
            "fecha_sentencia": "YYYY-MM-DD",
            "resultado": "Resumen breve",
            "tema": "Palabras clave",
            "tipo": "Uno de: [Sentencia Condenatoria, Sentencia Absolutoria, Recurso de Nulidad, Recurso de Amparo, Recurso de Apelación, Doctrina/Artículo, Ley/Normativa]"
        }}
        Texto: {texto_completo[:20000]}
        """
        model = get_generative_model_dinamico()
        resp = model.generate_content(prompt)
        clean_json = resp.text.replace('```json', '').replace('```', '').strip()
        return json.loads(clean_json)
    except:
        return {"tribunal": "Desconocido", "rol": "S/N", "fecha_sentencia": datetime.now().strftime("%Y-%m-%d"), "tipo": "Documento Legal"}

@st.cache_resource
def init_supabase():
    try:
        # Intenta usar secrets, fallback a hardcoded si falla (para desarrollo)
        url = st.secrets.get("SUPABASE_URL", "https://zblcddxbhyomkasmbvyz.supabase.co")
        key = st.secrets.get("SUPABASE_KEY", "sb_publishable_pHMqXxI39AssehHdBs1wqA_NVjPc-FT")
        return create_client(url, key)
    except:
        return None

supabase = init_supabase()

# =============================================================================
# 3. DATOS MAESTROS Y LÓGICA PENAL (INTEGRIDAD TOTAL)
# =============================================================================
TRIBUNALES = [
    "1° Juzgado de Garantía de Santiago", "2° Juzgado de Garantía de Santiago",
    "3° Juzgado de Garantía de Santiago", "4° Juzgado de Garantía de Santiago",
    "5° Juzgado de Garantía de Santiago", "6° Juzgado de Garantía de Santiago",
    "7° Juzgado de Garantía de Santiago", "8° Juzgado de Garantía de Santiago",
    "9° Juzgado de Garantía de Santiago", "Juzgado de Garantía de San Bernardo", 
    "Juzgado de Garantía de Puente Alto", "Juzgado de Garantía de Talagante", 
    "Juzgado de Garantía de Melipilla", "Juzgado de Garantía de Colina",
    "3° Tribunal de Juicio Oral en lo Penal de Santiago",
    "Iltma. Corte de Apelaciones de San Miguel",
    "Iltma. Corte de Apelaciones de Santiago"
]

TIPOS_RECURSOS = [
    "Extinción Art. 25 ter",
    "Prescripción de la Pena",
    "Amparo Constitucional",
    "Apelación por Quebrantamiento"
]

ESCALA_PENAS = [
    {"nombre": "Prisión en su grado mínimo", "min": 1, "max": 20},
    {"nombre": "Prisión en su grado medio", "min": 21, "max": 40},
    {"nombre": "Prisión en su grado máximo", "min": 41, "max": 60},
    {"nombre": "Presidio menor en su grado mínimo", "min": 61, "max": 540},
    {"nombre": "Presidio menor en su grado medio", "min": 541, "max": 1095},
    {"nombre": "Presidio menor en su grado máximo", "min": 1096, "max": 1825},
    {"nombre": "Presidio mayor en su grado mínimo", "min": 1826, "max": 3650},
    {"nombre": "Presidio mayor en su grado medio", "min": 3651, "max": 5475},
    {"nombre": "Presidio mayor en su grado máximo", "min": 5476, "max": 7300},
    {"nombre": "Presidio perpetuo", "min": 7301, "max": 14600}
]

# =============================================================================
# 4. MOTOR DE GENERACIÓN WORD (LÓGICA JURÍDICA EXACTA)
# =============================================================================
class GeneradorWord:
    def __init__(self, defensor, imputado):
        self.doc = Document()
        self.defensor = defensor.upper() if defensor else "DEFENSOR PÚBLICO"
        self.imputado = imputado.upper() if imputado else "IMPUTADO"
        
        section = self.doc.sections[0]
        section.left_margin = Inches(1.2); section.right_margin = Inches(1.0)
        section.top_margin = Inches(1.0); section.bottom_margin = Inches(1.0)
        
        style = self.doc.styles['Normal']
        font = style.font; font.name = 'Cambria'; font.size = Pt(12)
        pf = style.paragraph_format
        pf.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        pf.line_spacing_rule = WD_LINE_SPACING.ONE_POINT_FIVE

    def add_parrafo(self, texto, negrita=False, align="JUSTIFY", sangria=True):
        p = self.doc.add_paragraph()
        if align == "CENTER": p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        elif align == "LEFT": p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        else: p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        
        p.paragraph_format.line_spacing_rule = WD_LINE_SPACING.ONE_POINT_FIVE
        if sangria and align == "JUSTIFY": p.paragraph_format.first_line_indent = Inches(0.5)
        
        texto_final = texto.replace("{DEFENSOR}", self.defensor).replace("{IMPUTADO}", self.imputado)
        
        if negrita:
            run = p.add_run(texto_final); run.font.name = 'Cambria'; run.font.size = Pt(12); run.bold = True
        else:
            keywords = [
                r"RIT:?\s?[\w\d-]+", r"RUC:?\s?[\w\d-]+", "POR TANTO", "OTROSÍ", "EN LO PRINCIPAL", 
                "SOLICITA", "INTERPONE", "ACCIÓN CONSTITUCIONAL", "HECHOS:", "DERECHO:", "AGRAVIO:", 
                "PETICIONES CONCRETAS:", "FUNDAMENTOS DE DERECHO:", "ANTECEDENTES DE HECHO:",
                "RESOLUCIÓN IMPUGNADA:", "ARGUMENTOS DE LA DEFENSA:", "ANTECEDENTES SOCIALES:", "SANCIÓN:", "SANCIÓN QUEBRANTADA:"
            ]
            patron_regex = "|".join(keywords) + f"|{re.escape(self.defensor)}|{re.escape(self.imputado)}"
            matches = list(re.finditer(patron_regex, texto_final, flags=re.IGNORECASE))
            last_pos = 0
            for match in matches:
                start, end = match.span()
                if start > last_pos:
                    run = p.add_run(texto_final[last_pos:start])
                    run.font.name = 'Cambria'; run.font.size = Pt(12)
                run_bold = p.add_run(texto_final[start:end])
                run_bold.font.name = 'Cambria'; run_bold.font.size = Pt(12); run_bold.bold = True
                last_pos = end
            if last_pos < len(texto_final):
                run = p.add_run(texto_final[last_pos:])
                run.font.name = 'Cambria'; run.font.size = Pt(12)

    def generar(self, tipo, datos):
        # 1. ENCABEZADO Y SUMA
        sumas = {
            "Extinción Art. 25 ter": "EN LO PRINCIPAL: SOLICITA EXTINCIÓN; OTROSÍ: ACOMPAÑA DOCUMENTO.",
            "Prescripción de la Pena": "EN LO PRINCIPAL: Solicita Audiencia de Prescripción; OTROSÍ: Oficia a extranjería y se remita extracto de filiación y antecedentes.",
            "Amparo Constitucional": "EN LO PRINCIPAL: ACCIÓN CONSTITUCIONAL DE AMPARO; OTROSÍ: ORDEN DE NO INNOVAR.",
            "Apelación por Quebrantamiento": "EN LO PRINCIPAL: INTERPONE RECURSO DE APELACIÓN; OTROSÍ: FORMA DE NOTIFICACIÓN."
        }
        self.add_parrafo(sumas.get(tipo, "SOLICITUD"), negrita=True, align="LEFT", sangria=False)
        self.doc.add_paragraph() 
        destinatario = "ILTMA. CORTE DE APELACIONES DE SANTIAGO" if tipo in ["Amparo Constitucional", "Apelación por Quebrantamiento"] else datos.get('tribunal_ej', 'TRIBUNAL').upper()
        self.add_parrafo(destinatario, negrita=True, align="CENTER", sangria=False)
        self.doc.add_paragraph()
        
        # 2. COMPARECENCIA
        causas_str = ""
        lista_ind = datos.get('lista_individualizacion', [])
        if lista_ind:
            causas_txts = [f"RUC {c['ruc']}, RIT {c['rit']}" for c in lista_ind if c['ruc']]
            if causas_txts: causas_str = ", en las causas " + "; ".join(causas_txts) + ","
        elif tipo == "Prescripción de la Pena":
            lista_causas = datos.get('prescripcion_list', [])
            causas_txts = [f"RUC {c['ruc']}, RIT {c['rit']}" for c in lista_causas if c['ruc']]
            if causas_txts: causas_str = ", en las causas " + "; ".join(causas_txts) + ","
        elif tipo == "Apelación por Quebrantamiento":
            rit_ap = datos.get('rit_ap', ''); ruc_ap = datos.get('ruc_ap', '')
            if rit_ap: causas_str = f", en causa RIT {rit_ap}, RUC {ruc_ap},"
        else:
            lista_ej = datos.get('ejecucion', [])
            causas_txts = [f"RUC {c.get('ruc','')}, RIT {c.get('rit','')}" for c in lista_ej if c.get('rit')]
            if causas_txts and not causas_str: causas_str = ", en causas " + "; ".join(causas_txts) + ","

        intro = f"{{DEFENSOR}}, Abogada, Defensora Penal Pública, en representación de {{IMPUTADO}}{causas_str} a S.S. respetuosamente digo:"
        self.add_parrafo(intro)

        # 3. CUERPO SEGÚN TIPO (ARGUMENTACIÓN COMPLETA)
        if tipo == "Prescripción de la Pena":
            self.add_parrafo("Que, por medio de la presente, vengo en solicitar a S.S. se sirva fijar día y hora para celebrar audiencia con el objeto de debatir sobre la prescripción de la pena respecto de mi representado, de conformidad a lo dispuesto en el artículo 5 de la Ley N° 20.084 y las normas pertinentes del Código Penal.")
            self.add_parrafo("Fundamento esta solicitud en que existen sentencias condenatorias en las causas señaladas, cuyo cumplimiento a la fecha se encuentra prescrito por el transcurso del tiempo, conforme a los siguientes antecedentes:")
            for c in datos.get('prescripcion_list', []):
                self.add_parrafo(f"En la causa RUC {c['ruc']} (RIT {c['rit']} de este Tribunal): Mi representado fue condenado por sentencia de fecha {c['fecha_sentencia']}, dictada por el {c['tribunal']} a la pena de {c['pena']} por el delito de {c['delito']}. Dicha sentencia se encuentra ejecutoriada (o con cumplimiento suspendido) desde el {c['fecha_suspension']}.")
            self.add_parrafo("Teniendo presente el tiempo transcurrido desde las fechas de las sentencias y, específicamente, desde la suspensión del cumplimiento, hasta la fecha actual (transcurriendo en exceso el plazo legal exigido para la prescripción de las sanciones en el marco de la Responsabilidad Penal Adolescente), solicito se fije audiencia con el objeto de debatir y declarar la prescripción de la pena y el consecuente sobreseimiento definitivo.")
            self.add_parrafo("POR TANTO, en mérito de lo expuesto y normativa legal citada,", sangria=False)
            self.add_parrafo("SOLICITO A S. S. acceder a lo solicitado, fijando día y hora para celebrar audiencia a fin de que se abra debate y se declare la prescripción de las penas en las presentes causas.", sangria=False)
            self.add_parrafo("OTROSÍ: Que, de conformidad a la petición principal planteada y para contar con todos los antecedentes necesarios para la adecuada resolución del tribunal, vengo en solicitar a S. S. se oficie a Extranjería con el fin de que informen los movimientos migratorios de mi representado {IMPUTADO}, desde la fecha de la primera sentencia hasta la fecha actual. Asimismo, solicito que se requiera y se incorpore a la carpeta digital el Extracto de Filiación y Antecedentes actualizado.", negrita=False)
            self.add_parrafo("POR TANTO,", sangria=False)
            self.add_parrafo("SOLICITO A S. S. acceder a lo solicitado, oficiando a Extranjería y ordenando la remisión del extracto de filiación y antecedentes actualizado.", sangria=False)

        elif tipo == "Extinción Art. 25 ter":
            self.add_parrafo("Que, vengo en solicitar que declare la extinción de las sanciones de la Ley de Responsabilidad Penal Adolescente, o en subsidio se fije día y hora para celebrar audiencia para debatir sobre la extinción de la pena respecto de mi representado, en virtud del artículo 25 ter y 25 quinquies de la Ley 20.084.")
            self.add_parrafo("Mi representado fue condenado en la siguiente causa de la Ley RPA:")
            for idx, rpa in enumerate(datos.get('rpa', []), 1):
                txt = f"{idx}. RIT: {rpa.get('rit','')}, RUC: {rpa.get('ruc','')}: Condenado por el {rpa.get('tribunal','JUZGADO DE GARANTÍA')} a la pena de {rpa.get('sancion','')}, debiendo cumplirse con todas las prescripciones establecidas en la ley 20.084."
                self.add_parrafo(txt)
            self.add_parrafo("El fundamento para solicitar la discusión radica en una condena de mayor gravedad como adulto:")
            for idx, ad in enumerate(datos.get('adulto', []), 1):
                txt = f"{idx}. RIT: {ad.get('rit','')}, RUC: {ad.get('ruc','')}: Condenado por el {ad.get('tribunal','')} con fecha {ad.get('fecha','')}, a la pena de {ad.get('pena','')}, como autor de delito."
                self.add_parrafo(txt)
            self.add_parrafo("Se hace presente que el artículo 25 ter en su inciso tercero establece que se considerará más grave el delito o conjunto de ellos que tuviere asignada en la ley una mayor pena de conformidad con las reglas generales.")
            self.add_parrafo("POR TANTO,", sangria=False)
            self.add_parrafo("En mérito de lo expuesto, SOLICITO A S.S. acceder a lo solicitado extinguiendo de pleno derecho la sanción antes referida.", sangria=False)
            self.add_parrafo("OTROSÍ: Acompaña sentencia de adulto.", negrita=True, sangria=False)
            self.add_parrafo("POR TANTO, SOLICITO A S.S. se tenga por acompañada.", sangria=False)

        elif tipo == "Amparo Constitucional":
            self.add_parrafo("Que, en virtud de lo dispuesto en el artículo 21 de la Constitución Política de la República, vengo en deducir acción constitucional de amparo a favor de mi representado, por la perturbación grave e ilegítima a su libertad personal y seguridad individual.")
            self.add_parrafo("ANTECEDENTES DE HECHO:", negrita=True)
            self.add_parrafo(datos.get('argumento_extra', 'La resolución recurrida ordenó el ingreso inmediato del joven, quebrantando una sanción de adolescente, la cual no se encontraba ejecutoriada y estando pendiente recurso de apelación, siendo la resolución ilegal y arbitraria.'))
            self.add_parrafo("FUNDAMENTOS DE DERECHO:", negrita=True)
            self.add_parrafo("1. Normativa Internacional y Constitucional: El derecho a la libertad personal se encuentra garantizado en el artículo 7 de la Convención Americana de Derechos Humanos y el artículo 19 Nº 7 de la Constitución Política de la República. El artículo 21 de la Carta Fundamental establece el recurso de amparo como la vía idónea para restablecer el imperio del derecho.")
            self.add_parrafo("2. Vulneración del artículo 79 del Código Penal: Dicha norma establece que 'no podrá ejecutarse pena alguna sino en virtud de sentencia ejecutoriada'. En el presente caso, la resolución impugnada ordena un ingreso o mantiene una privación de libertad sin que exista una sentencia firme que lo habilite, vulnerando el principio de legalidad.")
            self.add_parrafo("3. Interés Superior del Adolescente y Convención de Derechos del Niño: El artículo 37 letra b) de la Convención prescribe que la detención o prisión de un niño se utilizará tan sólo como medida de último recurso y durante el período más breve que proceda.")
            self.add_parrafo("POR TANTO,", sangria=False)
            self.add_parrafo("SOLICITO A V.S. ILTMA. admitir a tramitación la presente acción, pedir informe urgente al recurrido y, en definitiva, acoger el amparo, dejando sin efecto la resolución impugnada y ordenando la libertad inmediata de mi representado.", sangria=False)
            self.add_parrafo("OTROSÍ: ORDEN DE NO INNOVAR.", negrita=True, sangria=False)
            self.add_parrafo("Solicito se decrete orden de no innovar para suspender los efectos de la resolución recurrida mientras se tramita la presente acción, a fin de evitar que se consolide la afectación a la libertad personal.", sangria=False)

        elif tipo == "Apelación por Quebrantamiento":
            self.add_parrafo("Que encontrándome dentro del plazo legal, vengo en interponer recurso de apelación en contra de la resolución que ordenó el quebrantamiento definitivo de la sanción de mi representado, solicitando se revoque y se mantenga la sanción original en el medio libre o se decrete un quebrantamiento parcial.")
            self.add_parrafo("I. HECHOS:", negrita=True)
            self.add_parrafo(datos.get('hechos_quebrantamiento', 'No especificados'))
            self.add_parrafo("RESOLUCIÓN IMPUGNADA:", negrita=True)
            self.add_parrafo(datos.get('resolucion_tribunal', 'No especificada'))
            self.add_parrafo("ARGUMENTOS DE LA DEFENSA:", negrita=True)
            self.add_parrafo(datos.get('argumentos_defensa', 'No especificados'))
            if datos.get('antecedentes_sociales'):
                self.add_parrafo("ANTECEDENTES SOCIALES:", negrita=True)
                self.add_parrafo(datos.get('antecedentes_sociales'))
            self.add_parrafo("SANCIÓN ORIGINAL:", negrita=True)
            self.add_parrafo(datos.get('sancion_orig', ''))
            self.add_parrafo("SANCIÓN QUEBRANTADA:", negrita=True)
            self.add_parrafo(datos.get('sancion_quebrantada', ''))
            self.add_parrafo("II. EL DERECHO Y AGRAVIO:", negrita=True)
            self.add_parrafo("La resolución causa agravio pues desestima que la privación de libertad es una medida de último recurso (ultima ratio) según el artículo 40 n°2 de la Convención de Derechos del Niño.")
            self.add_parrafo("Principio de Progresividad: El artículo 52 de la Ley 20.084 establece una gradualidad en las sanciones por incumplimiento. Saltar directamente al quebrantamiento definitivo vulnera este principio, interrumpiendo procesos de reinserción escolar o laboral.")
            self.add_parrafo("Reinserción Social: El fin de la pena adolescente es la prevención especial positiva. El encierro total frustra este objetivo.")
            self.add_parrafo("POR TANTO,", sangria=False)
            self.add_parrafo("SOLICITO A US. tener por interpuesto recurso de apelación, concederlo y elevar los antecedentes a la Iltma. Corte de Apelaciones para que revoque la resolución impugnada.", sangria=False)

        buffer = io.BytesIO()
        self.doc.save(buffer)
        buffer.seek(0)
        return buffer

# =============================================================================
# 5. SESIÓN
# =============================================================================
if "logged_in" not in st.session_state: st.session_state.logged_in = False
if "user_role" not in st.session_state: st.session_state.user_role = "user"
if "defensor_nombre" not in st.session_state: st.session_state.defensor_nombre = ""

def init_session_data():
    defaults = {
        "imputado": "", "tribunal_sel": TRIBUNALES[9],
        "ejecucion": [{"rit": "", "ruc": ""}],
        "rpa": [{"rit": "", "ruc": "", "tribunal": TRIBUNALES[9], "sancion": ""}],
        "adulto": [], "prescripcion_list": [], "lista_individualizacion": [],
        "datos_apelacion": {}, "argumento_extra": ""
    }
    for k, v in defaults.items():
        if k not in st.session_state: st.session_state[k] = v

# =============================================================================
# 6. PANTALLA DE LOGIN
# =============================================================================
def login_screen():
    add_vertical_space(4)
    st.markdown("<h1 style='text-align: center; color: #1e293b; font-size: 3rem;'>IABL</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #64748b; font-size: 1.2rem; margin-bottom: 2rem;'>SISTEMA JURÍDICO AVANZADO</p>", unsafe_allow_html=True)

    c1, c2, c3 = st.columns([1, 1.2, 1])
    with c2:
        ui.card(title="Acceso Institucional", 
                content="Bienvenido. Ingrese sus credenciales para continuar.",
                description="Conexión encriptada vía Supabase").render()
        
        tab_login, tab_registro = st.tabs(["🔐 Login", "📝 Registro"])
        
        with tab_login:
            with st.form("login_form"):
                email = ui.input(placeholder="usuario@defensoria.cl", label="Correo Electrónico")
                password = ui.input(placeholder="••••••••", label="Contraseña", type="password")
                add_vertical_space(1)
                submitted = st.form_submit_button("INGRESAR AL SISTEMA", use_container_width=True)
                
                if submitted:
                    try:
                        session = supabase.auth.sign_in_with_password({"email": email, "password": password})
                        perfil = supabase.table("profiles").select("*").eq("id", session.user.id).execute()
                        if perfil.data:
                            st.session_state.logged_in = True
                            st.session_state.user_role = perfil.data[0]['rol']
                            st.session_state.defensor_nombre = perfil.data[0]['nombre']
                            st.success("Acceso concedido.")
                            time.sleep(1); st.rerun()
                        else:
                            st.error("Error perfil usuario.")
                    except:
                        st.error("Credenciales inválidas")

        with tab_registro:
            with st.form("reg_form"):
                n_email = st.text_input("Correo")
                n_pass = st.text_input("Clave", type="password")
                n_name = st.text_input("Nombre Completo")
                if st.form_submit_button("Crear Cuenta"):
                    try:
                        supabase.auth.sign_up({"email": n_email, "password": n_pass, "options": {"data": {"nombre": n_name}}})
                        st.success("Revisa tu correo.")
                    except: st.error("Error en registro")

    add_vertical_space(3)
    f1, f2, f3, f4 = st.columns(4)
    with f1: card(title="Escritos IA", text="Redacción automática", image=None)
    with f2: card(title="Visión OCR", text="Lectura de partes", image=None)
    with f3: card(title="Jurisprudencia", text="Búsqueda RAG", image=None)
    with f4: card(title="Vectores", text="Base Supabase", image=None)

    st.markdown('<div class="custom-footer">Copyright © 2026 IABL Legal Tech. Todos los derechos reservados.</div>', unsafe_allow_html=True)

# =============================================================================
# 7. MAIN APP
# =============================================================================
def main_app():
    init_session_data()

    with st.sidebar:
        st.markdown(f"### 👤 {st.session_state.defensor_nombre}")
        st.markdown(f"<span class='status-badge'>{st.session_state.user_role}</span>", unsafe_allow_html=True)
        add_vertical_space(1)
        
        menu_choice = sac.menu([
            sac.MenuItem('Escritorio', icon='house-door', children=[
                sac.MenuItem('Generador de Escritos', icon='file-earmark-text'),
                sac.MenuItem('Cálculo de Penas', icon='calculator'),
            ]),
            sac.MenuItem('Inteligencia Digital', icon='robot', children=[
                sac.MenuItem('Analista Multimodal', icon='eye'),
                sac.MenuItem('Transcripción Audiencia', icon='mic'),
                sac.MenuItem('Biblioteca RAG', icon='search'),
            ]),
            sac.MenuItem('Configuración', icon='gear', children=[
                sac.MenuItem('Administración', icon='shield-lock', disabled=st.session_state.user_role != "Admin"),
                sac.MenuItem('Cerrar Sesión', icon='box-arrow-right'),
            ]),
        ], color='indigo', open_all=True)

    # VISTA 1: GENERADOR DE ESCRITOS
    if menu_choice == 'Generador de Escritos':
        colored_header(label="Generador de Escritos Inteligente", description="Automatización de trámites procesales", color_name="indigo-70")
        
        tipo_rec = st.selectbox("Seleccione el Tipo de Escrito", TIPOS_RECURSOS)
        
        col_form, col_meta = st.columns([2, 1])
        with col_meta:
            ui.card(title="Individualización", content="Datos del Imputado y Tribunal").render()
            st.session_state.defensor_nombre = ui.input(value=st.session_state.defensor_nombre, label="Defensor/a")
            st.session_state.imputado = ui.input(value=st.session_state.imputado, label="Imputado/a")
            st.session_state.tribunal_sel = st.selectbox("Tribunal de Origen", TRIBUNALES)
            
            st.markdown("---")
            st.markdown("**Causas Individualizadas**")
            for i, c in enumerate(st.session_state.lista_individualizacion):
                c1, c2, c3 = st.columns([3, 3, 1])
                c['rit'] = c1.text_input(f"RIT", c['rit'], key=f"r{i}")
                c['ruc'] = c2.text_input(f"RUC", c['ruc'], key=f"u{i}")
                if c3.button("🗑️", key=f"d{i}"): st.session_state.lista_individualizacion.pop(i); st.rerun()
            if st.button("➕ Causa Extra"): st.session_state.lista_individualizacion.append({"rit":"", "ruc":""}); st.rerun()

        with col_form:
            if tipo_rec == "Prescripción de la Pena":
                st.subheader("Causas a Prescribir")
                with st.form("f_pre"):
                    cc1, cc2 = st.columns(2)
                    p_rit = cc1.text_input("RIT"); p_ruc = cc2.text_input("RUC")
                    p_pena = st.text_input("Pena Impuesta")
                    p_fec = st.text_input("Fecha Sentencia")
                    p_del = st.text_input("Delito")
                    p_susp = st.text_input("Fecha Susp.")
                    if st.form_submit_button("Añadir al Escrito"):
                        st.session_state.prescripcion_list.append({
                            "rit": p_rit, "ruc": p_ruc, "tribunal": st.session_state.tribunal_sel, 
                            "pena": p_pena, "fecha_sentencia": p_fec, "delito": p_del, "fecha_suspension": p_susp
                        })
                        st.rerun()
                if st.session_state.prescripcion_list:
                    ui.table(data=[{"RIT": c['rit'], "Delito": c['delito']} for c in st.session_state.prescripcion_list])

            elif tipo_rec == "Extinción Art. 25 ter":
                c_rpa, c_ad = st.tabs(["Causas RPA", "Condenas Adulto"])
                with c_rpa:
                    for i, rpa in enumerate(st.session_state.rpa):
                        with st.expander(f"RPA {i+1}"):
                            rpa['rit'] = st.text_input("RIT", key=f"rr{i}")
                            rpa['sancion'] = st.text_input("Sanción", key=f"rs{i}")
                    if st.button("➕ RPA"): st.session_state.rpa.append({}); st.rerun()
                with c_ad:
                    for i, ad in enumerate(st.session_state.adulto):
                        with st.expander(f"Adulto {i+1}"):
                            ad['rit'] = st.text_input("RIT", key=f"ar{i}")
                            ad['pena'] = st.text_input("Pena", key=f"ap{i}")
                    if st.button("➕ Adulto"): st.session_state.adulto.append({}); st.rerun()

            elif tipo_rec == "Apelación por Quebrantamiento":
                st.session_state.datos_apelacion['rit_ap'] = st.text_input("RIT Apelación")
                st.session_state.datos_apelacion['hechos_quebrantamiento'] = st.text_area("Hechos del Quebrantamiento")
                st.session_state.datos_apelacion['argumentos_defensa'] = st.text_area("Fundamentos Jurídicos")
                if st.button("✨ Refinar con IA"):
                    with st.spinner("Mejorando argumentación..."):
                        resp = model_ia.generate_content(f"Refina estos argumentos jurídicos: {st.session_state.datos_apelacion['argumentos_defensa']}")
                        st.session_state.datos_apelacion['argumentos_defensa'] = resp.text; st.rerun()

            elif tipo_rec == "Amparo Constitucional":
                st.session_state.argumento_extra = st.text_area("Antecedentes de Hecho Adicionales")

            add_vertical_space(2)
            if st.button("🚀 GENERAR DOCUMENTO WORD", type="primary", use_container_width=True):
                gen = GeneradorWord(st.session_state.defensor_nombre, st.session_state.imputado)
                dfinal = {
                    "tribunal_ej": st.session_state.tribunal_sel,
                    "prescripcion_list": st.session_state.prescripcion_list,
                    "rpa": st.session_state.rpa, "adulto": st.session_state.adulto,
                    "lista_individualizacion": st.session_state.lista_individualizacion,
                    "argumento_extra": st.session_state.argumento_extra,
                    **st.session_state.datos_apelacion
                }
                buf = gen.generar(tipo_rec, dfinal)
                st.download_button("📥 Descargar DOCX", buf, f"{tipo_rec}.docx", 
                                 "application/vnd.openxmlformats-officedocument.wordprocessingml.document", 
                                 use_container_width=True)

    # VISTA 2: ANALISTA MULTIMODAL (TEORÍA DEL CASO MEJORADA + RESUMEN SIGDP)
    elif menu_choice == 'Analista Multimodal':
        colored_header(label="Visión Judicial IA", description="Análisis de evidencia y Teoría del Caso", color_name="violet-70")
        
        mode = sac.segmented([sac.SegmentedItem('Control Detención'), sac.SegmentedItem('Estrategia General')], align='center')
        
        files = st.file_uploader("Subir PDF/Fotos de Partes Policiales", accept_multiple_files=True)
        ctx = st.text_area("Instrucciones específicas (Ej: Buscar contradicciones en horarios)")
        
        if files and st.button("🔍 INICIAR ANÁLISIS"):
            with st.status("Procesando evidencia y generando Teoría del Caso...", expanded=True) as status:
                try:
                    docs_g = []
                    for f in files:
                        status.write(f"Digitalizando {f.name}...")
                        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{f.name.split('.')[-1]}") as tmp:
                            tmp.write(f.getvalue()); f_g = genai.upload_file(tmp.name)
                            while f_g.state.name == "PROCESSING": time.sleep(1); f_g = genai.get_file(f_g.name)
                            docs_g.append(f_g)
                    
                    # PROMPT MEJORADO PARA TEORÍA DEL CASO Y RESUMEN SIGDP
                    p_sys = """
                    Eres un Estratega Penal Senior. 
                    TU MISIÓN: Construir una TEORÍA DEL CASO sólida y detectar debilidades.
                    
                    ESTRUCTURA DE RESPUESTA REQUERIDA:
                    1. ANÁLISIS FÁCTICO: Hechos relevantes y controvertidos.
                    2. ANÁLISIS JURÍDICO: Calificación, atenuantes/agravantes, vicios de nulidad.
                    3. ANÁLISIS PROBATORIO: Fortalezas y debilidades de la prueba fiscal.
                    
                    IMPORTANTE: AL FINAL DE TU RESPUESTA, GENERA UN BLOQUE SEPARADO IDENTIFICADO COMO '###RESUMEN_SIGILO###'.
                    Este bloque debe contener un resumen de la teoría del caso de entre 50 y 80 palabras, escrito en lenguaje técnico y formal, sin formato markdown (negritas o viñetas), listo para ser copiado y pegado en un sistema de gestión de causas.
                    Ejemplo de tono: "La defensa se sustenta en la insuficiencia probatoria respecto a la participación, toda vez que el reconocimiento..."
                    """
                    if mode == 'Control Detención': p_sys += " Enfócate prioritariamente en Art. 85, indicios y flagrancia."
                    
                    resp = model_ia.generate_content([p_sys, ctx] + docs_g)
                    status.update(label="Análisis Finalizado", state="complete")
                    
                    # Lógica para extraer y mostrar el Resumen SIGDP en recuadro aparte
                    full_text = resp.text
                    if "###RESUMEN_SIGILO###" in full_text:
                        parts = full_text.split("###RESUMEN_SIGILO###")
                        main_content = parts[0]
                        resumen_sigilo = parts[1].strip()
                    else:
                        main_content = full_text
                        resumen_sigilo = "No se generó resumen automático."

                    st.markdown("### Informe Estratégico")
                    st.markdown(main_content)
                    
                    st.divider()
                    st.subheader("📋 Resumen para Sistema de Gestión (Copia Rápida)")
                    st.markdown('<div class="copy-area">', unsafe_allow_html=True)
                    st.text_area("Copiar y pegar en sistema interno:", value=resumen_sigilo, height=100)
                    st.markdown('</div>', unsafe_allow_html=True)

                except Exception as e: st.error(e)

    # VISTA 3: TRANSCRIPTOR
    elif menu_choice == 'Transcripción Audiencia':
        colored_header(label="Transcripción Forense", description="Audio a Borrador de Recurso", color_name="orange-70")
        uploaded_audio = st.file_uploader("Audio Audiencia", type=["mp3", "wav", "m4a", "ogg"])
        
        if uploaded_audio and st.button("Procesar Audio"):
            with st.spinner("Transcribiendo y Redactando..."):
                try:
                    suffix = f".{uploaded_audio.name.split('.')[-1]}"
                    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                        tmp.write(uploaded_audio.getvalue()); tmp_path = tmp.name
                    
                    f = genai.upload_file(tmp_path)
                    while f.state.name == "PROCESSING": time.sleep(2); f = genai.get_file(f.name)
                    
                    prompt = "Transcribe literalmente y redacta BORRADOR DE RECURSO (Apelación/Amparo) detectando vicios."
                    resp = model_ia.generate_content([prompt, f])
                    
                    st.success("Procesado")
                    st.text_area("Resultado", value=resp.text, height=400)
                    st.download_button("Descargar TXT", resp.text, "transcripcion.txt")
                    os.remove(tmp_path)
                except Exception as e: st.error(f"Error: {e}")

    # VISTA 4: BIBLIOTECA RAG (FUNCIÓN MEJORADA)
    elif menu_choice == 'Biblioteca RAG':
        colored_header(label="Buscador Jurídico Inteligente", description="Jurisprudencia y Leyes con Búsqueda Semántica", color_name="green-70")
        
        q = ui.input(placeholder="Ej: Requisitos de la prisión preventiva en delitos de robo")
        
        if q and st.button("🔎 Consultar Base de Datos"):
            with st.spinner("Buscando vectores..."):
                try:
                    emb = genai.embed_content(model=get_embedding_model(), content=q, task_type="retrieval_query")['embedding']
                    
                    res = supabase.table("documentos_legales").select("*").limit(50).execute()
                    
                    hits = []
                    for d in res.data:
                        v_d = json.loads(d['embedding']) if isinstance(d['embedding'], str) else d['embedding']
                        sim = np.dot(emb, v_d) / (np.linalg.norm(emb) * np.linalg.norm(v_d))
                        hits.append((sim, d))
                    
                    hits.sort(key=lambda x: x[0], reverse=True)
                    top = hits[:3]
                    
                    if top:
                        contexto = "\n".join([f"DOC {i}: {h[1]['contenido']}" for i, h in enumerate(top)])
                        # Prompt mejorado para respuesta jurídica precisa
                        ans = model_ia.generate_content(f"Actúa como abogado senior. Responde a '{q}' basándote estrictamente en: {contexto}. Cita roles y tribunales.")
                        
                        ui.card(title="Respuesta Jurídica", content=ans.text).render()
                        
                        st.divider()
                        st.caption("Fuentes Detectadas:")
                        for s, d in top:
                            with st.expander(f"Similitud: {int(s*100)}%"):
                                st.write(d['contenido'])
                    else: st.warning("Sin resultados")
                except Exception as e: st.error(e)

    # VISTA 5: ADMINISTRACIÓN (INGESTA LANGCHAIN)
    elif menu_choice == 'Administración':
        colored_header(label="Panel del Administrador", description="Gestión de usuarios e ingesta documental", color_name="red-70")
        
        tab_a, tab_b = st.tabs(["📂 Ingesta Inteligente (LangChain)", "👥 Usuarios"])
        
        with tab_a:
            st.info("Usa LangChain RecursiveCharacterTextSplitter para un chunking semántico superior.")
            up_pdf = st.file_uploader("Cargar Jurisprudencia (PDF)", accept_multiple_files=True)
            
            if up_pdf and st.button("💾 Procesar e Indexar"):
                p_bar = st.progress(0)
                e_model = get_embedding_model()
                
                text_splitter = RecursiveCharacterTextSplitter(
                    chunk_size=1500,
                    chunk_overlap=200,
                    separators=["\n\n", "\n", " ", ""]
                )
                
                for i, f in enumerate(up_pdf):
                    reader = PyPDF2.PdfReader(f)
                    txt = "".join([p.extract_text() for p in reader.pages])
                    meta = analizar_metadata_profunda(txt)
                    
                    chunks = text_splitter.split_text(txt)
                    
                    for chunk in chunks:
                        vec = genai.embed_content(model=e_model, content=chunk, task_type="retrieval_document")['embedding']
                        supabase.table("documentos_legales").insert({"contenido": chunk, "metadata": meta, "embedding": vec}).execute()
                    p_bar.progress((i+1)/len(up_pdf))
                st.success("Base de datos actualizada con chunking inteligente.")

        with tab_b:
            users = supabase.table("profiles").select("*").execute()
            if users.data:
                st.dataframe(users.data)
            
            with st.form("new_u"):
                n_mail = st.text_input("Email Corporativo")
                n_name = st.text_input("Nombre Funcionario")
                n_role = st.selectbox("Rol", ["User", "Admin"])
                n_pass = st.text_input("Contraseña Temporal", type="password")
                if st.form_submit_button("Registrar Funcionario"):
                    try:
                        res = supabase.auth.sign_up({"email": n_mail, "password": n_pass, "options": {"data": {"nombre": n_name}}})
                        if res.user:
                            supabase.table("profiles").update({"rol": n_role}).eq("id", res.user.id).execute()
                            st.success("Usuario creado.")
                    except Exception as e: st.error(f"Error: {e}")

    elif menu_choice == 'Cerrar Sesión':
        st.session_state.logged_in = False
        st.rerun()

    # Footer Copyright
    st.markdown('<div class="custom-footer">Copyright © 2026 IABL Legal Tech. Todos los derechos reservados.</div>', unsafe_allow_html=True)

# =============================================================================
# 9. EJECUCIÓN
# =============================================================================
if __name__ == "__main__":
    if st.session_state.logged_in:
        main_app()
    else:
        login_screen()
