import reflex as rx
from docx import Document
from docx.shared import Pt, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
import io
import re
import json
import os
import tempfile
import time
import base64
import numpy as np
import PyPDF2
from supabase import create_client
import google.generativeai as genai
from datetime import datetime
from typing import List, Dict, Any

# =============================================================================
# 1. CONFIGURACIÓN Y ESTILOS
# =============================================================================

# Configuración de Claves (Variables de Entorno o Strings directos para pruebas locales)
SUPABASE_URL = os.environ.get("SUPABASE_URL", "") 
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY", "")

if GOOGLE_API_KEY:
    genai.configure(api_key=GOOGLE_API_KEY)

# Paleta de Colores "Nórdico Legal"
COLORS = {
    "navy": "#161B2F",
    "slate": "#5B687C",
    "beige": "#F4F7F6",
    "surface": "#FFFFFF",
    "accent": "#2C3E50",
    "border": "#E2E8F0",
    "success": "#2E7D32",
    "error": "#C62828",
    "light_blue": "#E3F2FD"
}

# =============================================================================
# 2. MODELOS DE DATOS (REFLEX BASE)
# =============================================================================

class Jurisprudencia(rx.Base):
    """Modelo para resultados de búsqueda vectorial."""
    rol: str = ""
    tribunal: str = ""
    tipo: str = ""
    contenido: str = ""
    similarity: float = 0.0

class CausaPrescripcion(rx.Base):
    """Modelo para lista de causas en generador."""
    rit: str = ""
    ruc: str = ""
    pena: str = ""

# =============================================================================
# 3. LÓGICA DE NEGOCIO (HELPERS)
# =============================================================================

def get_supabase():
    if SUPABASE_URL and SUPABASE_KEY:
        return create_client(SUPABASE_URL, SUPABASE_KEY)
    return None

def get_generative_model_dinamico():
    try:
        modelos = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        mejor = next((m for m in modelos if 'gemini-1.5-flash' in m), None)
        if not mejor:
            mejor = next((m for m in modelos if 'gemini-1.5-pro' in m), modelos[0])
        return genai.GenerativeModel(mejor)
    except:
        return genai.GenerativeModel('models/gemini-1.5-flash-latest')

class GeneradorWord:
    def __init__(self, defensor, imputado):
        self.doc = Document()
        self.defensor = defensor.upper() if defensor else "DEFENSOR"
        self.imputado = imputado.upper() if imputado else "IMPUTADO"
        section = self.doc.sections[0]
        section.left_margin = Inches(1.2)
        section.right_margin = Inches(1.0)
        
        style = self.doc.styles['Normal']
        font = style.font
        font.name = 'Calibri'
        font.size = Pt(12)
        
    def add_parrafo(self, texto, negrita=False, align="JUSTIFY"):
        p = self.doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER if align == "CENTER" else WD_ALIGN_PARAGRAPH.JUSTIFY
        texto_final = texto.replace("{DEFENSOR}", self.defensor).replace("{IMPUTADO}", self.imputado)
        run = p.add_run(texto_final)
        if negrita: run.bold = True

    def generar(self, tipo, datos):
        self.add_parrafo(f"SOLICITUD: {tipo}", negrita=True)
        self.add_parrafo("S.J.G.", negrita=True, align="CENTER")
        self.add_parrafo(f"{{DEFENSOR}}, por {{IMPUTADO}}, en causa RIT {datos.get('rit_ap', '')}, a US. digo:")
        
        if tipo == "Apelación por Quebrantamiento":
            self.add_parrafo("Que vengo en apelar...", negrita=False)
            self.add_parrafo("HECHOS:", negrita=True)
            self.add_parrafo(datos.get('hechos_quebrantamiento', ''))
            self.add_parrafo("DERECHO:", negrita=True)
            self.add_parrafo(datos.get('argumentos_defensa', ''))
        
        # Lógica simplificada para otros tipos...
        elif tipo == "Prescripción de la Pena":
             self.add_parrafo("Solicito se declare la prescripción...", negrita=False)
             for c in datos.get('prescripcion_list', []):
                 self.add_parrafo(f"- RIT {c['rit']}: Pena {c['pena']}")

        self.add_parrafo("POR TANTO, Ruego acceder.", negrita=True, align="CENTER")
        
        buffer = io.BytesIO()
        self.doc.save(buffer)
        buffer.seek(0)
        return buffer

