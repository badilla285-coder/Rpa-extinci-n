import streamlit as st
from docx import Document
from docx.shared import Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
import PyPDF2, io, re, datetime

# --- SEGURIDAD ---
ADMIN_EMAIL = "badilla285@gmail.com"
USUARIOS_AUTORIZADOS = [ADMIN_EMAIL]

def check_auth():
    if "auth" not in st.session_state: st.session_state.auth = False
    if not st.session_state.auth:
        st.title("🔐 Acceso Restringido - LegalTech Pro")
        u = st.text_input("Usuario (Email)")
        p = st.text_input("Contraseña", type="password")
        if st.button("Ingresar"):
            if u in USUARIOS_AUTORIZADOS and p == "nacho2026":
                st.session_state.auth = True
                st.rerun()
            else: st.error("Acceso denegado.")
        return False
    return True

# --- MOTOR DE PLAZOS ---
def calcular_plazos(tipo, fecha):
    plazos = {
        "Apelación Prisión Preventiva / IP": 5,
        "Apelación Sentencia Definitiva": 5,
        "Recurso de Nulidad": 10,
        "Reposición (fuera de audiencia)": 3,
        "Revisión Mensual Cautelar (Sugerido)": 30
    }
    dias = plazos.get(tipo, 0)
    return fecha + datetime.timedelta(days=dias)

# --- INTERFAZ ---
if check_auth():
    st.set_page_config(page_title="Ignacio Badilla - Suite Jurídica", layout="wide")
    
    # Iniciar contadores de causas
    for k in ['ne', 'nr', 'na']:
        if k not in st.session_state: st.session_state[k] = 1

    st.sidebar.title("👨‍⚖️ Panel de Control")
    st.sidebar.info(f"Usuario: {ADMIN_EMAIL}\nVersión: 2.5 Gold")
    
    st.title("⚖️ Legal Intelligence Suite")
    
    tabs = st.tabs(["📄 Generador de Extinciones", "📅 Plazos y Cautelares", "🔍 Módulo MIA 360°"])

    # --- TAB 1: EL GENERADOR (TU CORAZÓN DEL NEGOCIO) ---
    with tabs[0]:
        st.subheader("Redactor de Escritos de Extinción")
        # Aquí mantienes tu lógica de RUC/RIT y generación de Word con Cambria 12
        st.write("Complete los datos para generar el escrito robusto.")
        # ... (Mantener aquí los campos de entrada de causas ejecución, RPA y Adulto que ya teníamos)

    # --- TAB 2: PLAZOS AMPLIADOS ---
    with tabs[1]:
        st.subheader("Calculadora de Plazos Críticos")
        c1, c2 = st.columns(2)
        with c1:
            res_tipo = st.selectbox("Tipo de Resolución", [
                "Apelación Prisión Preventiva / IP", 
                "Apelación Sentencia Definitiva",
                "Recurso de Nulidad",
                "Revisión Mensual Cautelar (Sugerido)"
            ])
        with c2:
            f_inicio = st.date_input("Fecha Notificación", datetime.date.today())
        
        vence = calcular_plazos(res_tipo, f_inicio)
        st.error(f"### 📅 Vencimiento: {vence.strftime('%d/%m/%Y')}")
        
        st.divider()
        st.write("**Resumen de Medidas Cautelares:**")
        st.info("Recordatorio: La Internación Provisoria en jóvenes debe revisarse judicialmente de forma periódica para asegurar el principio de excepcionalidad.")

    # --- TAB 3: NUEVO MIA ATRACTIVO (SIN ERRORES) ---
    with tabs[2]:
        st.subheader("🔍 Central de Investigación de Antecedentes")
        rut_input = st.text_input("Ingrese RUT del sujeto (ej: 12345678-9)")
        
        if rut_input:
            r_num = rut_input.replace(".","").split("-")[0]
            
            st.markdown(f"#### 🛰️ Radar para el RUT: {rut_input}")
            
            # Tarjetas Visuales de Interconexión
            col_a, col_b, col_c = st.columns(3)
            
            with col_a:
                st.markdown("🏛️ **Bases Judiciales**")
                st.link_button("⚖️ PJUD (Causas)", "https://oficinajudicialvirtual.pjud.cl/")
                st.link_button("📑 Diario Oficial", f"https://www.diariooficial.interior.gob.cl/edicionelectronica/busqueda.php?q={r_num}")
            
            with col_b:
                st.markdown("👤 **Datos Civiles**")
                st.link_button("🏠 Ver Domicilio (Rutificador)", f"https://www.nombrerutyfirma.com/rut/{r_num}")
                st.link_button("🗳️ Local Votación (Servel)", "https://consulta.servel.cl/")
            
            with col_c:
                st.markdown("🌐 **Huella Digital**")
                st.link_button("🔵 Perfiles Facebook", f"https://www.facebook.com/search/top/?q={rut_input}")
                st.link_button("📸 Google Social Check", f"https://www.google.com/search?q={rut_input}+instagram+detenido+noticias")

            st.divider()
            st.success("MIA ha configurado los túneles de acceso. Haga clic en la base que desea consultar.")

    st.markdown("---")
    st.caption("🚀 LegalTech diseñada por Ignacio Badilla Lara | San Bernardo, Chile")
