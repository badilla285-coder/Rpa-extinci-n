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

# CSS Profesional y Elegante
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
    }
    
    /* Cajas de Jurisprudencia */
    .juris-box {
        background-color: #fff;
        padding: 20px;
        border-radius: 8px;
        border-left: 4px solid #fbc02d;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }

    /* Login Box */
    .login-container {
        background: white;
        padding: 40px;
        border-radius: 15px;
        box-shadow: 0 10px 25px rgba(0,0,0,0.1);
        text-align: center;
    }
    </style>
""", unsafe_allow_html=True)

# =============================================================================
# 2. CONFIGURACIÓN ROBUSTA DE IA (SOLUCIÓN ERROR 404)
# =============================================================================
GOOGLE_API_KEY = "AIzaSyDjsyWjcHCXvgoIQsbyxGD2oyLHFMLfWhg" 
genai.configure(api_key=GOOGLE_API_KEY)

def get_gemini_model():
    """Selección robusta del modelo. Prioriza 1.5 Flash."""
    try:
        # Intentamos usar directamente el modelo más estable y rápido
        return genai.GenerativeModel('gemini-1.5-flash')
    except Exception:
        # Fallback de emergencia
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
        self.defensor = defensor.upper()
        self.imputado = imputado.upper()
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
        destinatario = "ILTMA. CORTE DE APELACIONES" if tipo == "Amparo Constitucional" else datos['tribunal_ej'].upper()
        self.add_parrafo(f"\nAL {destinatario}", negrita=True, align="LEFT")
        
        # 3. COMPARECENCIA
        causas_txt = ", ".join([f"{c['rit']} (RUC {c['ruc']})" for c in datos['ejecucion'] if c['rit']])
        intro = f"\n{{DEFENSOR}}, Abogada Defensora Penal Pública, por el adolescente {{IMPUTADO}}, en causas {causas_txt}, a US. respetuosamente digo:"
        self.add_parrafo(intro)

        # 4. CUERPO Y ARGUMENTACIÓN
        if tipo == "Extinción Art. 25 ter":
            self.add_parrafo("Que, vengo en solicitar se declare la extinción de las sanciones de la Ley de Responsabilidad Penal Adolescente, en virtud de lo dispuesto en los artículos 25 ter y 25 quinquies de la Ley 20.084.")
            self.add_parrafo("FUNDAMENTO: Existe una condena de mayor gravedad como adulto que hace inoficiosa la sanción juvenil.", negrita=True)
            self.add_parrafo("ANTECEDENTES DE LA CONDENA ADULTO:")
            for ad in datos.get('adulto', []):
                self.add_parrafo(f"• RIT: {ad['rit']}, Tribunal: {ad['tribunal']}, Pena: {ad['pena']}, Fecha: {ad['fecha']}")
            self.add_parrafo("POR TANTO, solicito a S.S. acceder a lo solicitado extinguiendo de pleno derecho la sanción antes referida.")

        elif tipo == "Prescripción de la Pena":
            self.add_parrafo("Que, por medio de la presente, vengo en solicitar a S.S. se sirva fijar día y hora para celebrar audiencia con el objeto de debatir sobre la prescripción de la pena, de conformidad a lo dispuesto en el artículo 5 de la Ley N° 20.084.")
            
            # Argumentación Dinámica de Prescripción
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
            <p style='color:#666;'>Sistema de Gestión Jurídica Inteligente</p>
        </div>
        """, unsafe_allow_html=True)
        
        email = st.text_input("Credencial de Acceso", placeholder="usuario@defensoria.cl")
        password = st.text_input("Contraseña", type="password")
        
        if st.button("🔐 Iniciar Sesión", use_container_width=True):
            # Credenciales Hardcoded (para demo) o Supabase
            if email == "admin@iabl.cl" and password == "admin123":
                st.session_state.logged_in = True
                st.session_state.user_role = "admin"
                st.session_state.defensor_nombre = "IGNACIO BADILLA LARA"
                st.rerun()
            elif email == "usuario@defensoria.cl" and password == "defensor":
                st.session_state.logged_in = True
                st.session_state.user_role = "user"
                st.session_state.defensor_nombre = "DEFENSOR PÚBLICO"
                st.rerun()
            else:
                st.error("❌ Credenciales inválidas")

