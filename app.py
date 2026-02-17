import streamlit as st
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

# =============================================================================
# 1. CONFIGURACIÓN Y ESTILOS (INTERFAZ ELEGANTE & LEGIBLE)
# =============================================================================
st.set_page_config(
    page_title="Sistema Jurídico Avanzado IABL",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS Profesional: Alto Contraste, Elegancia y Animaciones
st.markdown("""
    <style>
    /* Animación de entrada */
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(20px); }
        to { opacity: 1; transform: translateY(0); }
    }
    
    /* Tipografía y Fondo General */
    .main {
        background-color: #f4f7f6; /* Fondo gris muy suave y moderno */
        font-family: 'Segoe UI', 'Roboto', 'Helvetica Neue', sans-serif;
        color: #333333;
    }
    
    /* Encabezados */
    h1 { 
        color: #0d47a1; 
        font-weight: 800; 
        border-bottom: 3px solid #0d47a1; 
        padding-bottom: 15px; 
        letter-spacing: -0.5px;
        text-transform: uppercase;
        font-size: 1.8rem;
    }
    h2, h3 { color: #1565c0; font-weight: 600; }
    
    /* Botones Premium */
    .stButton>button {
        background-color: #0d47a1;
        color: white;
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
        background-color: #1976d2;
        transform: translateY(-2px);
        box-shadow: 0 6px 12px rgba(0,0,0,0.15);
    }
    
    /* Cajas de Información */
    .status-card {
        padding: 20px;
        border-radius: 10px;
        background: #ffffff;
        border-left: 5px solid #0d47a1;
        box-shadow: 0 4px 15px rgba(0,0,0,0.05);
        color: #212121;
        margin-bottom: 20px;
    }
    
    /* Login Box - Diseño Mejorado */
    .login-wrapper {
        display: flex;
        justify-content: center;
        align-items: center;
        padding-top: 50px;
        animation: fadeIn 0.8s ease-out;
    }
    .login-container {
        background: #ffffff;
        padding: 50px;
        border-radius: 16px;
        box-shadow: 0 20px 40px rgba(0,0,0,0.1);
        text-align: center;
        border-top: 6px solid #0d47a1;
        width: 100%;
        max-width: 450px;
    }
    .login-title {
        color: #0d47a1;
        font-size: 1.8rem;
        font-weight: 800;
        margin-bottom: 10px;
        letter-spacing: -0.5px;
    }
    .login-subtitle {
        font-size: 1rem;
        color: #546e7a;
        font-style: italic;
        margin-top: 25px;
        font-weight: 400;
        line-height: 1.5;
        border-top: 1px solid #eceff1;
        padding-top: 20px;
    }
    
    /* Minuta en Pantalla - Estilo Expediente */
    .minuta-box {
        background-color: #fffde7;
        padding: 30px;
        border-radius: 8px;
        border: 1px solid #fdd835;
        color: #212121 !important;
        margin-top: 20px;
        font-family: 'Courier New', Courier, monospace; 
        box-shadow: 0 4px 10px rgba(0,0,0,0.05);
        border-left: 6px solid #fbc02d;
    }
    </style>
""", unsafe_allow_html=True)

# =============================================================================
# 2. CONFIGURACIÓN SERVICIOS
# =============================================================================

# === CONFIGURACIÓN SEGURA (SECRETS) ===
try:
    if "GOOGLE_API_KEY" in st.secrets:
        genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
    else:
        st.error("⚠️ FALTA CONFIGURAR LA API KEY EN SECRETS (GOOGLE_API_KEY).")
except Exception as e:
    st.error(f"⚠️ Error configurando API Key: {e}")

# === NUEVA FUNCIÓN MAESTRA DE MODELOS DINÁMICOS ===
def get_generative_model_dinamico():
    """Busca automáticamente un modelo generativo disponible (Flash > Pro > Cualquiera)."""
    try:
        modelos = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        # Prioridad: 1.5 Flash -> 1.5 Pro -> Cualquiera
        mejor = next((m for m in modelos if 'gemini-1.5-flash' in m), None)
        if not mejor:
            mejor = next((m for m in modelos if 'gemini-1.5-pro' in m), modelos[0])
        # print(f"DEBUG: Usando modelo generativo: {mejor}") # Opcional
        return genai.GenerativeModel(mejor)
    except Exception as e:
        # Fallback de emergencia por si la lista falla
        return genai.GenerativeModel('models/gemini-1.5-flash-latest')

# Instancia global inicial (para compatibilidad con funciones antiguas del Tab 1)
model_ia = get_generative_model_dinamico()

# === LÓGICA DE DETECCIÓN AUTOMÁTICA DE MODELO DE EMBEDDING ===
MODELO_EMBEDDING_ACTUAL = None

def get_embedding_model():
    """Busca automáticamente un modelo de embedding disponible en la cuenta."""
    global MODELO_EMBEDDING_ACTUAL
    if MODELO_EMBEDDING_ACTUAL:
        return MODELO_EMBEDDING_ACTUAL

    try:
        # Listar todos los modelos y buscar uno que soporte 'embedContent'
        modelos = list(genai.list_models())
        
        # 1. Preferencia por text-embedding-004
        for m in modelos:
            if 'embedContent' in m.supported_generation_methods:
                if 'text-embedding-004' in m.name:
                    MODELO_EMBEDDING_ACTUAL = m.name
                    return m.name
        
        # 2. Si no, cualquiera que soporte embeddings
        for m in modelos:
            if 'embedContent' in m.supported_generation_methods:
                MODELO_EMBEDDING_ACTUAL = m.name
                return m.name
        
        # 3. Fallback hardcoded si la lista falla
        return 'models/text-embedding-004'
        
    except Exception as e:
        return 'models/text-embedding-004'

# === FUNCIÓN PARA METADATA PROFUNDA (ACTUALIZADA) ===
def analizar_metadata_profunda(texto_completo):
    """Usa IA para extraer metadata precisa del texto completo del documento."""
    try:
        prompt = f"""
        Eres un Actuario Judicial experto. Lee este documento legal COMPLETO. 
        Extrae con precisión quirúrgica un JSON válido con los siguientes campos:
        {{
            "tribunal": "Nombre exacto del tribunal (ej: 7 Juzgado de Garantía de Santiago)",
            "rol": "RIT o Rol de la causa (ej: 450-2023)",
            "fecha_sentencia": "Fecha del documento o sentencia (YYYY-MM-DD) o 'S/F'",
            "resultado": "Resumen muy breve (ej: Condenatoria, Absolutoria, Acoge Recurso)",
            "tema": "Palabras clave del tema jurídico (ej: Nulidad, Prisión Preventiva)",
            "tipo": "Tipo de documento (Jurisprudencia, Ley, Doctrina)"
        }}
        
        TEXTO DEL DOCUMENTO (Primeros 15000 caracteres):
        {texto_completo[:15000]}
        """
        
        # CAMBIO 2: USO DE MODELO DINÁMICO
        model = get_generative_model_dinamico()

        # Forzamos respuesta JSON limpia
        resp = model.generate_content(prompt)
        clean_json = resp.text.replace('```json', '').replace('```', '').strip()
        return json.loads(clean_json)
    except Exception as e:
        # Fallback en caso de error de IA
        return {
            "tribunal": "Desconocido/Error IA",
            "rol": "S/N",
            "fecha_sentencia": datetime.now().strftime("%Y-%m-%d"),
            "resultado": "Pendiente",
            "tema": "General",
            "tipo": "Documento Legal"
        }

SUPABASE_URL = "https://zblcddxbhyomkasmbvyz.supabase.co"
SUPABASE_KEY = "sb_publishable_pHMqXxI39AssehHdBs1wqA_NVjPc-FT"

@st.cache_resource
def init_supabase():
    try:
        return create_client(SUPABASE_URL, SUPABASE_KEY)
    except:
        return None

supabase = init_supabase()

# =============================================================================
# 3. DATOS MAESTROS Y LÓGICA PENAL MATEMÁTICA
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
    "Apelación por Quebrantamiento",
    "Minuta Control de Detención"
]

