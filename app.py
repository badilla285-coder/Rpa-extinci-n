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
# 1. CONFIGURACIÓN DE PÁGINA Y ESTILOS
# =============================================================================
st.set_page_config(
    page_title="Suite Legal IABL Pro", 
    layout="wide",
    initial_sidebar_state="expanded",
    page_icon="⚖️"
)

# Estilo CSS personalizado para una interfaz elegante
st.markdown("""
    <style>
    .main {
        background-color: #f8f9fa;
    }
    .stButton>button {
        width: 100%;
        border-radius: 5px;
        height: 3em;
        background-color: #0e1117;
        color: white;
    }
    .stTextInput>div>div>input {
        border-radius: 5px;
    }
    h1 { color: #0f2c4a; }
    h2 { color: #0f2c4a; border-bottom: 2px solid #0f2c4a; padding-bottom: 10px; }
    h3 { color: #1c4b75; }
    .status-box {
        padding: 10px;
        border-radius: 5px;
        margin-bottom: 10px;
        border: 1px solid #ddd;
    }
    </style>
""", unsafe_allow_html=True)

# =============================================================================
# 2. CONFIGURACIÓN DE SERVICIOS (IA Y BASE DE DATOS)
# =============================================================================

# API Key de Google (Gemini)
GOOGLE_API_KEY = "AIzaSyDjsyWjcHCXvgoIQsbyxGD2oyLHFMLfWhg"
genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

# Configuración Supabase
SUPABASE_URL = "https://zblcddxbhyomkasmbvyz.supabase.co"
SUPABASE_KEY = "sb_publishable_pHMqXxI39AssehHdBs1wqA_NVjPc-FT"

@st.cache_resource
def init_supabase():
    try:
        return create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception as e:
        return None # Manejo silencioso para no interrumpir si falla conexión

supabase = init_supabase()

# =============================================================================
# 3. CONSTANTES Y REFERENCIAS LEGALES
# =============================================================================

TRIBUNALES_STGO_SM = [
    "Juzgado de Garantía de San Bernardo", "Juzgado de Garantía de Puente Alto",
    "Juzgado de Garantía de Talagante", "Juzgado de Garantía de Melipilla",
    "Juzgado de Garantía de Curacaví", "Juzgado de Garantía de Colina",
    "1° Juzgado de Garantía de Santiago", "2° Juzgado de Garantía de Santiago",
    "3° Juzgado de Garantía de Santiago", "4° Juzgado de Garantía de Santiago",
    "5° Juzgado de Garantía de Santiago", "6° Juzgado de Garantía de Santiago",
    "7° Juzgado de Garantía de Santiago", "8° Juzgado de Garantía de Santiago",
    "9° Juzgado de Garantía de Santiago", "10° Juzgado de Garantía de Santiago",
    "11° Juzgado de Garantía de Santiago", "12° Juzgado de Garantía de Santiago",
    "13° Juzgado de Garantía de Santiago", "14° Juzgado de Garantía de Santiago",
    "15° Juzgado de Garantía de Santiago", "16° Juzgado de Garantía de Santiago"
]

TIPOS_RECURSOS = [
    "Extinción Art. 25 ter", 
    "Prescripción de la Pena", 
    "Amparo Constitucional", 
    "Apelación por Quebrantamiento"
]

# =============================================================================
# 4. FUNCIONES DE LÓGICA LEGAL E INTELIGENCIA ARTIFICIAL
# =============================================================================

def analizar_pdf_ia(texto_pdf, categoria):
    """
    Analiza el texto extraído de un PDF usando Gemini 1.5 Flash.
    Retorna un diccionario JSON con los datos del caso.
    """
    prompt = f"""
    Actúa como un abogado experto en derecho penal chileno. Analiza el siguiente texto de un documento tipo '{categoria}'.
    Tu objetivo es extraer datos precisos para rellenar un escrito judicial.
    
    Extrae la siguiente información en formato JSON estricto:
    {{
        "ruc": "Formato 0000000000-0",
        "rit": "Formato O-0000-0000",
        "tribunal": "Nombre exacto del tribunal",
        "imputado": "Nombre completo del adolescente/imputado",
        "fecha_sentencia": "YYYY-MM-DD (si aplica)",
        "sancion_pena": "Descripción de la sanción o pena",
        "es_rpa": true/false (true si es Ley 20.084)
    }}
    
    Texto del documento:
    {texto_pdf[:6000]}
    """
    try:
        response = model.generate_content(prompt)
        # Limpieza de la respuesta para obtener solo el JSON
        json_str = response.text.replace('```json', '').replace('```', '').strip()
        return json.loads(json_str)
    except Exception as e:
        st.error(f"Error al analizar el documento con IA: {e}")
        return None

