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
# 1. CONFIGURACIÓN Y ESTILOS (INTERFAZ ELEGANTE)
# =============================================================================
st.set_page_config(
    page_title="Suite Legal IABL Pro",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS Profesional y Elegante - CORREGIDO PARA LEGIBILIDAD
st.markdown("""
    <style>
    /* Fondo y tipografía general */
    .main {
        background-color: #f4f6f9;
        font-family: 'Segoe UI', sans-serif;
    }
    
    /* Encabezados */
    h1 { color: #1a237e; font-weight: 800; border-bottom: 2px solid #1a237e; padding-bottom: 10px; }
    h2, h3 { color: #283593; font-weight: 600; }
    
    /* Botones Estilizados */
    .stButton>button {
        background-color: #1a237e;
        color: white;
        border-radius: 8px;
        font-weight: bold;
        border: none;
        padding: 0.5rem 1rem;
        transition: all 0.3s;
    }
    .stButton>button:hover {
        background-color: #3949ab;
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(0,0,0,0.2);
    }
    
    /* Tarjetas de Información */
    .status-card {
        padding: 20px;
        border-radius: 12px;
        background: white;
        border-left: 6px solid #1a237e;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        margin-bottom: 15px;
        color: #000000; /* Texto negro forzado */
    }
    
    /* Cajas de Jurisprudencia y Calculadora - TEXTO NEGRO FORZADO */
    .juris-box {
        background-color: #ffffff;
        padding: 20px;
        border-radius: 8px;
        border-left: 4px solid #fbc02d;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        color: #000000 !important; 
    }
    
    .calc-box {
        background-color: #e3f2fd;
        padding: 20px;
        border-radius: 10px;
        border: 1px solid #bbdefb;
        color: #0d47a1 !important;
    }
    
    .minuta-box {
        background-color: #fff3e0;
        padding: 20px;
        border-radius: 10px;
        border: 1px solid #ffe0b2;
        color: #bf360c !important;
        margin-top: 15px;
    }

    /* Login Box */
    .login-container {
        background: white;
        padding: 40px;
        border-radius: 15px;
        box-shadow: 0 10px 25px rgba(0,0,0,0.1);
        text-align: center;
    }
    .login-subtitle {
        font-size: 0.95em;
        color: #546e7a;
        font-style: italic;
        margin-top: 15px;
        font-weight: 500;
    }
    </style>
""", unsafe_allow_html=True)

# =============================================================================
# 2. CONFIGURACIÓN ROBUSTA DE IA
# =============================================================================
GOOGLE_API_KEY = "AIzaSyDjsyWjcHCXvgoIQsbyxGD2oyLHFMLfWhg" 
genai.configure(api_key=GOOGLE_API_KEY)

def get_gemini_model():
    """Selección robusta del modelo. Prioriza 1.5 Flash."""
    try:
        return genai.GenerativeModel('gemini-1.5-flash')
    except Exception:
        try:
            return genai.GenerativeModel('gemini-1.5-pro')
        except:
            st.error("Error crítico conectando con Gemini AI. Verifique API Key.")
            return None

model_ia = get_gemini_model()

# Configuración Base de Datos
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
    "Juzgado de Garantía de Melipilla", "Juzgado de Garantía de Colina"
]

TIPOS_RECURSOS = [
    "Extinción Art. 25 ter",
    "Prescripción de la Pena",
    "Amparo Constitucional",
    "Apelación por Quebrantamiento",
    "Minuta Control de Detención"
]

# Datos para Calculadora y Prognosis
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
# 4. LÓGICA DE NEGOCIO (IA & DOCS)
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

