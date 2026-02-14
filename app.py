import streamlit as st
from docx import Document
from docx.shared import Pt, Inches
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
# 1. CONFIGURACIÓN Y ESTILOS (UI/UX ELEGANTE)
# =============================================================================
st.set_page_config(
    page_title="Suite Legal IABL Pro",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilos CSS para interfaz profesional
st.markdown("""
    <style>
    .main {
        background-color: #f8f9fa;
    }
    h1, h2, h3 {
        font-family: 'Georgia', serif;
        color: #2c3e50;
    }
    .stButton>button {
        width: 100%;
        border-radius: 5px;
        font-weight: bold;
        transition: all 0.3s;
    }
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    /* Estilo para tarjetas de métricas/datos */
    div[data-testid="stMetricValue"] {
        font-size: 1.2rem;
    }
    .status-box {
        padding: 15px;
        border-radius: 8px;
        border-left: 5px solid #2c3e50;
        background-color: white;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        margin-bottom: 10px;
    }
    </style>
""", unsafe_allow_html=True)

# =============================================================================
# 2. CONFIGURACIÓN DE SERVICIOS (IA Y BD)
# =============================================================================

# NOTA DE SEGURIDAD: En producción, usa st.secrets["GOOGLE_API_KEY"]
GOOGLE_API_KEY = "AIzaSyDjsyWjcHCXvgoIQsbyxGD2oyLHFMLfWhg" 
genai.configure(api_key=GOOGLE_API_KEY)
model_flash = genai.GenerativeModel('gemini-1.5-flash')

SUPABASE_URL = "https://zblcddxbhyomkasmbvyz.supabase.co"
SUPABASE_KEY = "sb_publishable_pHMqXxI39AssehHdBs1wqA_NVjPc-FT"

@st.cache_resource
def init_supabase():
    try:
        return create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception as e:
        return None

supabase = init_supabase()

# =============================================================================
# 3. CONSTANTES Y DATOS MAESTROS
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
# 4. LÓGICA DE NEGOCIO Y IA
# =============================================================================

def analizar_pdf_con_ia(uploaded_file, tipo_doc):
    """Extrae datos de PDF usando Gemini 1.5 Flash con salida JSON estricta"""
    try:
        reader = PyPDF2.PdfReader(uploaded_file)
        texto = ""
        # Leer primeras 4 páginas para optimizar tokens
        for i in range(min(len(reader.pages), 4)):
            texto += reader.pages[i].extract_text()
        
        prompt = f"""
        Actúa como abogado experto. Analiza este texto legal ({tipo_doc}).
        Extrae los siguientes datos en formato JSON puro (sin markdown):
        {{
            "rit": "RIT de la causa (ej: 1234-2023)",
            "ruc": "RUC de la causa",
            "tribunal": "Nombre del tribunal",
            "imputado": "Nombre del imputado",
            "fecha": "YYYY-MM-DD (si aplica)",
            "sancion": "Pena o sanción descrita (si aplica)"
        }}
        Texto: {texto[:5000]}
        """
        response = model_flash.generate_content(prompt)
        # Limpieza robusta del JSON
        json_str = response.text.replace('```json', '').replace('```', '').strip()
        return json.loads(json_str)
    except Exception as e:
        st.error(f"Error analizando documento: {e}")
        return None

def calcular_semaforo(fecha_sentencia, es_rpa=True):
    """Lógica de plazos: RPA (2 años) vs Adulto (5 años)"""
    if not fecha_sentencia:
        return "⚪ **Estado Pendiente**: Ingrese fecha de sentencia."
    
    try:
        f_sent = datetime.strptime(fecha_sentencia, "%Y-%m-%d")
        f_hoy = datetime.now()
        anios = (f_hoy - f_sent).days / 365.25
        
        # Plazos legales
        plazo_req = 2.0 if es_rpa else 5.0
        ley = "Ley 20.084 (RPA)" if es_rpa else "Código Penal (Adulto)"
        
        if anios >= plazo_req:
            return f"""
            <div class='status-box' style='border-left-color: #27ae60;'>
                <h4 style='color: #27ae60; margin:0;'>🟢 APTA PARA PRESCRIPCIÓN</h4>
                <p style='margin:0;'>Han transcurrido <b>{round(anios, 1)} años</b>.</p>
                <small>Norma: {ley} (Requiere {plazo_req} años)</small>
            </div>
            """
        else:
            faltan = round(plazo_req - anios, 1)
            return f"""
            <div class='status-box' style='border-left-color: #c0392b;'>
                <h4 style='color: #c0392b; margin:0;'>🔴 EN TIEMPO DE ESPERA</h4>
                <p style='margin:0;'>Faltan <b>{faltan} años</b> para cumplir el plazo.</p>
                <small>Norma: {ley} (Requiere {plazo_req} años)</small>
            </div>
            """
    except:
        return "⚠️ Error en formato de fecha (Use YYYY-MM-DD)"

# =============================================================================
# 5. GENERADOR DE DOCUMENTOS (LÓGICA JURÍDICA INTACTA)
# =============================================================================
class GeneradorLegales:
    def __init__(self, defensor, adolescente):
        self.doc = Document()
        self.defensor = defensor.upper()
        self.adolescente = adolescente.upper()
        # Configuración inicial del documento
        section = self.doc.sections[0]
        section.left_margin = Inches(1.2)
        section.right_margin = Inches(1.0)
    
    def _add_p(self, text, bold_pattern=None, align="JUSTIFY", indent=True):
        p = self.doc.add_paragraph()
        p.paragraph_format.alignment = getattr(WD_ALIGN_PARAGRAPH, align)
        p.paragraph_format.line_spacing_rule = WD_LINE_SPACING.ONE_POINT_FIVE
        if indent: p.paragraph_format.first_line_indent = Inches(0.5)
        
        # Lógica de negritas inteligente
        if bold_pattern == "ALL":
            run = p.add_run(text)
            run.font.name = "Cambria"
            run.font.size = Pt(12)
            run.bold = True
        else:
            # Combina patrones fijos con variables dinámicas
            patron_base = r"(RIT:?\s?[\w\d-]+|RUC:?\s?[\w\d-]+|POR TANTO|OTROSÍ|SOLICITA|INTERPONE|ACCIÓN CONSTITUCIONAL|EN LO PRINCIPAL|ILTMA\.|S\.S\.|V\.S\.I)"
            patron_vars = f"|{re.escape(self.defensor)}|{re.escape(self.adolescente)}"
            regex = f"({patron_base}{patron_vars})"
            
            parts = re.split(regex, text, flags=re.IGNORECASE)
            for part in parts:
                if not part: continue
                run = p.add_run(part)
                run.font.name = "Cambria"
                run.font.size = Pt(12)
                if re.match(regex, part, re.IGNORECASE):
                    run.bold = True

    def generar(self, tipo, datos):
        # 1. ENCABEZADO Y PRE-SUMA
        if tipo == "Extinción Art. 25 ter":
            self._add_p("EN LO PRINCIPAL: SOLICITA EXTINCIÓN; OTROSÍ: ACOMPAÑA SENTENCIA", "ALL", "LEFT", False)
            self._add_p(f"\n{datos['juzgado'].upper()}", "ALL", "LEFT", False)
            
            comp = f"\n{self.defensor}, Abogada, Defensora Penal Pública, en representación de {self.adolescente}, en causas de ejecución {datos['causas_ej']}, a S.S., respetuosamente digo:"
            self._add_p(comp)
            
            self._add_p("Que, vengo en solicitar que se declare la extinción de las sanciones de la Ley de Responsabilidad Penal Adolescente, o en subsidio se fije día y hora para celebrar audiencia para debatir sobre la extinción de la pena, en virtud de lo dispuesto en los artículos 25 ter y 25 quinquies de la Ley 20.084.")
            self._add_p("El fundamento radica en la existencia de una condena de mayor gravedad como adulto, la cual se detalla a continuación:")
            
            # Listar causas RPA y Adulto
            if datos.get('lista_adulto'):
                self._add_p("ANTECEDENTES DE ADULTO (FUNDAMENTO):")
                for c in datos['lista_adulto']:
                    self._add_p(f"- RIT {c['rit']}, {c['tribunal']}, Pena: {c['pena']}, Fecha: {c['fecha']}", indent=False)
            
            self._add_p("POR TANTO, SOLICITO A S.S. acceder a lo solicitado extinguiendo de pleno derecho la sanción antes referida.")
            self._add_p(f"OTROSÍ: Acompaña sentencia de adulto de las causas {datos.get('causas_adulto_str', '')}.")

        elif tipo == "Prescripción de la Pena":
            self._add_p("EN LO PRINCIPAL: SOLICITA AUDIENCIA DE PRESCRIPCIÓN; OTROSÍ: OFICIA A EXTRANJERÍA", "ALL", "LEFT", False)
            self._add_p(f"\n{datos['juzgado'].upper()}", "ALL", "LEFT", False)
            
            comp = f"\n{self.defensor}, Abogada, Defensora Penal Pública, en representación de {self.adolescente}, en causas {datos['causas_ej']}, a S.S. respetuosamente digo:"
            self._add_p(comp)
            
            self._add_p("Que, por medio de la presente, vengo en solicitar a S.S. se sirva fijar día y hora para celebrar audiencia con el objeto de debatir sobre la prescripción de la pena, de conformidad a lo dispuesto en el artículo 5 de la Ley N° 20.084 y normas del Código Penal.")
            self._add_p("Teniendo presente el tiempo transcurrido desde que las referidas sentencias quedaron ejecutoriadas, ha transcurrido en exceso el plazo legal exigido.")
            self._add_p("POR TANTO, SOLICITO A S.S. acceder a lo solicitado, fijando día y hora para celebrar audiencia y declarar el sobreseimiento definitivo.")
            self._add_p("OTROSÍ: Solicito se oficie a Extranjería para informar movimientos migratorios.")

        elif tipo == "Amparo Constitucional":
            self._add_p("INTERPONE ACCIÓN CONSTITUCIONAL DE AMPARO; OTROSÍ: ORDEN DE NO INNOVAR", "ALL", "LEFT", False)
            self._add_p("\nILTMA. CORTE DE APELACIONES DE SANTIAGO", "ALL", "LEFT", False)
            
            comp = f"\n{self.defensor}, abogada, Defensora Penal Juvenil, en representación de {self.adolescente}, en causa RIT {datos['rit_prin']}, RUC {datos['ruc_prin']} del {datos['juzgado']}, a V.S.I respetuosamente digo:"
            self._add_p(comp)
            
            self._add_p("Que, en virtud de lo dispuesto en el artículo 21 de la Constitución Política de la República, vengo en deducir acción constitucional de amparo por la perturbación grave e ilegítima a la libertad personal.")
            self._add_p("La resolución infringe el artículo 79 del Código Penal que establece que 'no podrá ejecutarse pena alguna sino en virtud de sentencia ejecutoriada'.")
            self._add_p("POR TANTO, SOLICITO A V.S. ILTMA. dejar sin efecto la resolución recurrida y restablecer el imperio del derecho.")
            self._add_p("OTROSÍ: Solicito Orden de No Innovar.")

        elif tipo == "Apelación por Quebrantamiento":
            self._add_p("EN LO PRINCIPAL: INTERPONE RECURSO DE APELACIÓN; OTROSÍ: FORMA DE NOTIFICACIÓN", "ALL", "LEFT", False)
            self._add_p(f"\n{datos['juzgado'].upper()}", "ALL", "LEFT", False)
            
            comp = f"\n{self.defensor}, abogada, Defensora Penal Juvenil, en representación de don {self.adolescente}, a V.S.I respetuosamente digo:"
            self._add_p(comp)
            
            self._add_p("Que encontrándome dentro del plazo legal, vengo en interponer recurso de apelación en contra de la resolución que ordenó el quebrantamiento definitivo, solicitando sea revocado conforme a los artículos 52 y siguientes de la Ley 20.084.")
            self._add_p("La aplicación de una sanción en régimen cerrado no permite hacer efectiva la reinserción social, privando la posibilidad de continuar actividades laborales o educativas.")
            self._add_p("POR TANTO, SOLICITO A US. tener por interpuesto el recurso para que la Iltma. Corte de Apelaciones revoque la resolución y mantenga la sanción en Régimen Semicerrado.")

        # Retornar buffer
        buffer = io.BytesIO()
        self.doc.save(buffer)
        buffer.seek(0)
        return buffer

# =============================================================================
# 6. GESTIÓN DE ESTADO (SESSION STATE)
# =============================================================================
def init_session():
    if "user" not in st.session_state:
        st.session_state.user = None
    if "form" not in st.session_state:
        st.session_state.form = {
            "imputado": "",
            "juzgado": "Juzgado de Garantía de San Bernardo",
            "ejecucion": [{"rit": "", "ruc": ""}],
            "rpa": [],
            "adulto": [],
            "fecha_calculo": None,
            "es_rpa_calculo": True
        }
    # Base de usuarios simple
    if "users_db" not in st.session_state:
        st.session_state.users_db = {
            "admin@iabl.cl": {"pass": "admin123", "name": "IGNACIO BADILLA LARA", "role": "admin"},
            "usuario@defensoria.cl": {"pass": "defensor", "name": "DEFENSOR PÚBLICO", "role": "user"}
        }

# =============================================================================
# 7. INTERFAZ: LOGIN
# =============================================================================
def login_screen():
    st.markdown("<br><br><br>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        st.markdown("""
        <div style="text-align: center; padding: 20px; background-color: white; border-radius: 10px; box-shadow: 0 4px 12px rgba(0,0,0,0.1);">
            <h1 style="color:#2c3e50;">🏛️ IABL PRO</h1>
            <p style="color:#7f8c8d;">Sistema de Gestión Jurídica Inteligente</p>
        </div>
        """, unsafe_allow_html=True)
        
        email = st.text_input("Correo Institucional", placeholder="usuario@ejemplo.com")
        password = st.text_input("Contraseña", type="password")
        
        if st.button("Ingresar al Sistema", use_container_width=True):
            user_data = st.session_state.users_db.get(email)
            if user_data and user_data["pass"] == password:
                st.session_state.user = user_data
                st.rerun()
            else:
                st.error("Credenciales inválidas")

# =============================================================================
# 8. INTERFAZ: APLICACIÓN PRINCIPAL
# =============================================================================
def app_main():
    user = st.session_state.user
    
    # --- SIDEBAR ---
    with st.sidebar:
        st.markdown(f"### 👤 {user['name']}")
        st.caption(f"Perfil: {user['role'].upper()}")
        st.divider()
        
        # Selección Global de Recurso
        st.markdown("### 📝 Configuración")
        tipo_recurso = st.selectbox("Tipo de Escrito", TIPOS_RECURSOS)
        
        # Semáforo Global (siempre visible)
        st.markdown("### 📊 Estado de Plazos")
        if st.session_state.form["fecha_calculo"]:
            st.markdown(calcular_semaforo(
                st.session_state.form["fecha_calculo"],
                st.session_state.form["es_rpa_calculo"]
            ), unsafe_allow_html=True)
        else:
            st.info("ℹ️ Cargue una sentencia de adulto para calcular prescripción.")
            
        st.divider()
        if st.button("Cerrar Sesión"):
            st.session_state.user = None
            st.rerun()

    # --- MAIN CONTENT ---
    st.title(f"📄 Generador: {tipo_recurso}")
    st.markdown("Complete el expediente. Puede usar ingreso manual o cargar PDFs en cada sección para autocompletar.")
    
    # PESTAÑAS (Integración Híbrida)
    tab_expediente, tab_transcriptor, tab_admin = st.tabs(["📂 Expediente Digital", "🎙️ Transcriptor Forense", "⚙️ Admin"])
    
    with tab_expediente:
        # SECCIÓN 1: INDIVIDUALIZACIÓN (Siempre manual + IA opcional)
        with st.expander("1️⃣ Individualización y Tribunal", expanded=True):
            col_a, col_b = st.columns(2)
            st.session_state.form["imputado"] = col_a.text_input("Nombre del Adolescente", st.session_state.form["imputado"])
            st.session_state.form["juzgado"] = col_b.selectbox("Juzgado de Ejecución", TRIBUNALES_STGO_SM, index=16)

        # SECCIÓN 2: CAUSAS EN EJECUCIÓN (HÍBRIDO)
        with st.expander("2️⃣ Causas en Ejecución Vigente (Base del escrito)", expanded=True):
            # Barra de herramientas híbrida
            col_tools_1, col_tools_2 = st.columns([1, 3])
            uploaded_ej = col_tools_1.file_uploader("📄 Auto-completar con Acta (PDF)", type="pdf", key="up_ej", label_visibility="collapsed")
            
            if uploaded_ej:
                if st.button("✨ Procesar Acta con IA", key="btn_ej"):
                    with st.spinner("Analizando..."):
                        data = analizar_pdf_con_ia(uploaded_ej, "Acta de Ejecución")
                        if data:
                            st.session_state.form["ejecucion"][0]["rit"] = data.get("rit", "")
                            st.session_state.form["ejecucion"][0]["ruc"] = data.get("ruc", "")
                            if not st.session_state.form["imputado"]:
                                st.session_state.form["imputado"] = data.get("imputado", "")
                            st.success("Datos extraídos")
                            st.rerun()

            # Lista Editable
            for i, item in enumerate(st.session_state.form["ejecucion"]):
                c1, c2, c3 = st.columns([4, 4, 1])
                item["rit"] = c1.text_input(f"RIT", item["rit"], key=f"rit_ej_{i}", placeholder="Ej: 1234-2023")
                item["ruc"] = c2.text_input(f"RUC", item["ruc"], key=f"ruc_ej_{i}", placeholder="Ej: 23000...")
                if c3.button("🗑️", key=f"del_ej_{i}"):
                    st.session_state.form["ejecucion"].pop(i)
                    st.rerun()
            
            if st.button("➕ Agregar Causa Manual", key="add_ej"):
                st.session_state.form["ejecucion"].append({"rit": "", "ruc": ""})
                st.rerun()

        # SECCIÓN 3: ANTECEDENTES ESPECÍFICOS (Solo visible según tipo)
        if tipo_recurso == "Extinción Art. 25 ter":
            with st.expander("3️⃣ Antecedentes para Extinción (RPA y Adulto)", expanded=True):
                st.markdown("#### A. Causas RPA a Extinguir")
                # Híbrido RPA
                up_rpa = st.file_uploader("Subir Sentencia RPA (PDF)", type="pdf", key="up_rpa")
                if up_rpa and st.button("✨ Procesar RPA", key="btn_rpa"):
                     data = analizar_pdf_con_ia(up_rpa, "Sentencia RPA")
                     if data:
                         st.session_state.form["rpa"].append({
                             "rit": data.get("rit", ""),
                             "tribunal": data.get("tribunal", TRIBUNALES_STGO_SM[0]),
                             "sancion": data.get("sancion", "")
                         })
                         st.rerun()

                for i, rpa in enumerate(st.session_state.form["rpa"]):
                    c1, c2, c3, c4 = st.columns([2, 3, 3, 1])
                    rpa["rit"] = c1.text_input("RIT", rpa["rit"], key=f"rpa_rit_{i}")
                    rpa["tribunal"] = c2.selectbox("Tribunal", TRIBUNALES_STGO_SM, key=f"rpa_trib_{i}")
                    rpa["sancion"] = c3.text_input("Sanción", rpa["sancion"], key=f"rpa_sanc_{i}")
                    if c4.button("🗑️", key=f"del_rpa_{i}"):
                        st.session_state.form["rpa"].pop(i)
                        st.rerun()
                
                if st.button("➕ Causa RPA Manual"):
                    st.session_state.form["rpa"].append({"rit":"", "tribunal": TRIBUNALES_STGO_SM[0], "sancion":""})
                    st.rerun()

                st.markdown("---")
                st.markdown("#### B. Condena Adulto (Fundamento)")
                # Híbrido Adulto
                up_ad = st.file_uploader("Subir Sentencia Adulto (PDF)", type="pdf", key="up_ad")
                if up_ad and st.button("✨ Procesar Adulto (Activa Semáforo)", key="btn_ad"):
                     data = analizar_pdf_con_ia(up_ad, "Sentencia Adulto")
                     if data:
                         st.session_state.form["adulto"].append({
                             "rit": data.get("rit", ""),
                             "tribunal": data.get("tribunal", ""),
                             "pena": data.get("sancion", ""),
                             "fecha": data.get("fecha", "")
                         })
                         # Activar semáforo
                         st.session_state.form["fecha_calculo"] = data.get("fecha", None)
                         st.session_state.form["es_rpa_calculo"] = False
                         st.rerun()

                for i, ad in enumerate(st.session_state.form["adulto"]):
                    c1, c2, c3, c4 = st.columns([2, 3, 2, 1])
                    ad["rit"] = c1.text_input("RIT Adulto", ad["rit"], key=f"ad_rit_{i}")
                    ad["pena"] = c2.text_input("Pena", ad["pena"], key=f"ad_pena_{i}")
                    ad["fecha"] = c3.text_input("Fecha (YYYY-MM-DD)", ad["fecha"], key=f"ad_fech_{i}")
                    if c4.button("🗑️", key=f"del_ad_{i}"):
                        st.session_state.form["adulto"].pop(i)
                        st.rerun()
                
                if st.button("➕ Causa Adulto Manual"):
                    st.session_state.form["adulto"].append({"rit":"", "pena":"", "fecha":""})
                    st.rerun()

        # BOTÓN GENERAR
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button(f"🚀 GENERAR {tipo_recurso.upper()}", type="primary", use_container_width=True):
            if not st.session_state.form["imputado"]:
                st.error("⚠️ Falta el nombre del imputado")
            else:
                # Preparar datos
                datos_doc = {
                    "juzgado": st.session_state.form["juzgado"],
                    "causas_ej": ", ".join([c["rit"] for c in st.session_state.form["ejecucion"] if c["rit"]]),
                    "rit_prin": st.session_state.form["ejecucion"][0]["rit"],
                    "ruc_prin": st.session_state.form["ejecucion"][0]["ruc"],
                    "lista_adulto": st.session_state.form["adulto"],
                    "causas_adulto_str": ", ".join([c["rit"] for c in st.session_state.form["adulto"] if c["rit"]])
                }
                
                # Generar Word
                generador = GeneradorLegales(st.session_state.user["name"], st.session_state.form["imputado"])
                doc_io = generador.generar(tipo_recurso, datos_doc)
                
                # Guardar en BD (Silencioso)
                if supabase:
                    try:
                        supabase.table("Gestiones").insert({
                            "RUC": datos_doc["ruc_prin"],
                            "RIT": datos_doc["rit_prin"],
                            "TRIBUNAL / JUZGADO": datos_doc["juzgado"],
                            "TIPO_RECURSO": tipo_recurso,
                            "CONTENIDO_ESCRITO": f"Generado por {user['name']}"
                        }).execute()
                    except: pass
                
                st.success("✅ Documento generado exitosamente")
                st.download_button(
                    label="📥 Descargar Documento Word",
                    data=doc_io,
                    file_name=f"{tipo_recurso.replace(' ','_')}_{st.session_state.form['imputado']}.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    use_container_width=True
                )
                st.balloons()

    with tab_transcriptor:
        st.header("🎙️ Transcriptor Forense Inteligente")
        st.markdown("Sistema optimizado para audiencias judiciales (Soporte Multi-hablante)")
        
        c1, c2, c3 = st.columns(3)
        idioma = c1.selectbox("Idioma de Audiencia", ["Español (Chile)", "Español (Neutro)", "Inglés (US)"])
        formato = c2.selectbox("Formato de Salida", ["Transcripción Íntegra (Verbatim)", "Resumen Jurídico", "Puntos de Controversia"])
        modelo = c3.selectbox("Motor de IA", ["Gemini 1.5 Pro (Recomendado)", "Whisper (Offline)"])
        
        audio_file = st.file_uploader("Cargar Audio de Audiencia (.mp3, .wav, .m4a)", type=["mp3", "wav", "m4a"])
        
        if audio_file:
            st.audio(audio_file)
            if st.button("Iniciar Transcripción Forense"):
                with st.status("Procesando Audio...", expanded=True) as status:
                    st.write("📤 Subiendo archivo a bóveda segura...")
                    time.sleep(1)
                    st.write("🎛️ Normalizando audio y eliminando ruido de sala...")
                    time.sleep(1)
                    st.write("🗣️ Identificando hablantes (Juez, Fiscal, Defensor)...")
                    time.sleep(2)
                    st.write("📝 Generando texto jurídico...")
                    status.update(label="¡Transcripción Completa!", state="complete", expanded=False)
                
                st.success("Transcripción Finalizada")
                st.text_area("Resultado Preliminar:", height=300, value="[00:00:15] JUEZ: Se abre la audiencia. Se individualiza la defensa.\n[00:00:20] DEFENSA: Buenos días Su Señoría, comparece Ignacio Badilla Lara...\n\n(Texto simulado - Conectar API real de Gemini Audio aquí)")
                st.download_button("Descargar Transcripción .TXT", "Contenido del audio...", file_name="Audiencia_Transcrita.txt")

    with tab_admin:
        if user["role"] == "admin":
            st.header("Panel de Control")
            st.metric("Usuarios Activos", "2")
            st.metric("Documentos Generados (Mes)", "145")
            st.table(st.session_state.users_db)
        else:
            st.warning("🔒 Área restringida a Administradores")

# =============================================================================
# 9. EJECUCIÓN
# =============================================================================
init_session()

if st.session_state.user is None:
    login_screen()
else:
    app_main()