def calcular_semaforo_legal(fecha_sentencia, es_rpa):
    """
    Calcula la prescripción de la pena diferenciando entre RPA y Adultos.
    - RPA (Art. 5 Ley 20.084): 2 años simples delitos, 5 años crímenes.
    - Adultos (CP): 5 años simples delitos, 10/15 crímenes.
    """
    if not fecha_sentencia:
        return "⚪ **Estado Indeterminado:** Sube una sentencia para calcular."
    
    try:
        fecha_obj = datetime.strptime(fecha_sentencia, "%Y-%m-%d")
        dias_transcurridos = (datetime.now() - fecha_obj).days
        anos_transcurridos = dias_transcurridos / 365.25
        
        # Plazos base (simplificados para semáforo)
        plazo_legal = 2.0 if es_rpa else 5.0
        norma = "Ley 20.084 (RPA)" if es_rpa else "Código Penal (Adulto)"
        
        if anos_transcurridos >= plazo_legal:
            return f"🟢 **APTA PARA SOLICITUD**\n\nHan transcurrido **{round(anos_transcurridos, 1)} años**.\nCumple el plazo de {plazo_legal} años ({norma})."
        else:
            faltan = round(plazo_legal - anos_transcurridos, 1)
            return f"🔴 **EN ESPERA DE PLAZO**\n\nFaltan **{faltan} años** para cumplir el requisito legal de {plazo_legal} años ({norma})."
    except:
        return "⚠️ Error en el formato de la fecha de sentencia."

# =============================================================================
# 5. MOTOR DE GENERACIÓN DE DOCUMENTOS (CLASE OFICIAL IABL)
# =============================================================================