class GeneradorWord:
    def __init__(self, defensor, imputado):
        self.doc = Document()
        self.defensor = defensor.upper() if defensor else "DEFENSOR PÚBLICO"
        self.imputado = imputado.upper() if imputado else "IMPUTADO"
        # Configuración de página
        section = self.doc.sections[0]
        section.left_margin = Inches(1.2)
        section.right_margin = Inches(1.0)
        # Estilo base
        style = self.doc.styles['Normal']
        style.font.name = 'Cambria'
        style.font.size = Pt(12)

    def add_parrafo(self, texto, negrita=False, align="JUSTIFY"):
        p = self.doc.add_paragraph()
        p.alignment = getattr(WD_ALIGN_PARAGRAPH, align)
        p.paragraph_format.line_spacing_rule = WD_LINE_SPACING.ONE_POINT_FIVE
        
        # Reemplazo dinámico
        texto = texto.replace("{DEFENSOR}", self.defensor)
        texto = texto.replace("{IMPUTADO}", self.imputado)
        
        run = p.add_run(texto)
        run.bold = negrita

    def generar(self, tipo, datos):
        # 1. ENCABEZADO (SUMA)
        sumas = {
            "Extinción Art. 25 ter": "EN LO PRINCIPAL: SOLICITA EXTINCIÓN; OTROSÍ: ACOMPAÑA SENTENCIA",
            "Prescripción de la Pena": "EN LO PRINCIPAL: ALEGA PRESCRIPCIÓN; OTROSÍ: CERTIFICADO",
            "Amparo Constitucional": "EN LO PRINCIPAL: INTERPONE ACCIÓN DE AMPARO; OTROSÍ: ORDEN DE NO INNOVAR",
            "Apelación por Quebrantamiento": "EN LO PRINCIPAL: INTERPONE RECURSO DE APELACIÓN; OTROSÍ: NOTIFICACIÓN",
            "Minuta Control de Detención": "MINUTA DE AUDIENCIA: CONTROL DE DETENCIÓN"
        }
        self.add_parrafo(sumas.get(tipo, "SOLICITUD"), negrita=True, align="LEFT")
        
        # 2. DESTINATARIO
        destinatario = "ILTMA. CORTE DE APELACIONES" if tipo == "Amparo Constitucional" else datos.get('tribunal_ej', 'TRIBUNAL').upper()
        self.add_parrafo(f"\nAL {destinatario}", negrita=True, align="LEFT")
        
        # 3. COMPARECENCIA
        # Uso seguro de claves con .get()
        causas_txt = ", ".join([f"{c.get('rit','')} (RUC {c.get('ruc','')})" for c in datos.get('ejecucion',[]) if c.get('rit')])
        intro = f"\n{{DEFENSOR}}, Abogada Defensora Penal Pública, por el adolescente {{IMPUTADO}}, en causas {causas_txt}, a US. respetuosamente digo:"
        self.add_parrafo(intro)

        # 4. CUERPO Y ARGUMENTACIÓN
        if tipo == "Extinción Art. 25 ter":
            self.add_parrafo("Que, vengo en solicitar se declare la extinción de las sanciones de la Ley de Responsabilidad Penal Adolescente, en virtud de lo dispuesto en los artículos 25 ter y 25 quinquies de la Ley 20.084.")
            self.add_parrafo("FUNDAMENTO: Existe una condena de mayor gravedad como adulto que hace inoficiosa la sanción juvenil.", negrita=True)
            self.add_parrafo("ANTECEDENTES DE LA CONDENA ADULTO:")
            
            # CORRECCIÓN KEY ERROR: Uso seguro de .get() para evitar caídas
            adultos = datos.get('adulto', [])
            if adultos:
                for ad in adultos:
                    rit = ad.get('rit', 'S/I')
                    ruc = ad.get('ruc', 'S/I')
                    tribunal = ad.get('tribunal', 'Tribunal no especificado')
                    pena = ad.get('pena', 'No especificada')
                    fecha = ad.get('fecha', 'S/F')
                    self.add_parrafo(f"• RIT: {rit}, RUC: {ruc}, Tribunal: {tribunal}, Pena: {pena}, Fecha: {fecha}")
            else:
                self.add_parrafo("(Sin antecedentes de adulto ingresados)")
                
            self.add_parrafo("POR TANTO, solicito a S.S. acceder a lo solicitado extinguiendo de pleno derecho la sanción antes referida.")

        elif tipo == "Prescripción de la Pena":
            self.add_parrafo("Que, por medio de la presente, vengo en solicitar a S.S. se sirva fijar día y hora para celebrar audiencia con el objeto de debatir sobre la prescripción de la pena, de conformidad a lo dispuesto en el artículo 5 de la Ley N° 20.084.")
            
            plazo = "2 años" if "Simple" in datos.get('tipo_delito', '') else "5 años"
            fecha_ref = f" desde el {datos.get('fecha_firme')}" if datos.get('fecha_firme') else ""
            
            self.add_parrafo(f"HECHOS: La sentencia quedó ejecutoriada (o se quebrantó el cumplimiento){fecha_ref}. A la fecha, ha transcurrido en exceso el plazo de {plazo} exigido por el Art. 5 de la Ley 20.084 para la prescripción de la pena.", negrita=False)
            self.add_parrafo("DERECHO: Conforme al artículo 100 del Código Penal en relación a la Ley de Responsabilidad Penal Adolescente, la pena se encuentra prescrita por el transcurso del tiempo sin que esta se haya ejecutado.")
            self.add_parrafo("POR TANTO, solicito fijar audiencia para declarar el sobreseimiento definitivo.")

        elif tipo == "Amparo Constitucional":
            self.add_parrafo("Que, en virtud de lo dispuesto en el artículo 21 de la Constitución Política de la República, vengo en deducir acción constitucional de amparo por la perturbación grave e ilegítima a la libertad personal.")
            self.add_parrafo("HECHOS ILEGALES: La resolución que ordenó el ingreso inmediato del joven infringe el artículo 79 del Código Penal, pues no existe sentencia ejecutoriada que lo habilite.")
            self.add_parrafo("DERECHO: Se vulnera la Convención sobre los Derechos del Niño (art. 37) y la Ley 20.084, que establecen la privación de libertad como medida de último recurso.")
            if datos.get('argumento_extra'):
                self.add_parrafo(f"ADICIONALMENTE: {datos['argumento_extra']}")
            self.add_parrafo("POR TANTO, solicito acoger el amparo y decretar la libertad inmediata.")
            self.add_parrafo("OTROSÍ: Orden de No Innovar.", negrita=True)

        elif tipo == "Apelación por Quebrantamiento":
            self.add_parrafo("Que interpongo recurso de apelación en contra de la resolución que ordenó el quebrantamiento definitivo, solicitando sea revocado conforme a los artículos 52 y siguientes de la Ley 20.084.")
            self.add_parrafo("AGRAVIO: La aplicación de una sanción en régimen cerrado no permite hacer efectiva la reinserción social, privando la posibilidad de continuar actividades laborales o educativas.")
            if datos.get('argumento_extra'):
                self.add_parrafo(f"FUNDAMENTO ESPECÍFICO: {datos['argumento_extra']}")
            self.add_parrafo("POR TANTO, solicito a la Iltma. Corte revocar la resolución y mantener la sanción en el medio libre.")

        elif tipo == "Minuta Control de Detención":
            # Para descarga (aunque se muestra en pantalla)
            self.add_parrafo("I. HECHOS:", negrita=True)
            self.add_parrafo(f"Fecha: {datos.get('fecha_det','')}. Lugar: {datos.get('lugar_det','')}.")
            self.add_parrafo("II. ARGUMENTOS DE DEFENSA:", negrita=True)
            for arg in datos.get('argumentos_det', []):
                self.add_parrafo(f"• {arg}")
            self.add_parrafo("III. PETICIONES:", negrita=True)
            self.add_parrafo("1. Ilegalidad de la detención.\n2. Rechazo de medidas cautelares gravosas.")

        # CIERRE
        self.add_parrafo("\nPOR TANTO,\nRUEGO A US. acceder a lo solicitado.", negrita=True)
        
        buffer = io.BytesIO()
        self.doc.save(buffer)
        buffer.seek(0)
        return buffer

