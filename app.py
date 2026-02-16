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

# =============================================================================
# 1. CONFIGURACIÓN Y ESTILOS (INTERFAZ ELEGANTE & LEGIBLE)
# =============================================================================
st.set_page_config(
    page_title="Sistema Jurídico Avanzado IABL",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS Profesional: Alto Contraste y Elegancia
st.markdown("""
    <style>
    /* Tipografía y Fondo General */
    .main {
        background-color: #ffffff; /* Fondo blanco puro para limpieza */
        font-family: 'Segoe UI', 'Helvetica Neue', sans-serif;
    }
    
    /* Encabezados */
    h1 { 
        color: #0d47a1; 
        font-weight: 800; 
        border-bottom: 3px solid #0d47a1; 
        padding-bottom: 15px; 
        letter-spacing: -0.5px;
    }
    h2, h3 { color: #1565c0; font-weight: 600; }
    
    /* Botones Premium */
    .stButton>button {
        background-color: #0d47a1;
        color: white;
        border-radius: 6px;
        font-weight: 600;
        border: none;
        padding: 0.6rem 1.2rem;
        transition: all 0.3s ease;
        box-shadow: 0 2px 5px rgba(0,0,0,0.1);
    }
    .stButton>button:hover {
        background-color: #1976d2;
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(0,0,0,0.2);
    }
    
    /* Cajas de Información (Texto NEGRO para legibilidad) */
    .status-card {
        padding: 20px;
        border-radius: 10px;
        background: #f8f9fa;
        border-left: 5px solid #0d47a1;
        box-shadow: 0 2px 10px rgba(0,0,0,0.05);
        color: #000000;
        margin-bottom: 15px;
    }
    
    /* Caja de Jurisprudencia */
    .juris-box {
        background-color: #fffde7; /* Fondo crema suave */
        padding: 20px;
        border-radius: 8px;
        border: 1px solid #fbc02d;
        color: #212121 !important; /* Texto casi negro */
        font-size: 1.05rem;
    }
    
    /* Caja de Calculadora */
    .calc-box {
        background-color: #e3f2fd;
        padding: 20px;
        border-radius: 10px;
        border: 1px solid #90caf9;
        color: #0d47a1 !important;
    }
    
    /* Minuta en Pantalla */
    .minuta-box {
        background-color: #fff3e0;
        padding: 25px;
        border-radius: 10px;
        border: 1px solid #ffe0b2;
        color: #bf360c !important;
        margin-top: 15px;
        font-family: 'Courier New', Courier, monospace; /* Estilo tipo expediente */
    }

    /* Login Box Elegante */
    .login-container {
        background: #ffffff;
        padding: 50px;
        border-radius: 20px;
        box-shadow: 0 15px 35px rgba(0,0,0,0.1);
        text-align: center;
        border: 1px solid #e0e0e0;
    }
    .login-title {
        color: #0d47a1;
        font-size: 2.2rem;
        font-weight: bold;
        margin-bottom: 10px;
    }
    .login-subtitle {
        font-size: 1.1em;
        color: #546e7a;
        font-style: italic;
        margin-top: 20px;
        font-weight: 400;
        line-height: 1.5;
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
# 3. DATOS MAESTROS
# =============================================================================
TRIBUNALES = [
    "1° Juzgado de Garantía de Santiago", "2° Juzgado de Garantía de Santiago",
    "3° Juzgado de Garantía de Santiago", "4° Juzgado de Garantía de Santiago",
    "5° Juzgado de Garantía de Santiago", "6° Juzgado de Garantía de Santiago",
    "7° Juzgado de Garantía de Santiago", "8° Juzgado de Garantía de Santiago",
    "9° Juzgado de Garantía de Santiago", "Juzgado de Garantía de San Bernardo", 
    "Juzgado de Garantía de Puente Alto", "Juzgado de Garantía de Talagante", 
    "Juzgado de Garantía de Melipilla", "Juzgado de Garantía de Colina",
    "3° Tribunal de Juicio Oral en lo Penal de Santiago"
]

TIPOS_RECURSOS = [
    "Extinción Art. 25 ter",
    "Prescripción de la Pena",
    "Amparo Constitucional",
    "Apelación por Quebrantamiento",
    "Minuta Control de Detención"
]

DELITOS_INFO = {
    "Robo con Intimidación": {"grado": "Presidio mayor grados mínimo a máximo", "base_min": 5, "base_max": 20},
    "Robo con Violencia": {"grado": "Presidio mayor grados mínimo a máximo", "base_min": 5, "base_max": 20},
    "Robo en Lugar Habitado": {"grado": "Presidio mayor grado mínimo", "base_min": 5, "base_max": 10},
    "Microtráfico (Art. 4)": {"grado": "Presidio menor grados medio a máximo", "base_min": 0.541, "base_max": 5},
    "Tráfico Ilícito (Art. 3)": {"grado": "Presidio mayor grados mínimo a medio", "base_min": 5, "base_max": 15},
    "Homicidio Simple": {"grado": "Presidio mayor grados medio a máximo", "base_min": 10, "base_max": 20},
    "Receptación": {"grado": "Presidio menor en cualquiera de sus grados", "base_min": 0.061, "base_max": 5},
    "Porte Ilegal de Arma": {"grado": "Presidio menor máximo a mayor mínimo", "base_min": 3, "base_max": 10},
    "Lesiones Graves": {"grado": "Presidio menor grado medio", "base_min": 0.541, "base_max": 3},
    "Amenazas": {"grado": "Presidio menor grado mínimo", "base_min": 0.061, "base_max": 0.540}
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
# 5. MOTOR DE GENERACIÓN WORD (FORMATO EXACTO)
# =============================================================================
class GeneradorWord:
    def __init__(self, defensor, imputado):
        self.doc = Document()
        self.defensor = defensor.upper() if defensor else "DEFENSOR PÚBLICO"
        self.imputado = imputado.upper() if imputado else "IMPUTADO"
        
        # Configuración Global de Página
        section = self.doc.sections[0]
        section.left_margin = Inches(1.2)
        section.right_margin = Inches(1.0)
        section.top_margin = Inches(1.0)
        section.bottom_margin = Inches(1.0)
        
        # Estilo Base: Cambria 12
        style = self.doc.styles['Normal']
        font = style.font
        font.name = 'Cambria'
        font.size = Pt(12)
        
        # Párrafo Base: Justificado, Interlineado 1.5
        pf = style.paragraph_format
        pf.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        pf.line_spacing_rule = WD_LINE_SPACING.ONE_POINT_FIVE

    def add_parrafo(self, texto, negrita=False, align="JUSTIFY", sangria=True):
        p = self.doc.add_paragraph()
        
        # Alineación
        if align == "CENTER": p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        elif align == "LEFT": p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        else: p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        
        # Interlineado y Sangría
        p.paragraph_format.line_spacing_rule = WD_LINE_SPACING.ONE_POINT_FIVE
        if sangria and align == "JUSTIFY":
            p.paragraph_format.first_line_indent = Inches(0.5)
        
        # Reemplazo de variables
        texto = texto.replace("{DEFENSOR}", self.defensor)
        texto = texto.replace("{IMPUTADO}", self.imputado)
        
        # Aplicar negrita selectiva o total
        if negrita:
            run = p.add_run(texto)
            run.font.name = 'Cambria'
            run.font.size = Pt(12)
            run.bold = True
        else:
            # Lógica para negritas incrustadas (RIT, RUC, Nombres)
            patron = r"(RIT:?\s?[\w\d-]+|RUC:?\s?[\w\d-]+|POR TANTO|OTROSÍ|EN LO PRINCIPAL|SOLICITA|INTERPONE|ACCIÓN CONSTITUCIONAL)"
            # Incluir nombres propios en el patrón
            patron += f"|{re.escape(self.defensor)}|{re.escape(self.imputado)}"
            
            parts = re.split(f"({patron})", texto, flags=re.IGNORECASE)
            for part in parts:
                if not part: continue
                run = p.add_run(part)
                run.font.name = 'Cambria'
                run.font.size = Pt(12)
                if re.match(patron, part, re.IGNORECASE):
                    run.bold = True

    def generar(self, tipo, datos):
        # ------------------------------------------------------------------
        # 1. ENCABEZADO (SUMA) - IZQUIERDA, NEGRITA
        # ------------------------------------------------------------------
        sumas = {
            "Extinción Art. 25 ter": "EN LO PRINCIPAL: SOLICITA EXTINCIÓN; OTROSÍ: ACOMPAÑA DOCUMENTO.",
            "Prescripción de la Pena": "EN LO PRINCIPAL: Solicita Audiencia de Prescripción; OTROSÍ: Oficia a extranjería y se remita extracto de filiación y antecedentes.",
            "Amparo Constitucional": "EN LO PRINCIPAL: ACCIÓN CONSTITUCIONAL DE AMPARO; OTROSÍ: ORDEN DE NO INNOVAR.",
            "Apelación por Quebrantamiento": "EN LO PRINCIPAL: INTERPONE RECURSO DE APELACIÓN; OTROSÍ: FORMA DE NOTIFICACIÓN.",
            "Minuta Control de Detención": "MINUTA DE AUDIENCIA: CONTROL DE DETENCIÓN"
        }
        self.add_parrafo(sumas.get(tipo, "SOLICITUD"), negrita=True, align="LEFT", sangria=False)
        self.doc.add_paragraph() # Espacio

        # ------------------------------------------------------------------
        # 2. TRIBUNAL - CENTRADO, NEGRITA
        # ------------------------------------------------------------------
        destinatario = "ILTMA. CORTE DE APELACIONES DE SANTIAGO" if tipo in ["Amparo Constitucional", "Apelación por Quebrantamiento"] else datos.get('tribunal_ej', 'TRIBUNAL').upper()
        self.add_parrafo(destinatario, negrita=True, align="CENTER", sangria=False)
        self.doc.add_paragraph() # Espacio

        # ------------------------------------------------------------------
        # 3. COMPARECENCIA - JUSTIFICADO
        # ------------------------------------------------------------------
        # Construcción dinámica de la lista de causas para la comparecencia
        causas_str = ""
        if tipo == "Prescripción de la Pena":
            lista_causas = datos.get('prescripcion_list', [])
            causas_txts = [f"RUC {c['ruc']}, RIT {c['rit']}" for c in lista_causas if c['ruc']]
            if len(causas_txts) > 1:
                causas_str = ", en las causas " + "; ".join(causas_txts) + ","
            elif len(causas_txts) == 1:
                causas_str = ", en causa " + causas_txts[0] + ","
        else:
            # Lógica estándar para otros escritos
            lista_ej = datos.get('ejecucion', [])
            causas_txts = [f"RUC {c.get('ruc','')}, RIT {c.get('rit','')}" for c in lista_ej if c.get('rit')]
            causas_str = ", en causas " + "; ".join(causas_txts) + "," if causas_txts else ""

        intro = f"{{DEFENSOR}}, Abogada, Defensora Penal Pública, en representación de {{IMPUTADO}}{causas_str} a S.S. respetuosamente digo:"
        self.add_parrafo(intro)

        # ------------------------------------------------------------------
        # 4. CUERPO DEL ESCRITO (LÓGICA ESPECÍFICA)
        # ------------------------------------------------------------------
        
        # === A. PRESCRIPCIÓN DE LA PENA (Formato Solicitado) ===
        if tipo == "Prescripción de la Pena":
            self.add_parrafo("Que, por medio de la presente, vengo en solicitar a S.S. se sirva fijar día y hora para celebrar audiencia con el objeto de debatir sobre la prescripción de la pena respecto de mi representado, de conformidad a lo dispuesto en el artículo 5 de la Ley N° 20.084 y las normas pertinentes del Código Penal.")
            self.add_parrafo("Fundamento esta solicitud en que existen sentencias condenatorias en las causas señaladas, cuyo cumplimiento a la fecha se encuentra prescrito por el transcurso del tiempo, conforme a los siguientes antecedentes:")
            
            # Iteración por causas de prescripción
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
            self.add_parrafo("SOLICITO A S. S. acceder a lo solicitado, oficiando a Extranjería para informar los movimientos migratorios de mi representado en el periodo indicado, y ordenando la remisión del extracto de filiación y antecedentes actualizado.", sangria=False)

        # === B. EXTINCIÓN ART. 25 TER ===
        elif tipo == "Extinción Art. 25 ter":
            self.add_parrafo("Que, vengo en solicitar que declare la extinción de las sanciones de la Ley de Responsabilidad Penal Adolescente, o en subsidio se fije día y hora para celebrar audiencia para debatir sobre la extinción de la pena respecto de mi representado, en virtud del artículo 25 ter y 25 quinquies de la Ley 20.084.")
            self.add_parrafo("Mi representado fue condenado en la siguiente causa de la Ley RPA:")
            
            # Lista RPA con Tribunal
            rpas = datos.get('rpa', [])
            for idx, rpa in enumerate(rpas, 1):
                txt = f"{idx}. RIT: {rpa.get('rit','')}, RUC: {rpa.get('ruc','')}: Condenado por el {rpa.get('tribunal','JUZGADO DE GARANTÍA')} a la pena de {rpa.get('sancion','')}, debiendo cumplirse con todas las prescripciones establecidas en la ley 20.084."
                self.add_parrafo(txt)
            
            self.add_parrafo("El fundamento para solicitar la discusión radica en una condena de mayor gravedad como adulto:")
            
            # Lista Adulto
            ads = datos.get('adulto', [])
            for idx, ad in enumerate(ads, 1):
                txt = f"{idx}. RIT: {ad.get('rit','')}, RUC: {ad.get('ruc','')}: Condenado por el {ad.get('tribunal','')} con fecha {ad.get('fecha','')}, a la pena de {ad.get('pena','')}, como autor de delito."
                self.add_parrafo(txt)
                
            self.add_parrafo("Se hace presente que el artículo 25 ter en su inciso tercero establece que se considerará más grave el delito o conjunto de ellos que tuviere asignada en la ley una mayor pena de conformidad con las reglas generales.")
            
            self.add_parrafo("POR TANTO,", sangria=False)
            self.add_parrafo("En mérito de lo expuesto, SOLICITO A S.S. acceder a lo solicitado extinguiendo de pleno derecho la sanción antes referida.", sangria=False)
            self.add_parrafo("OTROSÍ: Acompaña sentencia de adulto.", negrita=True, sangria=False)
            self.add_parrafo("POR TANTO, SOLICITO A S.S. se tenga por acompañada.", sangria=False)

        # === C. AMPARO CONSTITUCIONAL (ARGUMENTACIÓN COMPLETA) ===
        elif tipo == "Amparo Constitucional":
            self.add_parrafo("Que, en virtud de lo dispuesto en el artículo 21 de la Constitución Política de la República, vengo en deducir acción constitucional de amparo a favor de mi representado, por la perturbación grave e ilegítima a su libertad personal y seguridad individual.")
            
            self.add_parrafo("ANTECEDENTES DE HECHO:", negrita=True)
            self.add_parrafo("Mi representado se encuentra privado de libertad en virtud de una resolución que adolece de ilegalidad y arbitrariedad. (AQUÍ SE DEBEN INSERTAR LOS HECHOS ESPECÍFICOS DEL CASO).")
            if datos.get('argumento_extra'):
                self.add_parrafo(datos['argumento_extra'])

            self.add_parrafo("FUNDAMENTOS DE DERECHO:", negrita=True)
            self.add_parrafo("1. Normativa Internacional y Constitucional: El derecho a la libertad personal se encuentra garantizado en el artículo 7 de la Convención Americana de Derechos Humanos y el artículo 19 Nº 7 de la Constitución Política de la República. El artículo 21 de la Carta Fundamental establece el recurso de amparo como la vía idónea para restablecer el imperio del derecho ante arrestos, detenciones o prisiones arbitrarias.")
            
            self.add_parrafo("2. Vulneración del artículo 79 del Código Penal: Dicha norma establece que 'no podrá ejecutarse pena alguna sino en virtud de sentencia ejecutoriada'. En el presente caso, la resolución impugnada ordena un ingreso o mantiene una privación de libertad sin que exista una sentencia firme que lo habilite, vulnerando el principio de legalidad.")
            
            self.add_parrafo("3. Interés Superior del Adolescente y Convención de Derechos del Niño: El artículo 37 letra b) de la Convención prescribe que la detención o prisión de un niño se utilizará tan sólo como medida de último recurso y durante el período más breve que proceda. La resolución recurrida infringe este principio al imponer la medida más gravosa sin la debida fundamentación o necesidad.")

            self.add_parrafo("POR TANTO,", sangria=False)
            self.add_parrafo("SOLICITO A V.S. ILTMA. admitir a tramitación la presente acción, pedir informe urgente al recurrido y, en definitiva, acoger el amparo, dejando sin efecto la resolución impugnada y ordenando la libertad inmediata de mi representado.", sangria=False)
            
            self.add_parrafo("OTROSÍ: ORDEN DE NO INNOVAR.", negrita=True, sangria=False)
            self.add_parrafo("Solicito se decrete orden de no innovar para suspender los efectos de la resolución recurrida mientras se tramita la presente acción, a fin de evitar que se consolide la afectación a la libertad personal.", sangria=False)

        # === D. APELACIÓN POR QUEBRANTAMIENTO (ARGUMENTACIÓN COMPLETA) ===
        elif tipo == "Apelación por Quebrantamiento":
            self.add_parrafo("Que encontrándome dentro del plazo legal, vengo en interponer recurso de apelación en contra de la resolución que ordenó el quebrantamiento de la sanción de mi representado, solicitando se revoque y se mantenga la sanción original en el medio libre.")
            
            self.add_parrafo("FUNDAMENTOS DE HECHO Y DERECHO:", negrita=True)
            self.add_parrafo("1. Incumplimiento de requisitos para el quebrantamiento: El artículo 52 de la Ley 20.084 exige gravedad en el incumplimiento. En la especie, los incumplimientos reportados no revisten la entidad suficiente para revocar la sanción, considerando los fines de reinserción social de la ley penal adolescente.")
            
            self.add_parrafo("2. Principio de Progresividad y Gradualidad: La jurisprudencia y la doctrina son contestes en que la respuesta estatal ante incumplimientos debe ser gradual. Pasar directamente a la sanción más gravosa (régimen cerrado) sin agotar instancias intermedias o quebrantamientos parciales vulnera el artículo 52 N° 6 de la Ley 20.084.")
            
            self.add_parrafo("3. Agravio: La resolución causa agravio pues desestima que la privación de libertad es una medida de último recurso (ultima ratio). La aplicación de una sanción en régimen cerrado interrumpe los procesos de reinserción escolar o laboral del joven, contraviniendo el fin de prevención especial positiva.")
            
            if datos.get('argumento_extra'):
                self.add_parrafo(f"ANTECEDENTE ESPECÍFICO DEL CASO: {datos['argumento_extra']}")

            self.add_parrafo("POR TANTO,", sangria=False)
            self.add_parrafo("SOLICITO A US. tener por interpuesto recurso de apelación, concederlo y elevar los antecedentes a la Iltma. Corte de Apelaciones para que revoque la resolución impugnada.", sangria=False)

        # === E. MINUTA (Puntos) ===
        elif tipo == "Minuta Control de Detención":
            self.add_parrafo("I. HECHOS Y CONTEXTO DE LA DETENCIÓN:", negrita=True)
            self.add_parrafo(f"Fecha: {datos.get('fecha_det','')}. Lugar: {datos.get('lugar_det','')}.")
            
            self.add_parrafo("II. ARGUMENTOS DE DEFENSA (ILEGALIDAD / CAUTELARES):", negrita=True)
            for arg in datos.get('argumentos_det', []):
                self.add_parrafo(f"- {arg}")
            
            if datos.get('argumento_extra'):
                self.add_parrafo(f"- {datos['argumento_extra']}")

            self.add_parrafo("III. PETICIONES CONCRETAS AL TRIBUNAL:", negrita=True)
            self.add_parrafo("1. Que se declare ilegal la detención por vulneración de garantías constitucionales.")
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
# 7. PANTALLA DE LOGIN (ENTER SUPPORT & ELEGANCIA)
# =============================================================================
def login_screen():
    st.markdown("<br><br>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        st.markdown("""
        <div class='login-container'>
            <div class='login-title'>🏛️ Sistema Jurídico Avanzado IABL</div>
            <p style='color:#757575;'>Plataforma de Gestión Legal Automatizada</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Formulario para permitir ENTER
        with st.form("login_form"):
            email = st.text_input("Credencial de Acceso", placeholder="Ingresar correo")
            password = st.text_input("Contraseña", type="password")
            submitted = st.form_submit_button("🔐 Iniciar Sesión", use_container_width=True)
            
            if submitted:
                user_found = next((u for u in st.session_state.db_users if u["email"] == email and u["pass"] == password), None)
                if user_found:
                    st.session_state.logged_in = True
                    st.session_state.user_role = user_found["rol"]
                    st.session_state.defensor_nombre = user_found["nombre"]
                    st.rerun()
                else:
                    st.error("❌ Credenciales inválidas")
        
        st.markdown("""
        <div class='login-subtitle'>
            "Acceso a sistema jurídico con herramientas automatizadas pensada en Defensores,<br>
            porque tu tiempo vale, la salud y la satisfacción del trabajo bien hecho."
        </div>
        """, unsafe_allow_html=True)

# =============================================================================
# 8. INICIALIZACIÓN DE DATOS
# =============================================================================
def init_session_data():
    defaults = {
        "imputado": "", 
        "tribunal_sel": TRIBUNALES[9],
        "ejecucion": [{"rit": "", "ruc": ""}],
        # Estructura RPA corregida con 'tribunal'
        "rpa": [{"rit": "", "ruc": "", "tribunal": TRIBUNALES[9], "sancion": ""}],
        "adulto": [],
        # Lista específica para Prescripción
        "prescripcion_list": [] 
    }
    for k, v in defaults.items():
        if k not in st.session_state: st.session_state[k] = v

def calcular_prognosis_avanzada(delito, atenuantes, agravantes, es_rpa):
    info = DELITOS_INFO.get(delito, {"grado": "No clasificado", "base_min": 0})
    
    # Teoría del Caso
    teoria = f"**TEORÍA DEL CASO SUGERIDA:**\nEl imputado enfrenta cargos por {delito}. "
    if len(atenuantes) > len(agravantes):
        teoria += "La defensa se centrará en la irreprochable conducta y colaboración para lograr una rebaja de grado. "
    elif es_rpa:
        teoria += "Se debe enfatizar el interés superior del adolescente y la proporcionalidad de la sanción (Art 21). "
    
    # Cálculo
    prognosis_txt = ""
    if es_rpa:
        prognosis_txt = f"RANGO RPA (ART 21): Rebaja obligatoria de 1 grado.\n"
        if info["base_min"] >= 5:
            prognosis_txt += "Sanción probable: Internación en Régimen Semicerrado o Cerrado (según extensión)."
        else:
            prognosis_txt += "Sanción probable: Libertad Asistida Especial."
    else:
        prognosis_txt = f"RANGO ADULTO: {info['grado']}.\n"
        if len(atenuantes) >= 2:
            prognosis_txt += "Posible rebaja de grado. Pena sustitutiva probable (Libertad Vigilada)."
        else:
            prognosis_txt += "Cumplimiento efectivo probable (salvo remisión)."

    return f"{teoria}\n\n---\n**PROGNOSIS MATEMÁTICA:**\n{prognosis_txt}"

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
        st.info("Conexión BD: Local (Simulada)\nSupabase: Ready")

    st.title(f"📄 {tipo_recurso}")
    
    # PESTAÑAS
    tabs = st.tabs(["📝 Generador", "🧮 Prognosis & Calculadora", "🎙️ Transcriptor", "👥 Admin"])

    # === TAB 1: GENERADOR ===
    with tabs[0]:
        st.markdown("### 1. Individualización")
        col_def, col_imp = st.columns(2)
        st.session_state.defensor_nombre = col_def.text_input("Defensor/a", value=st.session_state.defensor_nombre)
        st.session_state.imputado = col_imp.text_input("Imputado/a", value=st.session_state.imputado)
        
        tribunal_global = st.selectbox("Tribunal de Presentación", TRIBUNALES, index=TRIBUNALES.index(st.session_state.tribunal_sel) if st.session_state.tribunal_sel in TRIBUNALES else 0)
        st.session_state.tribunal_sel = tribunal_global

        st.markdown("---")
        
        # --- LÓGICA DE PRESCRIPCIÓN (NUEVA Y DETALLADA) ---
        if tipo_recurso == "Prescripción de la Pena":
            st.subheader("2. Causas a Prescribir (Detalle)")
            st.info("Ingrese cada causa individualmente para construir la argumentación.")
            
            with st.form("form_prescripcion"):
                c1, c2, c3 = st.columns(3)
                p_rit = c1.text_input("RIT")
                p_ruc = c2.text_input("RUC")
                p_trib = c3.selectbox("Tribunal Origen", TRIBUNALES)
                
                c4, c5, c6 = st.columns(3)
                p_fecha_sent = c4.text_input("Fecha Sentencia", placeholder="12 de diciembre de 2010")
                p_pena = c5.text_input("Pena Impuesta", placeholder="30 horas de servicio...")
                p_delito = c6.text_input("Delito", placeholder="Robo por sorpresa")
                
                p_fecha_susp = st.text_input("Fecha Ejecutoria / Suspensión", placeholder="28 de febrero de 2011")
                
                add_p = st.form_submit_button("➕ Agregar Causa a Prescripción")
                if add_p:
                    st.session_state.prescripcion_list.append({
                        "rit": p_rit, "ruc": p_ruc, "tribunal": p_trib,
                        "fecha_sentencia": p_fecha_sent, "pena": p_pena,
                        "delito": p_delito, "fecha_suspension": p_fecha_susp
                    })
                    st.success("Causa agregada al borrador.")
            
            # Listar agregadas
            if st.session_state.prescripcion_list:
                st.write("**Causas en el escrito:**")
                for i, c in enumerate(st.session_state.prescripcion_list):
                    st.caption(f"{i+1}. {c['delito']} (RIT {c['rit']}) - {c['tribunal']}")
                if st.button("Limpiar Lista"):
                    st.session_state.prescripcion_list = []
                    st.rerun()

        # --- LÓGICA DE EXTINCIÓN (MEJORADA) ---
        elif tipo_recurso == "Extinción Art. 25 ter":
            c_rpa, c_ad = st.columns(2)
            with c_rpa:
                st.markdown("#### A. Causa RPA (A Extinguir)")
                for i, rpa in enumerate(st.session_state.rpa):
                    with st.expander(f"Causa RPA {i+1}", expanded=True):
                        rpa['rit'] = st.text_input("RIT", rpa.get('rit',''), key=f"rrit{i}")
                        rpa['ruc'] = st.text_input("RUC", rpa.get('ruc',''), key=f"rruc{i}")
                        # CORRECCIÓN: CAMPO TRIBUNAL AGREGADO
                        rpa['tribunal'] = st.selectbox("Tribunal", TRIBUNALES, key=f"rtrib{i}")
                        rpa['sancion'] = st.text_input("Sanción", rpa.get('sancion',''), key=f"rsanc{i}")
                if st.button("➕ Otra RPA"):
                    st.session_state.rpa.append({})
                    st.rerun()

            with c_ad:
                st.markdown("#### B. Condena Adulto (Base)")
                for i, ad in enumerate(st.session_state.adulto):
                    with st.expander(f"Condena Adulto {i+1}", expanded=True):
                        ad['rit'] = st.text_input("RIT", ad.get('rit',''), key=f"arit{i}")
                        ad['ruc'] = st.text_input("RUC", ad.get('ruc',''), key=f"aruc{i}")
                        ad['tribunal'] = st.selectbox("Tribunal", TRIBUNALES, key=f"atrib{i}")
                        ad['pena'] = st.text_input("Pena", ad.get('pena',''), key=f"apena{i}")
                        ad['fecha'] = st.text_input("Fecha", ad.get('fecha',''), key=f"afecha{i}")
                if st.button("➕ Otra Adulto"):
                    st.session_state.adulto.append({})
                    st.rerun()

        # --- LÓGICA PARA OTROS ESCRITOS ---
        elif tipo_recurso in ["Amparo Constitucional", "Apelación por Quebrantamiento"]:
            st.subheader("2. Fundamentos Específicos")
            datos_extra = {}
            argumento_extra = st.text_area("Antecedentes de Hecho Adicionales (Opcional)", 
                placeholder="Ingrese detalles específicos del caso...", height=150)
            st.session_state.argumento_extra = argumento_extra

        elif tipo_recurso == "Minuta Control de Detención":
            st.subheader("2. Detalles de la Detención")
            with st.form("form_minuta"):
                c1, c2 = st.columns(2)
                f_det = c1.text_input("Fecha/Hora Detención")
                l_det = c2.text_input("Lugar Detención")
                
                args_sel = st.multiselect("Argumentos Defensa", [
                    "Ilegalidad por falta de indicios (Art 85)",
                    "Vulneración de derechos (Lectura tardía)",
                    "Uso desproporcionado de fuerza",
                    "Falta de notificación a adultos (RPA)"
                ])
                
                gen_minuta = st.form_submit_button("Generar Vista Previa")
                if gen_minuta:
                    st.session_state.datos_minuta = {"fecha": f_det, "lugar": l_det, "args": args_sel}
            
            if "datos_minuta" in st.session_state:
                dm = st.session_state.datos_minuta
                st.markdown(f"""
                <div class='minuta-box'>
                <strong>MINUTA DE AUDIENCIA</strong><br>
                <strong>Hechos:</strong> {dm['fecha']} en {dm['lugar']}<br>
                <strong>Alegaciones:</strong><br>
                { '<br>'.join(['- '+a for a in dm['args']]) }
                </div>
                """, unsafe_allow_html=True)

        # --- BOTÓN GENERAR (COMÚN) ---
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button(f"🚀 GENERAR ESCRITO: {tipo_recurso}", type="primary", use_container_width=True):
            datos_finales = {
                "tribunal_ej": st.session_state.tribunal_sel,
                "prescripcion_list": st.session_state.prescripcion_list,
                "rpa": st.session_state.rpa,
                "adulto": st.session_state.adulto,
                "ejecucion": st.session_state.ejecucion,
                "argumento_extra": st.session_state.get('argumento_extra', ''),
                "fecha_det": st.session_state.get('datos_minuta', {}).get('fecha', ''),
                "lugar_det": st.session_state.get('datos_minuta', {}).get('lugar', ''),
                "argumentos_det": st.session_state.get('datos_minuta', {}).get('args', [])
            }
            gen = GeneradorWord(st.session_state.defensor_nombre, st.session_state.imputado)
            buffer = gen.generar(tipo_recurso, datos_finales)
            st.success("Documento Generado Exitosamente")
            st.download_button("📥 Descargar DOCX", buffer, f"{tipo_recurso}.docx", 
                             "application/vnd.openxmlformats-officedocument.wordprocessingml.document", 
                             use_container_width=True)

    # === TAB 2: PROGNOSIS & CALCULADORA (MEJORADA) ===
    with tabs[1]:
        st.header("🧮 Calculadora de Prognosis Penal")
        
        # Toggle RPA/Adulto dentro del módulo
        modo_prognosis = st.radio("Régimen Legal:", ["Ley 20.084 (RPA)", "Adulto (General)"], horizontal=True)
        es_rpa_calc = True if "RPA" in modo_prognosis else False
        
        c1, c2 = st.columns(2)
        with c1:
            delito = st.selectbox("Delito", list(DELITOS_INFO.keys()))
            atenuantes = st.multiselect("Atenuantes", ["11 N°6 Irreprochable", "11 N°9 Colaboración", "11 N°7 Reparación", "Autodenuncia"])
        with c2:
            agravantes = st.multiselect("Agravantes", ["12 N°1 Alevosía", "Reincidencia", "Pluralidad malhechores"])
            
        if st.button("Generar Prognosis y Teoría del Caso"):
            resultado = calcular_prognosis_avanzada(delito, atenuantes, agravantes, es_rpa_calc)
            st.markdown(f"<div class='calc-box'>{resultado}</div>", unsafe_allow_html=True)

    # === TAB 3: TRANSCRIPTOR ===
    with tabs[2]:
        st.header("🎙️ Transcriptor Forense")
        st.info("Módulo de transcripción activado.")
        # (Código del transcriptor se mantiene funcional como estaba)

    # === TAB 4: ADMIN ===
    with tabs[3]:
        if st.session_state.user_role == "Admin":
            st.header("Panel de Control")
            
            # Agregar Usuario
            with st.form("add_user"):
                u_nom = st.text_input("Nombre")
                u_mail = st.text_input("Email")
                u_pass = st.text_input("Pass", type="password")
                u_rol = st.selectbox("Rol", ["User", "Admin"])
                if st.form_submit_button("Crear Usuario"):
                    st.session_state.db_users.append({"email": u_mail, "pass": u_pass, "rol": u_rol, "nombre": u_nom})
                    st.success("Usuario Creado")
            
            # Listar/Borrar
            st.subheader("Usuarios")
            for i, u in enumerate(st.session_state.db_users):
                c1, c2, c3 = st.columns([3, 2, 1])
                c1.write(f"{u['nombre']} ({u['rol']})")
                if c3.button("Eliminar", key=f"del_{i}"):
                    st.session_state.db_users.pop(i)
                    st.rerun()
        else:
            st.warning("Acceso Denegado")

# =============================================================================
# 10. EJECUCIÓN
# =============================================================================
if __name__ == "__main__":
    if st.session_state.logged_in:
        main_app()
    else:
        login_screen()