class GeneradorOficialIABL:
    def __init__(self, defensor, adolescente):
        self.doc = Document()
        self.defensor = defensor.upper()
        self.adolescente = adolescente.upper()
        self.fuente = "Cambria"
        self.tamano = 12
        self._configurar_margenes()

    def _configurar_margenes(self):
        for section in self.doc.sections:
            section.top_margin = Inches(1.0)
            section.bottom_margin = Inches(1.0)
            section.left_margin = Inches(1.2)
            section.right_margin = Inches(1.0)

    def _add_p(self, texto, bold_all=False, indent=True, align="JUSTIFY"):
        p = self.doc.add_paragraph()
        
        # Alineación
        if align == "LEFT": p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        elif align == "CENTER": p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        else: p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        
        # Espaciado y Sangría
        p.paragraph_format.line_spacing_rule = WD_LINE_SPACING.ONE_POINT_FIVE
        if indent: p.paragraph_format.first_line_indent = Inches(0.5)
        
        # Lógica de Negritas Inteligentes
        # Detecta nombres, RITs, RUCs y palabras clave legales automáticamente
        keywords = [
            "EN LO PRINCIPAL", "OTROSÍ", "POR TANTO", "SOLICITO", "RIT", "RUC", 
            "ACCIÓN CONSTITUCIONAL", "INTERPONE", "APELACIÓN", "AMPARO", 
            "S.S.", "US.", "ILTMA.", self.defensor, self.adolescente
        ]
        
        # Tokenización simple para aplicar formato
        # (Esta lógica permite poner en negrita partes específicas sin romper el párrafo)
        escaped_keywords = [re.escape(k) for k in keywords]
        pattern = r"(" + "|".join(escaped_keywords) + r"|RIT \d+-\d+|RUC \d+-\d+|[\d\.-]+-[\dkK])"
        
        parts = re.split(pattern, texto, flags=re.IGNORECASE)
        
        for part in parts:
            if not part: continue
            run = p.add_run(part)
            run.font.name = self.fuente
            run.font.size = Pt(self.tamano)
            
            # Aplicar negrita si es keyword o si bold_all es True
            if bold_all or re.match(pattern, part, re.IGNORECASE):
                run.bold = True

    def generar_documento(self, tipo_escrito, data):
        """Genera el contenido jurídico completo según el tipo de recurso."""
        
        if tipo_escrito == "Extinción Art. 25 ter":
            self._add_p("EN LO PRINCIPAL: SOLICITA EXTINCIÓN DE SANCIÓN RPA; OTROSÍ: ACOMPAÑA SENTENCIA DE ADULTO.", bold_all=True, indent=False, align="LEFT")
            self._add_p(f"\n{data['juzgado'].upper()}", bold_all=True, indent=False)
            
            intro = f"\n{self.defensor}, Abogada, Defensora Penal Pública, en representación del adolescente {self.adolescente}, en causas de ejecución RIT {data['rit_prin']}, RUC {data['ruc_prin']}, a S.S. respetuosamente digo:"
            self._add_p(intro)
            
            self._add_p("Que, por medio de esta presentación, vengo en solicitar se declare la extinción de las sanciones impuestas en el marco de la Ley de Responsabilidad Penal Adolescente (Ley 20.084), o en subsidio se fije audiencia para debatir al respecto.")
            self._add_p("Fundo mi solicitud en lo dispuesto en el artículo 25 ter de la Ley 20.084, el cual establece que la condena de mayor gravedad impuesta a un adulto produce la extinción de pleno derecho de las sanciones RPA vigentes.")
            
            self._add_p("En el caso concreto, mi representado ha sido condenado como adulto en las siguientes causas, las cuales tienen una pena de mayor gravedad que las sanciones RPA que actualmente cumple:", bold_all=False)
            
            # Listado dinámico de causas de adulto
            if data['causas_adulto_list']:
                for i, ad in enumerate(data['causas_adulto_list'], 1):
                    self._add_p(f"{i}. RIT: {ad['rit']}, Juzgado: {ad['juzgado']}, Pena: {ad['pena']}, Fecha Sentencia: {ad['fecha']}.")
            else:
                self._add_p("(Detalle de condenas de adulto pendiente de ingreso manual)")

            self._add_p("POR TANTO, en virtud de lo expuesto y los artículos 25 ter y 25 quinquies de la Ley 20.084.", indent=True)
            self._add_p("SOLICITO A S.S. acceder a lo solicitado, declarando la extinción de las sanciones RPA y el consecuente sobreseimiento definitivo.", bold_all=True)
            self._add_p("OTROSÍ: Sírvase tener por acompañada copia de la(s) sentencia(s) condenatoria(s) de adulto invocada(s) como fundamento.", bold_all=True, indent=False)

        elif tipo_escrito == "Prescripción de la Pena":
            self._add_p("EN LO PRINCIPAL: SOLICITA AUDIENCIA DE PRESCRIPCIÓN; OTROSÍ: OFICIA A EXTRANJERÍA Y ADJUNTA ANTECEDENTES.", bold_all=True, indent=False, align="LEFT")
            self._add_p(f"\n{data['juzgado'].upper()}", bold_all=True, indent=False)
            
            intro = f"\n{self.defensor}, Abogada, Defensora Penal Pública, en representación de {self.adolescente}, en las causas RIT {data['rit_prin']}, a S.S. respetuosamente digo:"
            self._add_p(intro)
            
            self._add_p("Que, vengo en solicitar a S.S. se sirva fijar día y hora para celebrar audiencia con el objeto de debatir y declarar la prescripción de la pena respecto de mi representado.")
            self._add_p("Fundamento esta solicitud en el artículo 5 de la Ley N° 20.084, en relación con los artículos 97 y siguientes del Código Penal. Teniendo presente el tiempo transcurrido desde que las sentencias quedaron ejecutoriadas, ha transcurrido en exceso el plazo legal exigido para la prescripción de las sanciones.")
            
            self._add_p("POR TANTO, SOLICITO A S.S. fijar audiencia para debatir la prescripción y declarar el sobreseimiento definitivo.", bold_all=True)
            self._add_p("OTROSÍ: Solicito se oficie a Extranjería para informar movimientos migratorios y se incorpore Extracto de Filiación actualizado.", bold_all=True, indent=False)

        elif tipo_escrito == "Amparo Constitucional":
            self._add_p("INTERPONE ACCIÓN CONSTITUCIONAL DE AMPARO; OTROSÍ: ORDEN DE NO INNOVAR.", bold_all=True, indent=False, align="LEFT")
            self._add_p("\nILTMA. CORTE DE APELACIONES DE SANTIAGO", bold_all=True, indent=False)
            
            intro = f"\n{self.defensor}, abogada, Defensora Penal Juvenil, en representación del adolescente {self.adolescente}, en causa RIT {data['rit_prin']}, RUC {data['ruc_prin']} del Juzgado de Garantía de San Bernardo, a V.S.I respetuosamente digo:"
            self._add_p(intro)
            
            self._add_p("Que, en virtud de lo dispuesto en el artículo 21 de la Constitución Política de la República, vengo en deducir ACCIÓN CONSTITUCIONAL DE AMPARO por la perturbación grave e ilegítima a la libertad personal de mi representado.")
            self._add_p("HECHOS: Se ha ordenado el ingreso inmediato del adolescente a un centro de régimen cerrado/semicerrado en virtud de una resolución que carece de fundamento legal y vulnera el debido proceso.")
            self._add_p("DERECHO: La resolución infringe el artículo 79 del Código Penal, que establece que 'no podrá ejecutarse pena alguna sino en virtud de sentencia ejecutoriada'. Al ordenar el ingreso sin que la sentencia o quebrantamiento se encuentre firme, se vulnera la libertad personal de forma arbitraria.")
            
            self._add_p("POR TANTO, SOLICITO A V.S. ILTMA. acoger el presente amparo, dejar sin efecto la orden de ingreso y restablecer el imperio del derecho.", bold_all=True)
            self._add_p("OTROSÍ: Solicito Orden de No Innovar para suspender los efectos de la resolución recurrida mientras se tramita esta acción.", bold_all=True, indent=False)

        elif tipo_escrito == "Apelación por Quebrantamiento":
            self._add_p("EN LO PRINCIPAL: INTERPONE RECURSO DE APELACIÓN; OTROSÍ: FORMA DE NOTIFICACIÓN.", bold_all=True, indent=False, align="LEFT")
            self._add_p(f"\n{data['juzgado'].upper()}", bold_all=True, indent=False)
            
            intro = f"\n{self.defensor}, abogada, Defensora Penal Juvenil, en representación de don {self.adolescente}, a V.S.I respetuosamente digo:"
            self._add_p(intro)
            
            self._add_p("Que encontrándome dentro de plazo legal, interpongo recurso de apelación en contra de la resolución que decretó el quebrantamiento de la sanción, solicitando sea revocado.")
            self._add_p("FUNDAMENTOS: La resolución causa agravio pues desestima que la privación de libertad en el sistema RPA debe ser siempre una medida de 'último recurso' (Art. 37 Convención Derechos del Niño).")
            self._add_p("El quebrantamiento decretado no considera la finalidad de reinserción social de la Ley 20.084, y la sanción de régimen cerrado impuesta resulta desproporcionada para el saldo de pena pendiente.")
            
            self._add_p("POR TANTO, SOLICITO A US. tener por interpuesto recurso de apelación para ante la Iltma. Corte de Apelaciones, a fin de que revoque la resolución impugnada.", bold_all=True)

        buffer = io.BytesIO()
        self.doc.save(buffer)
        buffer.seek(0)
        return buffer

