import streamlit as st
from docx import Document
from docx.shared import Pt, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
import io
import re
from datetime import datetime, timedelta
import PyPDF2
from supabase import create_client, Client

# --- CONFIGURACIÓN DE BASE DE DATOS ---
# Usamos tus credenciales confirmadas para evitar el error 401
SUPABASE_URL = "https://zblcddxbhyomkasmbvyz.supabase.co"
SUPABASE_KEY = "sb_publishable_pHMqXxI39AssehHdBs1wqA_NVjPc-FT" 

try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as e:
    st.error(f"Error en la conexión con Supabase: {e}")

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

# --- GESTIÓN DE ESTADO ---
if "usuarios_db" not in st.session_state:
    st.session_state.usuarios_db = {
        "badilla285@gmail.com": {"nombre": "IGNACIO BADILLA LARA", "pw": "RPA2026", "nivel": "Admin"},
    }

if "form_data" not in st.session_state:
    st.session_state.form_data = {
        "imp_nom": "",
        "juz_ej_sel": "Seleccionar...",
        "rpa_list": [],
        "adulto_list": [],
        "ej_list": [{"rit":"", "ruc":""}]
    }

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
            patron = f"(RIT:?\s?\d+-\d{{4}}|RUC:?\s?\d{{7,10}}-[\dkK]|{def_esc}|{ado_esc}|POR TANTO|OTROSÍ|JUZGADO DE [A-ZÁÉÍÓÚÑ\s]+)"
            
            partes = re.split(patron, texto_base, flags=re.IGNORECASE)
            for fragmento in partes:
                if not fragmento: continue
                run = p.add_run(fragmento)
                run.font.name, run.font.size = self.fuente, Pt(self.tamano)
                if bold_all or re.match(patron, fragmento, re.IGNORECASE):
                    run.bold = True
            return p

        # --- SUMA ---
        suma = doc.add_paragraph()
        suma.alignment = WD_ALIGN_PARAGRAPH.LEFT
        r_suma = suma.add_run("EN LO PRINCIPAL: SOLICITA EXTINCIÓN;\nOTROSÍ: ACOMPAÑA SENTENCIA")
        r_suma.bold = True
        r_suma.font.name, r_suma.font.size = self.fuente, Pt(self.tamano)
        
        # --- TRIBUNAL ---
        add_p(f"\n{self.limpiar_tribunal(data['juzgado_ejecucion'])}", bold_all=True, indent=False)
        
        # --- COMPARECENCIA ---
        causas_ej_str = ", ".join([f"RIT: {c['rit']} RUC: {c['ruc']}" for c in data['causas_ej_principales'] if c['rit']])
        comp = (f"\n{self.defensor.upper()}, Abogada, Defensora Penal Pública, en representación de "
                f"{self.adolescente.upper()}, en causas de ejecución {causas_ej_str}, a S.S., respetuosamente digo:")
        add_p(comp, indent=True)
        
        # --- CUERPO ---
        add_p("Que, vengo en solicitar que se declare la extinción de las sanciones de la Ley de Responsabilidad Penal Adolescente, o en subsidio se fije día y hora para celebrar audiencia para debatir sobre la extinción de la pena respecto de mi representado, en virtud de lo dispuesto en los artículos 25 ter y 25 quinquies de la Ley 20.084.")
        
        add_p("Mi representado fue condenado en las siguientes causas de la Ley RPA:", indent=False)
        for i, c in enumerate(data['causas_rpa'], 1):
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            p.paragraph_format.line_spacing_rule = WD_LINE_SPACING.ONE_POINT_FIVE
            p.paragraph_format.first_line_indent = Inches(0.5)
            p.add_run(f"{i}. ").font.name = self.fuente
            p.add_run(f"RIT: {c['rit']}").bold = True
            p.add_run(", ").font.name = self.fuente
            p.add_run(f"RUC: {c['ruc']}").bold = True
            p.add_run(f": Condenado por el {self.limpiar_tribunal(c['juzgado'])} a la pena de ").font.name = self.fuente
            p.add_run(f"{c['sancion']}").bold = True
            for run in p.runs: run.font.size = Pt(self.tamano); run.font.name = self.fuente

        add_p("El fundamento para solicitar la discusión respecto de la extinción de responsabilidad penal radica en la existencia de una condena de mayor gravedad como adulto, la cual paso a detallar:")
        for i, c in enumerate(data['causas_adulto'], 1):
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            p.paragraph_format.line_spacing_rule = WD_LINE_SPACING.ONE_POINT_FIVE
            p.paragraph_format.first_line_indent = Inches(0.5)
            p.add_run(f"{i + len(data['causas_rpa'])}. ").font.name = self.fuente
            p.add_run(f"RIT: {c['rit']}").bold = True
            p.add_run(", ").font.name = self.fuente
            p.add_run(f"RUC: {c['ruc']}").bold = True
            p.add_run(f": Condenado por el {self.limpiar_tribunal(c['juzgado'])}, con fecha {c['fecha']}, a la pena de ").font.name = self.fuente
            p.add_run(f"{c['pena']}").bold = True
            for run in p.runs: run.font.size = Pt(self.tamano); run.font.name = self.fuente

        add_p("Se hace presente que el artículo 25 ter en su inciso tercero establece que de este artículo y del siguiente se considerará más grave el delito o conjunto de ellos que tuviere asignada en la ley una mayor pena de conformidad con las reglas generales. No obstante, el tribunal también podrá calificar su mayor gravedad teniendo en cuenta la naturaleza y extensión o cuantía de la sanción comparativa que fuere aplicable en concreto en uno y otro caso.")

        add_p("POR TANTO,", bold_all=True, indent=False)
        add_p("En mérito de lo expuesto, SOLICITO A S.S. acceder a lo solicitado extinguiendo de pleno derecho la sanción antes referida, o en subsidio se fije día y hora para celebrar audiencia para que se abra debate sobre la extinción de responsabilidad penal en la presente causa.")
        
        # --- OTROSÍ ---
        rits_ad = ", ".join([f"RIT: {c['rit']} RUC: {c['ruc']}" for c in data['causas_adulto'] if c['rit']])
        add_p(f"OTROSÍ: Acompaña sentencia de adulto de mi representado de las causas {rits_ad}", bold_all=True, indent=False)
        
        cant = "la" if len(data['causas_adulto']) <= 1 else "las"
        plural = "" if len(data['causas_adulto']) <= 1 else "s"
        add_p(f"POR TANTO, SOLICITO A S.S. se tengan por acompañada {cant} sentencia{plural} de adulto.", bold_all=True, indent=False)
        
        buf = io.BytesIO(); doc.save(buf); buf.seek(0)
        return buf