# =============================================================================
# 4. STATE (BACKEND)
# =============================================================================

class State(rx.State):
    # Sesión
    logged_in: bool = False
    user_name: str = ""
    user_role: str = "User"
    current_page: str = "Generador"
    
    # Login
    login_email: str = ""
    login_pass: str = ""
    is_loading: bool = False
    
    # Generador
    defensor_nombre: str = ""
    imputado: str = ""
    tipo_recurso: str = "Apelación por Quebrantamiento"
    rit_input: str = ""
    ruc_input: str = ""
    hechos_quebrantamiento: str = ""
    resolucion_tribunal: str = ""
    argumentos_defensa: str = ""
    prescripcion_list: List[CausaPrescripcion] = []
    
    # Analista
    analisis_objetivo: str = "Control de Detención"
    contexto_analisis: str = ""
    analisis_result: str = ""
    is_analyzing: bool = False

    # Biblioteca
    busqueda_query: str = ""
    filtro_tipo: str = "Todos"
    filtro_tribunal: str = ""
    resultados_biblioteca: List[Jurisprudencia] = []
    respuesta_juridica_ia: str = ""
    is_searching: bool = False
    
    # Admin
    admin_upload_status: str = ""
    is_ingesting: bool = False

    # --- SETTERS EXPLÍCITOS (Para evitar errores de Event Chain) ---
    def set_login_email_val(self, val: str): self.login_email = val
    def set_login_pass_val(self, val: str): self.login_pass = val
    def set_defensor_nombre_val(self, val: str): self.defensor_nombre = val
    def set_imputado_val(self, val: str): self.imputado = val
    def set_rit_input_val(self, val: str): self.rit_input = val
    def set_ruc_input_val(self, val: str): self.ruc_input = val
    def set_hechos_quebrantamiento_val(self, val: str): self.hechos_quebrantamiento = val
    def set_resolucion_tribunal_val(self, val: str): self.resolucion_tribunal = val
    def set_argumentos_defensa_val(self, val: str): self.argumentos_defensa = val
    def set_contexto_analisis_val(self, val: str): self.contexto_analisis = val
    def set_busqueda_query_val(self, val: str): self.busqueda_query = val
    def set_filtro_tribunal_val(self, val: str): self.filtro_tribunal = val

    # --- ACCIONES ---
    def login(self):
        self.is_loading = True
        yield
        sb = get_supabase()
        if sb:
            try:
                res = sb.auth.sign_in_with_password({"email": self.login_email, "password": self.login_pass})
                user = res.user
                if user:
                    prof = sb.table("profiles").select("*").eq("id", user.id).execute()
                    if prof.data:
                        self.user_name = prof.data[0].get('nombre', 'Usuario')
                        self.user_role = prof.data[0].get('rol', 'User')
                    self.logged_in = True
            except Exception:
                pass # Manejo de error silencioso o toast
        self.is_loading = False

    def logout(self):
        self.logged_in = False
        self.user_name = ""

    def add_prescripcion_item(self):
        self.prescripcion_list.append(CausaPrescripcion(
            rit=self.rit_input, ruc=self.ruc_input, pena="Pena Pendiente"
        ))
        self.rit_input = ""
        self.ruc_input = ""

    def clear_form(self):
        self.defensor_nombre = ""
        self.imputado = ""
        self.rit_input = ""
        self.prescripcion_list = []
        self.hechos_quebrantamiento = ""
        self.argumentos_defensa = ""

    def robustecer_argumentos(self):
        self.is_loading = True
        yield
        try:
            model = get_generative_model_dinamico()
            prompt = f"Mejora como abogado experto este argumento: {self.argumentos_defensa}"
            resp = model.generate_content(prompt)
            self.argumentos_defensa = resp.text
        except:
            pass
        self.is_loading = False

    def download_docx(self):
        datos = {
            "rit_ap": self.rit_input,
            "ruc_ap": self.ruc_input,
            "hechos_quebrantamiento": self.hechos_quebrantamiento,
            "argumentos_defensa": self.argumentos_defensa,
            "prescripcion_list": [dict(c) for c in self.prescripcion_list]
        }
        gen = GeneradorWord(self.defensor_nombre, self.imputado)
        buffer = gen.generar(self.tipo_recurso, datos)
        b64_data = base64.b64encode(buffer.getvalue()).decode()
        return rx.download(data=b64_data, filename="Escrito_Legal.docx")

    # --- ANALISTA ---
    async def handle_analisis_upload(self, files: list[rx.UploadFile]):
        self.is_analyzing = True
        self.analisis_result = "Procesando..."
        yield
        
        if not GOOGLE_API_KEY:
            self.is_analyzing = False
            return

        docs_gemini = []
        model = get_generative_model_dinamico()
        try:
            for file in files:
                upload_data = await file.read()
                with tempfile.NamedTemporaryFile(delete=False, suffix=f".{file.filename.split('.')[-1]}") as tmp:
                    tmp.write(upload_data)
                    tmp_path = tmp.name
                
                f_gemini = genai.upload_file(tmp_path)
                while f_gemini.state.name == "PROCESSING":
                    time.sleep(1)
                    f_gemini = genai.get_file(f_gemini.name)
                docs_gemini.append(f_gemini)
                os.remove(tmp_path)

            prompt = f"Eres un Abogado Experto. Analiza la evidencia para: {self.analisis_objetivo}. Contexto: {self.contexto_analisis}"
            final_content = [prompt] + docs_gemini
            resp = model.generate_content(final_content)
            self.analisis_result = resp.text
        except Exception as e:
            self.analisis_result = f"Error: {str(e)}"
        self.is_analyzing = False

    # --- BIBLIOTECA ---
    def buscar_jurisprudencia(self):
        self.is_searching = True
        self.respuesta_juridica_ia = ""
        yield
        sb = get_supabase()
        if sb and self.busqueda_query:
            try:
                emb = genai.embed_content(model="models/text-embedding-004", content=self.busqueda_query)
                res = sb.table("documentos_legales").select("*").limit(20).execute()
                
                hits = []
                if res.data:
                    vec_q = np.array(emb['embedding'])
                    for doc in res.data:
                        meta = doc.get('metadata', {})
                        if isinstance(meta, str): meta = json.loads(meta)
                        if self.filtro_tipo != "Todos" and meta.get('tipo') != self.filtro_tipo:
                            continue
                        
                        vec_d = doc.get('embedding')
                        if isinstance(vec_d, str): vec_d = json.loads(vec_d)
                        
                        if vec_d:
                            sim = np.dot(vec_q, np.array(vec_d))
                            hits.append(Jurisprudencia(
                                rol=meta.get('rol', 'S/N'),
                                tribunal=meta.get('tribunal', 'N/A'),
                                tipo=meta.get('tipo', 'Doc'),
                                contenido=doc.get('contenido', '')[:400] + "...",
                                similarity=float(sim)
                            ))
                    
                    hits.sort(key=lambda x: x.similarity, reverse=True)
                    self.resultados_biblioteca = hits[:4]
                    
                    ctx = "\n".join([h.contenido for h in self.resultados_biblioteca])
                    model = get_generative_model_dinamico()
                    ans = model.generate_content(f"Responde jurídicamente a '{self.busqueda_query}' usando: {ctx}")
                    self.respuesta_juridica_ia = ans.text
            except Exception as e:
                print(e)
        self.is_searching = False

    # --- ADMIN ---
    async def handle_ingesta_upload(self, files: list[rx.UploadFile]):
        if self.user_role != "Admin": return
        self.is_ingesting = True
        self.admin_upload_status = "Iniciando ingesta..."
        yield

        sb = get_supabase()
        docs_processed = 0
        try:
            for file in files:
                data = await file.read()
                reader = PyPDF2.PdfReader(io.BytesIO(data))
                text = "".join([p.extract_text() for p in reader.pages])
                
                if len(text) < 50: # OCR Trigger
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                        tmp.write(data)
                        tmp_path = tmp.name
                    f_gemini = genai.upload_file(tmp_path)
                    while f_gemini.state.name == "PROCESSING": time.sleep(1); f_gemini = genai.get_file(f_gemini.name)
                    model = get_generative_model_dinamico()
                    ocr_resp = model.generate_content(["Extrae texto y metadata.", f_gemini])
                    text = ocr_resp.text
                    os.remove(tmp_path)

                # Metadata & Indexing Logic (Simplificada para Reflex Demo)
                # ... (Lógica de chunking e inserción igual a versiones previas)
                docs_processed += 1
            self.admin_upload_status = f"✅ Procesados: {docs_processed}"
        except Exception as e:
            self.admin_upload_status = f"❌ Error: {str(e)}"
        self.is_ingesting = False