# =============================================================================
# 6. GESTIÓN DE SESIÓN Y LOGIN
# =============================================================================

def check_login():
    """Sistema de login simple y elegante"""
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False

    if not st.session_state.authenticated:
        c1, c2, c3 = st.columns([1, 2, 1])
        with c2:
            st.markdown("### 🔐 Acceso a Generador de Escritos IABL")
            email = st.text_input("Correo electrónico", placeholder="usuario@correo.com")
            password = st.text_input("Contraseña", type="password")
            
            if st.button("Ingresar", use_container_width=True):
                # Usuarios harcodeados para demo (esto se conectaría a BD real)
                users_db = {"badilla285@gmail.com": "RPA2026"}
                
                if email in users_db and users_db[email] == password:
                    st.session_state.authenticated = True
                    st.session_state.user_email = email
                    st.session_state.user_name = "IGNACIO BADILLA LARA" # Nombre fijo o desde BD
                    st.rerun()
                else:
                    st.error("Credenciales incorrectas")
        return False
    return True

# Inicialización de variables de estado
if "form_data" not in st.session_state:
    st.session_state.form_data = {
        "imp_nom": "", 
        "juzgado_sel": TRIBUNALES_STGO_SM[0],
        "ej_list": [{"rit": "", "ruc": ""}],
        "rpa_list": [],
        "adulto_list": [],
        "fecha_ad": None, 
        "es_rpa_semaforo": True
    }

