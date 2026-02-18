import reflex as rx

class State(rx.State):
    """Application state."""
    pass


def index() -> rx.Component:
    """Main page component."""
    return rx.container(
        rx.vstack(
            rx.heading("Welcome to iabl_reflex", size="lg"),
            rx.text("Your application starts here"),
            spacing="4",
            align="center",
        ),
        center_content=True,
        padding="2em",
    )


app = rx.App()
app.add_page(index)
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
from typing import List

# =============================================================================
# 1. CONFIGURACIÓN Y ESTILOS
# =============================================================================

# Configura tus claves aquí si estás en local, o usa .env
SUPABASE_URL = os.environ.get("SUPABASE_URL", "") 
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY", "")

if GOOGLE_API_KEY:
    genai.configure(api_key=GOOGLE_API_KEY)

# PALETA NÓRDICA
COLORS = {
    "navy": "#161B2F",
    "slate": "#5B687C",
    "beige": "#F4F7F6",  # Fondo más claro
    "surface": "#FFFFFF",
    "accent": "#2C3E50",
    "border": "#E2E8F0"
}

# =============================================================================
# 2. MODELOS DE DATOS
# =============================================================================

class Jurisprudencia(rx.Base):
    rol: str = ""
    tribunal: str = ""
    tipo: str = ""
    contenido: str = ""
    similarity: float = 0.0

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
            mejor = next((m for m in modelos if 'gemini-1.5-pro' in m), models[0])
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
    
    # Biblioteca
    busqueda_query: str = ""
    filtro_tipo: str = "Todos"
    resultados_biblioteca: List[Jurisprudencia] = []
    respuesta_juridica_ia: str = ""
    
    # Admin
    admin_status: str = ""

    def login(self):
        self.is_loading = True
        yield
        sb = get_supabase()
        if sb:
            try:
                res = sb.auth.sign_in_with_password({"email": self.login_email, "password": self.login_pass})
                user = res.user
                if user:
                    # Buscar perfil
                    prof = sb.table("profiles").select("*").eq("id", user.id).execute()
                    if prof.data:
                        self.user_name = prof.data[0].get('nombre', 'Usuario')
                        self.user_role = prof.data[0].get('rol', 'User')
                    self.logged_in = True
            except Exception as e:
                return rx.window_alert("Credenciales incorrectas.")
        self.is_loading = False

    def logout(self):
        self.logged_in = False
        self.user_name = ""

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
            "argumentos_defensa": self.argumentos_defensa
        }
        gen = GeneradorWord(self.defensor_nombre, self.imputado)
        buffer = gen.generar(self.tipo_recurso, datos)
        b64_data = base64.b64encode(buffer.getvalue()).decode()
        return rx.download(data=b64_data, filename="Escrito_Legal.docx")

    def buscar_jurisprudencia(self):
        self.is_loading = True
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
                    
                    # Generar respuesta
                    ctx = "\n".join([h.contenido for h in self.resultados_biblioteca])
                    model = get_generative_model_dinamico()
                    ans = model.generate_content(f"Responde jurídicamente a '{self.busqueda_query}' usando: {ctx}")
                    self.respuesta_juridica_ia = ans.text
            except Exception as e:
                print(e)
        self.is_loading = False

# =============================================================================
# 5. UI COMPONENTS (ESTILO SAAS PREMIUM)
# =============================================================================

def sidebar_button(text, icon, page_name):
    """Botón del menú lateral con estado activo"""
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
            rx.avatar(fallback=State.user_name[:2], size="3"),
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
        display=["none", "none", "flex"] # Ocultar en móvil
    )