# Escala de Penas (Grados) para cálculo matemático
ESCALA_PENAS = [
    {"nombre": "Prisión en su grado mínimo", "min": 1, "max": 20},
    {"nombre": "Prisión en su grado medio", "min": 21, "max": 40},
    {"nombre": "Prisión en su grado máximo", "min": 41, "max": 60},
    {"nombre": "Presidio menor en su grado mínimo", "min": 61, "max": 540},
    {"nombre": "Presidio menor en su grado medio", "min": 541, "max": 1095}, # 3 años
    {"nombre": "Presidio menor en su grado máximo", "min": 1096, "max": 1825}, # 5 años
    {"nombre": "Presidio mayor en su grado mínimo", "min": 1826, "max": 3650}, # 10 años
    {"nombre": "Presidio mayor en su grado medio", "min": 3651, "max": 5475}, # 15 años
    {"nombre": "Presidio mayor en su grado máximo", "min": 5476, "max": 7300}, # 20 años
    {"nombre": "Presidio perpetuo", "min": 7301, "max": 14600} # Simbólico
]

# Base de datos de delitos con índice de grado base en ESCALA_PENAS
DELITOS_INFO = {
    "Robo con Intimidación": {"idx_min": 6, "idx_max": 8},
    "Robo con Violencia": {"idx_min": 6, "idx_max": 8},
    "Robo en Lugar Habitado": {"idx_min": 6, "idx_max": 6},
    "Microtráfico (Art. 4)": {"idx_min": 4, "idx_max": 5},
    "Tráfico Ilícito (Art. 3)": {"idx_min": 6, "idx_max": 7},
    "Homicidio Simple": {"idx_min": 7, "idx_max": 8},
    "Receptación": {"idx_min": 3, "idx_max": 5},
    "Porte Ilegal de Arma": {"idx_min": 5, "idx_max": 6},
    "Lesiones Graves": {"idx_min": 4, "idx_max": 4},
    "Amenazas Simples": {"idx_min": 3, "idx_max": 3},
    "Maltrato de Obra a Carabineros": {"idx_min": 4, "idx_max": 5}
}

# =============================================================================
# 4. LÓGICA DE IA & PROCESAMIENTO
# =============================================================================
def analizar_pdf(uploaded_file, tipo):
    if not model_ia: return None
    try:
        reader = PyPDF2.PdfReader(uploaded_file)
        text = "".join([page.extract_text() for page in reader.pages[:3]])
        prompt = f"""
        Analiza este documento legal chileno ({tipo}). Extrae en JSON:
        {{
            "rit": "RIT completo", "ruc": "RUC completo",
            "tribunal": "Nombre tribunal", "imputado": "Nombre completo",
            "fecha_sentencia": "YYYY-MM-DD", "pena": "Texto de la pena",
            "sancion": "Texto de sanción RPA"
        }}
        Texto: {text[:4000]}
        """
        resp = model_ia.generate_content(prompt)
        clean_json = resp.text.replace('```json', '').replace('```', '').strip()
        return json.loads(clean_json)
    except Exception as e:
        st.error(f"Error IA: {e}")
        return None