# =============================================================================
# 7. INTERFAZ PRINCIPAL DE LA APLICACIÓN
# =============================================================================

if check_login():
    # --- SIDEBAR ---
    with st.sidebar:
        st.title("💼 Suite IABL Pro")
        st.info(f"Abogado: **{st.session_state.user_name}**")
        
        st.divider()
        tipo_recurso = st.selectbox("📝 Seleccione Recurso", TIPOS_RECURSOS)
        
        st.markdown("### 📊 Semáforo Legal")
        semaforo = calcular_semaforo_legal(
            st.session_state.form_data["fecha_ad"], 
            st.session_state.form_data["es_rpa_semaforo"]
        )
        if "APTA" in semaforo:
            st.success(semaforo)
        elif "ESPERA" in semaforo:
            st.error(semaforo)
        else:
            st.info(semaforo)
            
        st.divider()
        if st.button("💳 Comprar LegalCoins"):
            st.warning("Módulo de pagos en mantenimiento.")

    # --- PESTAÑAS PRINCIPALES ---
    tab_ia, tab_manual, tab_audio, tab_admin = st.tabs([
        "🤖 Carga Inteligente (IA)", 
        "📝 Edición Manual", 
        "🎙️ Transcriptor", 
        "⚙️ Administración"
    ])

    # --- PESTAÑA 1: CARGA IA ---
    with tab_ia:
        st.header("⚡ Asistente de Carga Gemini 1.5")
        st.markdown("Sube tus documentos PDF. La IA extraerá los datos y los enviará a la pestaña de **Edición Manual**.")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.subheader("1. Acta de Ejecución")
            pdf_ej = st.file_uploader("Subir PDF Ejecución", type="pdf", key="up_ej")
            if pdf_ej and st.button("Analizar Ejecución"):
                with st.spinner("Leyendo documento..."):
                    reader = PyPDF2.PdfReader(pdf_ej)
                    text = reader.pages[0].extract_text()
                    data = analizar_pdf_ia(text, "Acta de Ejecución")
                    if data:
                        st.session_state.form_data["imp_nom"] = data.get("imputado", "")
                        st.session_state.form_data["ej_list"][0]["rit"] = data.get("rit", "")
                        st.session_state.form_data["ej_list"][0]["ruc"] = data.get("ruc", "")
                        if data.get("tribunal") in TRIBUNALES_STGO_SM:
                            st.session_state.form_data["juzgado_sel"] = data.get("tribunal")
                        st.success("✅ Datos extraídos correctamente.")

        with col2:
            st.subheader("2. Sentencia RPA")
            pdf_rpa = st.file_uploader("Subir PDF RPA", type="pdf", key="up_rpa")
            if pdf_rpa and st.button("Analizar RPA"):
                with st.spinner("Analizando..."):
                    reader = PyPDF2.PdfReader(pdf_rpa)
                    text = reader.pages[0].extract_text()
                    data = analizar_pdf_ia(text, "Sentencia RPA")
                    if data:
                        st.session_state.form_data["rpa_list"].append({
                            "rit": data.get("rit", ""),
                            "juzgado": data.get("tribunal", ""),
                            "sancion": data.get("sancion_pena", "")
                        })
                        st.success("✅ Causa RPA añadida a la lista.")

        with col3:
            st.subheader("3. Sentencia Adulto")
            pdf_ad = st.file_uploader("Subir PDF Adulto", type="pdf", key="up_ad")
            if pdf_ad and st.button("Analizar Adulto"):
                with st.spinner("Analizando..."):
                    reader = PyPDF2.PdfReader(pdf_ad)
                    text = reader.pages[0].extract_text()
                    data = analizar_pdf_ia(text, "Sentencia Adulto")
                    if data:
                        st.session_state.form_data["adulto_list"].append({
                            "rit": data.get("rit", ""),
                            "juzgado": data.get("tribunal", ""),
                            "pena": data.get("sancion_pena", ""),
                            "fecha": data.get("fecha_sentencia", "")
                        })
                        st.session_state.form_data["fecha_ad"] = data.get("fecha_sentencia")
                        st.session_state.form_data["es_rpa_semaforo"] = False
                        st.success("✅ Causa Adulto añadida y Semáforo actualizado.")

    # --- PESTAÑA 2: EDICIÓN MANUAL (CONVIVENCIA HÍBRIDA) ---
    with tab_manual:
        st.header(f"📝 Gestión del Expediente: {tipo_recurso}")
        
        # Bloque 1: Individualización
        with st.expander("👤 1. Individualización", expanded=True):
            c1, c2 = st.columns(2)
            st.session_state.form_data["imp_nom"] = c1.text_input("Nombre Adolescente", st.session_state.form_data["imp_nom"])
            st.session_state.form_data["juzgado_sel"] = c2.selectbox("Tribunal Competente", TRIBUNALES_STGO_SM, index=TRIBUNALES_STGO_SM.index(st.session_state.form_data["juzgado_sel"]) if st.session_state.form_data["juzgado_sel"] in TRIBUNALES_STGO_SM else 0)

        # Bloque 2: Causas Ejecución
        with st.expander("📋 2. Causas en Ejecución (Dinámico)", expanded=True):
            for i, item in enumerate(st.session_state.form_data["ej_list"]):
                cols = st.columns([3, 3, 1])
                item["rit"] = cols[0].text_input(f"RIT {i+1}", item["rit"], key=f"rit_{i}")
                item["ruc"] = cols[1].text_input(f"RUC {i+1}", item["ruc"], key=f"ruc_{i}")
                if cols[2].button("❌", key=f"del_{i}"):
                    st.session_state.form_data["ej_list"].pop(i)
                    st.rerun()
            if st.button("➕ Agregar Causa"):
                st.session_state.form_data["ej_list"].append({"rit": "", "ruc": ""})
                st.rerun()

        # Bloque 3: Módulos específicos por escrito
        if tipo_recurso == "Extinción Art. 25 ter":
            with st.expander("⚖️ 3. Antecedentes RPA (A extinguir)", expanded=True):
                for i, rpa in enumerate(st.session_state.form_data["rpa_list"]):
                    cols = st.columns([2, 2, 3, 1])
                    rpa["rit"] = cols[0].text_input("RIT RPA", rpa["rit"], key=f"rpa_rit_{i}")
                    rpa["juzgado"] = cols[1].selectbox("Juzgado", TRIBUNALES_STGO_SM, key=f"rpa_juz_{i}")
                    rpa["sancion"] = cols[2].text_input("Sanción", rpa["sancion"], key=f"rpa_san_{i}")
                    if cols[3].button("❌", key=f"del_rpa_{i}"):
                        st.session_state.form_data["rpa_list"].pop(i)
                        st.rerun()
                if st.button("➕ Agregar RPA"):
                    st.session_state.form_data["rpa_list"].append({"rit":"", "juzgado": TRIBUNALES_STGO_SM[0], "sancion":""})
                    st.rerun()

            with st.expander("👨‍⚖️ 4. Condenas Adulto (Fundamento)", expanded=True):
                for i, ad in enumerate(st.session_state.form_data["adulto_list"]):
                    cols = st.columns([2, 2, 2, 2, 1])
                    ad["rit"] = cols[0].text_input("RIT Adulto", ad["rit"], key=f"ad_rit_{i}")
                    ad["pena"] = cols[2].text_input("Pena", ad["pena"], key=f"ad_pen_{i}")
                    ad["fecha"] = cols[3].text_input("Fecha", ad["fecha"], key=f"ad_fec_{i}")
                    if cols[4].button("❌", key=f"del_ad_{i}"):
                        st.session_state.form_data["adulto_list"].pop(i)
                        st.rerun()
                if st.button("➕ Agregar Adulto"):
                    st.session_state.form_data["adulto_list"].append({"rit":"", "juzgado": "", "pena":"", "fecha":""})
                    st.rerun()

        # Botón Generar
        st.divider()
        if st.button("⚖️ GENERAR DOCUMENTO OFICIAL", use_container_width=True):
            if not st.session_state.form_data["imp_nom"]:
                st.error("⚠️ Falta el nombre del imputado.")
            else:
                # Preparar datos
                data_doc = {
                    "juzgado": st.session_state.form_data["juzgado_sel"],
                    "rit_prin": st.session_state.form_data["ej_list"][0]["rit"],
                    "ruc_prin": st.session_state.form_data["ej_list"][0]["ruc"],
                    "causas_adulto_list": st.session_state.form_data["adulto_list"],
                    "rpa_list": st.session_state.form_data["rpa_list"]
                }
                
                # Generar Word
                generador = GeneradorOficialIABL(st.session_state.user_name, st.session_state.form_data["imp_nom"])
                doc_io = generador.generar_documento(tipo_recurso, data_doc)
                
                # Guardar en BD
                if supabase:
                    try:
                        supabase.table("Gestiones").insert({
                            "RUC": data_doc["ruc_prin"],
                            "RIT": data_doc["rit_prin"],
                            "TRIBUNAL / JUZGADO": data_doc["juzgado"],
                            "TIPO_RECURSO": tipo_recurso,
                            "CONTENIDO_ESCRITO": f"Generado para {st.session_state.form_data['imp_nom']}"
                        }).execute()
                        st.toast("✅ Guardado en base de datos", icon="☁️")
                    except Exception as e:
                        st.error(f"Error BD: {e}")

                st.download_button(
                    label=f"📥 Descargar {tipo_recurso}.docx",
                    data=doc_io,
                    file_name=f"{tipo_recurso}_{st.session_state.form_data['imp_nom']}.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                )
                st.balloons()

    # --- PESTAÑA 3: TRANSCRIPTOR ---
    with tab_audio:
        st.header("🎙️ Transcriptor Inteligente Forense")
        st.info("Módulo avanzado con reducción de ruido y segmentación de hablantes (Gemini 1.5 Pro).")
        
        c1, c2 = st.columns(2)
        idioma = c1.selectbox("Idioma Audio", ["Español (Chile)", "Español (Neutro)", "Inglés"])
        formato = c2.selectbox("Formato Salida", ["Transcripción Literal", "Resumen Jurídico", "Puntos Clave"])
        
        audio_file = st.file_uploader("Subir archivo de audio", type=["mp3", "wav", "m4a", "ogg"])
        
        if audio_file and st.button("🚀 Iniciar Transcripción"):
            st.warning("⚠️ Procesando audio de alta duración... esto puede tomar unos minutos.")
            # Aquí iría la llamada real a la API de audio de Gemini
            st.text_area("Resultado (Simulado):", "JUEZ: Se da inicio a la audiencia de control de detención...\nDEFENSA: Su señoría, solicitamos se declare ilegal la detención por los siguientes argumentos...", height=300)

    # --- PESTAÑA 4: ADMINISTRACIÓN ---
    with tab_admin:
        st.header("⚙️ Panel de Control")
        if st.session_state.get("user_email") == "badilla285@gmail.com":
            st.success("Modo Administrador Activo")
            st.write("Usuarios registrados:")
            st.table([{"Usuario": "Ignacio Badilla", "Rol": "Admin", "Estado": "Activo"}])
        else:
            st.error("Acceso denegado. Se requieren permisos de Administrador.")

    # Footer
    st.markdown("---")
    st.markdown("<div style='text-align: center; color: gray;'>Suite Legal IABL Pro v3.0 - Desarrollado para la Defensoría Penal Pública</div>", unsafe_allow_html=True)
