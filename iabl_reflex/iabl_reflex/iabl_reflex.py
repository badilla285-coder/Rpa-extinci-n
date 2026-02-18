import reflex as rx
from supabase import create_client
import asyncio

# ==========================================
# 1. CONFIGURACIÓN Y CLAVES 🔑
# ==========================================
# Puse tus claves directas para evitar errores de configuración por ahora
SUPABASE_URL = "https://zblcddxbhyomkasmbvyz.supabase.co"
SUPABASE_KEY = "sb_publishable_pHMqXxI39AssehHdBs1wqA_NVjPc-FT"

# ==========================================
# 2. ESTILO "LUXUS" (PALETA NÓRDICA PRO) 🎨
# ==========================================
STYLE = {
    "bg_app": "#F4F7F6",
    "primary": "#161B2F",      # Navy Profundo
    "secondary": "#5B687C",    # Slate Blue
    "accent": "#00BFA5",       # Turquesa elegante para botones
    "white": "#FFFFFF",
    "glass": "rgba(255, 255, 255, 0.9)", # Efecto Vidrio
    "shadow": "0 8px 32px 0 rgba(31, 38, 135, 0.15)", # Sombra de alta gama
    "border": "1px solid rgba(255, 255, 255, 0.18)",
    "font": "Inter, system-ui, sans-serif"
}

# ==========================================
# 3. CEREBRO (STATE) 🧠
# ==========================================
class State(rx.State):
    usuario: str = ""
    password: str = ""
    nombre_usuario: str = ""
    logged_in: bool = False
    loading: bool = False
    error_login: str = ""
    pagina_actual: str = "Generador"

    # Variables de la App
    imputado: str = ""
    delito: str = ""
    resultado_generacion: str = ""

    def conectar_supabase(self):
        """Crea la conexión real"""
        return create_client(SUPABASE_URL, SUPABASE_KEY)

    async def login(self):
        """LOGIN REAL CONTRA TU BASE DE DATOS"""
        self.loading = True
        self.error_login = ""
        yield # Actualiza la UI para mostrar spinner

        await asyncio.sleep(1) # Simula carga para efecto visual
        
        try:
            sb = self.conectar_supabase()
            # 1. Intentar Loguear
            session = sb.auth.sign_in_with_password({"email": self.usuario, "password": self.password})
            
            if session.user:
                # 2. Obtener Nombre del Perfil
                data = sb.table("profiles").select("nombre").eq("id", session.user.id).execute()
                if data.data:
                    self.nombre_usuario = data.data[0]['nombre']
                else:
                    self.nombre_usuario = "Abogado"
                
                self.logged_in = True
        except Exception as e:
            self.error_login = "Credenciales incorrectas o error de conexión."
            print(e)
        
        self.loading = False

    def logout(self):
        self.logged_in = False
        self.usuario = ""
        self.password = ""
        self.pagina_actual = "Generador"

    def set_pagina(self, pagina: str):
        self.pagina_actual = pagina

    def generar_escrito(self):
        self.resultado_generacion = f"Borrador generado para {self.imputado} ({self.delito})."

    # Setters necesarios para los inputs
    def set_usuario(self, val: str): self.usuario = val
    def set_password(self, val: str): self.password = val
    def set_imputado(self, val: str): self.imputado = val

# ==========================================
# 4. COMPONENTES DE DISEÑO (UI KIT) 💅
# ==========================================

def input_luxus(placeholder, icono, on_change_fn, tipo="text"):
    """Un input con diseño de alta gama"""
    return rx.hstack(
        rx.icon(icono, color=STYLE["secondary"], size=20),
        rx.input(
            placeholder=placeholder,
            on_change=on_change_fn,
            type_=tipo,
            variant="soft",
            bg="transparent",
            border="none",
            _focus={"outline": "none"},
            width="100%"
        ),
        padding="12px",
        bg="#F0F2F5",
        border_radius="12px",
        width="100%",
        align="center"
    )

def sidebar_btn(text, icon, page):
    """Botón del menú lateral inteligente"""
    # Calculamos si este botón está activo comparando con el estado
    active = State.pagina_actual == page
    
    return rx.button(
        rx.hstack(
            rx.icon(icon, color=rx.cond(active, STYLE["accent"], STYLE["white"]), size=22),
            rx.text(text, font_size="15px", font_weight="500"),
            spacing="3",
            align="center"
        ),
        bg=rx.cond(active, "rgba(255,255,255,0.1)", "transparent"),
        color=rx.cond(active, STYLE["accent"], "rgba(255,255,255,0.7)"),
        width="100%",
        justify="start",
        padding="20px",
        border_radius="12px",
        _hover={"bg": "rgba(255,255,255,0.05)", "color": STYLE["white"]},
        on_click=lambda: State.set_pagina(page)
    )