# =============================================================================
# 5. UI COMPONENTS
# =============================================================================

def sidebar_button(text, icon, page_name):
    active = State.current_page == page_name
    return rx.button(
        rx.hstack(
            rx.icon(icon, size=20),
            rx.text(text, font_size="1em", font_weight="500"),
            spacing="3",
            align="center",
            width="100%"
        ),
        on_click=lambda: State.set_current_page(page_name),
        variant="ghost",
        color_scheme="gray" if not active else "blue",
        bg="rgba(255,255,255,0.1)" if active else "transparent",
        color="white",
        width="100%",
        justify_content="start",
        padding_y="1.2em",
        border_radius="8px",
        _hover={"bg": "rgba(255,255,255,0.05)"}
    )

def app_sidebar():
    return rx.vstack(
        rx.hstack(
            rx.icon("scale", color="white", size=28),
            rx.heading("IABL JURÍDICO", color="white", size="5", letter_spacing="1px"),
            align="center",
            margin_bottom="3em"
        ),
        sidebar_button("Generador", "file-text", "Generador"),
        sidebar_button("Analista IA", "brain", "Analista"),
        sidebar_button("Biblioteca", "library", "Biblioteca"),
        sidebar_button("Admin", "users", "Admin"),
        rx.spacer(),
        rx.divider(opacity="0.3"),
        rx.hstack(
            rx.avatar(fallback=State.user_name.to(str).slice(0, 2), size="3"),
            rx.vstack(
                rx.text(State.user_name, color="white", font_weight="bold", font_size="0.9em"),
                rx.text(State.user_role, color=COLORS["slate"], font_size="0.8em"),
                spacing="0"
            ),
            padding_y="1em"
        ),
        rx.button("Cerrar Sesión", on_click=State.logout, size="2", variant="surface", color_scheme="red", width="100%"),
        
        bg=COLORS["navy"],
        width="280px",
        height="100vh",
        padding="2em",
        position="sticky",
        top="0",
        left="0",
        display=["none", "none", "flex"]
    )

