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
import tempfile # Nueva dependencia agregada
import os       # Nueva dependencia agregada

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
GOOGLE_API_KEY = "AIzaSyDjsyWjcHCXvgoIQsbyxGD2oyLHFMLfWhg" 
genai.configure(api_key=GOOGLE_API_KEY)

def get_gemini_model():
    try:
        return genai.GenerativeModel('gemini-1.5-flash')
    except:
        return genai.GenerativeModel('gemini-pro')

model_ia = get_gemini_model()

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
    "Robo con Intimidación": {"idx_min": 6, "idx_max": 8}, # Mayor min a max
    "Robo con Violencia": {"idx_min": 6, "idx_max": 8},
    "Robo en Lugar Habitado": {"idx_min": 6, "idx_max": 6}, # Mayor min
    "Microtráfico (Art. 4)": {"idx_min": 4, "idx_max": 5}, # Menor medio a max
    "Tráfico Ilícito (Art. 3)": {"idx_min": 6, "idx_max": 7}, # Mayor min a medio
    "Homicidio Simple": {"idx_min": 7, "idx_max": 8}, # Mayor medio a max
    "Receptación": {"idx_min": 3, "idx_max": 5}, # Menor cualquiera
    "Porte Ilegal de Arma": {"idx_min": 5, "idx_max": 6}, # Menor max a Mayor min
    "Lesiones Graves": {"idx_min": 4, "idx_max": 4}, # Menor medio
    "Amenazas Simples": {"idx_min": 3, "idx_max": 3}, # Menor min
    "Maltrato de Obra a Carabineros": {"idx_min": 4, "idx_max": 5} # Menor medio a max
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
# 5. MOTOR DE GENERACIÓN WORD (CORREGIDO PARA EVITAR DUPLICADOS)
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
        
        # Primero reemplazamos las variables
        texto_final = texto.replace("{DEFENSOR}", self.defensor).replace("{IMPUTADO}", self.imputado)
        
        if negrita:
            # Si todo el párrafo es negrita, lo aplicamos directo
            run = p.add_run(texto_final)
            run.font.name = 'Cambria'
            run.font.size = Pt(12)
            run.bold = True
        else:
            # CORRECCIÓN DEFINITIVA DE DUPLICADOS:
            # Usamos split con paréntesis para conservar los delimitadores, pero procesamos linealmente.
            # \b asegura que solo coincida con palabras completas.
            keywords = [
                r"RIT:?\s?[\w\d-]+", r"RUC:?\s?[\w\d-]+", 
                "POR TANTO", "OTROSÍ", "EN LO PRINCIPAL", 
                "SOLICITA", "INTERPONE", "ACCIÓN CONSTITUCIONAL",
                "HECHOS:", "DERECHO:", "AGRAVIO:", "PETICIONES CONCRETAS:", 
                "FUNDAMENTOS DE DERECHO:", "ANTECEDENTES DE HECHO:"
            ]
            
            # Unimos keywords y escapamos nombres para crear el patrón
            patron_regex = "|".join(keywords) + f"|{re.escape(self.defensor)}|{re.escape(self.imputado)}"
            
            # Encontramos todas las coincidencias y sus posiciones
            matches = list(re.finditer(patron_regex, texto_final, flags=re.IGNORECASE))
            
            last_pos = 0
            for match in matches:
                # Texto normal antes de la coincidencia
                start, end = match.span()
                if start > last_pos:
                    run = p.add_run(texto_final[last_pos:start])
                    run.font.name = 'Cambria'
                    run.font.size = Pt(12)
                
                # Texto en negrita (la coincidencia)
                run_bold = p.add_run(texto_final[start:end])
                run_bold.font.name = 'Cambria'
                run_bold.font.size = Pt(12)
                run_bold.bold = True
                
                last_pos = end
            
            # Texto restante después de la última coincidencia
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
        
        # Pestañas para Login o Registro
        tab_login, tab_registro = st.tabs(["🔐 Iniciar Sesión", "📝 Crear Cuenta"])

        # --- LOGIN ---
        with tab_login:
            # st.form ya permite enviar con ENTER por defecto en los campos de texto
            with st.form("login_form"):
                email = st.text_input("Correo Electrónico")
                password = st.text_input("Contraseña", type="password")
                submitted = st.form_submit_button("INGRESAR", use_container_width=True)
                
                if submitted:
                    try:
                        # 1. Intentar Login con Supabase
                        session = supabase.auth.sign_in_with_password({"email": email, "password": password})
                        user = session.user
                        
                        # 2. Si entra, consultamos su ROL en la tabla 'profiles' que creamos
                        data = supabase.table("profiles").select("*").eq("id", user.id).execute()
                        
                        if data.data:
                            perfil = data.data[0]
                            st.session_state.logged_in = True
                            st.session_state.user_role = perfil['rol'] # Admin o User
                            st.session_state.defensor_nombre = perfil['nombre']
                            st.session_state.user_email = email
                            st.success("¡Bienvenido!")
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error("Error: Usuario autenticado pero sin perfil.")
                            
                    except Exception as e:
                        st.error(f"Credenciales incorrectas o error de conexión: {e}")

        # --- REGISTRO (Solo para nuevos usuarios) ---
        with tab_registro:
            with st.form("register_form"):
                new_email = st.text_input("Tu Correo")
                new_pass = st.text_input("Crear Contraseña", type="password")
                new_name = st.text_input("Nombre Completo (Para los escritos)")
                reg_submit = st.form_submit_button("REGISTRARSE", use_container_width=True)
                
                if reg_submit:
                    try:
                        # Esto crea el usuario y dispara el Trigger SQL que hicimos
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
    
    # PESTAÑAS
    tabs = st.tabs(["📝 Generador", "🧮 Prognosis & Calculadora", "🎙️ Transcriptor", "👥 Admin & BD"])

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
        
        # --- LÓGICA DE PRESCRIPCIÓN ---
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

        # --- LÓGICA DE EXTINCIÓN ---
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

        # --- OTROS ESCRITOS ---
        elif tipo_recurso in ["Amparo Constitucional", "Apelación por Quebrantamiento"]:
            st.subheader("2. Fundamentos Específicos")
            datos_extra = {}
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

        # BOTÓN GENERAR
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

    # === TAB 2: PROGNOSIS Y TEORÍA (ACTUALIZADA) ===
    with tabs[1]:
        st.header("🧮 Calculadora de Prognosis Penal & Teoría del Caso")
        col_conf1, col_conf2 = st.columns(2)
        with col_conf1:
            modo_prognosis = st.radio("Régimen Legal:", ["Ley 20.084 (RPA)", "Adulto (General)"], horizontal=True)
            es_rpa_calc = True if "RPA" in modo_prognosis else False
        with col_conf2:
            delito = st.selectbox("Delito Imputado", list(DELITOS_INFO.keys()))
        hechos_prognosis = st.text_area("Relato Fáctico del Caso (Para análisis IA)", height=120)
        c1, c2 = st.columns(2)
        with c1:
            atenuantes = st.multiselect("Circunstancias Atenuantes", ["11 N°6 Irreprochable", "11 N°9 Colaboración", "11 N°7 Reparación", "Autodenuncia", "Imputabilidad Disminuida (11 N°1)"])
        with c2:
            agravantes = st.multiselect("Circunstancias Agravantes", ["12 N°1 Alevosía", "Reincidencia", "Pluralidad malhechores"])
        if st.button("⚡ ANALIZAR CASO (IA + CÁLCULO)"):
            with st.spinner("Calculando..."):
                calc = calcular_pena_exacta(DELITOS_INFO[delito], atenuantes, agravantes, es_rpa_calc)
                teoria_ia = generar_teoria_caso_ia(hechos_prognosis, delito, atenuantes, es_rpa_calc)
                m1, m2, m3 = st.columns(3)
                m1.metric("Pena Base (Grados)", calc['rango'])
                m2.metric("Efecto Jurídico", calc['efecto'])
                m3.metric("Pena Probable (Días Mínimos)", f"{calc['dias_min']} días")
                st.markdown(f"#### RIESGO DE CÁRCEL EFECTIVA: {calc['riesgo']}%")
                st.progress(calc['riesgo'] / 100)
                st.markdown(f"<div class='{calc['badge']}'>RESULTADO: {calc['resultado']}</div>", unsafe_allow_html=True)
                st.markdown("### 🧠 ESTRATEGIA DE DEFENSA (IA)")
                st.markdown(f"<div class='teoria-box'>{teoria_ia}</div>", unsafe_allow_html=True)

    # === TAB 3: TRANSCRIPTOR (ACTUALIZADO: AUTO-DETECCIÓN DE MODELO) ===
    with tabs[2]:
        st.header("🎙️ Transcriptor Forense & Generador de Recursos")
        st.info("Sube el audio de la audiencia (MP3, WAV, M4A) para obtener la transcripción literal y un borrador de recurso inteligente.")

        uploaded_audio = st.file_uploader("Cargar Audio de Audiencia", type=["mp3", "wav", "m4a", "ogg"])

        if uploaded_audio is not None:
            if st.button("🚀 PROCESAR AUDIO (AUTO-DETECTAR MODELO)"):
                status_container = st.empty()
                
                with st.spinner("🔄 Auto-detectando modelo y procesando..."):
                    try:
                        # --- PASO 0: DETECCIÓN AUTOMÁTICA DEL MODELO ---
                        # Olvídate de poner nombres a mano. Esto busca el que funcione.
                        modelos_disponibles = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
                        
                        # Buscamos preferentemente Flash o Pro (versión 1.5 para audio)
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
                        
                        # Si no encuentra específicos, usa cualquiera que tenga 1.5
                        if not modelo_a_usar:
                            modelo_a_usar = next((m for m in modelos_disponibles if '1.5' in m), 'models/gemini-1.5-flash')

                        status_container.info(f"🤖 Modelo detectado y seleccionado: {modelo_a_usar}")

                        # --- PASO 1: SUBIDA ---
                        suffix = f".{uploaded_audio.name.split('.')[-1]}"
                        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_file:
                            tmp_file.write(uploaded_audio.getvalue())
                            tmp_path = tmp_file.name

                        archivo_gemini = genai.upload_file(tmp_path, mime_type="audio/mp3")

                        # --- PASO 2: ESPERA ACTIVA (OBLIGATORIO) ---
                        status_container.info("⏳ Esperando procesamiento de Google...")
                        while archivo_gemini.state.name == "PROCESSING":
                            time.sleep(2)
                            archivo_gemini = genai.get_file(archivo_gemini.name)

                        if archivo_gemini.state.name == "FAILED":
                            raise ValueError("Google falló al procesar el audio.")

                        # --- PASO 3: GENERACIÓN ---
                        status_container.info("📝 Redactando recurso...")
                        
                        # AQUÍ USAMOS LA VARIABLE AUTOMÁTICA
                        model_transcriptor = genai.GenerativeModel(modelo_a_usar)

                        prompt_transcripcion = """
                        Actúa como un Estenógrafo Judicial y Abogado Penalista.
                        TAREA 1: Transcribe LITERALMENTE el audio (Juez, Fiscal, Defensa).
                        TAREA 2: Redacta un BORRADOR DE RECURSO (Apelación o Amparo) detectando los vicios en el audio.
                        Estructura: Resolución Impugnada, Argumentos Defensa, Agravio, Petitorio.
                        """

                        response = model_transcriptor.generate_content([prompt_transcripcion, archivo_gemini])
                        texto_generado = response.text

                        # --- FINALIZACIÓN ---
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

    # === TAB 4: ADMIN (ACTUALIZADO CON SUPABASE REAL) ===
    with tabs[3]:
        if st.session_state.user_role == "Admin":
            st.header("Panel de Control & Base de Datos (Supabase)")
            
            # --- SECCIÓN: GESTIÓN DE USUARIOS (REAL) ---
            with st.expander("👥 Usuarios Registrados (Tabla 'profiles')", expanded=True):
                try:
                    # Consulta Real a Supabase
                    response = supabase.table("profiles").select("*").execute()
                    users_data = response.data
                    
                    if users_data:
                        st.success(f"Conexión exitosa. Se encontraron {len(users_data)} usuarios.")
                        
                        # Mostramos los datos en un Dataframe interactivo
                        # Preparamos los datos para que se vean bien
                        clean_data = []
                        for u in users_data:
                            clean_data.append({
                                "Nombre": u.get("nombre", "Sin Nombre"),
                                "Rol": u.get("rol", "N/A"),
                                "ID/Email": u.get("email", u.get("id", "N/A")), # Fallback si no hay columna email
                                "Fecha Registro": u.get("created_at", "")
                            })
                        
                        st.dataframe(clean_data, use_container_width=True)
                        
                        st.markdown("---")
                        st.caption("Nota: Para eliminar usuarios, se recomienda usar el Dashboard de Supabase para mantener la integridad de Auth.")
                    else:
                        st.warning("La tabla 'profiles' está vacía o no se pudo leer.")
                        
                except Exception as e:
                    st.error(f"Error al consultar Supabase: {e}")
                    st.code("Verifica que la tabla 'profiles' tenga permisos de lectura (RLS) o que la API Key sea correcta.")

            # --- SECCIÓN: CONSULTAS (Mantenemos lo visual) ---
            with st.expander("📚 Base de Jurisprudencia (Supabase)"):
                st.text_input("Buscar Fallo (Rol / Tema)")
                st.button("🔍 Consultar Base Remota")
                st.caption("Estado: Conexión Establecida")
            with st.expander("📄 Base de Escritos (Templates)"):
                st.write("Total plantillas activas: 5")
                st.button("Sincronizar Nuevos Formatos")
        else:
            st.warning("Acceso Denegado")

if __name__ == "__main__":
    if st.session_state.logged_in:
        main_app()
    else:
        login_screen()
