import streamlit as st
from docx import Document
from docx.shared import Pt, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
import io
import re
from datetime import datetime, timedelta
import PyPDF2

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
                if "legal_coins" not in st.session_state:
                    st.session_state["legal_coins"] = 0
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
        """Evita el error de redundancia 'Juzgado de Juzgado de...'"""
        if not nombre: return ""
        nombre_up = nombre.upper().strip()
        if nombre_up.startswith("JUZGADO DE"):
            return nombre_up
        return f"JUZGADO DE GARANTÍA DE {nombre_up}"

    def generar_docx(self, data):
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
            
            def_esc = re.escape(self.defensor.upper())
            ado_esc = re.escape(self.adolescente.upper())
            
            # Patron de negritas sin afectar palabras comunes como 'mérito'
            patron = f"(RIT|RUC|{def_esc}|{ado_esc}|JUZGADO DE [A-ZÁÉÍÓÚÑ\s]+|\d+-\d{{4}}|\d{{7,10}}-[\dkK])"
            partes = re.split(patron, texto_base, flags=re.IGNORECASE)
            
            for fragmento in partes:
                if not fragmento: continue
                run = p.add_run(fragmento)
                run.font.name = self.fuente
                run.font.size = Pt(self.tamano)
                
                # Aplicar negrita si es dato clave, excluyendo explícitamente la palabra mérito
                if bold_all or (re.match(patron, fragmento, re.IGNORECASE) and "mérito" not in fragmento.lower()):
                    run.bold = True
            return p

        # 1. SUMA
        suma = doc.add_paragraph()
        suma.alignment = WD_ALIGN_PARAGRAPH.LEFT
        r_suma = suma.add_run("EN LO PRINCIPAL: SOLICITA EXTINCIÓN;\nOTROSÍ: ACOMPAÑA DOCUMENTO.")
        r_suma.bold = True
        r_suma.font.name, r_suma.font.size = self.fuente, Pt(self.tamano)

        # 2. TRIBUNAL
        add_p(f"\n{self.limpiar_tribunal(data['juzgado_ejecucion'])}", bold_all=True, indent=False)
        
        # 3. COMPARECENCIA MULTICAUSAL
        causas_ej_str = ", ".join([f"RIT: {c['rit']} (RUC: {c['ruc']})" for c in data['causas_ej_principales'] if c['rit']])
        comp = (f"\n{self.defensor.upper()}, Abogada, Defensora Penal Pública, en representación de "
                f"{self.adolescente.upper()}, en causas de ejecución {causas_ej_str}, a S.S., respetuosamente digo:")
        add_p(comp, indent=True)

        # 4. CUERPO LEGAL
        add_p("\nQue, vengo en solicitar que declare la extinción de las sanciones de la Ley de "
                "Responsabilidad Penal Adolescente, o en subsidio se fije día y hora para celebrar "
                "audiencia para debatir sobre la extinción de la pena respecto de mi representado, en "
                "virtud del artículo 25 ter y 25 quinquies de la Ley 20.084.")

        add_p("Mi representado fue condenado en la siguiente causa de la Ley RPA:")
        for i, c in enumerate(data['causas_rpa'], 1):
            add_p(f"{i}. RIT: {c['rit']}, RUC: {c['ruc']}: Condenado por el {self.limpiar_tribunal(c['juzgado'])} a la pena de {c['sancion']}.")

        add_p("El fundamento para solicitar la discusión radica en una condena de mayor gravedad como adulto:")
        for i, c in enumerate(data['causas_adulto'], 1):
            idx = i + len(data['causas_rpa'])
            add_p(f"{idx}. RIT: {c['rit']}, RUC: {c['ruc']}: Condenado por el {self.limpiar_tribunal(c['juzgado'])}, "
                  f"con fecha {c['fecha']}, a la pena de {c['pena']}.")

        add_p("Se hace presente que el artículo 25 ter en su inciso tercero establece que se considerará más grave el delito o conjunto de ellos "
              "que tuviere asignada en la ley una mayor pena de conformidad con las reglas generales.")

        # 6. PETITORIA (Corrección palabra mérito)
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
    st.set_page_config(page_title="Generador de Escritos", layout="wide")
    
    if "rpa_list" not in st.session_state: st.session_state.rpa_list = []
    if "adulto_list" not in st.session_state: st.session_state.adulto_list = []
    if "ej_list" not in st.session_state: st.session_state.ej_list = [{"rit":"", "ruc":""}]

    # SIDEBAR
    with st.sidebar:
        # Reloj digital discreto
        st.markdown(f"🕒 **{datetime.now().strftime('%H:%M')}**")
        st.header("🎮 Perfil Judicial")
        st.write(f"LegalCoins: **{st.session_state.legal_coins}** 🪙")
        
        st.markdown("---")
        st.header("📂 Unir PDFs")
        pdfs_to_merge = st.file_uploader("Subir documentos", accept_multiple_files=True, type="pdf")
        if st.button("Unir Documentos"):
            if pdfs_to_merge:
                merger = PyPDF2.PdfMerger()
                for pdf in pdfs_to_merge:
                    merger.append(pdf)
                output = io.BytesIO()
                merger.write(output)
                st.download_button("⬇️ Descargar PDF Unido", output.getvalue(), "causa_completa.pdf")
        
        st.markdown("---")
        st.header("⏳ Calculadora de Plazos")
        tipo_res = st.selectbox("Tipo de Resolución", ["Amparo", "Apelación (5d)", "Apelación (10d)"])
        fecha_not = st.date_input("Fecha Notificación")
        if st.button("Calcular Vencimiento"):
            dias = {"Amparo": 1, "Apelación (5d)": 5, "Apelación (10d)": 10}
            venc = fecha_not + timedelta(days=dias[tipo_res])
            st.error(f"Vencimiento: {venc.strftime('%d-%m-%Y')}")

    st.title("⚖️ Generador de Escritos RPA")

    # 1. INDIVIDUALIZACIÓN
    st.header("1. Individualización")
    c1, c2, c3 = st.columns(3)
    def_nom = c1.text_input("Defensor/a", "IGNACIO BADILLA LARA")
    imp_nom = c2.text_input("Nombre Adolescente")
    
    juz_ej_select = c3.selectbox("Juzgado Ejecución", ["Seleccionar...", "Otro (Manual)"] + TRIBUNALES_STGO_SM)
    if juz_ej_select == "Otro (Manual)":
        juz_ej = c3.text_input("Escriba Juzgado")
    else:
        juz_ej = juz_ej_select

    # Punto 3: Multiples causas de ejecución (RIT/RUC)
    st.subheader("Causas en conocimiento del Tribunal")
    for i, item in enumerate(st.session_state.ej_list):
        cols_ej = st.columns([4, 4, 1])
        item['rit'] = cols_ej[0].text_input(f"RIT Ejecución {i+1}", item['rit'], key=f"ej_rit_{i}")
        item['ruc'] = cols_ej[1].text_input(f"RUC Ejecución {i+1}", item['ruc'], key=f"ej_ruc_{i}")
        if cols_ej[2].button("❌", key=f"del_ej_{i}"):
            st.session_state.ej_list.pop(i); st.rerun()
    if st.button("➕ Agregar RIT de Ejecución"):
        st.session_state.ej_list.append({"rit":"", "ruc":""}); st.rerun()

    # 2. CAUSAS RPA
    st.header("2. Causas RPA")
    for i, item in enumerate(st.session_state.rpa_list):
        cols = st.columns([2, 2, 3, 3, 0.5])
        item['rit'] = cols[0].text_input("RIT", item['rit'], key=f"r_rit_{i}")
        item['ruc'] = cols[1].text_input("RUC", item['ruc'], key=f"r_ruc_{i}")
        item['juzgado'] = cols[2].selectbox("Juzgado", TRIBUNALES_STGO_SM, key=f"r_juz_{i}")
        item['sancion'] = cols[3].text_input("Sanción", item['sancion'], key=f"r_san_{i}")
        if cols[4].button("❌", key=f"del_rpa_{i}"): 
            st.session_state.rpa_list.pop(i); st.rerun()
    if st.button("➕ Agregar Causa RPA"): st.session_state.rpa_list.append({"rit":"", "ruc":"", "juzgado":"", "sancion":""}); st.rerun()

    # 3. CONDENAS ADULTO
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

    # 4. GENERACIÓN
    if st.button("🚀 GENERAR ESCRITO WORD", use_container_width=True):
        if not imp_nom or not st.session_state.ej_list[0]['rit']:
            st.error("⚠️ Datos faltantes.")
        else:
            # Sumar LegalCoins
            st.session_state.legal_coins += 10
            datos = {
                "defensor": def_nom, 
                "adolescente": imp_nom, 
                "juzgado_ejecucion": juz_ej, 
                "causas_ej_principales": st.session_state.ej_list,
                "causas_rpa": st.session_state.rpa_list, 
                "causas_adulto": st.session_state.adulto_list
            }
            gen = GeneradorOficial(def_nom, imp_nom)
            st.download_button("⬇️ Descargar Word", gen.generar_docx(datos), f"Extincion_{imp_nom}.docx", use_container_width=True)
            st.balloons()
