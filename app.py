import streamlit as st
from docx import Document
from docx.shared import Pt, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
import io
import re
from datetime import datetime, timedelta
import PyPDF2
import pandas as pd

# --- CONFIGURACIÓN Y LISTAS ---
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

# --- GESTIÓN DE USUARIOS INICIAL ---
if "usuarios_db" not in st.session_state:
    st.session_state.usuarios_db = {
        "badilla285@gmail.com": {"nombre": "IGNACIO BADILLA LARA", "pw": "RPA2026", "nivel": "Admin"},
        "colega1@pjud.cl": {"nombre": "DEFENSOR ASOCIADO 1", "pw": "LEGAL2026", "nivel": "Usuario"},
    }

# --- FUNCIONES DE APOYO ---
def validar_ruc_chileno(ruc):
    if not ruc: return True
    patron = r"^\d{7,9}-[\dkK]$"
    return bool(re.match(patron, ruc))

def check_password():
    if "auth_user" not in st.session_state:
        st.title("🔐 Acceso a Generador de Escritos")
        c1, c2 = st.columns(2)
        email = c1.text_input("Correo electrónico")
        pw = c2.text_input("Contraseña", type="password")
        if st.button("Ingresar"):
            if email in st.session_state.usuarios_db and st.session_state.usuarios_db[email]["pw"] == pw:
                st.session_state["auth_user"] = email
                st.session_state["user_name"] = st.session_state.usuarios_db[email]["nombre"]
                st.session_state["is_admin"] = (st.session_state.usuarios_db[email]["nivel"] == "Admin")
                if "legal_coins" not in st.session_state: st.session_state["legal_coins"] = 0
                if "stats_count" not in st.session_state: st.session_state["stats_count"] = 0
                st.rerun()
            else:
                st.error("Credenciales incorrectas")
        return False
    return True

class GeneradorOficial:
    def __init__(self, defensor, adolescente):
        self.fuente = "Cambria"
        self.tamano = 12
        self.defensor = defensor
        self.adolescente = adolescente

    def limpiar_tribunal(self, nombre):
        if not nombre: return ""
        nombre_up = nombre.upper().strip()
        if nombre_up.startswith("JUZGADO DE"): return nombre_up
        return f"JUZGADO DE GARANTÍA DE {nombre_up}"

    def generar_docx(self, data):
        doc = Document()
        for s in doc.sections:
            s.left_margin, s.right_margin = Inches(1.2), Inches(1.0)

        def add_p(texto_base, bold_all=False, indent=True):
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            p.paragraph_format.line_spacing_rule = WD_LINE_SPACING.ONE_POINT_FIVE
            if indent: p.paragraph_format.first_line_indent = Inches(0.5)
            def_esc = re.escape(self.defensor.upper())
            ado_esc = re.escape(self.adolescente.upper())
            patron = f"(RIT|RUC|{def_esc}|{ado_esc}|JUZGADO DE [A-ZÁÉÍÓÚÑ\s]+|\d+-\d{{4}}|\d{{7,10}}-[\dkK])"
            partes = re.split(patron, texto_base, flags=re.IGNORECASE)
            for fragmento in partes:
                if not fragmento: continue
                run = p.add_run(fragmento)
                run.font.name, run.font.size = self.fuente, Pt(self.tamano)
                if bold_all or (re.match(patron, fragmento, re.IGNORECASE) and fragmento.lower() != "mérito"):
                    run.bold = True
            return p

        suma = doc.add_paragraph()
        r_suma = suma.add_run("EN LO PRINCIPAL: SOLICITA EXTINCIÓN;\nOTROSÍ: ACOMPAÑA DOCUMENTO.")
        r_suma.bold = True
        r_suma.font.name, r_suma.font.size = self.fuente, Pt(self.tamano)
        add_p(f"\n{self.limpiar_tribunal(data['juzgado_ejecucion'])}", bold_all=True, indent=False)
        causas_ej_str = ", ".join([f"RIT: {c['rit']} (RUC: {c['ruc']})" for c in data['causas_ej_principales'] if c['rit']])
        comp = (f"\n{self.defensor.upper()}, Abogada, Defensora Penal Pública, en representación de "
                f"{self.adolescente.upper()}, en causas de ejecución {causas_ej_str}, a S.S., respetuosamente digo:")
        add_p(comp, indent=True)
        add_p("\nQue, vengo en solicitar que declare la extinción de las sanciones de la Ley de Responsabilidad Penal Adolescente, en virtud del artículo 25 ter y 25 quinquies de la Ley 20.084.")
        for i, c in enumerate(data['causas_rpa'], 1):
            add_p(f"{i}. RIT: {c['rit']}, RUC: {c['ruc']}: Condenado por el {self.limpiar_tribunal(c['juzgado'])} a la pena de {c['sancion']}.")
        add_p("\nEl fundamento para solicitar la discusión radica en una condena de mayor gravedad como adulto:")
        for i, c in enumerate(data['causas_adulto'], 1):
            idx = i + len(data['causas_rpa'])
            add_p(f"{idx}. RIT: {c['rit']}, RUC: {c['ruc']}: Condenado por el {self.limpiar_tribunal(c['juzgado'])}, con fecha {c['fecha']}, a la pena de {c['pena']}.")
        add_p("\nPOR TANTO,", indent=False)
        add_p("En mérito de lo expuesto, SOLICITO A S.S. acceder a lo solicitado extinguiendo de pleno derecho la sanción antes referida.")
        
        rits_adulto = ", ".join([f"RIT: {c['rit']} (RUC: {c['ruc']})" for c in data['causas_adulto'] if c['rit']])
        add_p(f"\nOTROSÍ: Acompaña sentencias de adulto de mi representado de las causas {rits_adulto}.", bold_all=True, indent=False)
        add_p("POR TANTO, SOLICITO A S.S. se tengan por acompañadas.", indent=False)
        buf = io.BytesIO(); doc.save(buf); buf.seek(0)
        return buf