# =============================================================================
# 5. MOTOR DE GENERACIÓN WORD
# =============================================================================
class GeneradorWord:
    def __init__(self, defensor, imputado):
        self.doc = Document()
        self.defensor = defensor.upper() if defensor else "DEFENSOR PÚBLICO"
        self.imputado = imputado.upper() if imputado else "IMPUTADO"
        
        section = self.doc.sections[0]
        section.left_margin = Inches(1.2)
        section.right_margin = Inches(1.0)
        section.top_margin = Inches(1.0)
        section.bottom_margin = Inches(1.0)
        
        style = self.doc.styles['Normal']
        font = style.font
        font.name = 'Cambria'
        font.size = Pt(12)
        
        pf = style.paragraph_format
        pf.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        pf.line_spacing_rule = WD_LINE_SPACING.ONE_POINT_FIVE

    def add_parrafo(self, texto, negrita=False, align="JUSTIFY", sangria=True):
        p = self.doc.add_paragraph()
        
        if align == "CENTER": p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        elif align == "LEFT": p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        else: p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        
        p.paragraph_format.line_spacing_rule = WD_LINE_SPACING.ONE_POINT_FIVE
        if sangria and align == "JUSTIFY":
            p.paragraph_format.first_line_indent = Inches(0.5)
        
        texto_final = texto.replace("{DEFENSOR}", self.defensor).replace("{IMPUTADO}", self.imputado)
        
        if negrita:
            run = p.add_run(texto_final)
            run.font.name = 'Cambria'
            run.font.size = Pt(12)
            run.bold = True
        else:
            keywords = [
                r"RIT:?\s?[\w\d-]+", r"RUC:?\s?[\w\d-]+", 
                "POR TANTO", "OTROSÍ", "EN LO PRINCIPAL", 
                "SOLICITA", "INTERPONE", "ACCIÓN CONSTITUCIONAL",
                "HECHOS:", "DERECHO:", "AGRAVIO:", "PETICIONES CONCRETAS:", 
                "FUNDAMENTOS DE DERECHO:", "ANTECEDENTES DE HECHO:"
            ]
            
            patron_regex = "|".join(keywords) + f"|{re.escape(self.defensor)}|{re.escape(self.imputado)}"
            matches = list(re.finditer(patron_regex, texto_final, flags=re.IGNORECASE))
            
            last_pos = 0
            for match in matches:
                start, end = match.span()
                if start > last_pos:
                    run = p.add_run(texto_final[last_pos:start])
                    run.font.name = 'Cambria'
                    run.font.size = Pt(12)
                
                run_bold = p.add_run(texto_final[start:end])
                run_bold.font.name = 'Cambria'
                run_bold.font.size = Pt(12)
                run_bold.bold = True
                last_pos = end
            
            if last_pos < len(texto_final):
                run = p.add_run(texto_final[last_pos:])
                run.font.name = 'Cambria'
                run.font.size = Pt(12)

    def generar(self, tipo, datos):
        # 1. ENCABEZADO
        sumas = {
            "Extinción Art. 25 ter": "EN LO PRINCIPAL: SOLICITA EXTINCIÓN; OTROSÍ: ACOMPAÑA DOCUMENTO.",
            "Prescripción de la Pena": "EN LO PRINCIPAL: Solicita Audiencia de Prescripción; OTROSÍ: Oficia a extranjería y se remita extracto de filiación y antecedentes.",
            "Amparo Constitucional": "EN LO PRINCIPAL: ACCIÓN CONSTITUCIONAL DE AMPARO; OTROSÍ: ORDEN DE NO INNOVAR.",
            "Apelación por Quebrantamiento": "EN LO PRINCIPAL: INTERPONE RECURSO DE APELACIÓN; OTROSÍ: FORMA DE NOTIFICACIÓN.",
            "Minuta Control de Detención": "MINUTA DE AUDIENCIA: CONTROL DE DETENCIÓN"
        }
        self.add_parrafo(sumas.get(tipo, "SOLICITUD"), negrita=True, align="LEFT", sangria=False)
        self.doc.add_paragraph() 

        # 2. TRIBUNAL
        destinatario = "ILTMA. CORTE DE APELACIONES DE SANTIAGO" if tipo in ["Amparo Constitucional", "Apelación por Quebrantamiento"] else datos.get('tribunal_ej', 'TRIBUNAL').upper()
        self.add_parrafo(destinatario, negrita=True, align="CENTER", sangria=False)
        self.doc.add_paragraph()

        # 3. COMPARECENCIA (Multicausa)
        causas_str = ""
        lista_ind = datos.get('lista_individualizacion', [])
        if lista_ind:
            causas_txts = [f"RUC {c['ruc']}, RIT {c['rit']}" for c in lista_ind if c['ruc']]
            if causas_txts:
                causas_str = ", en las causas " + "; ".join(causas_txts) + ","
        
        elif tipo == "Prescripción de la Pena":
            lista_causas = datos.get('prescripcion_list', [])
            causas_txts = [f"RUC {c['ruc']}, RIT {c['rit']}" for c in lista_causas if c['ruc']]
            if causas_txts:
                causas_str = ", en las causas " + "; ".join(causas_txts) + ","
        else:
            lista_ej = datos.get('ejecucion', [])
            causas_txts = [f"RUC {c.get('ruc','')}, RIT {c.get('rit','')}" for c in lista_ej if c.get('rit')]
            if causas_txts and not causas_str:
                causas_str = ", en causas " + "; ".join(causas_txts) + ","

        intro = f"{{DEFENSOR}}, Abogada, Defensora Penal Pública, en representación de {{IMPUTADO}}{causas_str} a S.S. respetuosamente digo:"
        self.add_parrafo(intro)

        # 4. CUERPO DEL ESCRITO
        if tipo == "Prescripción de la Pena":
            self.add_parrafo("Que, por medio de la presente, vengo en solicitar a S.S. se sirva fijar día y hora para celebrar audiencia con el objeto de debatir sobre la prescripción de la pena respecto de mi representado, de conformidad a lo dispuesto en el artículo 5 de la Ley N° 20.084 y las normas pertinentes del Código Penal.")
            self.add_parrafo("Fundamento esta solicitud en que existen sentencias condenatorias en las causas señaladas, cuyo cumplimiento a la fecha se encuentra prescrito por el transcurso del tiempo, conforme a los siguientes antecedentes:")
            lista_p = datos.get('prescripcion_list', [])
            if not lista_p:
                self.add_parrafo("(Debe ingresar las causas en el formulario lateral)")
            for c in lista_p:
                parrafo_causa = (
                    f"En la causa RUC {c['ruc']} (RIT {c['rit']} de este Tribunal): Mi representado fue condenado por sentencia de fecha {c['fecha_sentencia']}, "
                    f"dictada por el {c['tribunal']} a la pena de {c['pena']} por el delito de {c['delito']}. "
                    f"Dicha sentencia se encuentra ejecutoriada (o con cumplimiento suspendido) desde el {c['fecha_suspension']}."
                )
                self.add_parrafo(parrafo_causa)
            self.add_parrafo("Teniendo presente el tiempo transcurrido desde las fechas de las sentencias y, específicamente, desde la suspensión del cumplimiento, hasta la fecha actual (transcurriendo en exceso el plazo legal exigido para la prescripción de las sanciones en el marco de la Responsabilidad Penal Adolescente), solicito se fije audiencia con el objeto de debatir y declarar la prescripción de la pena y el consecuente sobreseimiento definitivo.")
            self.add_parrafo("POR TANTO, en mérito de lo expuesto y normativa legal citada,", sangria=False)
            self.add_parrafo("SOLICITO A S. S. acceder a lo solicitado, fijando día y hora para celebrar audiencia a fin de que se abra debate y se declare la prescripción de las penas en las presentes causas.", sangria=False)
            self.add_parrafo("OTROSÍ: Que, de conformidad a la petición principal planteada y para contar con todos los antecedentes necesarios para la adecuada resolución del tribunal, vengo en solicitar a S. S. se oficie a Extranjería con el fin de que informen los movimientos migratorios de mi representado {IMPUTADO}, desde la fecha de la primera sentencia hasta la fecha actual. Asimismo, solicito que se requiera y se incorpore a la carpeta digital el Extracto de Filiación y Antecedentes actualizado.", negrita=False)
            self.add_parrafo("POR TANTO,", sangria=False)
            self.add_parrafo("SOLICITO A S. S. acceder a lo solicitado, oficiando a Extranjería y ordenando la remisión del extracto de filiación y antecedentes actualizado.", sangria=False)

        elif tipo == "Extinción Art. 25 ter":
            self.add_parrafo("Que, vengo en solicitar que declare la extinción de las sanciones de la Ley de Responsabilidad Penal Adolescente, o en subsidio se fije día y hora para celebrar audiencia para debatir sobre la extinción de la pena respecto de mi representado, en virtud del artículo 25 ter y 25 quinquies de la Ley 20.084.")
            self.add_parrafo("Mi representado fue condenado en la siguiente causa de la Ley RPA:")
            rpas = datos.get('rpa', [])
            for idx, rpa in enumerate(rpas, 1):
                txt = f"{idx}. RIT: {rpa.get('rit','')}, RUC: {rpa.get('ruc','')}: Condenado por el {rpa.get('tribunal','JUZGADO DE GARANTÍA')} a la pena de {rpa.get('sancion','')}, debiendo cumplirse con todas las prescripciones establecidas en la ley 20.084."
                self.add_parrafo(txt)
            self.add_parrafo("El fundamento para solicitar la discusión radica en una condena de mayor gravedad como adulto:")
            ads = datos.get('adulto', [])
            for idx, ad in enumerate(ads, 1):
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
            if datos.get('argumento_extra'):
                self.add_parrafo(datos['argumento_extra'])
            else:
                self.add_parrafo("La resolución recurrida ordenó el ingreso inmediato del joven, quebrantando una sanción de adolescente, la cual no se encontraba ejecutoriada y estando pendiente recurso de apelación, siendo la resolución ilegal y arbitraria.")
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
            if datos.get('argumento_extra'):
                self.add_parrafo(datos['argumento_extra'])
            else:
                self.add_parrafo("El tribunal decretó el quebrantamiento total sin considerar las circunstancias personales del adolescente y la posibilidad de reinserción.")
            self.add_parrafo("II. EL DERECHO Y AGRAVIO:", negrita=True)
            self.add_parrafo("La resolución causa agravio pues desestima que la privación de libertad es una medida de último recurso (ultima ratio) según el artículo 40 n°2 de la Convención de Derechos del Niño.")
            self.add_parrafo("Principio de Progresividad: El artículo 52 de la Ley 20.084 establece una gradualidad en las sanciones por incumplimiento. Saltar directamente al quebrantamiento definitivo vulnera este principio, interrumpiendo procesos de reinserción escolar o laboral.")
            self.add_parrafo("Reinserción Social: El fin de la pena adolescente es la prevención especial positiva. El encierro total frustra este objetivo.")
            self.add_parrafo("POR TANTO,", sangria=False)
            self.add_parrafo("SOLICITO A US. tener por interpuesto recurso de apelación, concederlo y elevar los antecedentes a la Iltma. Corte de Apelaciones para que revoque la resolución impugnada.", sangria=False)

        elif tipo == "Minuta Control de Detención":
            self.add_parrafo("I. HECHOS (RELATO FISCALÍA):", negrita=True)
            self.add_parrafo(f"Fecha: {datos.get('fecha_det','')}. Lugar: {datos.get('lugar_det','')}.")
            self.add_parrafo(datos.get('hechos_relato', 'No especificado'))
            self.add_parrafo("II. VERSIÓN DEL IMPUTADO / DEFENSA:", negrita=True)
            self.add_parrafo(datos.get('version_imputado', 'El imputado hizo uso de su derecho a guardar silencio, sin embargo la defensa sostiene...'))
            self.add_parrafo("III. INCIDENCIAS Y ARGUMENTOS DE DERECHO:", negrita=True)
            for arg in datos.get('argumentos_det', []):
                self.add_parrafo(f"- {arg}")
            if datos.get('argumento_extra'):
                self.add_parrafo(f"- {datos['argumento_extra']}")
            self.add_parrafo("IV. PETICIONES CONCRETAS AL TRIBUNAL:", negrita=True)
            self.add_parrafo("1. Que se declare ilegal la detención por vulneración de garantías constitucionales (Art 85, 83 CPP).")
            self.add_parrafo("2. Que se rechace la prisión preventiva/internación provisoria por falta de necesidad de cautela o proporcionalidad.")
            self.add_parrafo("3. Subsidiarimente, medidas del Art. 155 CPP.")

        buffer = io.BytesIO()
        self.doc.save(buffer)
        buffer.seek(0)
        return buffer

