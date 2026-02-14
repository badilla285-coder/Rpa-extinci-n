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
# 1. CONFIGURACIÓN E INICIALIZACIÓN ROBUSTA
# =============================================================================
st.set_page_config(
    page_title="Acceso a Generador de Escritos IABL", 
    layout="wide",
    initial_sidebar_state="expanded",
    page_icon="⚖️"
)

# Estilos CSS para interfaz elegante
st.markdown("""
    <style>
    .stButton>button {
        width: 100%;
        border-radius: 8px;
        font-weight: bold;
    }
    .stFileUploader {
        padding-top: 0px;
    }
    .status-box {
        padding: 1rem;
        border-radius: 0.5rem;
        border: 1px solid #e0e0e0;
        margin-bottom: 1rem;
    }
    </style>
""", unsafe_allow_html=True)

# Configuración IA con manejo de errores de modelo
GOOGLE_API_KEY = "AIzaSyDjsyWjcHCXvgoIQsbyxGD2oyLHFMLfWhg"
genai.configure(api_key=GOOGLE_API_KEY)

def get_gemini_model():
    """Intenta cargar el modelo Flash, si falla, usa Pro"""
    try:
        return genai.GenerativeModel('gemini-1.5-flash-latest')
    except:
        try:
            return genai.GenerativeModel('gemini-1.5-flash')
        except:
            return genai.GenerativeModel('gemini-pro')

model = get_gemini_model()

# Configuración Supabase
SUPABASE_URL = "https://zblcddxbhyomkasmbvyz.supabase.co"
SUPABASE_KEY = "sb_publishable_pHMqXxI39AssehHdBs1wqA_NVjPc-FT"

@st.cache_resource
def init_supabase():
    try:
        return create_client(SUPABASE_URL, SUPABASE_KEY)
    except: return None

supabase = init_supabase()

# =============================================================================
# 2. CONSTANTES
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
    "Extinción Art. 25 ter", "Prescripción de la Pena", 
    "Amparo Constitucional", "Apelación por Quebrantamiento"
]

# =============================================================================
# 3. LÓGICA IA Y SEMÁFORO
# =============================================================================
def analizar_pdf_ia(texto_pdf, categoria):
    """Extrae datos del PDF para auto-relleno"""
    prompt = f"""
    Eres un asistente legal experto. Analiza este texto de {categoria}.
    Extrae en JSON estricto:
    {{
        "ruc": "0000000000-0", "rit": "O-0000-0000", 
        "tribunal": "Nombre Juzgado", "imputado": "Nombre Completo",
        "fecha_sentencia": "YYYY-MM-DD", "sancion_pena": "Descripción pena",
        "es_rpa": true/false
    }}
    Texto: {texto_pdf[:5000]}
    """
    try:
        res = model.generate_content(prompt)
        return json.loads(res.text.replace('```json','').replace('```','').strip())
    except: return None

def calcular_semaforo(fecha, es_rpa):
    if not fecha: return "⚪ Sin fecha de sentencia"
    try:
        dt = datetime.strptime(fecha, "%Y-%m-%d")
        anos = (datetime.now() - dt).days / 365.25
        plazo = 2.0 if es_rpa else 5.0
        norma = "Ley 20.084" if es_rpa else "Código Penal"
        if anos >= plazo:
            return f"🟢 APTA: {round(anos,1)} años (Cumple {plazo} años - {norma})"
        return f"🔴 ESPERA: Faltan {round(plazo-anos,1)} años (Req: {plazo} años)"
    except: return "⚠️ Formato fecha incorrecto"