# --- INTERFAZ STREAMLIT ---
if check_password():
    st.set_page_config(page_title="Generador Judicial IBL", layout="wide")
    if "rpa_list" not in st.session_state: st.session_state.rpa_list = []
    if "adulto_list" not in st.session_state: st.session_state.adulto_list = []
    if "ej_list" not in st.session_state: st.session_state.ej_list = [{"rit":"", "ruc":""}]

    with st.sidebar:
        # Reloj Chile (Elegante)
        hora_cl = (datetime.utcnow() - timedelta(hours=3)).strftime('%H:%M:%S')
        st.markdown(f"🖋️ **Horario de Gestión:** {hora_cl}")
        st.header("👤 Perfil")
        st.write(f"Defensor: **{st.session_state.user_name}**")
        st.write(f"LegalCoins: **{st.session_state.legal_coins}** 🪙")
        st.progress(min(st.session_state.legal_coins / 500, 1.0))

        st.markdown("---")
        st.header("📂 Unir Documentos")
        pdfs = st.file_uploader("Adjuntar archivos a unir", accept_multiple_files=True, type="pdf", key="sidebar_pdf")
        if st.button("Unir PDFs"):
            if pdfs:
                merger = PyPDF2.PdfMerger()
                for p in pdfs: merger.append(p)
                out = io.BytesIO(); merger.write(out)
                st.download_button("⬇️ Descargar PDF Unido", out.getvalue(), "Causa_Unida.pdf")
        
        st.markdown("---")
        st.header("⏳ Calculadora de Plazos")
        tipo_res = st.selectbox("Resolución", ["Amparo", "Apelación (5d)", "Apelación (10d)"])
        fecha_not = st.date_input("Fecha Notificación")
        if st.button("Calcular"):
            d_map = {"Amparo": 1, "Apelación (5d)": 5, "Apelación (10d)": 10}
            st.error(f"Vencimiento: {(fecha_not + timedelta(days=d_map[tipo_res])).strftime('%d-%m-%Y')}")

    tab1, tab2 = st.tabs(["📝 Generador de Escritos", "⚙️ Administración de Usuarios"])

    with tab1:
        st.header("1. Individualización")
        c1, c2, c3 = st.columns(3)
        def_nom = c1.text_input("Defensor/a", st.session_state.user_name)
        imp_nom = c2.text_input("Nombre Adolescente")
        juz_ej_sel = c3.selectbox("Juzgado Ejecución", ["Seleccionar..."] + TRIBUNALES_STGO_SM)
        juz_ej = juz_ej_sel if juz_ej_sel != "Seleccionar..." else ""

        st.subheader("Causas en conocimiento del Tribunal")
        for i, item in enumerate(st.session_state.ej_list):
            cols_ej = st.columns([4, 4, 1])
            item['rit'] = cols_ej[0].text_input(f"RIT {i+1}", item['rit'], key=f"ej_rit_{i}")
            item['ruc'] = cols_ej[1].text_input(f"RUC {i+1}", item['ruc'], key=f"ej_ruc_{i}")
            if item['ruc'] and not validar_ruc_chileno(item['ruc']):
                st.caption("⚠️ Formato RUC incorrecto (12345678-K)")
            if cols_ej[2].button("❌", key=f"del_ej_{i}"):
                st.session_state.ej_list.pop(i); st.rerun()
        
        if st.button("➕ Añadir Ruc y Rit"):
            st.session_state.ej_list.append({"rit":"", "ruc":""}); st.rerun()

        st.header("2. Causas RPA")
        for i, item in enumerate(st.session_state.rpa_list):
            cols = st.columns([2, 2, 3, 3, 0.5])
            item['rit'] = cols[0].text_input("RIT RPA", item['rit'], key=f"r_rit_{i}")
            item['ruc'] = cols[1].text_input("RUC RPA", item['ruc'], key=f"r_ruc_{i}")
            item['juzgado'] = cols[2].selectbox("Juzgado RPA", TRIBUNALES_STGO_SM, key=f"r_juz_{i}")
            item['sancion'] = cols[3].text_input("Sanción", item['sancion'], key=f"r_san_{i}")
            if cols[4].button("❌", key=f"del_rpa_{i}"): 
                st.session_state.rpa_list.pop(i); st.rerun()
        if st.button("➕ Agregar Causa RPA"): st.session_state.rpa_list.append({"rit":"", "ruc":"", "juzgado":"", "sancion":""}); st.rerun()

        st.header("3. Condenas Adulto")
        for i, item in enumerate(st.session_state.adulto_list):
            cols = st.columns([2, 2, 2, 2, 2, 0.5])
            item['rit'] = cols[0].text_input("RIT Ad", item['rit'], key=f"a_rit_{i}")
            item['ruc'] = cols[1].text_input("RUC Ad", item['ruc'], key=f"a_ruc_{i}")
            item['juzgado'] = cols[2].selectbox("Juzgado Ad", TRIBUNALES_STGO_SM, key=f"a_juz_{i}")
            item['pena'] = cols[3].text_input("Pena", item['pena'], key=f"a_pen_{i}")
            item['fecha'] = cols[4].text_input("Fecha", item['fecha'], key=f"a_fec_{i}")
            if cols[5].button("❌", key=f"del_ad_{i}"): 
                st.session_state.adulto_list.pop(i); st.rerun()
        if st.button("➕ Agregar Condena Adulto"): st.session_state.adulto_list.append({"rit":"", "ruc":"", "juzgado":"", "pena":"", "fecha":""}); st.rerun()

        # PUNTO 1: Documentación Otrosí (Modificado para ser profesional)
        st.markdown("---")
        st.header("📄 Documentación de Respaldo (Otrosí)")
        st.info("Adjunte las sentencias de adulto para generar un archivo consolidado.")
        sentencias_respaldo = st.file_uploader("Adjuntar Sentencias (PDF)", accept_multiple_files=True, type="pdf", key="respaldo")

        if st.button("🚀 GENERAR ESCRITO Y ADJUNTAR SENTENCIAS", use_container_width=True):
            if not imp_nom or not st.session_state.ej_list[0]['rit']:
                st.error("⚠️ Faltan datos críticos.")
            else:
                st.session_state.legal_coins += 25
                st.session_state.stats_count += 1
                datos = {
                    "defensor": def_nom, "adolescente": imp_nom, "juzgado_ejecucion": juz_ej, 
                    "causas_ej_principales": st.session_state.ej_list,
                    "causas_rpa": st.session_state.rpa_list, "causas_adulto": st.session_state.adulto_list
                }
                gen = GeneradorOficial(def_nom, imp_nom)
                word_buf = gen.generar_docx(datos)
                st.download_button("⬇️ Descargar Escrito (Word)", word_buf, f"Extincion_{imp_nom}.docx")
                
                if sentencias_respaldo:
                    merger_r = PyPDF2.PdfMerger()
                    for s in sentencias_respaldo: merger_r.append(s)
                    out_r = io.BytesIO(); merger_r.write(out_r)
                    st.download_button("⬇️ Descargar Sentencias Consolidadas (PDF)", out_r.getvalue(), f"Sentencias_{imp_nom}.pdf")
                st.balloons()

    with tab2:
        st.header("⚙️ Gestión de Usuarios")
        if st.session_state.is_admin:
            # PUNTO 2: Formulario para agregar colegas
            with st.form("nuevo_usuario"):
                st.write("Añadir nuevo colega/cliente")
                n_email = st.text_input("Email")
                n_nombre = st.text_input("Nombre Completo")
                n_pw = st.text_input("Contraseña")
                n_nivel = st.selectbox("Nivel", ["Usuario", "Admin"])
                if st.form_submit_button("Registrar"):
                    st.session_state.usuarios_db[n_email] = {"nombre": n_nombre, "pw": n_pw, "nivel": n_nivel}
                    st.success(f"Usuario {n_email} registrado.")
            
            st.markdown("---")
            st.write("Usuarios Actuales")
            df_users = pd.DataFrame.from_dict(st.session_state.usuarios_db, orient='index')
            st.table(df_users[['nombre', 'nivel']])
        else:
            st.warning("Solo administradores pueden gestionar accesos.")

    st.caption(f"Generador Judicial IBL | {datetime.now().year}")