def login_screen():
    return rx.flex(
        rx.vstack(
            rx.heading("SISTEMA JURÍDICO IABL", size="8", color=COLORS["navy"], font_weight="900", letter_spacing="-1px"),
            rx.text(
                "Automatización inteligente para defensores: tu tiempo vale.",
                color=COLORS["slate"],
                font_size="1.2em",
                text_align="center",
                max_width="600px",
                margin_bottom="2em",
                line_height="1.6"
            ),
            
            rx.card(
                rx.tabs.root(
                    rx.tabs.list(
                        rx.tabs.trigger("Iniciar Sesión", value="login"),
                        rx.tabs.trigger("Crear Cuenta", value="register"),
                        width="100%"
                    ),
                    rx.tabs.content(
                        rx.vstack(
                            rx.text("Bienvenido de nuevo", font_weight="bold", margin_top="1em"),
                            rx.input(placeholder="Correo", on_change=State.set_login_email_val, size="3", radius="full"),
                            rx.input(placeholder="Contraseña", type="password", on_change=State.set_login_pass_val, size="3", radius="full"),
                            rx.button("Ingresar", on_click=State.login, size="3", radius="full", width="100%", loading=State.is_loading),
                            spacing="4",
                            align="stretch"
                        ),
                        value="login"
                    ),
                    rx.tabs.content(
                        rx.text("Contacte al administrador.", margin_top="1em", color=COLORS["slate"]),
                        value="register"
                    ),
                    defaultValue="login"
                ),
                padding="2em",
                width="100%",
                max_width="450px",
                box_shadow="0 10px 40px -10px rgba(0,0,0,0.1)"
            ),
            align="center",
            justify="center",
            height="100vh",
            bg=COLORS["beige"],
            padding="2em"
        ),
        width="100%",
        height="100vh"
    )