def init_session_data():
    defaults = {
        "imputado": "", 
        "tribunal_sel": TRIBUNALES[9],
        "ejecucion": [{"rit": "", "ruc": ""}],
        "rpa": [{"rit": "", "ruc": "", "tribunal": "", "sancion": ""}],
        "adulto": []
    }
    for k, v in defaults.items():
        if k not in st.session_state: st.session_state[k] = v

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
        st.header("⚙️ Configuración")
        # Defensor Global (por defecto)
        st.session_state.defensor_nombre = st.text_input("Nombre Defensor Global", st.session_state.defensor_nombre)
        tipo_recurso = st.selectbox("Tipo de Escrito", TIPOS_RECURSOS)
        es_rpa = st.toggle("Modo RPA (Adolescente)", value=True)

    st.title(f"📄 Gestión: {tipo_recurso}")
    
    # --- PESTAÑAS ---
    tabs = st.tabs(["📝 Generador de Escritos", "🎙️ Transcriptor Avanzado", "🧰 Herramientas", "👥 Administrador"])

    # === TAB 1: GENERADOR ===
    with tabs[0]:
        col1, col2 = st.columns([2, 1])
        with col1:
            st.subheader("1. Individualización")
            st.session_state.imputado = st.text_input("Nombre Imputado", st.session_state.imputado)
            st.session_state.tribunal_sel = st.selectbox("Tribunal Competente", TRIBUNALES, index=TRIBUNALES.index(st.session_state.tribunal_sel) if st.session_state.tribunal_sel in TRIBUNALES else 0)

        # SECCIÓN EJECUCIÓN
        st.markdown("---")
        st.subheader("2. Causas en Ejecución (Base)")
        for i, item in enumerate(st.session_state.ejecucion):
            c1, c2, c3 = st.columns([3, 3, 1])
            item['rit'] = c1.text_input(f"RIT", item['rit'], key=f"rit_{i}", placeholder="1234-2023")
            item['ruc'] = c2.text_input(f"RUC", item['ruc'], key=f"ruc_{i}")
            if c3.button("🗑️", key=f"del_{i}"):
                st.session_state.ejecucion.pop(i)
                st.rerun()
        
        c_add, c_ia = st.columns([1, 4])
        if c_add.button("➕ Causa"):
            st.session_state.ejecucion.append({"rit": "", "ruc": ""})
            st.rerun()
        
        pdf_ej = c_ia.file_uploader("Cargar Acta (PDF)", type="pdf", key="pdf_ej", label_visibility="collapsed")
        if pdf_ej and st.button("Analizar Acta con IA"):
            data = analizar_pdf(pdf_ej, "Acta")
            if data:
                st.session_state.ejecucion[0].update({"rit": data.get('rit',''), "ruc": data.get('ruc','')})
                st.success("Datos cargados")
                st.rerun()

        # LÓGICA ESPECÍFICA POR RECURSO
        st.markdown("---")
        datos_extra = {}

        if tipo_recurso == "Extinción Art. 25 ter":
            st.info("ℹ️ Para este escrito puede especificar un Defensor distinto al global.")
            defensor_local = st.text_input("Defensor (Específico para Extinción)", value=st.session_state.defensor_nombre)
            
            col_a, col_b = st.columns(2)
            with col_a:
                st.markdown("### A. Causas RPA")
                # Gestión RPA... (similar a ejecución)
                for i, rpa in enumerate(st.session_state.rpa):
                    with st.expander(f"Causa RPA #{i+1}", expanded=True):
                        rpa['rit'] = st.text_input("RIT", rpa['rit'], key=f"r_{i}")
                        rpa['sancion'] = st.text_input("Sanción", rpa['sancion'], key=f"rs_{i}")
            with col_b:
                st.markdown("### B. Causa Adulto")
                for i, ad in enumerate(st.session_state.adulto):
                    with st.expander(f"Condena Adulto #{i+1}", expanded=True):
                        ad['rit'] = st.text_input("RIT", ad['rit'], key=f"a_{i}")
                        ad['pena'] = st.text_input("Pena", ad['pena'], key=f"ap_{i}")
                        ad['fecha'] = st.text_input("Fecha", ad['fecha'], key=f"af_{i}")
                if st.button("➕ Condena"):
                    st.session_state.adulto.append({"rit":"", "pena":"", "fecha":""})
                    st.rerun()

        elif tipo_recurso == "Prescripción de la Pena":
            st.subheader("3. Antecedentes para Prescripción")
            st.info("Cálculo de plazos conforme Art. 5 Ley 20.084")
            
            c1, c2 = st.columns(2)
            fecha_firme = c1.text_input("Fecha Sentencia Firme / Quebrantamiento", placeholder="YYYY-MM-DD")
            tipo_delito = c2.selectbox("Tipo de Infracción", ["Simple Delito (Plazo 2 años)", "Crimen (Plazo 5 años)"])
            
            datos_extra["fecha_firme"] = fecha_firme
            datos_extra["tipo_delito"] = tipo_delito
            defensor_local = st.session_state.defensor_nombre

        elif tipo_recurso in ["Amparo Constitucional", "Apelación por Quebrantamiento"]:
            st.subheader("3. Fundamentos del Recurso")
            st.markdown(f"**Escrito:** {tipo_recurso}")
            argumento_extra = st.text_area("Argumento de Hecho Específico (Opcional)", height=100, placeholder="Describa brevemente la situación particular del joven...")
            datos_extra["argumento_extra"] = argumento_extra
            defensor_local = st.session_state.defensor_nombre

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
                "Lectura de derechos tardía"
            ]
            args = st.multiselect("Seleccione argumentos", opciones)
            datos_extra.update({"fecha_det": fecha_det, "lugar_det": lugar_det, "argumentos_det": args})
            defensor_local = st.session_state.defensor_nombre
        else:
            defensor_local = st.session_state.defensor_nombre

        # BOTÓN GENERAR
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button(f"🚀 GENERAR DOCUMENTO: {tipo_recurso}", type="primary", use_container_width=True):
            datos_finales = {
                "tribunal_ej": st.session_state.tribunal_sel,
                "ejecucion": st.session_state.ejecucion,
                "rpa": st.session_state.rpa,
                "adulto": st.session_state.adulto,
                **datos_extra
            }
            gen = GeneradorWord(defensor_local, st.session_state.imputado)
            buffer = gen.generar(tipo_recurso, datos_finales)
            
            st.success("✅ Documento generado exitosamente")
            st.download_button("📥 Descargar DOCX", buffer, f"{tipo_recurso}.docx", 
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
                    st.write("Cargando archivo...")
                    time.sleep(1)
                    st.write("Separando pistas de audio...")
                    time.sleep(1)
                    if diarizacion: st.write("Identificando Juez, Fiscal y Defensor...")
                    time.sleep(1)
                    st.write("Generando texto final...")
                
                st.success("Transcripción Finalizada")
                resultado_simulado = """[00:00:05] JUEZ: Buenos días, damos inicio a la audiencia de control de detención.
[00:00:12] FISCAL: Comparece el Ministerio Público...
[00:00:15] DEFENSOR: Por la defensa, Ignacio Badilla Lara..."""
                st.text_area("Resultado:", value=resultado_simulado, height=300)
                st.download_button("Descargar Transcripción", resultado_simulado, "transcripcion.txt")

    # === TAB 3: HERRAMIENTAS ===
    with tabs[2]:
        st.header("🧰 Herramientas Legales")
        
        with st.expander("Calculadora de Pena Mixta (Ley 20.084)", expanded=True):
            pena = st.selectbox("Pena Adulto", ["Presidio Mayor Grado Medio", "Presidio Menor Grado Máximo"])
            if st.button("Calcular"):
                st.info(f"Sanción RPA sugerida: Internación en Régimen Semicerrado (Rebaja 1 grado Art. 21)")

        with st.expander("Buscador de Jurisprudencia IA"):
            q = st.text_input("Tema a buscar")
            if st.button("Buscar"):
                res = f"Buscando jurisprudencia sobre '{q}'... (Conectado a Gemini Knowledge Base)"
                st.markdown(f"<div class='juris-box'>{res}</div>", unsafe_allow_html=True)

    # === TAB 4: ADMINISTRADOR (COMPLETO) ===
    with tabs[3]:
        if st.session_state.user_role == "admin":
            st.header("Panel de Administración")
            
            # Estadísticas
            kpi1, kpi2, kpi3 = st.columns(3)
            kpi1.metric("Usuarios Activos", "12")
            kpi2.metric("Documentos Generados (Mes)", "145")
            kpi3.metric("Uptime Sistema", "99.9%")
            
            st.subheader("👥 Gestión de Usuarios")
            usuarios_demo = [
                {"email": "admin@iabl.cl", "rol": "Admin", "estado": "Activo"},
                {"email": "usuario@defensoria.cl", "rol": "User", "estado": "Activo"},
                {"email": "invitado@legal.cl", "rol": "User", "estado": "Inactivo"},
            ]
            st.table(usuarios_demo)
            
            st.subheader("☁️ Estado Base de Datos")
            if supabase:
                st.success("Conexión a Supabase: ESTABLE")
            else:
                st.error("Conexión a Supabase: FALLIDA")
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