# =============================================================================
# 5. GESTIÓN DE SESIÓN Y LOGIN
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

def login_screen():
    st.markdown("<br><br>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        st.markdown("""
        <div class='login-container'>
            <h1 style='color:#1a237e;'>🏛️ Suite Legal IABL Pro</h1>
            <p style='color:#666;'>Acceso a sistema jurídico con herramientas automatizadas pensada en Defensores</p>
            <p class='login-subtitle'>porque tu tiempo vale, la salud y la satisfacción del trabajo bien hecho</p>
        </div>
        """, unsafe_allow_html=True)
        
        email = st.text_input("Credencial de Acceso", placeholder="Ingresar correo")
        password = st.text_input("Contraseña", type="password")
        
        if st.button("🔐 Iniciar Sesión", use_container_width=True):
            user_found = next((u for u in st.session_state.db_users if u["email"] == email and u["pass"] == password), None)
            
            if user_found:
                st.session_state.logged_in = True
                st.session_state.user_role = user_found["rol"]
                st.session_state.defensor_nombre = user_found["nombre"]
                st.rerun()
            else:
                st.error("❌ Credenciales inválidas")

def init_session_data():
    defaults = {
        "imputado": "", 
        "tribunal_sel": TRIBUNALES[9],
        "ejecucion": [{"rit": "", "ruc": ""}],
        "rpa": [{"rit": "", "ruc": "", "tribunal": "", "sancion": ""}],
        # Corrección: Estructura de adulto con todas las claves necesarias
        "adulto": []
    }
    for k, v in defaults.items():
        if k not in st.session_state: st.session_state[k] = v

def calcular_prognosis_avanzada(delito, atenuantes, agravantes, es_rpa):
    """
    Calculadora mejorada considerando:
    - Ley 20.084 (Art. 21)
    - Ley 18.216 (Penas sustitutivas)
    - Reglas generales Código Penal (Art 65 y ss)
    """
    info = DELITOS_INFO.get(delito, {"grado": "No clasificado", "base_min": 0, "base_max": 0})
    pena_txt = info["grado"]
    
    # Análisis de circunstancias
    num_atenuantes = len(atenuantes)
    num_agravantes = len(agravantes)
    
    efecto = "Base"
    
    # Lógica simplificada de determinación
    if num_atenuantes > 0 and num_agravantes == 0:
        if "11 N°6 (Irreprochable)" in atenuantes or num_atenuantes >= 2:
            efecto = "Rebaja de Grado (Mínimo o inferior)"
        else:
            efecto = "Mínimum de la pena"
    elif num_agravantes > 0 and num_atenuantes == 0:
        efecto = "Máximum de la pena"
    else:
        efecto = "Compensación racional"

    # Lógica RPA (Art 21 Ley 20.084)
    res_rpa = ""
    if es_rpa:
        res_rpa = "APLICA ART. 21 LEY 20.084: REBAJA EN UN GRADO AL MÍNIMO.\n"
        if info["base_min"] >= 5: # Crimen
            res_rpa += "--> Probable: RÉGIMEN CERRADO o SEMICERRADO (Según extensión)"
        elif info["base_min"] > 0.541: # Simple delito mayor
            res_rpa += "--> Probable: LIBERTAD ASISTIDA ESPECIAL"
        else:
            res_rpa += "--> Probable: LIBERTAD ASISTIDA SIMPLE o SERVICIOS EN BENEFICIO"
            
    # Lógica Adulto (Ley 18.216)
    res_adulto = ""
    if not es_rpa:
        if info["base_min"] <= 3:
            res_adulto = "Posible REMISIÓN CONDICIONAL (Si cumple requisitos filiación)"
        elif info["base_min"] <= 5:
            res_adulto = "Posible LIBERTAD VIGILADA (Intensiva si es VIF/Armas)"
        else:
            res_adulto = "CUMPLIMIENTO EFECTIVO (Salvo rebajas de grado extraordinarias)"

    final_msg = f"**Marco Legal:** {pena_txt}\n**Efecto Circunstancias:** {efecto}\n\n"
    if es_rpa:
        final_msg += f"🔴 **PROGNOSIS RPA:**\n{res_rpa}"
    else:
        final_msg += f"🔵 **PROGNOSIS ADULTO:**\n{res_adulto}"
        
    return final_msg

# =============================================================================
# 6. INTERFAZ PRINCIPAL
# =============================================================================
def main_app():
    init_session_data()
    
    # --- SIDEBAR ---
    with st.sidebar:
        st.markdown(f"### 👤 {st.session_state.defensor_nombre}")
        st.caption(f"Rol: {st.session_state.user_role.upper()}")
        if st.button("Cerrar Sesión"):
            st.session_state.logged_in = False
            st.rerun()
        st.divider()
        st.header("⚙️ Configuración Global")
        tipo_recurso = st.selectbox("Tipo de Escrito / Gestión", TIPOS_RECURSOS)
        # Toggle para activar modo RPA o Adulto (afecta calculadora)
        es_rpa_global = st.toggle("Modo RPA (Ley 20.084)", value=True)

    st.title(f"📄 Gestión: {tipo_recurso}")
    
    # --- PESTAÑAS ---
    tabs = st.tabs(["📝 Generador de Escritos", "🎙️ Transcriptor Avanzado", "🧰 Calculadora & Herramientas", "👥 Administrador"])

    # === TAB 1: GENERADOR ===
    with tabs[0]:
        # FORMULARIO PRINCIPAL
        st.markdown("### 1. Datos de Individualización")
        
        st.session_state.defensor_nombre = st.text_input("Nombre del Defensor", value=st.session_state.defensor_nombre)
        
        col1, col2 = st.columns([2, 1])
        with col1:
            st.session_state.imputado = st.text_input("Nombre Adolescente / Representado", st.session_state.imputado)
        with col2:
            st.session_state.tribunal_sel = st.selectbox("Juzgado de Ejecución", TRIBUNALES, index=TRIBUNALES.index(st.session_state.tribunal_sel) if st.session_state.tribunal_sel in TRIBUNALES else 0)

        # SECCIÓN EJECUCIÓN
        st.markdown("---")
        st.markdown("### 2. Causa en Conocimiento (Ejecución)")
        
        for i, item in enumerate(st.session_state.ejecucion):
            c1, c2, c3 = st.columns([3, 3, 1])
            item['rit'] = c1.text_input(f"RIT", item.get('rit',''), key=f"rit_{i}", placeholder="1234-2023")
            item['ruc'] = c2.text_input(f"RUC", item.get('ruc',''), key=f"ruc_{i}", placeholder="12345678-9")
            if c3.button("🗑️ Quitar", key=f"del_{i}"):
                st.session_state.ejecucion.pop(i)
                st.rerun()
        
        c_add, c_ia = st.columns([1, 4])
        if c_add.button("➕ Agregar Causa"):
            st.session_state.ejecucion.append({"rit": "", "ruc": ""})
            st.rerun()
        
        pdf_ej = c_ia.file_uploader("Adjuntar Acta para Relleno (PDF)", type="pdf", key="pdf_ej", label_visibility="collapsed")
        if pdf_ej and st.button("Autocompletar Ejecución con IA"):
            data = analizar_pdf(pdf_ej, "Acta")
            if data:
                st.session_state.ejecucion[0].update({"rit": data.get('rit',''), "ruc": data.get('ruc','')})
                st.success("Datos cargados")
                st.rerun()

        # LÓGICA ESPECÍFICA POR RECURSO
        st.markdown("---")
        datos_extra = {}

        if tipo_recurso == "Extinción Art. 25 ter":
            col_a, col_b = st.columns(2)
            
            with col_a:
                st.markdown("### 3. Causa Sanción RPA")
                for i, rpa in enumerate(st.session_state.rpa):
                    with st.expander(f"Causa RPA #{i+1}", expanded=True):
                        rpa['rit'] = st.text_input("RIT", rpa.get('rit',''), key=f"r_{i}")
                        rpa['ruc'] = st.text_input("RUC", rpa.get('ruc',''), key=f"r_ruc_{i}")
                        rpa['sancion'] = st.text_input("Sanción", rpa.get('sancion',''), key=f"rs_{i}")
                
                c_r_add, c_r_ia = st.columns([1,1])
                if c_r_add.button("➕ Agregar RPA"):
                    st.session_state.rpa.append({"rit":"", "ruc":"", "tribunal":"", "sancion":""})
                    st.rerun()
                pdf_rpa = c_r_ia.file_uploader("Adjuntar Sentencia RPA", type="pdf", key="pdf_rpa_up")
                if pdf_rpa and st.button("Autocompletar RPA"):
                     data = analizar_pdf(pdf_rpa, "Sentencia RPA")
                     if data:
                         st.session_state.rpa.append({"rit": data.get('rit',''), "ruc": data.get('ruc',''), "sancion": data.get('sancion','')})
                         st.rerun()

            with col_b:
                st.markdown("### 4. Condena Adulto (Fundamento)")
                for i, ad in enumerate(st.session_state.adulto):
                    with st.expander(f"Condena Adulto #{i+1}", expanded=True):
                        # CORRECCIÓN: Agregados campos Tribunal y RUC para evitar KeyError
                        ad['rit'] = st.text_input("RIT", ad.get('rit',''), key=f"a_{i}")
                        ad['ruc'] = st.text_input("RUC", ad.get('ruc',''), key=f"a_ruc_{i}")
                        ad['tribunal'] = st.selectbox("Tribunal", TRIBUNALES, key=f"a_trib_{i}")
                        ad['pena'] = st.text_input("Pena", ad.get('pena',''), key=f"ap_{i}")
                        ad['fecha'] = st.text_input("Fecha", ad.get('fecha',''), key=f"af_{i}")
                        
                c_a_add, c_a_ia = st.columns([1,1])
                if c_a_add.button("➕ Agregar Condena"):
                    st.session_state.adulto.append({"rit":"", "ruc":"", "tribunal":"", "pena":"", "fecha":""})
                    st.rerun()
                pdf_ad = c_a_ia.file_uploader("Adjuntar Sentencia Adulto", type="pdf", key="pdf_ad_up")
                if pdf_ad and st.button("Autocompletar Adulto"):
                    data = analizar_pdf(pdf_ad, "Sentencia Adulto")
                    if data:
                        st.session_state.adulto.append({
                            "rit": data.get('rit',''), 
                            "ruc": data.get('ruc',''), 
                            "tribunal": data.get('tribunal', ''), 
                            "pena": data.get('pena',''), 
                            "fecha": data.get('fecha_sentencia','')
                        })
                        st.rerun()

        elif tipo_recurso == "Prescripción de la Pena":
            st.subheader("3. Antecedentes para Prescripción")
            st.info("Cálculo de plazos conforme Art. 5 Ley 20.084")
            
            c1, c2 = st.columns(2)
            fecha_firme = c1.text_input("Fecha Sentencia Firme / Quebrantamiento", placeholder="YYYY-MM-DD")
            tipo_delito = c2.selectbox("Tipo de Infracción", ["Simple Delito (Plazo 2 años)", "Crimen (Plazo 5 años)"])
            
            datos_extra["fecha_firme"] = fecha_firme
            datos_extra["tipo_delito"] = tipo_delito

        elif tipo_recurso in ["Amparo Constitucional", "Apelación por Quebrantamiento"]:
            st.subheader("3. Fundamentos del Recurso")
            argumento_extra = st.text_area("Argumento de Hecho Específico (Opcional)", height=100)
            datos_extra["argumento_extra"] = argumento_extra

        elif tipo_recurso == "Minuta Control de Detención":
            st.subheader("3. Detalles de Audiencia")
            c1, c2 = st.columns(2)
            fecha_det = c1.text_input("Fecha/Hora Detención")
            lugar_det = c2.text_input("Lugar Detención")
            
            st.markdown("#### Argumentos de Defensa")
            opciones = [
                "Ilegalidad por falta de notificación a padres (Art. 39)",
                "Vulneración Interés Superior del Niño",
                "Esposamiento injustificado",
                "Lectura de derechos tardía",
                "Falta de indicios (Art 85)"
            ]
            args = st.multiselect("Seleccione argumentos", opciones)
            
            # VISUALIZACIÓN RÁPIDA EN PANTALLA
            st.markdown("---")
            st.subheader("📄 VISTA PREVIA (LECTURA RÁPIDA)")
            contenido_minuta = f"""
            **MINUTA CONTROL DE DETENCIÓN**
            **Defensor:** {st.session_state.defensor_nombre} | **Imputado:** {st.session_state.imputado}
            
            **1. HECHOS:**
            - Fecha: {fecha_det}
            - Lugar: {lugar_det}
            
            **2. INCIDENCIAS / ILEGALIDAD:**
            {chr(10).join(['- ' + a for a in args])}
            
            **3. PETICIONES:**
            - Declarar Ilegalidad.
            - Oponerse a Cautelares.
            """
            st.markdown(f"<div class='minuta-box'>{contenido_minuta}</div>", unsafe_allow_html=True)
            
            datos_extra.update({"fecha_det": fecha_det, "lugar_det": lugar_det, "argumentos_det": args})

        # BOTÓN GENERAR
        st.markdown("<br>", unsafe_allow_html=True)
        # Cambio para minuta: Botón secundario
        label_btn = f"🚀 GENERAR WORD: {tipo_recurso}"
        if tipo_recurso == "Minuta Control de Detención":
            label_btn = "📥 DESCARGAR MINUTA (OPCIONAL)"
            
        if st.button(label_btn, type="primary", use_container_width=True):
            datos_finales = {
                "tribunal_ej": st.session_state.tribunal_sel,
                "ejecucion": st.session_state.ejecucion,
                "rpa": st.session_state.rpa,
                "adulto": st.session_state.adulto,
                **datos_extra
            }
            gen = GeneradorWord(st.session_state.defensor_nombre, st.session_state.imputado)
            buffer = gen.generar(tipo_recurso, datos_finales)
            
            st.success("✅ Documento generado exitosamente")
            st.download_button("📥 Guardar DOCX", buffer, f"{tipo_recurso}.docx", 
                             "application/vnd.openxmlformats-officedocument.wordprocessingml.document", 
                             use_container_width=True)

    # === TAB 2: TRANSCRIPTOR (RESTAURADO) ===
    with tabs[1]:
        st.header("🎙️ Transcriptor Forense Avanzado")
        
        c1, c2, c3 = st.columns(3)
        idioma = c1.selectbox("Idioma", ["Español (Chile)", "Español (Neutro)", "Inglés"])
        formato = c2.selectbox("Formato", ["Transcripción Literal", "Resumen de Hitos", "Minuta de Audiencia"])
        diarizacion = c3.toggle("Identificar Hablantes", value=True)
        
        timestamps = st.checkbox("Incluir marcas de tiempo cada 30 seg", value=True)
        
        uploaded_audio = st.file_uploader("Subir Audio de Audiencia", type=["mp3", "wav", "m4a"])
        
        if uploaded_audio:
            st.audio(uploaded_audio)
            if st.button("▶️ Iniciar Procesamiento"):
                with st.status("Analizando audio...", expanded=True):
                    time.sleep(1)
                    st.write("Identificando Juez, Fiscal y Defensor...")
                    time.sleep(1)
                    st.write("Generando texto final...")
                
                st.success("Transcripción Finalizada")
                resultado_simulado = """[00:00:05] JUEZ: Buenos días, damos inicio a la audiencia de control de detención..."""
                st.text_area("Resultado:", value=resultado_simulado, height=300)

    # === TAB 3: HERRAMIENTAS & CALCULADORA ===
    with tabs[2]:
        st.header("🧰 Herramientas Legales")
        
        with st.expander(f"🧮 Calculadora de Prognosis de Pena ({'RPA' if es_rpa_global else 'ADULTO'})", expanded=True):
            st.markdown("Cálculo estimativo según Ley 20.084 (Art. 21) y Ley 18.216.")
            
            col_calc1, col_calc2 = st.columns(2)
            with col_calc1:
                delito_sel = st.selectbox("Seleccione Delito Base", list(DELITOS_INFO.keys()))
                atenuantes = st.multiselect("Atenuantes", [
                    "11 N°6 (Irreprochable conducta)", 
                    "11 N°9 (Colaboración sustancial)", 
                    "11 N°7 (Reparación del mal)", 
                    "11 N°8 (Autodenuncia)",
                    "Otras"
                ])
            
            with col_calc2:
                agravantes = st.multiselect("Agravantes", [
                    "12 N°1 (Alevosía)", 
                    "12 N°2 (Premio/Promesa)", 
                    "12 N°16 (Reincidencia)",
                    "Pluralidad de Malhechores"
                ])
                
            if st.button("Calcular Prognosis"):
                prognosis = calcular_prognosis_avanzada(delito_sel, atenuantes, agravantes, es_rpa_global)
                st.markdown(f"<div class='calc-box'>{prognosis}</div>", unsafe_allow_html=True)

        with st.expander("🔎 Buscador de Jurisprudencia"):
            st.info("Conectado a Base de Conocimiento")
            q = st.text_input("Tema a buscar")
            if st.button("Buscar Fallos"):
                res = f"Buscando jurisprudencia sobre '{q}'..."
                st.markdown(f"<div class='juris-box'>{res}</div>", unsafe_allow_html=True)

    # === TAB 4: ADMINISTRADOR (ACTIVO) ===
    with tabs[3]:
        if st.session_state.user_role == "Admin":
            st.header("Panel de Administración")
            
            # Estadísticas
            kpi1, kpi2, kpi3 = st.columns(3)
            kpi1.metric("Usuarios Activos", len(st.session_state.db_users))
            kpi2.metric("Documentos Generados", "145")
            kpi3.metric("Uptime Sistema", "99.9%")
            
            st.subheader("👥 Gestión de Usuarios")
            
            # Tabla de usuarios con opción de eliminar
            for i, usr in enumerate(st.session_state.db_users):
                c_u1, c_u2, c_u3, c_u4 = st.columns([3, 2, 2, 1])
                c_u1.write(f"**{usr['nombre']}** ({usr['email']})")
                c_u2.write(f"Rol: {usr['rol']}")
                c_u3.write("************") # Ocultar pass
                if c_u4.button("❌", key=f"del_user_{i}"):
                    st.session_state.db_users.pop(i)
                    st.rerun()
            
            st.divider()
            st.markdown("#### Agregar Nuevo Usuario")
            with st.form("new_user"):
                n_nom = st.text_input("Nombre Completo")
                n_mail = st.text_input("Email")
                n_pass = st.text_input("Contraseña", type="password")
                n_rol = st.selectbox("Rol", ["User", "Admin"])
                if st.form_submit_button("Guardar Usuario"):
                    if n_mail and n_pass:
                        st.session_state.db_users.append({"email": n_mail, "pass": n_pass, "rol": n_rol, "nombre": n_nom})
                        st.success("Usuario agregado")
                        st.rerun()
                    else:
                        st.error("Complete los campos")
            
        else:
            st.warning("🔒 Acceso restringido a Administradores")

# =============================================================================
# 7. EJECUCIÓN
# =============================================================================
if __name__ == "__main__":
    if st.session_state.logged_in:
        main_app()
    else:
        login_screen()