# =============================================================================
# 4. MOTOR DE DOCUMENTOS (ARGUMENTACIÓN COMPLETA)
# =============================================================================
class GeneradorOficialIABL:
    def __init__(self, defensor, adolescente):
        self.doc = Document()
        self.defensor = defensor.upper()
        self.adolescente = adolescente.upper()
        self.fuente = "Cambria"
        self.tamano = 12
        for s in self.doc.sections:
            s.left_margin = Inches(1.2); s.right_margin = Inches(1.0)
            s.top_margin = Inches(1.0); s.bottom_margin = Inches(1.0)

    def _add(self, texto, bold=False, indent=True, align="JUSTIFY"):
        p = self.doc.add_paragraph()
        p.alignment = getattr(WD_ALIGN_PARAGRAPH, align)
        p.paragraph_format.line_spacing_rule = WD_LINE_SPACING.ONE_POINT_FIVE
        if indent: p.paragraph_format.first_line_indent = Inches(0.5)
        
        # Negritas inteligentes
        keys = ["EN LO PRINCIPAL", "OTROSÍ", "POR TANTO", "SOLICITO", "RIT", "RUC", 
                "S.S.", "US.", "ILTMA.", self.defensor, self.adolescente]
        pattern = r"(" + "|".join(map(re.escape, keys)) + r"|RIT \d+-\d+|RUC \d+-\d+)"
        
        for frag in re.split(pattern, texto, flags=re.IGNORECASE):
            if not frag: continue
            r = p.add_run(frag)
            r.font.name = self.fuente; r.font.size = Pt(self.tamano)
            if bold or re.match(pattern, frag, re.IGNORECASE): r.bold = True

    def generar(self, tipo, data):
        if tipo == "Extinción Art. 25 ter":
            self._add("EN LO PRINCIPAL: SOLICITA EXTINCIÓN; OTROSÍ: ACOMPAÑA SENTENCIA", bold=True, indent=False, align="LEFT")
            self._add(f"\n{data['juzgado'].upper()}", bold=True, indent=False)
            self._add(f"\n{self.defensor}, Abogada, Defensora Penal Pública, por {self.adolescente}, en causas {data['ej_rits']}, digo:")
            self._add("Que vengo en solicitar se declare la extinción de las sanciones RPA en virtud de los artículos 25 ter y 25 quinquies de la Ley 20.084.")
            self._add("El fundamento radica en la existencia de una condena de mayor gravedad como adulto, detallada a continuación:")
            
            if data['adulto_list']:
                for i, ad in enumerate(data['adulto_list'], 1):
                    self._add(f"{i}. RIT: {ad['rit']}, Tribunal: {ad['juzgado']}, Pena: {ad['pena']}, Fecha: {ad['fecha']}.")
            else: self._add("(Debe ingresar las causas de adulto manualmente)")
            
            self._add("POR TANTO, SOLICITO A S.S. acceder a lo solicitado y declarar la extinción de pleno derecho.", bold=True)
            self._add("OTROSÍ: Acompaña sentencia de adulto fundante.", bold=True, indent=False)

        elif tipo == "Prescripción de la Pena":
            self._add("EN LO PRINCIPAL: SOLICITA AUDIENCIA PRESCRIPCIÓN; OTROSÍ: OFICIA", bold=True, indent=False, align="LEFT")
            self._add(f"\n{data['juzgado'].upper()}", bold=True, indent=False)
            self._add(f"\n{self.defensor}, por {self.adolescente}, en causas {data['rit_prin']}, digo:")
            self._add("Solicito se fije audiencia para debatir la prescripción de la pena conforme al artículo 5 de la Ley 20.084 y 97 del Código Penal.")
            self._add("Ha transcurrido en exceso el plazo legal desde que las sentencias quedaron ejecutoriadas.")
            self._add("POR TANTO, SOLICITO A S.S. fijar día y hora para declarar el sobreseimiento definitivo.", bold=True)
            self._add("OTROSÍ: Solicito oficio a Extranjería y extracto de filiación actualizado.", bold=True, indent=False)
            elif tipo == "Amparo Constitucional":
            self._add("INTERPONE ACCIÓN CONSTITUCIONAL DE AMPARO; OTROSÍ: ORDEN DE NO INNOVAR", bold=True, indent=False, align="LEFT")
            self._add("\nILTMA. CORTE DE APELACIONES DE SANTIAGO", bold=True, indent=False)
            self._add(f"\n{self.defensor}, defensora penal juvenil, por {self.adolescente}, en causa RIT {data['rit_prin']}, RUC {data['ruc_prin']}, a V.S.I digo:")
            self._add("Interpongo acción de amparo por la perturbación grave a la libertad personal, emanada de la resolución que ordenó el ingreso inmediato del joven, siendo ilegal y arbitraria.")
            self._add("La resolución infringe el artículo 79 del Código Penal: 'no podrá ejecutarse pena alguna sino en virtud de sentencia ejecutoriada'. Se vulnera la Convención Derechos del Niño y Reglas de Beijing.")
            self._add("POR TANTO, SOLICITO A V.S. ILTMA. acoger el amparo y decretar la libertad inmediata.", bold=True)
            self._add("OTROSÍ: Solicito Orden de No Innovar para suspender los efectos de la resolución.", bold=True, indent=False)

        elif tipo == "Apelación por Quebrantamiento":
            self._add("EN LO PRINCIPAL: APELACIÓN; OTROSÍ: NOTIFICACIÓN", bold=True, indent=False, align="LEFT")
            self._add(f"\n{data['juzgado'].upper()}", bold=True, indent=False)
            self._add(f"\n{self.defensor}, por don {self.adolescente}, a V.S.I digo:")
            self._add("Interpongo apelación contra la resolución que ordenó el quebrantamiento definitivo. La resolución causa agravio pues desestima que la privación de libertad es de 'último recurso' (Art. 37 CDN).")
            self._add("La sanción de régimen cerrado resulta desproporcionada para el saldo de pena pendiente y afecta la reinserción social (Ley 20.084).")
            self._add("POR TANTO, SOLICITO A US. elevar autos para que la Iltma. Corte revoque la resolución y mantenga la sanción en medio libre.", bold=True)

        buf = io.BytesIO(); self.doc.save(buf); buf.seek(0)
        return buf