def login_screen():
    return rx.flex(
        rx.vstack(
            rx.heading("SISTEMA JURÍDICO IABL", size="8", color=COLORS["navy"], font_weight="900", letter_spacing="-1px"),
            rx.text(
                "Sistema de automatización avanzada con herramientas inteligentes pensada en defensores, porque tu tiempo vale, la salud laboral y la satisfacción del trabajo bien hecho.",
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
                            rx.input(placeholder="Correo Institucional", on_change=State.set_login_email, size="3", radius="full"),
                            rx.input(placeholder="Contraseña", type="password", on_change=State.set_login_pass, size="3", radius="full"),
                            rx.button("Ingresar al Sistema", on_click=State.login, size="3", radius="full", width="100%", loading=State.is_loading),
                            spacing="4",
                            align="stretch"
                        ),
                        value="login"
                    ),
                    rx.tabs.content(
                        rx.text("Contacte al administrador para crear cuenta.", margin_top="1em", color=COLORS["slate"]),
                        value="register"
                    ),
                    defaultValue="login"
                ),
                padding="2em",
                width="100%",
                max_width="450px",
                box_shadow="0 10px 40px -10px rgba(0,0,0,0.1)"
            ),
            
            rx.hstack(
                rx.card(rx.hstack(rx.icon("file-pen"), rx.text("Redacción")), padding="1em"),
                rx.card(rx.hstack(rx.icon("scan-eye"), rx.text("Visión IA")), padding="1em"),
                rx.card(rx.hstack(rx.icon("database"), rx.text("RAG Legal")), padding="1em"),
                spacing="4",
                margin_top="3em",
                opacity="0.8"
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
                rx.text("Redacción automatizada de escritos penales complejos.", color=COLORS["slate"]),
                rx.separator(),
                
                rx.card(
                    rx.vstack(
                        rx.heading("1. Individualización", size="4"),
                        rx.grid(
                            rx.vstack(rx.text("Defensor", weight="bold"), rx.input(value=State.defensor_nombre, on_change=State.set_defensor_nombre)),
                            rx.vstack(rx.text("Imputado", weight="bold"), rx.input(value=State.imputado, on_change=State.set_imputado)),
                            columns="2", spacing="4", width="100%"
                        ),
                        rx.heading("2. Datos de la Causa", size="4", margin_top="1em"),
                        rx.select(["Prescripción de la Pena", "Apelación por Quebrantamiento"], value=State.tipo_recurso, on_change=State.set_tipo_recurso),
                        rx.grid(
                            rx.input(placeholder="RIT (ej: 450-2023)", value=State.rit_input, on_change=State.set_rit_input),
                            rx.input(placeholder="RUC", value=State.ruc_input, on_change=State.set_ruc_input),
                            columns="2", spacing="4", width="100%"
                        ),
                        rx.text_area(placeholder="Hechos del Quebrantamiento...", value=State.hechos_quebrantamiento, on_change=State.set_hechos_quebrantamiento),
                        rx.text_area(placeholder="Argumentos de Derecho (Borrador)...", value=State.argumentos_defensa, on_change=State.set_argumentos_defensa, height="150px"),
                        rx.hstack(
                            rx.button("Limpiar", on_click=State.clear_form, variant="soft", color_scheme="gray"),
                            rx.button("✨ Mejorar con IA", on_click=State.robustecer_argumentos, variant="surface", color_scheme="blue", loading=State.is_loading),
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
                rx.text("Buscador semántico potenciado por RAG.", color=COLORS["slate"]),
                rx.separator(),
                
                rx.card(
                    rx.vstack(
                        rx.hstack(
                            rx.input(placeholder="Describe el problema jurídico (ej: Nulidad por falta de emplazamiento)...", value=State.busqueda_query, on_change=State.set_busqueda_query, width="100%", size="3"),
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
                                            rx.text(res.tribunal, font_weight="bold", font_size="0.9em"),
                                            rx.spacer(),
                                            rx.badge(res.tipo, variant="outline")
                                        ),
                                        rx.text(res.contenido, size="1", color="gray"),
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
        
        # Placeholder para otras páginas
        rx.cond(
            (State.current_page != "Generador") & (State.current_page != "Biblioteca"),
            rx.center(rx.text("Módulo en construcción", size="5", color="gray"), height="50vh")
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