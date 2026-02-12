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

# --- GESTIÓN DE ESTADO Y USUARIOS ---
if "usuarios_db" not in st.session_state:
    st.session_state.usuarios_db = {
        "badilla285@gmail.com": {"nombre": "IGNACIO BADILLA LARA", "pw": "RPA2026", "nivel": "Admin"},
        "colega1@pjud.cl": {"nombre": "DEFENSOR ASOCIADO 1", "pw": "LEGAL2026", "nivel": "Usuario"},
    }

if "form_data" not in st.session_state:
    st.session_state.form_data = {
        "imp_nom": "",
        "juz_ej_sel": "Seleccionar...",
        "rpa_list": [],
        "adulto_list": [],
        "ej_list": [{"rit":"", "ruc":""}]
    }

# --- FUNCIONES DE APOYO ---
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
        if "JUZGADO DE" in nombre_up: return nombre_up
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

        # --- CONSTRUCCIÓN DEL ESCRITO ---
        suma = doc.add_paragraph()
        r_suma = suma.add_run("EN LO PRINCIPAL: SOLICITA EXTINCIÓN;\nOTROSÍ: ACOMPAÑA DOCUMENTO.")
        r_suma.bold = True
        r_suma.font.name, r_suma.font.size = self.fuente, Pt(self.tamano)
        
        add_p(f"\n{self.limpiar_tribunal(data['juzgado_ejecucion'])}", bold_all=True, indent=False)
        
        causas_ej_str = ", ".join([f"RIT: {c['rit']} (RUC: {c['ruc']})" for c in data['causas_ej_principales'] if c['rit']])
        comp = (f"\n{self.defensor.upper()}, Abogada, Defensora Penal Pública, en representación de "
                f"{self.adolescente.upper()}, en causas de ejecución {causas_ej_str}, a S.S., respetuosamente digo:")
        add_p(comp, indent=True)
        
        add_p("\nQue, vengo en solicitar que se declare la extinción de las sanciones de la Ley de Responsabilidad Penal Adolescente, o en subsidio se fije día y hora para celebrar audiencia para debatir sobre la extinción de la pena respecto de mi representado, en virtud de lo dispuesto en los artículos 25 ter y 25 quinquies de la Ley 20.084.")
        
        add_p("\nMi representado fue condenado en las siguientes causas de la Ley RPA:", indent=False)
        for i, c in enumerate(data['causas_rpa'], 1):
            add_p(f"{i}. RIT: {c['rit']}, RUC: {c['ruc']}: Condenado por el {self.limpiar_tribunal(c['juzgado'])} a la pena de {c['sancion']}.")
        
        add_p("\nEl fundamento para solicitar la discusión respecto de la extinción de responsabilidad penal radica en la existencia de una condena de mayor gravedad como adulto, la cual paso a detallar:", indent=False)
        for i, c in enumerate(data['causas_adulto'], 1):
            idx = i + len(data['causas_rpa'])
            add_p(f"{idx}. RIT: {c['rit']}, RUC: {c['ruc']}: Condenado por el {self.limpiar_tribunal(c['juzgado'])}, con fecha {c['fecha']}, a la pena de {c['pena']}.")
        
        add_p("\nAl respecto, cabe señalar que el artículo 25 ter en su inciso tercero establece que se considerará más grave el delito o conjunto de ellos que tuviere asignada en la ley una mayor pena de conformidad con las reglas generales.")
        add_p("En el presente caso, la sanción impuesta como adulto reviste una mayor gravedad, tanto por la naturaleza del ilícito como por la cuantía de la pena impuesta, configurándose así los presupuestos legales para la extinción de la responsabilidad penal en la presente causa.")

        add_p("\nPOR TANTO,", indent=False)
        add_p("En mérito de lo expuesto, SOLICITO A S.S. acceder a lo solicitado extinguiendo de pleno derecho la sanción antes referida, o en subsidio se fije día y hora para celebrar audiencia para que se abra debate sobre la extinción de responsabilidad penal en la presente causa.")
        
        rits_adulto = ", ".join([f"RIT: {c['rit']} (RUC: {c['ruc']})" for c in data['causas_adulto'] if c['rit']])
        add_p(f"\nOTROSÍ: Acompaña sentencia de adulto de mi representado de las causas {rits_adulto}.", bold_all=True, indent=False)
        add_p("POR TANTO, SOLICITO A S.S. se tengan por acompañadas.", indent=False)
        
        buf = io.BytesIO(); doc.save(buf); buf.seek(0)
        return buf