# =============================================================================
# 6. LÓGICA DE SESIÓN Y USUARIOS
# =============================================================================
if "db_users" not in st.session_state:
    st.session_state.db_users = [
        {"email": "admin@iabl.cl", "pass": "admin123", "rol": "Admin", "nombre": "IGNACIO BADILLA LARA"},
        {"email": "usuario@defensoria.cl", "pass": "defensor", "rol": "User", "nombre": "DEFENSOR PÚBLICO"}
    ]

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "user_role" not in st.session_state:
    st.session_state.user_role = "user"
if "defensor_nombre" not in st.session_state:
    st.session_state.defensor_nombre = ""

# =============================================================================
# 7. PANTALLA DE LOGIN
# =============================================================================
def login_screen():
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        st.markdown("""
        <div class='login-wrapper'>
            <div class='login-container'>
                <div class='login-title'>🏛️ ACCESO AL SISTEMA IABL</div>
        """, unsafe_allow_html=True)
        
        tab_login, tab_registro = st.tabs(["🔐 Iniciar Sesión", "📝 Crear Cuenta"])

        with tab_login:
            with st.form("login_form"):
                email = st.text_input("Correo Electrónico")
                password = st.text_input("Contraseña", type="password")
                submitted = st.form_submit_button("INGRESAR", use_container_width=True)
                
                if submitted:
                    try:
                        session = supabase.auth.sign_in_with_password({"email": email, "password": password})
                        user = session.user
                        data = supabase.table("profiles").select("*").eq("id", user.id).execute()
                        if data.data:
                            perfil = data.data[0]
                            st.session_state.logged_in = True
                            st.session_state.user_role = perfil['rol']
                            st.session_state.defensor_nombre = perfil['nombre']
                            st.session_state.user_email = email
                            st.success("¡Bienvenido!")
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error("Error: Usuario autenticado pero sin perfil.")
                    except Exception as e:
                        st.error(f"Credenciales incorrectas o error de conexión: {e}")

        with tab_registro:
            with st.form("register_form"):
                new_email = st.text_input("Tu Correo")
                new_pass = st.text_input("Crear Contraseña", type="password")
                new_name = st.text_input("Nombre Completo (Para los escritos)")
                reg_submit = st.form_submit_button("REGISTRARSE", use_container_width=True)
                
                if reg_submit:
                    try:
                        response = supabase.auth.sign_up({
                            "email": new_email, 
                            "password": new_pass,
                            "options": {"data": {"nombre": new_name}}
                        })
                        st.success("✅ Cuenta creada. Revisa tu correo o intenta iniciar sesión.")
                    except Exception as e:
                        st.error(f"Error al registrar: {e}")

        st.markdown("</div></div>", unsafe_allow_html=True)

# =============================================================================
# 8. CÁLCULO PENAL AVANZADO (LÓGICA JURÍDICA MATEMÁTICA)
# =============================================================================
def init_session_data():
    defaults = {
        "imputado": "", 
        "tribunal_sel": TRIBUNALES[9],
        "ejecucion": [{"rit": "", "ruc": ""}],
        "rpa": [{"rit": "", "ruc": "", "tribunal": TRIBUNALES[9], "sancion": ""}],
        "adulto": [],
        "prescripcion_list": [],
        "lista_individualizacion": []
    }
    for k, v in defaults.items():
        if k not in st.session_state: st.session_state[k] = v

def calcular_pena_exacta(delito_info, atenuantes, agravantes, es_rpa):
    idx_min = delito_info["idx_min"]
    idx_max = delito_info["idx_max"]
    
    n_at = len(atenuantes)
    n_ag = len(agravantes)
    
    if n_at > 0 and n_ag == 0:
        if n_at >= 2 or "11 N°6 Irreprochable" in atenuantes:
            idx_max = max(0, idx_min - 1)
            idx_min = max(0, idx_min - 1)
            efecto = "Rebaja de un grado"
        else:
            idx_max = idx_min
            efecto = "Mínimum del grado"
    elif n_ag > 0 and n_at == 0:
        idx_min = idx_max
        efecto = "Máximum del grado"
    elif n_at > 0 and n_ag > 0:
        efecto = "Compensación Racional (Rango completo)"
    else:
        efecto = "Sin modificatorias (Rango completo)"

    if es_rpa:
        idx_min = max(0, idx_min - 1)
        idx_max = max(0, idx_max - 1)
        efecto += " + Rebaja RPA Art. 21"

    rango_final = f"{ESCALA_PENAS[idx_min]['nombre']} a {ESCALA_PENAS[idx_max]['nombre']}"
    dias_min = ESCALA_PENAS[idx_min]['min']
    
    if es_rpa:
        if dias_min > 1825:
            resultado = "Régimen Cerrado (Crimen)"
            riesgo = 90
            badge = "badge-danger"
        elif dias_min > 1095:
            resultado = "Régimen Semicerrado"
            riesgo = 60
            badge = "badge-warning"
        else:
            resultado = "Libertad Asistida / Especial"
            riesgo = 20
            badge = "badge-success"
    else:
        if dias_min <= 1095:
            resultado = "Remisión Condicional (Probable)"
            riesgo = 10
            badge = "badge-success"
        elif dias_min <= 1825:
            resultado = "Libertad Vigilada (Probable)"
            riesgo = 40
            badge = "badge-warning"
        else:
            resultado = "Cumplimiento Efectivo"
            riesgo = 95
            badge = "badge-danger"

    return {
        "rango": rango_final,
        "dias_min": dias_min,
        "efecto": efecto,
        "resultado": resultado,
        "riesgo": riesgo,
        "badge": badge
    }

def generar_teoria_caso_ia(hechos, delito, atenuantes, es_rpa):
    contexto = "Adolescente (Ley 20.084)" if es_rpa else "Adulto"
    prompt = f"""
    Actúa como abogado penalista experto en litigación oral.
    Genera una TEORÍA DEL CASO estructurada para la defensa.
    DATOS DEL CASO:
    - Delito: {delito}
    - Contexto: {contexto}
    - Atenuantes invocadas: {", ".join(atenuantes)}
    - Relato de Hechos (Fiscalía): {hechos}
    ESTRUCTURA DE RESPUESTA REQUERIDA (NO USES MARKDOWN PESADO, SOLO TEXTO LIMPIO):
    1. PROPOSICIÓN FÁCTICA (Nuestra versión de los hechos, minimizando dolo o participación).
    2. PROPOSICIÓN JURÍDICA (Argumentos de derecho, calificación jurídica, improcedencia de prisión preventiva).
    3. PROPOSICIÓN PROBATORIA (Diligencias sugeridas: peritajes, testigos, documentos a solicitar).
    """
    try:
        response = model_ia.generate_content(prompt)
        return response.text
    except:
        return "Error conectando con IA Jurídica. Verifique conexión."