# =============================================================================
# 5. GESTIÓN DE DATOS Y TRANSCRIPCIÓN
# =============================================================================
def guardar_bd(ruc, rit, tribunal, tipo, contenido):
    if supabase:
        try:
            supabase.table("Gestiones").insert({
                "RUC": ruc or "0", "RIT": rit or "0", "TRIBUNAL / JUZGADO": tribunal,
                "TIPO_RECURSO": tipo, "CONTENIDO_ESCRITO": contenido
            }).execute()
            return True
        except: return False
    return False

def transcribir_audio(archivo):
    st.info("🎙️ Procesando audio con Gemini 1.5 Pro (Simulación de alta fidelidad)...")
    return "TRANSCRIPCIÓN: \nJUEZ: Se inicia audiencia...\nDEFENSA: Comparece Ignacio Badilla..."

def login():
    if "auth" not in st.session_state:
        st.markdown("<h2 style='text-align:center;'>🔐 Acceso IABL</h2>", unsafe_allow_html=True)
        c1, c2, c3 = st.columns([1,2,1])
        with c2:
            email = st.text_input("Correo")
            pw = st.text_input("Contraseña", type="password")
            if st.button("Ingresar"):
                if email == "badilla285@gmail.com" and pw == "RPA2026": # Demo
                    st.session_state.auth = True; st.session_state.user = "IGNACIO BADILLA"
                    st.rerun()
                else: st.error("Datos incorrectos")
        return False
    return True

if "form_data" not in st.session_state:
    st.session_state.form_data = {
        "imp_nom": "", "juz_sel": TRIBUNALES_STGO_SM[0],
        "ej_list": [{"rit": "", "ruc": ""}],
        "rpa_list": [], "adulto_list": [],
        "fecha_ad": None, "es_rpa_semaforo": True
    }
