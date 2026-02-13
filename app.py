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

# =============================================================================
# CONFIGURACIÓN INICIAL
# =============================================================================

st.set_page_config(
    page_title="Acceso a Generador de Escritos IABL", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# Configuración de IA (Google AI Studio)
GOOGLE_API_KEY = "AIzaSyDjsyWjcHCXvgoIQsbyxGD2oyLHFMLfWhg"
genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

# Configuración de Base de Datos (Supabase)
SUPABASE_URL = "https://zblcddxbhyomkasmbvyz.supabase.co"
SUPABASE_KEY = "sb_publishable_pHMqXxI39AssehHdBs1wqA_NVjPc-FT"

@st.cache_resource
def init_supabase():
    """Inicializa conexión con Supabase con manejo de errores mejorado"""
    try:
        return create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception as e:
        st.error(f"❌ Error crítico en conexión con Supabase: {e}")
        return None

supabase = init_supabase()

# =============================================================================
# CONSTANTES Y CONFIGURACIÓN
# =============================================================================

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

TIPOS_RECURSOS = [
    "Extinción Art. 25 ter", 
    "Prescripción de la Pena", 
    "Amparo Constitucional", 
    "Apelación por Quebrantamiento"
]

# =============================================================================
# FUNCIONES DE ANÁLISIS DE IA
# =============================================================================

def analizar_pdf_legal(texto_pdf: str, categoria: str) -> dict:
    """
    Analiza documentos legales usando Gemini 1.5 Flash
    Retorna datos estructurados en formato JSON
    """
    prompt = f"""
    Eres un experto legal chileno especializado en análisis de documentos judiciales.
    Analiza este texto de {categoria} y extrae los datos más relevantes.
    
    Responde ÚNICAMENTE con un JSON válido con esta estructura exacta:
    {{
        "ruc": "00.000.000-0",
        "rit": "O-000-0000", 
        "tribunal": "Nombre exacto del juzgado",
        "imputado": "Nombre completo del imputado",
        "fecha_sentencia": "YYYY-MM-DD",
        "sancion_pena": "Descripción completa de la condena",
        "es_rpa": true
    }}
    
    IMPORTANTE: Si no encuentras algún dato, usa "" para strings y null para fechas.
    
    Texto a analizar:
    {texto_pdf[:3000]}
    """
    
    try:
        with st.spinner(f"🤖 Analizando {categoria} con IA..."):
            response = model.generate_content(prompt)
            texto_limpio = response.text.replace('```json', '').replace('```', '').strip()
            
            # Validación adicional del JSON
            datos = json.loads(texto_limpio)
            
            # Validaciones de formato
            if datos.get("ruc") and not re.match(r'\d{7,10}-[\dkK]', datos["ruc"]):
                datos["ruc"] = ""
            if datos.get("rit") and not re.match(r'[A-Z]-\d+-\d{4}', datos["rit"]):
                datos["rit"] = ""
                
            return datos
            
    except json.JSONDecodeError as e:
        st.error(f"❌ Error al procesar respuesta de IA: {e}")
        return None
    except Exception as e:
        st.error(f"❌ Error en análisis de IA: {e}")
        return None

def calcular_semaforo_prescripcion(fecha_sentencia: str, es_rpa: bool) -> str:
    """
    Sistema de semaforización diferenciada para plazos de prescripción
    - RPA (Art. 5 Ley 20.084): 2 años simples delitos, 5 años crímenes
    - Adultos (Código Penal): 5 años simples delitos, 10-15 años crímenes
    """
    if not fecha_sentencia:
        return "⚪ **Datos incompletos** - Sube sentencia para calcular"
    
    try:
        fecha_sent = datetime.strptime(fecha_sentencia, "%Y-%m-%d")
        fecha_actual = datetime.now()
        años_transcurridos = (fecha_actual - fecha_sent).days / 365.25
        
        # Determinación de plazos según normativa
        plazo_legal = 2.0 if es_rpa else 5.0
        tipo_normativa = "Ley 20.084 (RPA)" if es_rpa else "Código Penal (Adultos)"
        
        if años_transcurridos >= plazo_legal:
            return f"🟢 **APTA PARA PRESCRIPCIÓN**\n📅 {round(años_transcurridos, 1)} años transcurridos\n⚖️ Plazo legal: {plazo_legal} años ({tipo_normativa})"
        else:
            años_faltantes = round(plazo_legal - años_transcurridos, 1)
            return f"🔴 **EN PERÍODO DE ESPERA**\n⏳ Faltan {años_faltantes} años\n⚖️ Plazo legal: {plazo_legal} años ({tipo_normativa})"
            
    except ValueError:
        return "❌ **Error en formato de fecha** - Verificar datos"
    except Exception as e:
        return f"❌ **Error en cálculo**: {str(e)}"

# =============================================================================
# MOTOR DE GENERACIÓN DE DOCUMENTOS WORD
# =============================================================================

class GeneradorDocumentosLegales:
    """
    Motor avanzado de generación de escritos legales en formato DOCX
    Mantiene formato profesional y estándares judiciales chilenos
    """
    
    def __init__(self, defensor: str, adolescente: str):
        self.fuente_principal = "Cambria"
        self.tamaño_fuente = 12
        self.defensor = defensor.strip()
        self.adolescente = adolescente.strip()
    
    def _aplicar_formato_profesional(self, doc, texto: str, negrita_completa=False, 
                                   sangria=True, alineacion="JUSTIFY") -> None:
        """Aplica formato profesional con reconocimiento inteligente de elementos legales"""
        
        parrafo = doc.add_paragraph()
        
        # Configuración de alineación
        if alineacion == "LEFT":
            parrafo.alignment = WD_ALIGN_PARAGRAPH.LEFT
        elif alineacion == "CENTER":
            parrafo.alignment = WD_ALIGN_PARAGRAPH.CENTER
        else:
            parrafo.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        
        # Configuración de espaciado y sangría
        parrafo.paragraph_format.line_spacing_rule = WD_LINE_SPACING.ONE_POINT_FIVE
        if sangria:
            parrafo.paragraph_format.first_line_indent = Inches(0.5)
        
        # Patrón para elementos que requieren negrita
        defensor_escapado = re.escape(self.defensor.upper())
        adolescente_escapado = re.escape(self.adolescente.upper())
        
        patron_negrita = (
            r"(RIT:?\s?\d+-\d{4}|RUC:?\s?\d{7,10}-[\dkK]|"
            r"POR TANTO|OTROSÍ|SOLICITA|INTERPONE|ACCIÓN CONSTITUCIONAL|"
            r"EN LO PRINCIPAL|ILTMA\.|S\.S\.|V\.S\.I|"
            rf"{defensor_escapado}|{adolescente_escapado})"
        )
        
        # División del texto y aplicación de formato
        fragmentos = re.split(patron_negrita, texto, flags=re.IGNORECASE)
        
        for fragmento in fragmentos:
            if not fragmento:
                continue
                
            run = parrafo.add_run(fragmento)
            run.font.name = self.fuente_principal
            run.font.size = Pt(self.tamaño_fuente)
            
            # Aplicar negrita según criterios
            if negrita_completa or re.match(patron_negrita, fragmento, re.IGNORECASE):
                run.bold = True
    
    def generar_escrito_legal(self, tipo_recurso: str, datos: dict) -> io.BytesIO:
        """
        Genera documento Word según el tipo de recurso solicitado
        Mantiene estructura y contenido legal profesional
        """
        documento = Document()
        
        # Configuración de márgenes
        for seccion in documento.sections:
            seccion.left_margin = Inches(1.2)
            seccion.right_margin = Inches(1.0)
            seccion.top_margin = Inches(1.0)
            seccion.bottom_margin = Inches(1.0)
        
        # Generación según tipo de recurso
        if tipo_recurso == "Extinción Art. 25 ter":
            self._generar_extincion_25ter(documento, datos)
        elif tipo_recurso == "Prescripción de la Pena":
            self._generar_prescripcion_pena(documento, datos)
        elif tipo_recurso == "Amparo Constitucional":
            self._generar_amparo_constitucional(documento, datos)
        elif tipo_recurso == "Apelación por Quebrantamiento":
            self._generar_apelacion_quebrantamiento(documento, datos)
        
        # Conversión a BytesIO para descarga
        buffer = io.BytesIO()
        documento.save(buffer)
        buffer.seek(0)
        return buffer
    
    def _generar_extincion_25ter(self, doc, datos):
        """Genera escrito de Extinción Art. 25 ter"""
        self._aplicar_formato_profesional(
            doc, 
            "EN LO PRINCIPAL: SOLICITA EXTINCIÓN; OTROSÍ: ACOMPAÑA SENTENCIA", 
            negrita_completa=True, sangria=False, alineacion="LEFT"
        )
        
        self._aplicar_formato_profesional(
            doc, f"\n{datos.get('juzgado_ejecucion', '').upper()}", 
            negrita_completa=True, sangria=False
        )
        
        comparecencia = (
            f"\n{self.defensor.upper()}, Abogada, Defensora Penal Pública, "
            f"en representación de {self.adolescente.upper()}, "
            f"en causas de ejecución {datos.get('causas_ej_str', '')}, "
            f"a S.S., respetuosamente digo:"
        )
        self._aplicar_formato_profesional(doc, comparecencia)
        
        self._aplicar_formato_profesional(
            doc, 
            "Que, vengo en solicitar que se declare la extinción de las sanciones "
            "de la Ley de Responsabilidad Penal Adolescente, o en subsidio se fije "
            "día y hora para celebrar audiencia para debatir sobre la extinción de "
            "la pena respecto de mi representado, en virtud de lo dispuesto en los "
            "artículos 25 ter y 25 quinquies de la Ley 20.084."
        )
        
        self._aplicar_formato_profesional(
            doc,
            "El fundamento radica en la existencia de una condena de mayor gravedad "
            "como adulto, la cual se detalla a continuación."
        )
        
        self._aplicar_formato_profesional(
            doc,
            "POR TANTO, SOLICITO A S.S. acceder a lo solicitado extinguiendo de "
            "pleno derecho la sanción antes referida."
        )
        
        self._aplicar_formato_profesional(
            doc,
            f"OTROSÍ: Acompaña sentencia de adulto de las causas {datos.get('causas_adulto_str', '')}",
            negrita_completa=True, sangria=False
        )
    
    def _generar_prescripcion_pena(self, doc, datos):
        """Genera escrito de Prescripción de la Pena"""
        self._aplicar_formato_profesional(
            doc,
            "EN LO PRINCIPAL: SOLICITA AUDIENCIA DE PRESCRIPCIÓN; OTROSÍ: OFICIA A EXTRANJERÍA Y ADJUNTA ANTECEDENTES",
            negrita_completa=True, sangria=False, alineacion="LEFT"
        )
        
        self._aplicar_formato_profesional(
            doc, f"\n{datos.get('juzgado_ejecucion', '').upper()}",
            negrita_completa=True, sangria=False
        )
        
        comparecencia = (
            f"\n{self.defensor.upper()}, Abogada, Defensora Penal Pública, "
            f"en representación de {self.adolescente.upper()}, "
            f"en causas {datos.get('causas_str', '')}, a S.S. respetuosamente digo:"
        )
        self._aplicar_formato_profesional(doc, comparecencia)
        
        self._aplicar_formato_profesional(
            doc,
            "Que, por medio de la presente, vengo en solicitar a S.S. se sirva "
            "fijar día y hora para celebrar audiencia con el objeto de debatir "
            "sobre la prescripción de la pena respecto de mi representado, de "
            "conformidad a lo dispuesto en el artículo 5 de la Ley N° 20.084 "
            "y las normas pertinentes del Código Penal."
        )
        
        self._aplicar_formato_profesional(
            doc,
            "Teniendo presente el tiempo transcurrido desde que las referidas "
            "sentencias quedaron ejecutoriadas, ha transcurrido en exceso el "
            "plazo legal exigido."
        )
        
        self._aplicar_formato_profesional(
            doc,
            "POR TANTO, SOLICITO A S.S. acceder a lo solicitado, fijando día "
            "y hora para celebrar audiencia y declarar el sobreseimiento definitivo."
        )
        
        self._aplicar_formato_profesional(
            doc,
            "OTROSÍ: Solicito se oficie a Extranjería para informar movimientos "
            "migratorios y se incorpore Extracto de Filiación actualizado.",
            negrita_completa=True, sangria=False
        )
    
    def _generar_amparo_constitucional(self, doc, datos):
        """Genera escrito de Amparo Constitucional"""
        self._aplicar_formato_profesional(
            doc,
            "INTERPONE ACCIÓN CONSTITUCIONAL DE AMPARO; OTROSÍ: ORDEN DE NO INNOVAR",
            negrita_completa=True, sangria=False, alineacion="LEFT"
        )
        
        self._aplicar_formato_profesional(
            doc, "\nILTMA. CORTE DE APELACIONES DE SANTIAGO",
            negrita_completa=True, sangria=False
        )
        
        comparecencia = (
            f"\n{self.defensor.upper()}, abogada, Defensora Penal Juvenil, "
            f"en representación de {self.adolescente.upper()}, "
            f"en causa RIT {datos.get('rit_prin', '')}, "
            f"RUC {datos.get('ruc_prin', '')} del Juzgado de Garantía, "
            f"a V.S.I respetuosamente digo:"
        )
        self._aplicar_formato_profesional(doc, comparecencia)
        
        self._aplicar_formato_profesional(
            doc,
            "Que, en virtud de lo dispuesto en el artículo 21 de la Constitución "
            "Política de la República, vengo en deducir acción constitucional de "
            "amparo por la perturbación grave e ilegítima a la libertad personal, "
            "emanada de la resolución que ordenó el ingreso inmediato del joven, "
            "siendo esta ilegal y arbitraria."
        )
        
        self._aplicar_formato_profesional(
            doc,
            "La resolución infringe el artículo 79 del Código Penal que establece "
            "que 'no podrá ejecutarse pena alguna sino en virtud de sentencia ejecutoriada'."
        )
        
        self._aplicar_formato_profesional(
            doc,
            "POR TANTO, SOLICITO A V.S. ILTMA. dejar sin efecto la resolución "
            "recurrida y restablecer el imperio del derecho."
        )
        
        self._aplicar_formato_profesional(
            doc,
            "OTROSÍ: Solicito Orden de No Innovar para suspender los efectos "
            "de la ilegalidad atacada.",
            negrita_completa=True, sangria=False
        )
    
    def _generar_apelacion_quebrantamiento(self, doc, datos):
        """Genera escrito de Apelación por Quebrantamiento"""
        self._aplicar_formato_profesional(
            doc,
            "EN LO PRINCIPAL: INTERPONE RECURSO DE APELACIÓN; OTROSÍ: FORMA DE NOTIFICACIÓN",
            negrita_completa=True, sangria=False, alineacion="LEFT"
        )
        
        self._aplicar_formato_profesional(
            doc, f"\n{datos.get('juzgado_ejecucion', '').upper()}",
            negrita_completa=True, sangria=False
        )
        
        comparecencia = (
            f"\n{self.defensor.upper()}, abogada, Defensora Penal Juvenil, "
            f"en representación de don {self.adolescente.upper()}, "
            f"a V.S.I respetuosamente digo:"
        )
        self._aplicar_formato_profesional(doc, comparecencia)
        
        self._aplicar_formato_profesional(
            doc,
            "Que encontrándome dentro del plazo legal, vengo en interponer recurso "
            "de apelación en contra de la resolución que ordenó el quebrantamiento "
            "definitivo, solicitando sea revocado conforme a los artículos 52 y "
            "siguientes de la Ley 20.084."
        )
        
        self._aplicar_formato_profesional(
            doc,
            "La aplicación de una sanción en régimen cerrado no permite hacer "
            "efectiva la reinserción social, privando la posibilidad de continuar "
            "actividades laborales o educativas."
        )
        
        self._aplicar_formato_profesional(
            doc,
            "POR TANTO, SOLICITO A US. tener por interpuesto el recurso para que "
            "la Iltma. Corte de Apelaciones de San Miguel revoque la resolución "
            "y mantenga la sanción en Régimen Semicerrado."
        )

# =============================================================================
# FUNCIONES DE PERSISTENCIA Y GESTIÓN DE DATOS
# =============================================================================

def guardar_gestion_en_bd(ruc: str, rit: str, tribunal: str, tipo_recurso: str, contenido: str) -> bool:
    """
    Guarda gestión en Supabase con manejo robusto de errores
    Utiliza las columnas exactas requeridas por la base de datos
    """
    if not supabase:
        st.error("❌ No hay conexión con la base de datos")
        return False
    
    try:
        datos_insercion = {
            "RUC": ruc or "Sin RUC",
            "RIT": rit or "Sin RIT", 
            "TRIBUNAL / JUZGADO": tribunal,
            "TIPO_RECURSO": tipo_recurso,
            "CONTENIDO_ESCRITO": contenido
        }
        
        resultado = supabase.table("Gestiones").insert(datos_insercion).execute()
        
        if resultado.data:
            return True
        else:
            st.error("❌ Error al insertar en base de datos")
            return False
            
    except Exception as e:
        st.error(f"❌ Error crítico en base de datos: {str(e)}")
        return False

def extraer_texto_pdf(archivo_pdf) -> str:
    """Extrae texto de PDF con manejo de errores mejorado"""
    try:
        lector = PyPDF2.PdfReader(archivo_pdf)
        texto_completo = ""
        
        # Limitar a las primeras 5 páginas para optimizar procesamiento
        paginas_a_procesar = min(len(lector.pages), 5)
        
        for i in range(paginas_a_procesar):
            texto_completo += lector.pages[i].extract_text() + "\n"
        
        return texto_completo.strip()
        
    except Exception as e:
        st.error(f"❌ Error al procesar PDF: {str(e)}")
        return ""

def transcribir_audio_audiencia(archivo_audio) -> str:
    """
    Función preparada para transcripción de audio con IA
    Integración futura con Gemini 1.5 Pro para audios largos
    """
    st.info("🎙️ Función de transcripción íntegra activada. Procesando audio...")
    st.info("⚠️ Módulo en desarrollo - Integración con Gemini 1.5 Pro próximamente")
    
    # Aquí iría la lógica de transcripción real
    return "Texto íntegro de la audiencia transcrito por IA (Función en desarrollo)..."

# =============================================================================
# SISTEMA DE AUTENTICACIÓN
# =============================================================================

def verificar_credenciales() -> bool:
    """Sistema de autenticación mejorado con mejor UX"""
    
    if "usuario_autenticado" not in st.session_state:
        st.markdown("""
        <div style='text-align: center; padding: 2rem;'>
            <h1>🔐 Acceso a Generador de Escritos IABL</h1>
            <p style='color: #666; font-size: 1.1rem;'>Sistema Profesional de Generación de Documentos Legales</p>
        </div>
        """, unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns([1, 2, 1])
        
        with col2:
            with st.container():
                st.markdown("### Credenciales de Acceso")
                
                email_usuario = st.text_input(
                    "📧 Email Institucional", 
                    placeholder="usuario@defensoria.cl"
                )
                
                contraseña_usuario = st.text_input(
                    "🔑 Contraseña", 
                    type="password",
                    placeholder="Ingrese su contraseña"
                )
                
                col_btn1, col_btn2 = st.columns(2)
                
                with col_btn1:
                    if st.button("🚀 Ingresar al Sistema", use_container_width=True):
                        if validar_usuario(email_usuario, contraseña_usuario):
                            st.session_state["usuario_autenticado"] = email_usuario
                            st.session_state["nombre_usuario"] = st.session_state.base_usuarios[email_usuario]["nombre"]
                            st.session_state["es_administrador"] = (st.session_state.base_usuarios[email_usuario]["nivel"] == "Admin")
                            st.success("✅ Acceso autorizado")
                            st.rerun()
                        else:
                            st.error("❌ Credenciales incorrectas")
                
                with col_btn2:
                    if st.button("ℹ️ Ayuda", use_container_width=True):
                        st.info("Contacte al administrador del sistema para obtener credenciales")
        
        return False
    
    return True

def validar_usuario(email: str, contraseña: str) -> bool:
    """Valida credenciales contra base de usuarios"""
    usuarios_validos = st.session_state.get("base_usuarios", {})
    return (email in usuarios_validos and 
            usuarios_validos[email]["pw"] == contraseña)

# =============================================================================
# INICIALIZACIÓN DE ESTADO DE SESIÓN
# =============================================================================

def inicializar_estado_sesion():
    """Inicializa todas las variables de estado de sesión"""
    
    if "base_usuarios" not in st.session_state:
        st.session_state.base_usuarios = {
            "badilla285@gmail.com": {
                "nombre": "IGNACIO BADILLA LARA", 
                "pw": "RPA2026", 
                "nivel": "Admin"
            }
        }
    
    if "datos_formulario" not in st.session_state:
        st.session_state.datos_formulario = {
            "nombre_imputado": "",
            "juzgado_seleccionado": "Juzgado de Garantía de San Bernardo",
            "lista_causas_rpa": [],
            "lista_causas_adulto": [],
            "lista_ejecucion": [{"rit": "", "ruc": ""}],
            "fecha_sentencia_adulto": None,
            "es_rpa_para_semaforo": True
        }
    
    if "creditos_legales" not in st.session_state:
        st.session_state.creditos_legales = 50  # Créditos iniciales

# =============================================================================
# INTERFAZ PRINCIPAL DE STREAMLIT
# =============================================================================

def main():
    """Función principal de la aplicación"""
    
    # Inicialización
    inicializar_estado_sesion()
    
    # Verificación de autenticación
    if not verificar_credenciales():
        return
    
    # Sidebar con información del usuario y configuración
    with st.sidebar:
        st.markdown("### 💼 Suite Legal IABL Pro")
        st.markdown(f"**Usuario:** {st.session_state.get('nombre_usuario', 'Usuario')}")
        
        # Módulo de créditos y suscripciones
        st.markdown("---")
        st.markdown("### 💳 Gestión de Créditos")
        
        creditos_actuales = st.session_state.get("creditos_legales", 0)
        
        if creditos_actuales < 10:
            st.warning(f"⚠️ Saldo bajo: {creditos_actuales} LegalCoins")
            if st.button("💳 Adquirir Créditos"):
                st.info("🔄 Redirigiendo a pasarela de pagos segura (Stripe/Webpay)...")
        else:
            st.success(f"✅ Créditos disponibles: {creditos_actuales}")
        
        # Selector de tipo de recurso
        st.markdown("---")
        st.markdown("### 📝 Tipo de Recurso")
        tipo_recurso_seleccionado = st.selectbox(
            "Seleccione el recurso a generar:",
            TIPOS_RECURSOS,
            help="Elija el tipo de escrito legal que desea generar"
        )
        
        # Semáforo de plazos inteligente
        st.markdown("---")
        st.markdown("### 📊 Semáforo de Plazos")
        
        fecha_para_calculo = st.session_state.datos_formulario.get("fecha_sentencia_adulto")
        es_rpa_calculo = st.session_state.datos_formulario.get("es_rpa_para_semaforo", True)
        
        if fecha_para_calculo:
            estado_semaforo = calcular_semaforo_prescripcion(fecha_para_calculo, es_rpa_calculo)
            st.markdown(estado_semaforo)
        else:
            st.info("📄 Suba una sentencia para activar el cálculo de plazos")
    
    # Pestañas principales de la aplicación
    tab_ia, tab_transcriptor, tab_formulario, tab_administracion = st.tabs([
        "🤖 Análisis Inteligente (IA)",
        "🎙️ Transcriptor de Audiencias", 
        "📄 Generación de Escritos",
        "⚙️ Administración"
    ])
    
    # TAB 1: Análisis con IA
    with tab_ia:
        st.markdown("## ⚡ Asistente Gemini 1.5 Flash")
        st.markdown("Automatice el llenado de datos mediante análisis inteligente de documentos PDF")
        
        col_ejecucion, col_rpa, col_adulto = st.columns(3)
        
        with col_ejecucion:
            st.markdown("### 📋 1. Acta de Ejecución")
            archivo_ejecucion = st.file_uploader(
                "Subir Acta de Ejecución", 
                type=["pdf"], 
                key="upload_ejecucion",
                help="Documento que contiene los datos de la causa en ejecución"
            )
            
            if archivo_ejecucion and st.button("🔍 Procesar Ejecución", key="btn_procesar_ejecucion"):
                texto_extraido = extraer_texto_pdf(archivo_ejecucion)
                if texto_extraido:
                    resultado_analisis = analizar_pdf_legal(texto_extraido, "Acta de Ejecución")
                    if resultado_analisis:
                        # Actualizar datos del formulario
                        st.session_state.datos_formulario["lista_ejecucion"][0]["rit"] = resultado_analisis.get("rit", "")
                        st.session_state.datos_formulario["lista_ejecucion"][0]["ruc"] = resultado_analisis.get("ruc", "")
                        st.session_state.datos_formulario["nombre_imputado"] = resultado_analisis.get("imputado", "")
                        
                        tribunal_detectado = resultado_analisis.get("tribunal", "")
                        if tribunal_detectado in TRIBUNALES_STGO_SM:
                            st.session_state.datos_formulario["juzgado_seleccionado"] = tribunal_detectado
                        
                        st.success("✅ Datos de ejecución cargados automáticamente")
                        st.json(resultado_analisis)
        
        with col_rpa:
            st.markdown("### ⚖️ 2. Sentencia RPA")
            archivo_rpa = st.file_uploader(
                "Subir Sentencia Ley 20.084", 
                type=["pdf"], 
                key="upload_rpa",
                help="Sentencia de la Ley de Responsabilidad Penal Adolescente"
            )
            
            if archivo_rpa and st.button("🔍 Procesar RPA", key="btn_procesar_rpa"):
                texto_extraido = extraer_texto_pdf(archivo_rpa)
                if texto_extraido:
                    resultado_analisis = analizar_pdf_legal(texto_extraido, "Sentencia RPA")
                    if resultado_analisis:
                        nueva_causa_rpa = {
                            "rit": resultado_analisis.get("rit", ""),
                            "ruc": resultado_analisis.get("ruc", ""),
                            "tribunal": resultado_analisis.get("tribunal", ""),
                            "sancion": resultado_analisis.get("sancion_pena", "")
                        }
                        st.session_state.datos_formulario["lista_causas_rpa"].append(nueva_causa_rpa)
                        st.session_state.datos_formulario["es_rpa_para_semaforo"] = True
                        
                        st.success("✅ Sentencia RPA agregada al expediente")
                        st.json(resultado_analisis)
        
        with col_adulto:
            st.markdown("### 👨‍⚖️ 3. Sentencia Adulto")
            archivo_adulto = st.file_uploader(
                "Subir Sentencia de Adulto", 
                type=["pdf"], 
                key="upload_adulto",
                help="Sentencia bajo el Código Penal (adultos)"
            )
            
            if archivo_adulto and st.button("🔍 Procesar Adulto", key="btn_procesar_adulto"):
                texto_extraido = extraer_texto_pdf(archivo_adulto)
                if texto_extraido:
                    resultado_analisis = analizar_pdf_legal(texto_extraido, "Sentencia Adulto")
                    if resultado_analisis:
                        nueva_causa_adulto = {
                            "rit": resultado_analisis.get("rit", ""),
                            "ruc": resultado_analisis.get("ruc", ""),
                            "tribunal": resultado_analisis.get("tribunal", ""),
                            "pena": resultado_analisis.get("sancion_pena", ""),
                            "fecha": resultado_analisis.get("fecha_sentencia", "")
                        }
                        st.session_state.datos_formulario["lista_causas_adulto"].append(nueva_causa_adulto)
                        st.session_state.datos_formulario["fecha_sentencia_adulto"] = resultado_analisis.get("fecha_sentencia", "")
                        st.session_state.datos_formulario["es_rpa_para_semaforo"] = False
                        
                        st.success("✅ Sentencia de adulto cargada - Semáforo activado")
                        st.json(resultado_analisis)
    
    # TAB 2: Transcriptor de Audio
    with tab_transcriptor:
        st.markdown("## 🎙️ Transcriptor Inteligente de Audiencias")
        st.markdown("Convierta audio de audiencias judiciales en texto íntegro mediante IA")
        
        col_upload, col_config = st.columns([2, 1])
        
        with col_upload:
            archivo_audio = st.file_uploader(
                "📁 Subir Audio de Audiencia",
                type=["mp3", "wav", "m4a", "ogg"],
                help="Formatos soportados: MP3, WAV, M4A, OGG"
            )
            
            if archivo_audio:
                st.audio(archivo_audio)
                
                if st.button("🎯 Iniciar Transcripción Completa"):
                    texto_transcrito = transcribir_audio_audiencia(archivo_audio)
                    
                    st.markdown("### 📝 Resultado de la Transcripción")
                    st.text_area(
                        "Texto transcrito:",
                        value=texto_transcrito,
                        height=400,
                        help="Transcripción generada automáticamente por IA"
                    )
                    
                    # Opción de descarga
                    st.download_button(
                        "💾 Descargar Transcripción",
                        texto_transcrito,
                        file_name=f"transcripcion_audiencia_{datetime.now().strftime('%Y%m%d_%H%M')}.txt",
                        mime="text/plain"
                    )
        
        with col_config:
            st.markdown("### ⚙️ Configuración")
            st.info("🔧 Configuraciones avanzadas de transcripción próximamente")
    
    # TAB 3: Formulario de Generación
    with tab_formulario:
        st.markdown(f"## 📄 Generación: {tipo_recurso_seleccionado}")
        
        with st.form("formulario_principal_legal"):
            st.markdown("### 👤 Datos de Individualización")
            
            col_defensor, col_imputado = st.columns(2)
            
            with col_defensor:
                nombre_defensor = st.text_input(
                    "👩‍⚖️ Defensor/a:",
                    value=st.session_state.get("nombre_usuario", ""),
                    help="Nombre completo del defensor público"
                )
            
            with col_imputado:
                nombre_imputado = st.text_input(
                    "👤 Nombre del Adolescente:",
                    value=st.session_state.datos_formulario["nombre_imputado"],
                    help="Nombre completo del adolescente imputado"
                )
            
            # Selector de tribunal
            tribunal_seleccionado = st.selectbox(
                "🏛️ Juzgado de Ejecución:",
                TRIBUNALES_STGO_SM,
                index=TRIBUNALES_STGO_SM.index(st.session_state.datos_formulario["juzgado_seleccionado"]) 
                      if st.session_state.datos_formulario["juzgado_seleccionado"] in TRIBUNALES_STGO_SM else 0,
                help="Seleccione el tribunal competente"
            )
            
            # Mostrar datos cargados por IA
            if st.session_state.datos_formulario["lista_ejecucion"][0]["rit"]:
                st.markdown("### 📋 Datos Cargados por IA")
                col_rit, col_ruc = st.columns(2)
                
                with col_rit:
                    st.info(f"**RIT:** {st.session_state.datos_formulario['lista_ejecucion'][0]['rit']}")
                
                with col_ruc:
                    st.info(f"**RUC:** {st.session_state.datos_formulario['lista_ejecucion'][0]['ruc']}")
            
            st.markdown("---")
            
            # Botón de generación
            if st.form_submit_button(f"⚖️ GENERAR Y GUARDAR {tipo_recurso_seleccionado.upper()}", use_container_width=True):
                
                if not nombre_imputado.strip():
                    st.error("❌ El nombre del adolescente es obligatorio")
                elif not nombre_defensor.strip():
                    st.error("❌ El nombre del defensor es obligatorio")
                else:
                    # Preparar datos para generación
                    datos_documento = {
                        "juzgado_ejecucion": tribunal_seleccionado,
                        "causas_ej_str": ", ".join([
                            causa['rit'] for causa in st.session_state.datos_formulario["lista_ejecucion"] 
                            if causa['rit']
                        ]),
                        "causas_adulto_str": ", ".join([
                            causa['rit'] for causa in st.session_state.datos_formulario["lista_causas_adulto"] 
                            if causa['rit']
                        ]),
                        "causas_str": ", ".join([
                            causa['rit'] for causa in st.session_state.datos_formulario["lista_causas_rpa"] 
                            if causa['rit']
                        ]),
                        "rit_prin": st.session_state.datos_formulario["lista_ejecucion"][0]["rit"],
                        "ruc_prin": st.session_state.datos_formulario["lista_ejecucion"][0]["ruc"]
                    }
                    
                    # Generar documento
                    with st.spinner("📝 Generando documento legal..."):
                        generador = GeneradorDocumentosLegales(nombre_defensor, nombre_imputado)
                        archivo_word = generador.generar_escrito_legal(tipo_recurso_seleccionado, datos_documento)
                    
                    # Guardar en base de datos
                    exito_bd = guardar_gestion_en_bd(
                        datos_documento["ruc_prin"],
                        datos_documento["rit_prin"],
                        tribunal_seleccionado,
                        tipo_recurso_seleccionado,
                        f"Escrito generado automáticamente para {nombre_imputado}"
                    )
                    
                    # Interfaz de descarga
                    nombre_archivo = f"{tipo_recurso_seleccionado.replace(' ', '_')}_{nombre_imputado.replace(' ', '_')}.docx"
                    
                    st.success("✅ Documento generado exitosamente")
                    
                    col_descarga, col_estado = st.columns([2, 1])
                    
                    with col_descarga:
                        st.download_button(
                            f"📂 Descargar {tipo_recurso_seleccionado}.docx",
                            archivo_word,
                            file_name=nombre_archivo,
                            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                            use_container_width=True
                        )
                    
                    with col_estado:
                        if exito_bd:
                            st.success("☁️ Guardado en BD")
                        else:
                            st.warning("⚠️ Error en BD")
                    
                    st.balloons()
    
    # TAB 4: Administración
    with tab_administracion:
        st.markdown("## ⚙️ Panel de Administración")
        
        if st.session_state.get("es_administrador", False):
            
            st.markdown("### 👥 Gestión de Usuarios")
            
            # Mostrar usuarios registrados
            usuarios_registrados = []
            for email, datos in st.session_state.base_usuarios.items():
                usuarios_registrados.append({
                    "Email": email,
                    "Nombre": datos["nombre"],
                    "Nivel": datos["nivel"]
                })
            
            if usuarios_registrados:
                st.dataframe(usuarios_registrados, use_container_width=True)
            
            st.markdown("---")
            
            # Estadísticas del sistema
            st.markdown("### 📊 Estadísticas del Sistema")
            
            col_stats1, col_stats2, col_stats3 = st.columns(3)
            
            with col_stats1:
                st.metric("Usuarios Activos", len(st.session_state.base_usuarios))
            
            with col_stats2:
                st.metric("Documentos Generados", "En desarrollo")
            
            with col_stats3:
                st.metric("Créditos Totales", "En desarrollo")
            
            st.markdown("---")
            
            # Configuración de pagos
            st.markdown("### 💳 Configuración de Pagos")
            st.info("🔧 Módulo de integración con Stripe/Webpay en desarrollo")
            
        else:
            st.warning("⚠️ Acceso restringido a administradores del sistema")
    
    # Footer
    st.markdown("---")
    st.markdown(
        "<div style='text-align: center; color: #666; padding: 1rem;'>"
        "Suite Legal Pro - <strong>IGNACIO ANTONIO BADILLA LARA</strong> - Defensoría Penal Pública"
        "</div>", 
        unsafe_allow_html=True
    )

# =============================================================================
# EJECUCIÓN PRINCIPAL
# =============================================================================

if __name__ == "__main__":
    main()