# =============================================================================
# 9. APLICACIÓN PRINCIPAL
# =============================================================================
def main_app():
    init_session_data()
    
    with st.sidebar:
        st.markdown(f"### 👤 {st.session_state.defensor_nombre}")
        if st.button("Cerrar Sesión"):
            st.session_state.logged_in = False
            st.rerun()
        st.divider()
        st.header("Gestión de Escritos")
        tipo_recurso = st.selectbox("Seleccionar Trámite", TIPOS_RECURSOS)
        st.divider()
        st.success("Supabase: Conectado (Ready)")
        st.info("BD Usuarios: Activa")
        st.info("BD Escritos: Activa")

    st.title(f"📄 {tipo_recurso}")
    
    tabs = st.tabs([
        "📝 Generador", 
        "🕵️ Analista Multimodal", 
        "🎙️ Transcriptor", 
        "📚 Biblioteca Inteligente", 
        "⚙️ Admin & BD"
    ])

    # === TAB 1: GENERADOR ===
    with tabs[0]:
        st.markdown("### 1. Individualización")
        col_def, col_imp = st.columns(2)
        st.session_state.defensor_nombre = col_def.text_input("Defensor/a", value=st.session_state.defensor_nombre)
        st.session_state.imputado = col_imp.text_input("Imputado/a", value=st.session_state.imputado)
        
        st.markdown("**Causas Individualizadas:**")
        for i, c in enumerate(st.session_state.lista_individualizacion):
            c1, c2, c3 = st.columns([3, 3, 1])
            c['rit'] = c1.text_input(f"RIT {i+1}", c['rit'], key=f"rit_ind_{i}")
            c['ruc'] = c2.text_input(f"RUC {i+1}", c['ruc'], key=f"ruc_ind_{i}")
            if c3.button("🗑️ Quitar", key=f"del_ind_{i}"):
                st.session_state.lista_individualizacion.pop(i)
                st.rerun()
                
        if st.button("➕ Agregar Causa a Individualización"):
            st.session_state.lista_individualizacion.append({"rit": "", "ruc": ""})
            st.rerun()
        
        tribunal_global = st.selectbox("Tribunal de Presentación", TRIBUNALES, index=TRIBUNALES.index(st.session_state.tribunal_sel) if st.session_state.tribunal_sel in TRIBUNALES else 0)
        st.session_state.tribunal_sel = tribunal_global

        st.markdown("---")
        
        if tipo_recurso == "Prescripción de la Pena":
            st.subheader("2. Causas a Prescribir (Detalle)")
            with st.form("form_prescripcion"):
                c1, c2, c3 = st.columns(3)
                p_rit = c1.text_input("RIT")
                p_ruc = c2.text_input("RUC")
                p_trib = c3.selectbox("Tribunal Origen", TRIBUNALES)
                c4, c5, c6 = st.columns(3)
                p_fecha_sent = c4.text_input("Fecha Sentencia", placeholder="12-12-2010")
                p_pena = c5.text_input("Pena Impuesta")
                p_delito = c6.text_input("Delito")
                p_fecha_susp = st.text_input("Fecha Ejecutoria / Suspensión")
                if st.form_submit_button("➕ Agregar Causa"):
                    st.session_state.prescripcion_list.append({
                        "rit": p_rit, "ruc": p_ruc, "tribunal": p_trib,
                        "fecha_sentencia": p_fecha_sent, "pena": p_pena,
                        "delito": p_delito, "fecha_suspension": p_fecha_susp
                    })
                    st.success("Causa agregada.")
            
            if st.session_state.prescripcion_list:
                st.write("**Causas en el escrito:**")
                for i, c in enumerate(st.session_state.prescripcion_list):
                    c1, c2 = st.columns([8, 1])
                    c1.caption(f"{i+1}. {c['delito']} (RIT {c['rit']})")
                    if c2.button("🗑️", key=f"del_pres_{i}"):
                        st.session_state.prescripcion_list.pop(i)
                        st.rerun()

        elif tipo_recurso == "Extinción Art. 25 ter":
            c_rpa, c_ad = st.columns(2)
            with c_rpa:
                st.markdown("#### A. Causa RPA")
                for i, rpa in enumerate(st.session_state.rpa):
                    with st.expander(f"Causa RPA {i+1}", expanded=True):
                        rpa['rit'] = st.text_input("RIT", rpa.get('rit',''), key=f"rrit{i}")
                        rpa['ruc'] = st.text_input("RUC", rpa.get('ruc',''), key=f"rruc{i}")
                        rpa['tribunal'] = st.selectbox("Tribunal", TRIBUNALES, key=f"rtrib{i}")
                        rpa['sancion'] = st.text_input("Sanción", rpa.get('sancion',''), key=f"rsanc{i}")
                        if st.button("🗑️ Quitar", key=f"del_rpa_{i}"):
                            st.session_state.rpa.pop(i)
                            st.rerun()
                if st.button("➕ Otra RPA"):
                    st.session_state.rpa.append({})
                    st.rerun()

            with c_ad:
                st.markdown("#### B. Condena Adulto")
                for i, ad in enumerate(st.session_state.adulto):
                    with st.expander(f"Condena Adulto {i+1}", expanded=True):
                        ad['rit'] = st.text_input("RIT", ad.get('rit',''), key=f"arit{i}")
                        ad['ruc'] = st.text_input("RUC", ad.get('ruc',''), key=f"aruc{i}")
                        ad['tribunal'] = st.selectbox("Tribunal", TRIBUNALES, key=f"atrib{i}")
                        ad['pena'] = st.text_input("Pena", ad.get('pena',''), key=f"apena{i}")
                        ad['fecha'] = st.text_input("Fecha", ad.get('fecha',''), key=f"afecha{i}")
                        if st.button("🗑️ Quitar", key=f"del_ad_{i}"):
                            st.session_state.adulto.pop(i)
                            st.rerun()
                if st.button("➕ Otra Adulto"):
                    st.session_state.adulto.append({})
                    st.rerun()

        elif tipo_recurso in ["Amparo Constitucional", "Apelación por Quebrantamiento"]:
            st.subheader("2. Fundamentos Específicos")
            argumento_extra = st.text_area("Antecedentes de Hecho Adicionales (Opcional)", height=150)
            st.session_state.argumento_extra = argumento_extra

        elif tipo_recurso == "Minuta Control de Detención":
            st.subheader("2. Detalles de la Detención")
            with st.form("form_minuta"):
                c1, c2 = st.columns(2)
                f_det = c1.text_input("Fecha/Hora Detención")
                l_det = c2.text_input("Lugar Detención")
                hechos_relato = st.text_area("Relato de Hechos (Fiscalía)", height=100)
                version_imp = st.text_area("Versión del Imputado", height=100)
                args_sel = st.multiselect("Argumentos Defensa", [
                    "Ilegalidad: Falta de indicios (Art 85 CPP)",
                    "Ilegalidad: Ausencia de Flagrancia (Art 83 CPP)",
                    "Ilegalidad: Lectura tardía de derechos",
                    "RPA: Falta de notificación a padres",
                    "RPA: Esposamiento Injustificado"
                ])
                gen_minuta = st.form_submit_button("Generar Vista Previa")
                if gen_minuta:
                    st.session_state.datos_minuta = {
                        "fecha": f_det, "lugar": l_det, "args": args_sel,
                        "hechos_relato": hechos_relato, "version_imputado": version_imp
                    }
            if "datos_minuta" in st.session_state:
                dm = st.session_state.datos_minuta
                st.markdown(f"""
                <div class='minuta-box'>
                <strong>MINUTA DE AUDIENCIA</strong><br>
                <strong>Hechos:</strong> {dm['fecha']} en {dm['lugar']}<br>
                <strong>Relato:</strong> {dm['hechos_relato']}<br>
                <strong>Versión Imputado:</strong> {dm['version_imputado']}<br>
                <hr>
                <strong>Alegaciones:</strong><br>
                { '<br>'.join(['- '+a for a in dm['args']]) }
                </div>
                """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        if st.button(f"🚀 GENERAR ESCRITO: {tipo_recurso}", type="primary", use_container_width=True):
            dm_safe = st.session_state.get('datos_minuta', {})
            datos_finales = {
                "tribunal_ej": st.session_state.tribunal_sel,
                "prescripcion_list": st.session_state.prescripcion_list,
                "rpa": st.session_state.rpa,
                "adulto": st.session_state.adulto,
                "ejecucion": st.session_state.ejecucion,
                "lista_individualizacion": st.session_state.lista_individualizacion,
                "argumento_extra": st.session_state.get('argumento_extra', ''),
                "fecha_det": dm_safe.get('fecha', ''),
                "lugar_det": dm_safe.get('lugar', ''),
                "argumentos_det": dm_safe.get('args', []),
                "hechos_relato": dm_safe.get('hechos_relato', ''),
                "version_imputado": dm_safe.get('version_imputado', '')
            }
            gen = GeneradorWord(st.session_state.defensor_nombre, st.session_state.imputado)
            buffer = gen.generar(tipo_recurso, datos_finales)
            st.success("Documento Generado Exitosamente")
            st.download_button("📥 Descargar DOCX", buffer, f"{tipo_recurso}.docx", 
                             "application/vnd.openxmlformats-officedocument.wordprocessingml.document", 
                             use_container_width=True)

    # === TAB 2: ANALISTA MULTIMODAL (MERGED FUNCTIONS) ===
    with tabs[1]:
        st.header("🕵️ Analista Jurídico Multimodal (Vision & Strategy)")
        st.info("Sube Carpetas Investigativas, Partes Policiales Escaneados, Fotos de Evidencia o Textos.")

        # MERGED: Se unió Teoría del Caso con Salidas Alternativas
        objetivo_analisis = st.radio(
            "¿Qué buscas en estos documentos?",
            ["📄 Control de Detención (Busca ilegalidades)", 
             "⚖️ Estrategia Integral (Teoría del Caso, Salidas & Prognosis)"],
            horizontal=True
        )

        archivos_evidencia = st.file_uploader(
            "Cargar Evidencia (PDF, JPG, PNG, TXT)", 
            type=["pdf", "jpg", "png", "txt", "jpeg"], 
            accept_multiple_files=True
        )

        contexto_usuario = st.text_area("Contexto adicional (Ej: 'El cliente dice que Carabineros mintió...')")

        if archivos_evidencia and st.button("⚡ ANALIZAR EVIDENCIA CON IA"):
            status_box = st.empty()
            with st.spinner("Procesando evidencia multimodal (Vision IA)..."):
                try:
                    # CAMBIO 3: Instancia local del modelo analista
                    model_analista = get_generative_model_dinamico()
                    docs_para_gemini = []
                    
                    for archivo in archivos_evidencia:
                        status_box.info(f"Subiendo a Gemini Vision: {archivo.name}...")
                        
                        suffix = f".{archivo.name.split('.')[-1]}"
                        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                            tmp.write(archivo.getvalue())
                            tmp_path = tmp.name

                        f_gemini = genai.upload_file(tmp_path)
                        while f_gemini.state.name == "PROCESSING":
                            time.sleep(1)
                            f_gemini = genai.get_file(f_gemini.name)
                            
                        docs_para_gemini.append(f_gemini)
                        os.remove(tmp_path)

                    status_box.info("🧠 Generando estrategia jurídica integral...")

                    if "Control de Detención" in objetivo_analisis:
                        system_prompt = """
                        Eres un Abogado Penalista experto en Garantías. Analiza la evidencia visual y textual adjunta (Partes, Actas).
                        TU MISIÓN: Detectar vicios de legalidad para un Control de Detención.
                        
                        BUSCA ESPECÍFICAMENTE:
                        1. Indicios del Art. 85 CPP: ¿Son objetivos o subjetivos?
                        2. Flagrancia (Art. 130 CPP): Tiempos, visualización.
                        3. Lectura de Derechos: ¿Consta en actas? ¿Hora?
                        4. Uso de la fuerza / Constatación de lesiones.
                        
                        SALIDA: Lista de ilegalidades con probabilidad de éxito y argumentos.
                        """
                    else:
                        # PROMPT COMBINADO (Teoría del Caso + Salidas Alternativas)
                        system_prompt = """
                        Eres un Estratega de Defensa Penal y Experto en Ejecución. Analiza toda la evidencia adjunta.
                        TU MISIÓN: Construir una Estrategia de Defensa Integral.
                        
                        DEBES ANALIZAR Y RESPONDER ESTOS 3 BLOQUES:
                        
                        BLOQUE 1: TEORÍA DEL CASO Y PROGNOSIS
                        - Debilidades de la prueba de cargo (Fiscalía).
                        - Coartadas posibles derivadas de la evidencia visual/documental.
                        - Prognosis de Pena: Calcula pena probable según el delito y atenuantes visibles.
                        - ¿Recomiendas ir a Juicio o Negociar?
                        
                        BLOQUE 2: SALIDAS ALTERNATIVAS (TÉRMINOS ANTICIPADOS)
                        - Suspensión Condicional (Art. 237 CPP): ¿Es viable? (Pena probable < 3 años).
                        - Acuerdo Reparatorio (Art. 241 CPP): ¿Hay bienes jurídicos disponibles?
                        - Procedimiento Abreviado: Requisitos y conveniencia estratégica.
                        
                        BLOQUE 3: CUMPLIMIENTO (LEY 18.216)
                        - Si es condenado, ¿a qué pena sustitutiva podría optar? (Remisión, Libertad Vigilada, etc).
                        """

                    prompt_final = [system_prompt, f"Contexto adicional: {contexto_usuario}"]
                    prompt_final.extend(docs_para_gemini)

                    # Usamos la instancia local
                    response = model_analista.generate_content(prompt_final)
                    
                    status_box.success("✅ Análisis Completado")
                    
                    st.markdown("---")
                    st.markdown(response.text)
                    st.download_button("📥 Descargar Informe", response.text, "Analisis_Integral_Legal.txt")

                except Exception as e:
                    st.error(f"Error en el análisis multimodal: {e}")

    # === TAB 3: TRANSCRIPTOR ===
    with tabs[2]:
        st.header("🎙️ Transcriptor Forense & Generador de Recursos")
        st.info("Sube el audio de la audiencia (MP3, WAV, M4A) para obtener la transcripción literal y un borrador de recurso inteligente.")

        uploaded_audio = st.file_uploader("Cargar Audio de Audiencia", type=["mp3", "wav", "m4a", "ogg"])

        if uploaded_audio is not None:
            if st.button("🚀 PROCESAR AUDIO (AUTO-DETECTAR MODELO)"):
                status_container = st.empty()
                
                with st.spinner("🔄 Auto-detectando modelo y procesando..."):
                    try:
                        modelos_disponibles = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
                        
                        modelo_a_usar = None
                        for m in modelos_disponibles:
                            if 'gemini-1.5-flash' in m:
                                modelo_a_usar = m
                                break
                        
                        if not modelo_a_usar:
                            for m in modelos_disponibles:
                                if 'gemini-1.5-pro' in m:
                                    modelo_a_usar = m
                                    break
                        
                        if not modelo_a_usar:
                            modelo_a_usar = next((m for m in modelos_disponibles if '1.5' in m), 'models/gemini-1.5-flash')

                        status_container.info(f"🤖 Modelo detectado y seleccionado: {modelo_a_usar}")

                        suffix = f".{uploaded_audio.name.split('.')[-1]}"
                        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_file:
                            tmp_file.write(uploaded_audio.getvalue())
                            tmp_path = tmp_file.name

                        archivo_gemini = genai.upload_file(tmp_path, mime_type="audio/mp3")

                        status_container.info("⏳ Esperando procesamiento de Google...")
                        while archivo_gemini.state.name == "PROCESSING":
                            time.sleep(2)
                            archivo_gemini = genai.get_file(archivo_gemini.name)

                        if archivo_gemini.state.name == "FAILED":
                            raise ValueError("Google falló al procesar el audio.")

                        status_container.info("📝 Redactando recurso...")
                        
                        model_transcriptor = genai.GenerativeModel(modelo_a_usar)

                        prompt_transcripcion = """
                        Actúa como un Estenógrafo Judicial y Abogado Penalista.
                        TAREA 1: Transcribe LITERALMENTE el audio (Juez, Fiscal, Defensa).
                        TAREA 2: Redacta un BORRADOR DE RECURSO (Apelación o Amparo) detectando los vicios en el audio.
                        Estructura: Resolución Impugnada, Argumentos Defensa, Agravio, Petitorio.
                        """

                        response = model_transcriptor.generate_content([prompt_transcripcion, archivo_gemini])
                        texto_generado = response.text

                        status_container.success("✅ ¡Listo!")
                        st.subheader(f"📄 Resultado (Usando {modelo_a_usar})")
                        st.markdown(texto_generado)

                        st.download_button("📥 Descargar", texto_generado, "Recurso_Audiencia.txt")

                    except Exception as e:
                        st.error(f"Error: {e}")
                    finally:
                        if 'tmp_path' in locals() and os.path.exists(tmp_path):
                            os.remove(tmp_path)
        else:
            st.warning("Por favor, carga un archivo de audio para comenzar.")

    # === TAB 4: BIBLIOTECA INTELIGENTE (ACTUALIZADO: BÚSQUEDA DINÁMICA) ===
    with tabs[3]:
        st.header("📚 Biblioteca Jurídica Inteligente")
        
        modo_biblio = st.radio("Herramienta", ["🔍 Buscador de Jurisprudencia", "📄 Analizar mi Escrito"], horizontal=True)
        
        if modo_biblio == "🔍 Buscador de Jurisprudencia":
            st.info("Busca conceptualmente en la base de datos de fallos y leyes.")
            query_busqueda = st.text_input("¿Qué tema jurídico necesitas investigar?", placeholder="Ej: Nulidad por entrada y registro sin orden...")
            
            if query_busqueda and st.button("Buscar Fallos"):
                with st.spinner("Buscando en cerebro legal..."):
                    try:
                        # USO DE DETECCIÓN AUTOMÁTICA DE MODELO
                        modelo_dinamico = get_embedding_model()
                        emb_resp = genai.embed_content(
                            model=modelo_dinamico,
                            content=query_busqueda,
                            task_type="retrieval_query"
                        )
                        vector_consulta = emb_resp['embedding']
                        
                        if vector_consulta:
                            # 2. Traer documentos (Simulación de búsqueda vectorial si no hay RPC configurada)
                            res = supabase.table("documentos_legales").select("*").limit(50).execute()
                            
                            if res.data:
                                import numpy as np
                                resultados = []
                                for doc in res.data:
                                    vec_doc = doc.get('embedding')
                                    if vec_doc:
                                        # Cálculo similitud coseno simple
                                        sim = np.dot(vector_consulta, vec_doc) / (np.linalg.norm(vector_consulta) * np.linalg.norm(vec_doc))
                                        resultados.append((sim, doc))
                                
                                # Ordenar por similitud
                                resultados.sort(key=lambda x: x[0], reverse=True)
                                
                                st.subheader("Resultados Relevantes:")
                                for sim, doc in resultados[:5]: # Top 5
                                    meta = doc['metadata']
                                    with st.expander(f"⚖️ {meta.get('tribunal','Tribunal')} - Rol: {meta.get('rol','S/N')} ({int(sim*100)}% Coincidencia)"):
                                        st.caption(f"Tema: {meta.get('tema','General')} | Tipo: {meta.get('tipo_doc','Documento')}")
                                        st.markdown(f"**Resultado:** {meta.get('resultado', '')}")
                                        st.write(doc['contenido'][:500] + "...")
                                        st.button("Copiar Cita", key=f"btn_{doc['id']}")
                            else:
                                st.warning("No hay documentos en la base de datos aún.")
                        else:
                            st.error("No se pudo generar el vector de búsqueda.")

                    except Exception as e:
                        st.error(f"Error en búsqueda: {e}")

        else: # Analizar mi Escrito
            st.info("Sube tu borrador. La IA extraerá conceptos y buscará jurisprudencia de apoyo.")
            borrador = st.file_uploader("Sube tu borrador (PDF/Word/Txt)", type=["pdf","docx","txt"])
            
            if borrador and st.button("Analizar y Buscar Apoyo"):
                st.success("Funcionalidad en desarrollo: Conectará tu borrador con la búsqueda vectorial mostrada arriba.")

    # === TAB 5: ADMIN & CARGA (GESTIÓN USUARIOS + INGESTA DINÁMICA + OCR) ===
    with tabs[4]:
        if st.session_state.user_role == "Admin":
            st.header("⚙️ Cerebro Centralizado & Gestión (Admin)")
            
            # Sub-tabs para organizar mejor la vista de Admin
            tab_ingesta, tab_usuarios = st.tabs(["📂 Ingesta Documental", "👥 Gestión de Usuarios"])
            
            # --- SUB-TAB A: INGESTA ---
            with tab_ingesta:
                st.info("Alimenta el sistema con Leyes y Jurisprudencia. Proceso inteligente con IA.")
                col_subida, col_consulta = st.columns([2, 1])

                with col_subida:
                    st.subheader("1. Ingesta Inteligente de Documentos")
                    
                    archivos_pdf = st.file_uploader(
                        "Subir Archivos (PDF) - Máx 10", 
                        type="pdf", 
                        accept_multiple_files=True,
                        key="pdf_rag_multi"
                    )

                    if archivos_pdf:
                        if len(archivos_pdf) > 10:
                            st.error("⚠️ Por estabilidad y seguridad, sube máximo 10 archivos a la vez.")
                            st.stop()

                        if st.button("💾 Procesar y Guardar en Memoria"):
                            progress_bar_general = st.progress(0)
                            total_files = len(archivos_pdf)
                            
                            # Obtener modelo dinámico UNA vez al inicio del lote para embeddings
                            modelo_dinamico = get_embedding_model()
                            st.write(f"Usando modelo de embedding: {modelo_dinamico}")
                            
                            for idx_file, archivo_pdf in enumerate(archivos_pdf):
                                with st.status(f"Procesando {archivo_pdf.name}...", expanded=False) as status:
                                    try:
                                        status.write("Leyendo documento completo...")
                                        reader = PyPDF2.PdfReader(archivo_pdf)
                                        texto_completo = ""
                                        for page in reader.pages:
                                            texto_completo += page.extract_text() or ""
                                        
                                        # CAMBIO 4: OCR HÍBRIDO (Si hay poco texto, usamos Vision)
                                        if len(texto_completo) < 50:
                                            status.write("⚠️ Texto insuficiente, activando OCR con IA Vision...")
                                            st.toast(f"Activando OCR para {archivo_pdf.name}")
                                            
                                            # 1. Guardar temporal y subir a Gemini
                                            suffix = f".{archivo_pdf.name.split('.')[-1]}"
                                            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                                                tmp.write(archivo_pdf.getvalue())
                                                tmp_path = tmp.name
                                            
                                            f_gemini = genai.upload_file(tmp_path)
                                            while f_gemini.state.name == "PROCESSING": 
                                                time.sleep(1)
                                                f_gemini = genai.get_file(f_gemini.name)
                                            
                                            # 2. Pedir Metadata y Texto a la vez
                                            model_ocr = get_generative_model_dinamico()
                                            prompt_ocr = """
                                            Analiza este documento legal escaneado.
                                            1. Extrae el TEXTO COMPLETO (transcripción literal).
                                            2. Genera un JSON con metadata: tribunal, rol, fecha_sentencia, resultado, tema, tipo.
                                            FORMATO RESPUESTA:
                                            ---JSON---
                                            {json_aqui}
                                            ---TEXTO---
                                            (texto_aqui)
                                            """
                                            resp_ocr = model_ocr.generate_content([prompt_ocr, f_gemini])
                                            
                                            # 3. Parsear respuesta (separar JSON de Texto) para poder guardar
                                            parts = resp_ocr.text.split("---TEXTO---")
                                            json_part = parts[0].replace("---JSON---", "").replace("```json", "").replace("```", "").strip()
                                            texto_completo = parts[1].strip() if len(parts) > 1 else ""
                                            try:
                                                metadata_ia = json.loads(json_part)
                                            except:
                                                metadata_ia = {"rol": "Error OCR", "tribunal": "Desconocido"}
                                            
                                            os.remove(tmp_path) # Limpieza

                                        else:
                                            # Flujo normal para PDF digital
                                            status.write("Analizando metadata jurídica con IA...")
                                            metadata_ia = analizar_metadata_profunda(texto_completo)
                                        
                                        # Agregar origen
                                        metadata_ia["origen"] = archivo_pdf.name
                                        status.write(f"Metadata detectada: {metadata_ia.get('rol')} - {metadata_ia.get('tribunal')}")

                                        status.write("Fragmentando texto...")
                                        chunk_size = 1500 
                                        chunks = [texto_completo[i:i+chunk_size] for i in range(0, len(texto_completo), chunk_size)]
                                        
                                        status.write("Generando vectores y guardando...")
                                        for i, chunk in enumerate(chunks):
                                            # USO DE MODELO DINÁMICO
                                            emb_resp = genai.embed_content(
                                                model=modelo_dinamico,
                                                content=chunk,
                                                task_type="retrieval_document"
                                            )
                                            vector = emb_resp['embedding']

                                            if vector:
                                                data_insert = {
                                                    "contenido": chunk,
                                                    "metadata": metadata_ia,
                                                    "embedding": vector
                                                }
                                                supabase.table("documentos_legales").insert(data_insert).execute()
                                        
                                        status.update(label=f"✅ {archivo_pdf.name} Procesado Exitosamente", state="complete")
                                        st.toast(f"✅ Guardado: {metadata_ia.get('rol')} - {metadata_ia.get('tribunal')}")

                                    except Exception as e:
                                        status.update(label=f"❌ Error en {archivo_pdf.name}: {str(e)}", state="error")
                                        st.error(f"Detalle error: {e}")
                                
                                progress_bar_general.progress((idx_file + 1) / total_files)

                            st.success("🏁 Proceso de ingesta finalizado.")
                            time.sleep(2)
                            st.rerun()

                with col_consulta:
                    st.subheader("2. Inventario Documental")
                    try:
                        res = supabase.table("documentos_legales").select("metadata, id").limit(15).execute()
                        if res.data:
                            tabla_fallos = []
                            seen_rols = set()
                            for d in res.data:
                                meta = d['metadata']
                                rol = meta.get('rol', 'S/N')
                                if rol not in seen_rols:
                                    tabla_fallos.append({
                                        "Tipo": meta.get('tipo', 'N/A'),
                                        "Rol": rol,
                                        "Tribunal": meta.get('tribunal', ''),
                                        "Resultado": meta.get('resultado', '-')
                                    })
                                    seen_rols.add(rol)
                            st.dataframe(tabla_fallos, use_container_width=True)
                        else:
                            st.info("Base de datos vacía.")
                    except Exception as e:
                        st.error(f"Error conexión: {e}")
            
            # --- SUB-TAB B: USUARIOS ---
            with tab_usuarios:
                st.subheader("👥 Gestión de Usuarios del Sistema")
                
                c_lista, c_crear = st.columns([2, 1])
                
                with c_lista:
                    st.markdown("##### Usuarios Registrados")
                    try:
                        # Consultar la tabla 'profiles'
                        users_data = supabase.table("profiles").select("*").execute()
                        if users_data.data:
                            # Prepara datos para mostrar
                            clean_users = []
                            for u in users_data.data:
                                clean_users.append({
                                    "Nombre": u.get('nombre', 'Sin Nombre'),
                                    "Rol": u.get('rol', 'User'),
                                    "Fecha Registro": u.get('created_at', '')[:10]
                                })
                            st.dataframe(clean_users, use_container_width=True)
                        else:
                            st.info("No se encontraron perfiles de usuario.")
                    except Exception as e:
                        st.error(f"Error al cargar usuarios: {e}")

                with c_crear:
                    st.markdown("##### Registrar Nuevo Funcionario")
                    with st.form("admin_create_user"):
                        new_u_email = st.text_input("Correo Institucional")
                        new_u_pass = st.text_input("Contraseña Temporal", type="password")
                        new_u_name = st.text_input("Nombre Funcionario")
                        new_u_role = st.selectbox("Rol Asignado", ["User", "Admin"])
                        
                        btn_crear = st.form_submit_button("Crear Usuario")
                        
                        if btn_crear:
                            try:
                                # Nota: sign_up loguea al usuario automáticamente en el cliente.
                                # Como esto es una herramienta admin simple, advertimos o usamos una función administrativa si estuviera disponible.
                                # Aquí usamos el sign_up estándar pero guardamos el rol en profiles vía trigger o manual.
                                
                                # 1. Crear Auth User
                                res = supabase.auth.sign_up({
                                    "email": new_u_email,
                                    "password": new_u_pass,
                                    "options": {
                                        "data": {
                                            "nombre": new_u_name,
                                            # Pasamos el rol en metadata para que el Trigger lo capture si está configurado,
                                            # o para referencia futura.
                                            "rol_solicitado": new_u_role 
                                        }
                                    }
                                })
                                
                                if res.user:
                                    # 2. Forzar actualización del Rol en la tabla profiles (si el trigger no lo hizo con el rol correcto)
                                    # El trigger suele poner "User" por defecto. El admin lo promueve aquí.
                                    time.sleep(1) # Esperar a que el trigger cree el profile
                                    supabase.table("profiles").update({"rol": new_u_role}).eq("id", res.user.id).execute()
                                    
                                    st.success(f"Usuario {new_u_name} creado correctamente.")
                                    st.warning("⚠️ Nota: Es posible que debas volver a iniciar sesión si el sistema te cambió de cuenta automáticamente.")
                                else:
                                    st.error("No se pudo crear el usuario. Verifique el correo.")
                                    
                            except Exception as e:
                                st.error(f"Error creando usuario: {e}")

        else:
            st.warning("🔒 Acceso restringido a Administradores.")
            st.info("Debes iniciar sesión con una cuenta autorizada.")

if __name__ == "__main__":
    if st.session_state.logged_in:
        main_app()
    else:
        login_screen()