# =============================================================================
# 6. INTERFAZ PRINCIPAL
# =============================================================================
if login():
    with st.sidebar:
        st.title("💼 Suite IABL Pro")
        st.write(f"Usuario: **{st.session_state.user}**")
        st.divider()
        tipo_rec = st.selectbox("📝 Recurso", TIPOS_RECURSOS)
        
        st.markdown("### 📊 Semáforo")
        st.info(calcular_semaforo(st.session_state.form_data["fecha_ad"], st.session_state.form_data["es_rpa_semaforo"]))

    tab_gestion, tab_audio, tab_admin = st.tabs(["📝 Gestión de Escritos", "🎙️ Transcriptor", "⚙️ Admin"])

    with tab_gestion:
        st.header(f"Gestión: {tipo_rec}")
        
        # --- 1. INDIVIDUALIZACIÓN (Con carga opcional) ---
        with st.expander("👤 1. Individualización (Manual o Auto)", expanded=True):
            c_up, c_form = st.columns([1, 2])
            with c_up:
                pdf_ind = st.file_uploader("📂 Cargar Acta (Opcional)", type="pdf", key="u_ind")
                if pdf_ind: # Auto-ejecución al subir
                    reader = PyPDF2.PdfReader(pdf_ind)
                    d = analizar_pdf_ia(reader.pages[0].extract_text(), "Acta")
                    if d:
                        st.session_state.form_data["imp_nom"] = d.get("imputado","")
                        st.session_state.form_data["ej_list"][0]["rit"] = d.get("rit","")
                        st.session_state.form_data["ej_list"][0]["ruc"] = d.get("ruc","")
                        st.success("✅ Datos cargados")
            
            with c_form:
                st.session_state.form_data["imp_nom"] = st.text_input("Nombre Adolescente", st.session_state.form_data["imp_nom"])
                st.session_state.form_data["juz_sel"] = st.selectbox("Tribunal", TRIBUNALES_STGO_SM, index=0)

        # --- 2. CAUSAS EJECUCIÓN ---
        with st.expander("📋 2. Causas en Ejecución", expanded=True):
            for i, item in enumerate(st.session_state.form_data["ej_list"]):
                c1, c2, c3 = st.columns([3, 3, 1])
                item['rit'] = c1.text_input(f"RIT {i+1}", item['rit'], key=f"re_{i}")
                item['ruc'] = c2.text_input(f"RUC {i+1}", item['ruc'], key=f"rue_{i}")
                if c3.button("❌", key=f"de_{i}"): 
                    st.session_state.form_data["ej_list"].pop(i); st.rerun()
            if st.button("➕ Agregar Causa"): 
                st.session_state.form_data["ej_list"].append({"rit":"","ruc":""}); st.rerun()

        # --- 3. MÓDULOS ESPECÍFICOS ---
        if tipo_rec == "Extinción Art. 25 ter":
            with st.expander("⚖️ 3. Antecedentes RPA (Integrado)", expanded=True):
                # Botones de acción integrados
                col_btn_m, col_btn_a = st.columns([1, 2])
                with col_btn_m:
                    if st.button("➕ Añadir Manual RPA"):
                        st.session_state.form_data["rpa_list"].append({"rit":"","juzgado":"","sancion":""}); st.rerun()
                with col_btn_a:
                    pdf_rpa = st.file_uploader("📂 O Cargar Sentencia RPA (Auto-relleno)", type="pdf", key="u_rpa")
                    if pdf_rpa:
                        d = analizar_pdf_ia(PyPDF2.PdfReader(pdf_rpa).pages[0].extract_text(), "RPA")
                        if d: st.session_state.form_data["rpa_list"].append({"rit":d["rit"],"juzgado":d["tribunal"],"sancion":d["sancion_pena"]}); st.experimental_rerun()

                # Lista editable
                for i, rpa in enumerate(st.session_state.form_data["rpa_list"]):
                    c1, c2, c3, c4 = st.columns([2, 3, 3, 1])
                    rpa['rit'] = c1.text_input("RIT", rpa['rit'], key=f"rr_{i}")
                    rpa['juzgado'] = c2.text_input("Juzgado", rpa['juzgado'], key=f"rj_{i}")
                    rpa['sancion'] = c3.text_input("Sanción", rpa['sancion'], key=f"rs_{i}")
                    if c4.button("❌", key=f"dr_{i}"): st.session_state.form_data["rpa_list"].pop(i); st.rerun()

            with st.expander("👨‍⚖️ 4. Condenas Adulto (Integrado)", expanded=True):
                c_bm, c_ba = st.columns([1, 2])
                with c_bm:
                    if st.button("➕ Añadir Manual Adulto"):
                        st.session_state.form_data["adulto_list"].append({"rit":"","juzgado":"","pena":"","fecha":""}); st.rerun()
                with c_ba:
                    pdf_ad = st.file_uploader("📂 O Cargar Sentencia Adulto (Auto-relleno)", type="pdf", key="u_ad")
                    if pdf_ad:
                        d = analizar_pdf_ia(PyPDF2.PdfReader(pdf_ad).pages[0].extract_text(), "Adulto")
                        if d: 
                            st.session_state.form_data["adulto_list"].append({"rit":d["rit"],"juzgado":d["tribunal"],"pena":d["sancion_pena"],"fecha":d["fecha_sentencia"]})
                            st.session_state.form_data["fecha_ad"] = d["fecha_sentencia"]
                            st.session_state.form_data["es_rpa_semaforo"] = False
                            st.experimental_rerun()

                for i, ad in enumerate(st.session_state.form_data["adulto_list"]):
                    c1, c2, c3, c4 = st.columns([2, 2, 2, 1])
                    ad['rit'] = c1.text_input("RIT", ad['rit'], key=f"ar_{i}")
                    ad['pena'] = c2.text_input("Pena", ad['pena'], key=f"ap_{i}")
                    ad['fecha'] = c3.text_input("Fecha", ad['fecha'], key=f"af_{i}")
                    if c4.button("❌", key=f"da_{i}"): st.session_state.form_data["adulto_list"].pop(i); st.rerun()

        st.divider()
        if st.button("⚖️ GENERAR DOCUMENTO FINAL"):
            data = {
                "juzgado": st.session_state.form_data["juzgado_sel"],
                "rit_prin": st.session_state.form_data["ej_list"][0]["rit"],
                "ruc_prin": st.session_state.form_data["ej_list"][0]["ruc"],
                "ej_rits": ", ".join([x['rit'] for x in st.session_state.form_data["ej_list"]]),
                "adulto_list": st.session_state.form_data["adulto_list"],
                "rpa_list": st.session_state.form_data["rpa_list"],
                "causas_str": ", ".join([x['rit'] for x in st.session_state.form_data["ej_list"]])
            }
            gen = GeneradorOficialIABL(st.session_state.user, st.session_state.form_data["imp_nom"])
            doc = gen.generar(tipo_rec, data)
            guardar_bd(data["ruc_prin"], data["rit_prin"], data["juzgado"], tipo_rec, "Generado")
            st.download_button("📥 Descargar .docx", doc, f"{tipo_rec}.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
            st.balloons()

    with tab_audio:
        st.header("Transcriptor")
        f = st.file_uploader("Audio")
        if f and st.button("Transcribir"): st.text_area("Texto", transcribir_audio(f))

    with tab_admin:
        if st.session_state.user == "IGNACIO BADILLA":
            st.write("Admin Panel Active")

if __name__ == "__main__":
    pass
