import streamlit as st
from docx import Document
from docx.shared import Pt, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
import io
import re
from datetime import datetime, timedelta

# --- SEGURIDAD Y ACCESO ---
def check_password():
    if "password_correct" not in st.session_state:
        st.title("🔐 Acceso Sistema Judicial")
        c1, c2 = st.columns(2)
        email = c1.text_input("Correo electrónico")
        pw = c2.text_input("Contraseña", type="password")
        if st.button("Ingresar"):
            if email == "badilla285@gmail.com" and pw == "RPA2026":
                st.session_state["password_correct"] = True
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

    def generar_docx(self, data):
        """Genera el Word con formato Cambria 12, interlineado 1.5 y sangría en todos los párrafos."""
        doc = Document()
        for s in doc.sections:
            s.left_margin = Inches(1.2)
            s.right_margin = Inches(1.0)

        def add_p(texto_base, bold_all=False, indent=True):
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            p.paragraph_format.line_spacing_rule = WD_LINE_SPACING.ONE_POINT_FIVE
            if indent: 
                p.paragraph_format.first_line_indent = Inches(0.5)
            
            # Patrón para negritas: RIT, RUC, Juzgados, Nombre Defensor y Nombre Adolescente
            # Escapamos los nombres para el regex por si tienen caracteres especiales
            def_esc = re.escape(self.defensor.upper())
            ado_esc = re.escape(self.adolescente.upper())
            
            patron = f"(RIT|RUC|{def_esc}|{ado_esc}|JUZGADO DE GARANTÍA DE [A-ZÁÉÍÓÚÑ\s]+|\d+-\d{{4}}|\d{{7,10}}-[\dkK])"
            partes = re.split(patron, texto_base, flags=re.IGNORECASE)
            
            for fragmento in partes:
                if not fragmento: continue
                run = p.add_run(fragmento)
                run.font.name = self.fuente
                run.font.size = Pt(self.tamano)
                
                # Aplicar negrita si es un dato clave o se solicita para todo el párrafo
                if bold_all or re.match(patron, fragmento, re.IGNORECASE):
                    run.bold = True
            return p

        # 1. SUMA (Sin encabezado/logo previo)
        suma = doc.add_paragraph()
        suma.alignment = WD_ALIGN_PARAGRAPH.LEFT
        r_suma = suma.add_run("EN LO PRINCIPAL: SOLICITA EXTINCIÓN;\nOTROSÍ: ACOMPAÑA DOCUMENTO.")
        r_suma.bold = True
        r_suma.font.name, r_suma.font.size = self.fuente, Pt(self.tamano)

        # 2. TRIBUNAL
        add_p(f"\nJUZGADO DE GARANTÍA DE {data['juzgado_ejecucion'].upper()}", bold_all=True, indent=False)
        
        # 3. COMPARECENCIA (Ahora con sangría)
        comp = (f"\n{self.defensor.upper()}, Abogada, Defensora Penal Pública, en representación de "
                f"{self.adolescente.upper()}, en causa RIT: {data['rit_principal']}, "
                f"RUC: {data['ruc_principal']}, a S.S., respetuosamente digo:")
        add_p(comp, indent=True)

        # 4. CUERPO LEGAL (Con sangría)
        add_p("\nQue, vengo en solicitar que declare la extinción de las sanciones de la Ley de "
                "Responsabilidad Penal Adolescente, o en subsidio se fije día y hora para celebrar "
                "audiencia para debatir sobre la extinción de la pena respecto de mi representado, en "
                "virtud del artículo 25 ter y 25 quinquies de la Ley 20.084.")

        add_p("Mi representado fue condenado en la siguiente causa de la Ley RPA:")
        for i, c in enumerate(data['causas_rpa'], 1):
            add_p(f"{i}. RIT: {c['rit']}, RUC: {c['ruc']}: Condenado por el JUZGADO DE GARANTÍA DE "
                  f"{c['juzgado'].upper()} a la pena de {c['sancion']}.")

        add_p("El fundamento para solicitar la discusión radica en una condena de mayor gravedad como adulto:")
        for i, c in enumerate(data['causas_adulto'], 1):
            idx = i + len(data['causas_rpa'])
            add_p(f"{idx}. RIT: {c['rit']}, RUC: {c['ruc']}: Condenado por el JUZGADO DE GARANTÍA DE {c['juzgado'].upper()}, "
                  f"con fecha {c['fecha']}, a la pena de {c['pena']}.")

        # 5. FUNDAMENTO TÉCNICO
        add_p("Se hace presente que el artículo 25 ter en su inciso tercero establece que se considerará más grave el delito o conjunto de ellos "
              "que tuviere asignada en la ley una mayor pena de conformidad con las reglas generales.")

        # 6. PETITORIA
        add_p("\nPOR TANTO,", indent=False)
        add_p("En mérito de lo expuesto, SOLICITO A S.S. acceder a lo solicitado extinguiendo de pleno derecho la sanción antes referida.")

        # 7. OTROSÍ
        add_p("\nOTROSÍ: Acompaña sentencia de adulto.", bold_all=True, indent=False)
        add_p("POR TANTO, SOLICITO A S.S. se tenga por acompañada.", indent=False)

        buf = io.BytesIO()
        doc.save(buf)
        buf.seek(0)
        return buf