# ==========================================
# 5. PÁGINAS (VIEWS) 💻
# ==========================================

def login_view():
    return rx.center(
        rx.vstack(
            rx.heading("IABL LEGAL", size="8", color=STYLE["primary"], font_weight="900", letter_spacing="-1px"),
            rx.text("Inteligencia Artificial para Defensores", color=STYLE["secondary"], font_size="16px"),
            
            rx.card(
                rx.vstack(
                    rx.text("Bienvenido de nuevo", font_weight="bold", font_size="20px", color=STYLE["primary"]),
                    
                    input_luxus("Correo Institucional", "mail", State.set_usuario),
                    input_luxus("Contraseña", "lock", State.set_password, "password"),
                    
                    rx.cond(
                        State.error_login != "",
                        rx.callout(State.error_login, icon="alert-triangle", color_scheme="red", width="100%")
                    ),

                    rx.button(
                        rx.cond(State.loading, rx.spinner(color="white", size="small"), "INGRESAR AL SISTEMA"),
                        bg=STYLE["primary"],
                        color="white",
                        width="100%",
                        padding="22px",
                        border_radius="12px",
                        font_weight="bold",
                        box_shadow="0 4px 14px 0 rgba(0,0,0,0.39)",
                        _hover={"transform": "scale(1.02)", "bg": "#2C3550"},
                        on_click=State.login,
                    ),
                    spacing="5",
                    align="center",
                    width="100%"
                ),
                padding="40px",
                width="400px",
                bg=STYLE["white"],
                box_shadow=STYLE["shadow"],
                border_radius="24px"
            ),
            spacing="6",
            align="center"
        ),
        bg=STYLE["bg_app"],
        height="100vh",
        width="100%"
    )

def dashboard_view():
    return rx.hstack(
        # --- SIDEBAR ---
        rx.vstack(
            rx.heading("IABL", size="7", color="white", font_weight="900"),
            rx.text("LegalTech v2.0", color="rgba(255,255,255,0.5)", font_size="12px"),
            rx.divider(opacity="0.2", margin_y="20px"),
            
            rx.vstack(
                sidebar_btn("Generador de Escritos", "file-text", "Generador"),
                sidebar_btn("Analista Multimodal", "scan-eye", "Analista"),
                sidebar_btn("Biblioteca Jurídica", "library", "Biblioteca"),
                spacing="2",
                width="100%"
            ),
            
            rx.spacer(),
            
            rx.hstack(
                rx.avatar(fallback="AB", size="3", radius="full"),
                rx.vstack(
                    rx.text(State.nombre_usuario, color="white", font_weight="bold", font_size="14px"),
                    rx.text("Plan PRO", color=STYLE["accent"], font_size="11px"),
                    spacing="0"
                ),
                padding="15px",
                bg="rgba(0,0,0,0.2)",
                border_radius="12px",
                width="100%",
                align="center"
            ),
            
            bg=STYLE["primary"],
            width="280px",
            height="100vh",
            padding="30px",
            position="sticky",
            top="0"
        ),
        
        # --- CONTENIDO ---
        rx.box(
            rx.vstack(
                # Header
                rx.hstack(
                    rx.heading(State.pagina_actual, size="6", color=STYLE["primary"]),
                    rx.spacer(),
                    rx.icon("bell", color=STYLE["secondary"]),
                    width="100%",
                    padding_bottom="30px"
                ),
                
                # Contenido Dinámico
                rx.cond(
                    State.pagina_actual == "Generador",
                    rx.card(
                        rx.vstack(
                            rx.heading("Nueva Solicitud", size="4"),
                            rx.text("El sistema redactará el escrito basado en tus parámetros.", color="gray"),
                            rx.grid(
                                input_luxus("Nombre Imputado", "user", State.set_imputado),
                                input_luxus("RIT / RUC", "hash", lambda x: x), # lambda x: x es placeholder
                                columns="2",
                                spacing="4",
                                width="100%"
                            ),
                            rx.button("GENERAR DOCUMENTO", bg=STYLE["accent"], color="white", size="3", on_click=State.generar_escrito),
                             rx.cond(
                                State.resultado_generacion != "",
                                rx.callout(State.resultado_generacion, icon="check-circle", color_scheme="green")
                            ),
                            spacing="4",
                            align="start"
                        ),
                        width="100%", padding="30px", box_shadow="sm"
                    ),
                    rx.text("Módulo en construcción...")
                ),
                
                width="100%",
                max_width="1200px",
                margin="0 auto"
            ),
            bg=STYLE["bg_app"],
            width="100%",
            height="100vh",
            padding="40px",
            overflow="auto"
        ),
        spacing="0"
    )

def index():
    return rx.cond(State.logged_in, dashboard_view(), login_view())

app = rx.App(style={"font_family": "Inter"})
app.add_page(index)