# --- INTERFAZ STREAMLIT ---
# Nota: st.set_page_config se maneja dentro de check_password o al inicio absoluto
if check_password():
    with st.sidebar:
        st.header("👤 Perfil Profesional")
        st.write(f"Defensor: **{st.session_state.user_name}**")
        st.write(f"LegalCoins: **{st.session_state.legal_coins}** 🪙")
        st.divider()
        st.info("Sistema de Generación Documental de Alta Fidelidad")

    tab1, tab2 = st.tabs(["📝 Generador de Escritos", "⚙️ Administración"])

    with tab1:
        st.header("1. Individualización")
        c1, c2, c3 = st.columns(3)
        def_nom = c1.text_input("Defensor/a", st.session_state.user_name)
        st.session_state.form_data["imp_nom"] = c2.text_input("Nombre Adolescente", value=st.session_state.form_data["imp_nom"])
        st.session_state.form_data["juz_ej_sel"] = c3.selectbox("Juzgado Ejecución", ["Seleccionar..."] + TRIBUNALES_STGO_SM, index=(["Seleccionar..."] + TRIBUNALES_STGO_SM).index(st.session_state.form_data["juz_ej_sel"]))
        
        imp_nom = st.session_state.form_data["imp_nom"]
        juz_ej = st.session_state.form_data["juz_ej_sel"] if st.session_state.form_data["juz_ej_sel"] != "Seleccionar..." else ""

        st.subheader("Causas en ejecución (Tribunal actual)")
        for i, item in enumerate(st.session_state.form_data["ej_list"]):
            cols_ej = st.columns([4, 4, 1])
            item['rit'] = cols_ej[0].text_input(f"RIT Ejecución {i+1}", item['rit'], key=f"ej_rit_{i}")
            item['ruc'] = cols_ej[1].text_input(f"RUC Ejecución {i+1}", item['ruc'], key=f"ej_ruc_{i}")
            if cols_ej[2].button("❌", key=f"del_ej_{i}"):
                st.session_state.form_data["ej_list"].pop(i); st.rerun()
        if st.button("➕ Añadir Causa Ejecución"): st.session_state.form_data["ej_list"].append({"rit":"", "ruc":""}); st.rerun()

        st.header("2. Causas RPA (A extinguir)")
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

        st.header("3. Condenas Adulto (Fundamento)")
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
        if st.button("⚖️ GENERAR ESCRITO JURÍDICO", use_container_width=True):
            if not imp_nom or not st.session_state.form_data["ej_list"][0]['rit']:
                st.error("⚠️ Faltan datos críticos para la individualización.")
            else:
                st.session_state.legal_coins += 25
                datos = {
                    "defensor": def_nom, "adolescente": imp_nom, "juzgado_ejecucion": juz_ej, 
                    "causas_ej_principales": st.session_state.form_data["ej_list"],
                    "causas_rpa": st.session_state.form_data["rpa_list"], "causas_adulto": st.session_state.form_data["adulto_list"]
                }
                
                # --- GUARDADO EN NUBE (SUPABASE) ---
                try:
                    registro_nube = {
                        "RUC": st.session_state.form_data["ej_list"][0]['ruc'],
                        "RIT": st.session_state.form_data["ej_list"][0]['rit'],
                        "TRIBUNAL / J": juz_ej,
                        "Tipo_Recurso": "Extinción Art. 25 ter",
                        "Contenido_es": f"Escrito para {imp_nom}. Incluye {len(st.session_state.form_data['rpa_list'])} causas RPA."
                    }
                    supabase.table("Gestiones").insert(registro_nube).execute()
                    st.toast('Gestión sincronizada con GESTIONES IABL.', icon='☁️')
                except Exception as db_err:
                    st.warning(f"Error de sincronización con la nube: {db_err}")

                # Generación del archivo físico Word
                gen = GeneradorOficial(def_nom, imp_nom)
                word_buf = gen.generar_docx(datos)
                st.download_button("📂 Descargar Escrito Formateado (Word)", word_buf, f"Extincion_{imp_nom}.docx")
                st.success("El escrito ha sido procesado siguiendo los estándares de la Defensoría Penal Pública.")

    with tab2:
        st.header("⚙️ Gestión de Usuarios")
        if st.session_state.is_admin:
            for email, info in list(st.session_state.usuarios_db.items()):
                b_col1, b_col2, b_col3, b_col4 = st.columns([3, 3, 2, 1])
                b_col1.write(email)
                b_col2.write(info['nombre'])
                b_col3.write(info['nivel'])
                if email != st.session_state.auth_user:
                    if b_col4.button("🗑️", key=f"del_user_{email}"):
                        del st.session_state.usuarios_db[email]; st.rerun()
            
            st.divider()
            st.subheader("Añadir Nuevo Usuario")
            with st.form("new_user_form"):
                new_email = st.text_input("Email")
                new_name = st.text_input("Nombre Completo")
                new_pw = st.text_input("Contraseña Temporal")
                new_level = st.selectbox("Nivel", ["User", "Admin"])
                if st.form_submit_button("Registrar Usuario"):
                    if new_email and new_name and new_pw:
                        st.session_state.usuarios_db[new_email] = {"nombre": new_name, "pw": new_pw, "nivel": new_level}
                        st.success(f"Usuario {new_name} registrado.")
                        st.rerun()
        else:
            st.warning("Acceso restringido a administradores.")

    st.markdown("---")
    st.markdown("<div style='text-align: center; color: gray;'>Aplicación profesional creada por <b>IGNACIO ANTONIO BADILLA LARA</b></div>", unsafe_allow_html=True)
