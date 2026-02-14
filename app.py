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
# 1. CONFIGURACIÓN Y ESTILOS
# =============================================================================
st.set_page_config(
    page_title="Suite Legal IABL Pro",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    h1, h2, h3 { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; color: #1a237e; }
    .stButton>button { border-radius: 8px; font-weight: 600; text-transform: uppercase; letter-spacing: 1px; }
    .stButton>button:hover { transform: translateY(-2px); box-shadow: 0 4px 8px rgba(0,0,0,0.2); }
    .block-container { padding-top: 2rem; }
    .status-card { padding: 15px; border-radius: 10px; background: white; border-left: 6px solid #1a237e; box-shadow: 0 2px 5px rgba(0,0,0,0.05); }
    .juris-box { background-color: #e8eaf6; padding: 15px; border-radius: 5px; margin-bottom: 10px; border: 1px solid #c5cae9; }
    </style>
""", unsafe_allow_html=True)

# =============================================================================
# 2. CONFIGURACIÓN ROBUSTA DE IA
# =============================================================================
GOOGLE_API_KEY = "AIzaSyDjsyWjcHCXvgoIQsbyxGD2oyLHFMLfWhg" 
genai.configure(api_key=GOOGLE_API_KEY)

def get_gemini_model():
    """Intenta conectar con el modelo más avanzado disponible"""
    models_to_try = [
        'gemini-1.5-flash', 
        'gemini-1.5-flash-latest', 
        'models/gemini-1.5-flash',
        'gemini-pro'
    ]
    for m in models_to_try:
        try:
            model = genai.GenerativeModel(m)
            model.generate_content("test")
            return model
        except Exception:
            continue
    return genai.GenerativeModel('gemini-pro')

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
# 3. DATOS MAESTROS Y TRIBUNALES
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

ARGUMENTOS_DETENCION = {
    "RPA": [
        "Ilegalidad por falta de notificación a padres (Art. 39 Ley 20.084)",
        "Vulneración de Interés Superior del Niño (Art. 3 Convención)",
        "Esposamiento injustificado (Reglas de Beijing)",
        "Exceso de plazo en puesta a disposición (Art. 131 CPP)"
    ],
    "Adulto": [
        "Falta de lectura de derechos (Art. 135 CPP)",
        "Indicios insuficientes para control identidad (Art. 85 CPP)",
        "Ingreso a domicilio sin autorización (Art. 205 CPP)",
        "Uso desproporcionado de la fuerza"
    ]
}

# =============================================================================
# 4. LÓGICA DE IA Y PROCESAMIENTO
# =============================================================================
def analizar_pdf(uploaded_file, tipo):
    """Extrae RIT, RUC y Fechas de PDF"""
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

def buscar_jurisprudencia_ia(tema):
    """Simula un asistente de investigación jurídica"""
    prompt = f"""
    Actúa como un abogado investigador experto en Derecho Penal Chileno y Ley 20.084.
    Busca argumentos y jurisprudencia relevante sobre: "{tema}".
    
    Estructura tu respuesta así:
    1. **Tesis Jurídica:** Resumen breve.
    2. **Argumentos Clave:** Lista de puntos para alegar en audiencia.
    3. **Jurisprudencia Referencial:** Cita fallos conocidos (Roles Corte Suprema o Apelaciones) si existen en tu base de conocimiento, o principios generales aceptados.
    
    Sé preciso y técnico.
    """
    try:
        response = model_ia.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Error en consulta: {e}"

def calcular_pena_rpa(pena_adulto_str):
    """Lógica simplificada de conversión Art. 21 Ley 20.084"""
    # Esta es una aproximación lógica para la herramienta
    mapa_penas = {
        "Presidio Perpetuo": "Internación en Régimen Cerrado (5-10 años)",
        "Presidio Mayor": "Internación en Régimen Cerrado (Inf. a 5 años)",
        "Presidio Menor": "Libertad Asistida Especial / Régimen Semicerrado",
        "Reclusión Menor": "Libertad Asistida Simple / Servicios en Beneficio",
        "Prisión": "Amonestación / Multa"
    }
    
    resultado = "No determinable automáticamente. Requiere análisis del Art. 21."
    for clave, valor in mapa_penas.items():
        if clave.lower() in pena_adulto_str.lower():
            resultado = valor
            break
            
    return resultado

# =============================================================================
# 5. GENERADOR DE DOCUMENTOS (WORD)
# =============================================================================
class GeneradorWord:
    def __init__(self, defensor, imputado):
        self.doc = Document()
        self.defensor = defensor.upper()
        self.imputado = imputado.upper()
        # Estilos
        style = self.doc.styles['Normal']
        style.font.name = 'Cambria'
        style.font.size = Pt(12)
        # Márgenes
        sec = self.doc.sections[0]
        sec.left_margin = Inches(1.2)
        sec.right_margin = Inches(1.0)

    def add_parrafo(self, texto, negrita=False, align="JUSTIFY"):
        p = self.doc.add_paragraph()
        p.alignment = getattr(WD_ALIGN_PARAGRAPH, align)
        p.paragraph_format.line_spacing_rule = WD_LINE_SPACING.ONE_POINT_FIVE
        
        texto = texto.replace("{DEFENSOR}", self.defensor)
        texto = texto.replace("{IMPUTADO}", self.imputado)
        
        run = p.add_run(texto)
        run.bold = negrita

    def generar(self, tipo, datos):
        # --- ENCABEZADO COMÚN ---
        suma_map = {
            "Extinción Art. 25 ter": "EN LO PRINCIPAL: SOLICITA EXTINCIÓN; OTROSÍ: ACOMPAÑA SENTENCIA",
            "Prescripción de la Pena": "EN LO PRINCIPAL: ALEGA PRESCRIPCIÓN; OTROSÍ: CERTIFICADO",
            "Minuta Control de Detención": "MINUTA DE AUDIENCIA: CONTROL DE DETENCIÓN"
        }
        titulo = suma_map.get(tipo, f"SOLICITUD: {tipo.upper()}")
        self.add_parrafo(titulo, negrita=True, align="LEFT")
        
        self.add_parrafo(f"\nAL {datos['tribunal_ej'].upper()}", negrita=True, align="LEFT")
        
        causas_txt = ", ".join([f"{c['rit']} (RUC {c['ruc']})" for c in datos['ejecucion'] if c['rit']])
        intro = f"\n{{DEFENSOR}}, Abogada Defensora Penal Pública, por el adolescente {{IMPUTADO}}, en causas de ejecución {causas_txt}, a US. respetuosamente digo:"
        self.add_parrafo(intro)

        # --- CUERPO ESPECÍFICO ---
        if tipo == "Extinción Art. 25 ter":
            self.add_parrafo("Que vengo en solicitar la extinción de las sanciones vigentes en virtud del art. 25 ter de la Ley 20.084, por existir condena posterior como adulto de mayor gravedad.")
            self.add_parrafo("ANTECEDENTES DE LA CONDENA ADULTO (FUNDAMENTO):", negrita=True)
            for ad in datos['adulto']:
                self.add_parrafo(f"• RIT: {ad['rit']}, Tribunal: {ad['tribunal']}, Pena: {ad['pena']}, Fecha: {ad['fecha']}")
            self.add_parrafo("POR TANTO, solicito se declare extinta la pena RPA y se deje sin efecto el saldo de condena.")

        elif tipo == "Prescripción de la Pena":
            self.add_parrafo("Que vengo en solicitar se declare la prescripción de la pena conforme al artículo 100 del Código Penal y Ley 20.084.")
            self.add_parrafo("Ha transcurrido el plazo legal desde que la sentencia quedó ejecutoriada sin que se haya completado el cumplimiento.")
            self.add_parrafo("POR TANTO, solicito fijar audiencia para debatir el sobreseimiento definitivo.")

        elif tipo == "Minuta Control de Detención":
            self.add_parrafo("I. HECHOS DE LA DETENCIÓN:", negrita=True)
            self.add_parrafo(f"Fecha/Hora: {datos.get('fecha_det', 'N/A')}. Lugar: {datos.get('lugar_det', 'N/A')}")
            self.add_parrafo("II. ARGUMENTOS DE ILEGALIDAD / INCIDENCIAS:", negrita=True)
            for arg in datos.get('argumentos_det', []):
                self.add_parrafo(f"• {arg}")
            self.add_parrafo("III. PETICIONES CONCRETAS:", negrita=True)
            self.add_parrafo("Que se declare ilegal la detención por vulneración de garantías constitucionales.")

        self.add_parrafo("\nPOR TANTO,")
        self.add_parrafo("RUEGO A US. acceder a lo solicitado.", negrita=True)

        buffer = io.BytesIO()
        self.doc.save(buffer)
        buffer.seek(0)
        return buffer

# =============================================================================
# 6. GESTIÓN DE SESIÓN
# =============================================================================
def init_session():
    defaults = {
        "imputado": "", 
        "tribunal_sel": TRIBUNALES[9],
        "ejecucion": [{"rit": "", "ruc": ""}],
        "rpa": [{"rit": "", "ruc": "", "tribunal": "", "sancion": ""}],
        "adulto": [],
        "defensor_nombre": ""
    }
    for k, v in defaults.items():
        if k not in st.session_state: st.session_state[k] = v

# =============================================================================
# 7. INTERFAZ PRINCIPAL
# =============================================================================
def main():
    init_session()
    
    with st.sidebar:
        st.header("⚖️ Configuración Letrada")
        st.session_state.defensor_nombre = st.text_input("Nombre Defensor/a", st.session_state.defensor_nombre, placeholder="EJ: IGNACIO BADILLA LARA")
        st.divider()
        tipo_recurso = st.selectbox("Tipo de Escrito", TIPOS_RECURSOS)
        es_rpa = st.toggle("Es causa RPA (Adolescente)", value=True)

    st.title(f"📄 Suite IABL: {tipo_recurso}")
    
    # --- PESTAÑAS PRINCIPALES ---
    tab_gen, tab_tools, tab_admin = st.tabs(["📝 Generador de Escritos", "🧰 Herramientas Legales", "⚙️ Admin"])

    # === PESTAÑA 1: GENERADOR ===
    with tab_gen:
        col1, col2 = st.columns([2, 1])
        with col1:
            st.subheader("1. Individualización")
            st.session_state.imputado = st.text_input("Nombre Imputado", st.session_state.imputado)
            st.session_state.tribunal_sel = st.selectbox("Tribunal Competente", TRIBUNALES, index=TRIBUNALES.index(st.session_state.tribunal_sel) if st.session_state.tribunal_sel in TRIBUNALES else 0)

        st.subheader("2. Causas en Ejecución (Base)")
        for i, item in enumerate(st.session_state.ejecucion):
            c1, c2, c3 = st.columns([3, 3, 1])
            item['rit'] = c1.text_input(f"RIT", item['rit'], key=f"rit_{i}", placeholder="Ej: 1234-2023")
            item['ruc'] = c2.text_input(f"RUC", item['ruc'], key=f"ruc_{i}", placeholder="Ej: 2300123456-8")
            if c3.button("🗑️", key=f"del_ej_{i}"):
                st.session_state.ejecucion.pop(i)
                st.rerun()
                
        col_btn_1, col_btn_2 = st.columns([1, 4])
        if col_btn_1.button("➕ Causa"):
            st.session_state.ejecucion.append({"rit": "", "ruc": ""})
            st.rerun()
        
        pdf_ej = col_btn_2.file_uploader("O cargar PDF (Acta)", type="pdf", label_visibility="collapsed", key="pdf_ej")
        if pdf_ej and st.button("Analizar Acta Ejecución"):
            data = analizar_pdf(pdf_ej, "Acta")
            if data:
                st.session_state.ejecucion[0]['rit'] = data.get('rit', '')
                st.session_state.ejecucion[0]['ruc'] = data.get('ruc', '')
                st.success("✅ Datos cargados")
                st.rerun()

        st.markdown("---")

        # Lógica Específica
        if tipo_recurso == "Extinción Art. 25 ter":
            c_rpa, c_adulto = st.columns(2)
            with c_rpa:
                st.markdown("### A. Causas RPA")
                for i, item in enumerate(st.session_state.rpa):
                    with st.expander(f"Causa RPA #{i+1}", expanded=True):
                        item['rit'] = st.text_input("RIT", item['rit'], key=f"rpa_rit_{i}")
                        item['tribunal'] = st.selectbox("Tribunal", TRIBUNALES, key=f"rpa_trib_{i}")
                        item['sancion'] = st.text_input("Sanción", item['sancion'], key=f"rpa_sanc_{i}")
                if st.button("➕ Otra RPA"):
                    st.session_state.rpa.append({"rit":"", "tribunal":"", "sancion":""})
                    st.rerun()

            with c_adulto:
                st.markdown("### B. Causa Adulto")
                for i, item in enumerate(st.session_state.adulto):
                    with st.expander(f"Condena Adulto #{i+1}", expanded=True):
                        item['rit'] = st.text_input("RIT", item['rit'], key=f"ad_rit_{i}")
                        item['pena'] = st.text_input("Pena", item['pena'], key=f"ad_pena_{i}")
                        item['fecha'] = st.text_input("Fecha", item['fecha'], key=f"ad_fec_{i}")
                if st.button("➕ Condena Adulto"):
                    st.session_state.adulto.append({"rit":"", "pena":"", "fecha":""})
                    st.rerun()
                pdf_ad = st.file_uploader("Subir Sentencia Adulto", type="pdf")
                if pdf_ad and st.button("Extraer Datos Adulto"):
                    data = analizar_pdf(pdf_ad, "Sentencia Adulto")
                    if data:
                        st.session_state.adulto.append({"rit": data.get('rit',''), "pena": data.get('pena',''), "fecha": data.get('fecha_sentencia','')})
                        st.rerun()

        elif tipo_recurso == "Minuta Control de Detención":
            st.subheader("⏱️ Detalles Detención")
            c1, c2 = st.columns(2)
            fecha_det = c1.text_input("Fecha/Hora", placeholder="Ej: 12-02-2024 14:30")
            lugar_det = c2.text_input("Lugar", placeholder="Ej: 14 Comisaría")
            
            st.subheader("🛡️ Argumentos")
            tipo_args = "RPA" if es_rpa else "Adulto"
            args_seleccionados = st.multiselect(f"Seleccione ({tipo_args})", ARGUMENTOS_DETENCION[tipo_args])
            extra_arg = st.text_area("Argumento Adicional")
            if extra_arg: args_seleccionados.append(extra_arg)

        st.markdown("<br>", unsafe_allow_html=True)
        if st.button(f"🚀 GENERAR {tipo_recurso.upper()}", type="primary", use_container_width=True):
            if not st.session_state.defensor_nombre or not st.session_state.imputado:
                st.error("⚠️ Faltan datos (Defensor o Imputado)")
            else:
                datos_finales = {
                    "tribunal_ej": st.session_state.tribunal_sel,
                    "ejecucion": st.session_state.ejecucion,
                    "rpa": st.session_state.rpa,
                    "adulto": st.session_state.adulto,
                    "fecha_det": locals().get('fecha_det', ''),
                    "lugar_det": locals().get('lugar_det', ''),
                    "argumentos_det": locals().get('args_seleccionados', [])
                }
                gen = GeneradorWord(st.session_state.defensor_nombre, st.session_state.imputado)
                doc_buffer = gen.generar(tipo_recurso, datos_finales)
                st.success("✅ Generado")
                st.download_button("📥 Descargar DOCX", doc_buffer, f"{tipo_recurso}_{st.session_state.imputado}.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document", use_container_width=True)

    # === PESTAÑA 2: HERRAMIENTAS LEGALES ===
    with tab_tools:
        st.header("🧰 Caja de Herramientas IABL")
        
        # HERRAMIENTA 1: CALCULADORA RPA
        with st.expander("🧮 Calculadora de Pena Mixta (Ley 20.084)", expanded=True):
            st.markdown("Convierte una pena teórica de adulto a su equivalente RPA según reglas del Art. 21.")
            pena_input = st.selectbox("Seleccione Pena de Adulto (Marco Abstracto)", 
                ["Presidio Perpetuo Calificado", "Presidio Perpetuo Simple", 
                 "Presidio Mayor en su grado máximo", "Presidio Mayor en su grado medio",
                 "Presidio Menor en su grado máximo", "Presidio Menor en su grado medio"])
            
            if st.button("Calcular Sanción RPA"):
                res = calcular_pena_rpa(pena_input)
                st.success(f"📌 Sanción Probable RPA: **{res}**")
                st.caption("*Cálculo referencial basado en rebaja de grado Art. 21 Ley 20.084")

        # HERRAMIENTA 2: BUSCADOR JURISPRUDENCIA
        with st.expander("🔎 Asistente de Jurisprudencia (IA)", expanded=True):
            st.markdown("Busca argumentos y jurisprudencia referencial utilizando la base de conocimiento de Gemini.")
            tema_busqueda = st.text_input("Tema a investigar (Ej: 'Prisión preventiva rpa peligro sociedad')")
            
            if st.button("Investigar Tema"):
                with st.spinner("Analizando doctrina y fallos recientes..."):
                    resultado = buscar_jurisprudencia_ia(tema_busqueda)
                    st.markdown(f"<div class='juris-box'>{resultado}</div>", unsafe_allow_html=True)
                    st.info("⚠️ Verifica siempre los roles citados en la página del Poder Judicial.")

    # === PESTAÑA 3: ADMIN ===
    with tab_admin:
        st.write("Panel de Administración - Conexión Supabase")
        if supabase:
            st.success("🟢 Conexión Activa")
        else:
            st.error("🔴 Sin Conexión")

if __name__ == "__main__":
    main()