# --- INTERFAZ STREAMLIT ---
if check_password():
    st.set_page_config(page_title="Generador Judicial IBL", layout="wide")

    with st.sidebar:
        st.header("👤 Perfil")
        st.write(f"Defensor: **{st.session_state.user_name}**")
        st.write(f"LegalCoins: **{st.session_state.legal_coins}** 🪙")
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
        st.session_state.form_data["imp_nom"] = c2.text_input("Nombre Adolescente", value=st.session_state.form_data["imp_nom"])
        st.session_state.form_data["juz_ej_sel"] = c3.selectbox("Juzgado Ejecución", ["Seleccionar..."] + TRIBUNALES_STGO_SM, index=(["Seleccionar..."] + TRIBUNALES_STGO_SM).index(st.session_state.form_data["juz_ej_sel"]))
        
        imp_nom = st.session_state.form_data["imp_nom"]
        juz_ej = st.session_state.form_data["juz_ej_sel"] if st.session_state.form_data["juz_ej_sel"] != "Seleccionar..." else ""

        st.subheader("Causas en conocimiento del Tribunal")
        for i, item in enumerate(st.session_state.form_data["ej_list"]):
            cols_ej = st.columns([4, 4, 1])
            item['rit'] = cols_ej[0].text_input(f"RIT {i+1}", item['rit'], key=f"ej_rit_{i}")
            item['ruc'] = cols_ej[1].text_input(f"RUC {i+1}", item['ruc'], key=f"ej_ruc_{i}")
            if cols_ej[2].button("❌", key=f"del_ej_{i}"):
                st.session_state.form_data["ej_list"].pop(i); st.rerun()
        if st.button("➕ Añadir Ruc y Rit"):
            st.session_state.form_data["ej_list"].append({"rit":"", "ruc":""}); st.rerun()

        st.header("2. Causas RPA")
        for i, item in enumerate(st.session_state.form_data["rpa_list"]):
            cols = st.columns([2, 2, 3, 3, 0.5])
            item['rit'] = cols[0].text_input("RIT RPA", item['rit'], key=f"r_rit_{i}")
            item['ruc'] = cols[1].text_input("RUC RPA", item['ruc'], key=f"r_ruc_{i}")
            default_idx = TRIBUNALES_STGO_SM.index(item['juzgado']) if item['juzgado'] in TRIBUNALES_STGO_SM else 0
            item['juzgado'] = cols[2].selectbox("Juzgado RPA", TRIBUNALES_STGO_SM, index=default_idx, key=f"r_juz_{i}")
            item['sancion'] = cols[3].text_input("Sanción", item['sancion'], key=f"r_san_{i}")
            if cols[4].button("❌", key=f"del_rpa_{i}"): 
                st.session_state.form_data["rpa_list"].pop(i); st.rerun()
        if st.button("➕ Agregar Causa RPA"): st.session_state.form_data["rpa_list"].append({"rit":"", "ruc":"", "juzgado":TRIBUNALES_STGO_SM[0], "sancion":""}); st.rerun()

        st.header("3. Condenas Adulto")
        for i, item in enumerate(st.session_state.form_data["adulto_list"]):
            cols = st.columns([2, 2, 2, 2, 2, 0.5])
            item['rit'] = cols[0].text_input("RIT Ad", item['rit'], key=f"a_rit_{i}")
            item['ruc'] = cols[1].text_input("RUC Ad", item['ruc'], key=f"a_ruc_{i}")
            default_idx_ad = TRIBUNALES_STGO_SM.index(item['juzgado']) if item['juzgado'] in TRIBUNALES_STGO_SM else 0
            item['juzgado'] = cols[2].selectbox("Juzgado Ad", TRIBUNALES_STGO_SM, index=default_idx_ad, key=f"a_juz_{i}")
            item['pena'] = cols[3].text_input("Pena", item['pena'], key=f"a_pen_{i}")
            item['fecha'] = cols[4].text_input("Fecha", item['fecha'], key=f"a_fec_{i}")
            if cols[5].button("❌", key=f"del_ad_{i}"): 
                st.session_state.form_data["adulto_list"].pop(i); st.rerun()
        if st.button("➕ Agregar Condena Adulto"): st.session_state.form_data["adulto_list"].append({"rit":"", "ruc":"", "juzgado":TRIBUNALES_STGO_SM[0], "pena":"", "fecha":""}); st.rerun()

        st.markdown("---")
        if st.button("🚀 GENERAR ESCRITO ROBUSTO", use_container_width=True):
            if not imp_nom or not st.session_state.form_data["ej_list"][0]['rit']:
                st.error("⚠️ Faltan datos críticos.")
            else:
                st.session_state.legal_coins += 25
                datos = {
                    "defensor": def_nom, "adolescente": imp_nom, "juzgado_ejecucion": juz_ej, 
                    "causas_ej_principales": st.session_state.form_data["ej_list"],
                    "causas_rpa": st.session_state.form_data["rpa_list"], "causas_adulto": st.session_state.form_data["adulto_list"]
                }
                gen = GeneradorOficial(def_nom, imp_nom)
                word_buf = gen.generar_docx(datos)
                st.download_button("⬇️ Descargar Escrito Final (Word)", word_buf, f"Extincion_{imp_nom}.docx")
                st.balloons()

    with tab2:
        st.header("⚙️ Gestión de Usuarios")
        if st.session_state.is_admin:
            for email, info in list(st.session_state.usuarios_db.items()):
                b_col1, b_col2, b_col3, b_col4 = st.columns([3, 3, 2, 1])
                b_col1.write(email); b_col2.write(info['nombre']); b_col3.write(info['nivel'])
                if email != st.session_state.auth_user:
                    if b_col4.button("🗑️", key=f"del_user_{email}"):
                        del st.session_state.usuarios_db[email]; st.rerun()
                else: b_col4.markdown("🔒")
        else: st.warning("Solo administradores pueden gestionar accesos.")

    st.markdown("---")
    st.markdown("<div style='text-align: center; color: gray;'>Aplicación creada por <b>IGNACIO ANTONIO BADILLA LARA</b></div>", unsafe_allow_html=True)
    st.caption(f"Generador Judicial IBL | {datetime.now().year}")