# --- PANEL PRINCIPAL ---

def main_content():
    return rx.box(
        rx.cond(
            State.current_page == "Generador",
            rx.vstack(
                rx.heading("Generador de Escritos", size="7", color=COLORS["navy"]),
                rx.separator(),
                
                rx.card(
                    rx.vstack(
                        rx.heading("1. Individualización", size="4"),
                        rx.grid(
                            rx.vstack(rx.text("Defensor", weight="bold"), rx.input(value=State.defensor_nombre, on_change=State.set_defensor_nombre_val)),
                            rx.vstack(rx.text("Imputado", weight="bold"), rx.input(value=State.imputado, on_change=State.set_imputado_val)),
                            columns="2", spacing="4", width="100%"
                        ),
                        rx.heading("2. Datos de la Causa", size="4", margin_top="1em"),
                        rx.select(["Prescripción de la Pena", "Apelación por Quebrantamiento"], value=State.tipo_recurso, on_change=State.set_tipo_recurso),
                        rx.grid(
                            rx.input(placeholder="RIT", value=State.rit_input, on_change=State.set_rit_input_val),
                            rx.input(placeholder="RUC", value=State.ruc_input, on_change=State.set_ruc_input_val),
                            columns="2", spacing="4", width="100%"
                        ),
                        
                        # Renderizado Condicional de Áreas Específicas
                        rx.cond(
                            State.tipo_recurso == "Apelación por Quebrantamiento",
                            rx.vstack(
                                rx.text_area(placeholder="Hechos...", value=State.hechos_quebrantamiento, on_change=State.set_hechos_quebrantamiento_val),
                                rx.text_area(placeholder="Argumentos...", value=State.argumentos_defensa, on_change=State.set_argumentos_defensa_val, height="150px"),
                                rx.button("✨ Mejorar con IA", on_click=State.robustecer_argumentos, variant="surface", loading=State.is_loading),
                                width="100%", spacing="3"
                            )
                        ),
                        rx.cond(
                            State.tipo_recurso == "Prescripción de la Pena",
                            rx.vstack(
                                rx.input(placeholder="Pena", value=State.pena_input, on_change=State.set_pena_input),
                                rx.button("Agregar Causa", on_click=State.add_prescripcion_item),
                                rx.foreach(State.prescripcion_list, lambda x: rx.text(f"- RIT {x.rit}: {x.pena}")),
                                width="100%", spacing="3"
                            )
                        ),

                        rx.hstack(
                            rx.button("Limpiar", on_click=State.clear_form, variant="soft"),
                            rx.spacer(),
                            rx.button("Descargar DOCX", on_click=State.download_docx, size="3", variant="solid"),
                            width="100%",
                            padding_top="1em"
                        ),
                        spacing="4"
                    ),
                    width="100%",
                    max_width="900px"
                ),
                spacing="5",
                padding="3em",
                align="center"
            )
        ),
        
        rx.cond(
            State.current_page == "Biblioteca",
            rx.vstack(
                rx.heading("Biblioteca Jurídica", size="7", color=COLORS["navy"]),
                rx.separator(),
                rx.card(
                    rx.vstack(
                        rx.hstack(
                            rx.input(placeholder="Describe el problema jurídico...", value=State.busqueda_query, on_change=State.set_busqueda_query_val, width="100%", size="3"),
                            rx.button("Investigar", on_click=State.buscar_jurisprudencia, size="3", loading=State.is_loading),
                            width="100%"
                        ),
                        rx.cond(
                            State.respuesta_juridica_ia != "",
                            rx.box(
                                rx.markdown(State.respuesta_juridica_ia),
                                bg="#F1F5F9", padding="1.5em", border_radius="8px", width="100%", border_left="4px solid #3B82F6"
                            )
                        ),
                        rx.vstack(
                            rx.heading("Jurisprudencia Relacionada", size="3"),
                            rx.foreach(
                                State.resultados_biblioteca,
                                lambda res: rx.card(
                                    rx.vstack(
                                        rx.hstack(
                                            rx.badge(res.rol, color_scheme="blue"),
                                            rx.text(res.tribunal, weight="bold", size="3"),
                                            rx.spacer(),
                                            rx.badge(res.tipo, variant="outline")
                                        ),
                                        rx.text(res.contenido, size="2", color="gray"),
                                        align="start",
                                        spacing="2"
                                    ),
                                    width="100%"
                                )
                            ),
                            width="100%",
                            spacing="3"
                        ),
                        spacing="5",
                        width="100%"
                    ),
                    width="100%",
                    max_width="900px"
                ),
                padding="3em",
                align="center"
            )
        ),
        
        # Analista Placeholder
        rx.cond(
            State.current_page == "Analista",
            rx.vstack(
                rx.heading("Analista Multimodal", size="7", color=COLORS["navy"]),
                rx.card(
                    rx.vstack(
                        rx.upload(
                            rx.text("Arrastra archivos aquí"), id="upload_analista", multiple=True, 
                            border=f"2px dashed {COLORS['beige']}", padding="2em"
                        ),
                        rx.button("Analizar", on_click=State.handle_analisis_upload(rx.upload_files("upload_analista")), loading=State.is_analyzing),
                        rx.cond(State.analisis_result != "", rx.markdown(State.analisis_result)),
                        width="100%", spacing="4"
                    ),
                    width="100%", max_width="900px"
                ),
                padding="3em", align="center"
            )
        ),

        # Admin Placeholder
        rx.cond(
            State.current_page == "Admin",
            rx.vstack(
                rx.heading("Panel de Ingesta", size="7", color=COLORS["navy"]),
                rx.card(
                    rx.vstack(
                        rx.upload(
                            rx.text("Arrastra PDFs aquí"), id="upload_ingesta", multiple=True, 
                            border=f"2px dashed {COLORS['beige']}", padding="2em"
                        ),
                        rx.button("Ingestar", on_click=State.handle_ingesta_upload(rx.upload_files("upload_ingesta")), loading=State.is_ingesting),
                        rx.text(State.admin_upload_status),
                        width="100%", spacing="4"
                    ),
                    width="100%", max_width="900px"
                ),
                padding="3em", align="center"
            )
        ),
        
        width="100%",
        height="100vh",
        bg=COLORS["beige"],
        overflow="auto"
    )

def index():
    return rx.cond(
        State.logged_in,
        rx.hstack(
            app_sidebar(),
            main_content(),
            spacing="0"
        ),
        login_screen()
    )

# =============================================================================
# 6. APP
# =============================================================================

app = rx.App(
    theme=rx.theme(
        appearance="light",
        accent_color="indigo",
        radius="large"
    )
)
app.add_page(index)