# --- INTERFAZ STREAMLIT ---
if check_password():
    st.set_page_config(page_title="Generador Judicial Nacho", layout="wide")
    
    if "rpa_list" not in st.session_state: st.session_state.rpa_list = []
    if "adulto_list" not in st.session_state: st.session_state.adulto_list = []

    # SIDEBAR: CALCULADORA
    with st.sidebar:
        st.header("⏳ Calculadora de Plazos")
        tipo_res = st.selectbox("Tipo de Resolución", 
                                ["Amparo", "Apelación (General)", "Apelación (Sent. Definitiva)", "Reposición"])
        fecha_not = st.date_input("Fecha Notificación")
        if st.button("Calcular"):
            dias = {"Amparo": 1, "Apelación (General)": 5, "Apelación (Sent. Definitiva)": 10, "Reposición": 3}
            venc = fecha_not + timedelta(days=dias[tipo_res])
            st.error(f"Vencimiento: {venc.strftime('%d-%m-%Y')}")
        st.markdown("---")
        st.button("🧹 Reiniciar Caso", on_click=lambda: st.session_state.update({"rpa_list":[], "adulto_list":[]}))

    st.title("⚖️ Generador de Escritos de Extinción")

    # 1. INDIVIDUALIZACIÓN
    st.header("1. Individualización")
    c1, c2, c3 = st.columns(3)
    def_nom = c1.text_input("Defensor/a", "IGNACIO BADILLA LARA")
    imp_nom = c2.text_input("Nombre Adolescente")
    juz_ej = c3.text_input("Juzgado Ejecución")
    
    c4, c5 = st.columns(2)
    rit_pr = c4.text_input("RIT Principal")
    ruc_pr = c5.text_input("RUC Principal")

    # 2. CAUSAS RPA
    st.header("2. Causas RPA")
    for i, item in enumerate(st.session_state.rpa_list):
        cols = st.columns([2, 2, 2, 3, 0.5])
        item['rit'] = cols[0].text_input("RIT", item['rit'], key=f"r_rit_{i}")
        item['ruc'] = cols[1].text_input("RUC", item['ruc'], key=f"r_ruc_{i}")
        item['juzgado'] = cols[2].text_input("Juzgado", item['juzgado'], key=f"r_juz_{i}")
        item['sancion'] = cols[3].text_input("Sanción", item['sancion'], key=f"r_san_{i}")
        if cols[4].button("❌", key=f"del_rpa_{i}"): 
            st.session_state.rpa_list.pop(i); st.rerun()
    if st.button("➕ Causa RPA"): st.session_state.rpa_list.append({"rit":"", "ruc":"", "juzgado":"", "sancion":""}); st.rerun()

    # 3. CONDENAS ADULTO
    st.header("3. Condenas Adulto")
    for i, item in enumerate(st.session_state.adulto_list):
        cols = st.columns([2, 2, 2, 2, 2, 0.5])
        item['rit'] = cols[0].text_input("RIT Ad", item['rit'], key=f"a_rit_{i}")
        item['ruc'] = cols[1].text_input("RUC Ad", item['ruc'], key=f"a_ruc_{i}")
        item['juzgado'] = cols[2].text_input("Juzgado", item['juzgado'], key=f"a_juz_{i}")
        item['pena'] = cols[3].text_input("Pena", item['pena'], key=f"a_pen_{i}")
        item['fecha'] = cols[4].text_input("Fecha", item['fecha'], key=f"a_fec_{i}")
        if cols[5].button("❌", key=f"del_ad_{i}"): 
            st.session_state.adulto_list.pop(i); st.rerun()
    if st.button("➕ Condena Adulto"): st.session_state.adulto_list.append({"rit":"", "ruc":"", "juzgado":"", "pena":"", "fecha":""}); st.rerun()

    # 4. GENERACIÓN
    if st.button("🚀 GENERAR ESCRITO WORD", use_container_width=True):
        if not imp_nom or not rit_pr:
            st.error("⚠️ Faltan datos obligatorios (Adolescente y RIT principal).")
        else:
            datos = {
                "defensor": def_nom, 
                "adolescente": imp_nom, 
                "juzgado_ejecucion": juz_ej, 
                "rit_principal": rit_pr, 
                "ruc_principal": ruc_pr, 
                "causas_rpa": st.session_state.rpa_list, 
                "causas_adulto": st.session_state.adulto_list
            }
            gen = GeneradorOficial(def_nom, imp_nom)
            st.download_button("⬇️ Descargar", gen.generar_docx(datos), f"Extincion_{imp_nom}.docx", use_container_width=True)
