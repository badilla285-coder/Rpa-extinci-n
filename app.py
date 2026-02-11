import streamlit as st
import fitz  # PyMuPDF
from docx import Document
from docx.shared import Pt, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
import io
import re

# --- SEGURIDAD Y ACCESO ---
def check_password():
    if "password_correct" not in st.session_state:
        st.title("🔐 Acceso Sistema Judicial")
        c1, c2 = st.columns(2)
        email = c1.text_input("Correo electrónico")
        pw = c2.text_input("Contraseña", type="password")
        if st.button("Ingresar"):
            if email == "badilla285@gmail.com" and pw == "nacho2026":
                st.session_state["password_correct"] = True
                st.rerun()
            else:
                st.error("Credenciales incorrectas")
        return False
    return True

class MotorJudicialPro:
    def __init__(self):
        self.fuente = "Cambria"
        self.tamano = 12

    def analizar_documento(self, file):
        """Analiza semánticamente el documento y detecta si es una imagen/escaneo."""
        file.seek(0)
        texto_paginas = []
        es_imagen = False
        
        with fitz.open(stream=file.read(), filetype="pdf") as doc:
            for pagina in doc:
                t = pagina.get_text("text")
                if not t.strip():
                    es_imagen = True
                texto_paginas.append(t)
        
        texto_full = " ".join(texto_paginas)
        if es_imagen and len(texto_full.strip()) < 30:
            return {"error": "El documento parece ser un escaneo/imagen sin capa de texto. Ingresa los datos manualmente."}

        # Limpieza para análisis contextual
        cuerpo = " ".join(texto_full.split())

        # Razonamiento de RIT y RUC (Busca patrones numéricos en contexto judicial)
        rit = re.search(r"(?:RIT|Rit)[:\s-]*(\d+[\s-](?:201|202)\d)", cuerpo)
        ruc = re.search(r"(?:RUC|Ruc)[:\s-]*(\d{8,10}[-][\dkK])", cuerpo)
        
        # Razonamiento de Tribunal (Busca la ubicación tras la palabra 'Garantía')
        tribunal = re.search(r"(?:Garantía|Letras|TOP)\s+(?:de\s+)?([A-ZÁÉÍÓÚÑa-z]+)", cuerpo)
        
        # Razonamiento de Imputado (Busca nombres tras palabras clave de representación)
        imputado = re.search(r"(?:representación de|contra|condenado|sentenciado)\s+([A-ZÁÉÍÓÚÑ\s]{10,60})", texto_full)

        return {
            "rit": rit.group(1).replace(" ", "-") if rit else "",
            "ruc": ruc.group(1) if ruc else "",
            "juzgado": tribunal.group(1).upper() if tribunal else "",
            "imputado": imputado.group(1).strip().upper() if imputado else "",
            "texto": texto_full
        }

    def generar_escrito(self, data):
        """Genera el Word con formato Cambria 12, interlineado 1.5 y sangría."""
        doc = Document()
        for s in doc.sections:
            s.left_margin, s.right_margin = Inches(1.2), Inches(1.0)

        def add_p(texto, bold=False, indent=True, space_after=True):
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            p.paragraph_format.line_spacing_rule = WD_LINE_SPACING.ONE_POINT_FIVE
            if indent: p.paragraph_format.first_line_indent = Inches(0.5)
            run = p.add_run(texto)
            run.font.name, run.font.size, run.bold = self.fuente, Pt(self.tamano), bold
            return p

        # 1. SUMA (Izquierda)
        suma = doc.add_paragraph()
        suma.alignment = WD_ALIGN_PARAGRAPH.LEFT
        r = suma.add_run("EN LO PRINCIPAL: SOLICITA EXTINCIÓN;\nOTROSÍ: ACOMPAÑA DOCUMENTO.")
        r.bold, r.font.name, r.font.size = True, self.fuente, Pt(self.tamano)

        # 2. TRIBUNAL Y COMPARECENCIA
        add_p(f"\nJUZGADO DE GARANTÍA DE {data['juzgado_ejecucion'].upper()}", bold=True, indent=False)
        
        comp = (f"\n{data['defensor'].upper()}, Abogada, Defensora Penal Pública, en representación de "
                f"{data['adolescente'].upper()}, en causa RIT: {data['rit_principal']}, "
                f"RUC: {data['ruc_principal']}, a S.S., respetuosamente digo:")
        add_p(comp, indent=False)

        # 3. CUERPO LEGAL (Art. 25 ter y quinquies)
        add_p("\nQue, vengo en solicitar que declare la extinción de las sanciones de la Ley de "
                "Responsabilidad Penal Adolescente, o en subsidio se fije día y hora para celebrar "
                "audiencia para debatir sobre la extinción de la pena respecto de mi representado, en "
                "virtud del artículo 25 ter y 25 quinquies de la Ley 20.084.")

        add_p("Mi representado fue condenado en la siguiente causa de la Ley RPA:")
        for i, c in enumerate(data['causas_rpa'], 1):
            add_p(f"{i}. RIT: {c['rit']}, RUC: {c['ruc']}: Condenado por el Juzgado de Garantía de "
                  f"{c['juzgado']} a la pena de {c['sancion']}. Cabe señalar que dicha pena no se encuentra cumplida.")

        add_p("El fundamento para solicitar la discusión radica en una condena de mayor gravedad como adulto:")
        for i, c in enumerate(data['causas_adulto'], 1):
            idx = i + len(data['causas_rpa'])
            add_p(f"{idx}. RIT: {c['rit']}, RUC: {c['ruc']}: Condenado por el {c['juzgado']}, "
                  f"con fecha {c['fecha']}, a la pena de {c['pena']}. Esta sanción reviste mayor gravedad, configurándose los presupuestos legales.")

        # 4. CIERRE
        add_p("Se hace presente que el artículo 25 ter en su inciso tercero establece que se considerará más grave el delito o conjunto de ellos "
              "que tuviere asignada en la ley una mayor pena de conformidad con las reglas generales.")

        add_p("\nPOR TANTO,", indent=False)
        add_p("En mérito de lo expuesto, SOLICITO A S.S. acceder a lo solicitado extinguiendo de pleno derecho la sanción antes referida.")

        add_p("\nOTROSÍ: Acompaña sentencia de adulto.", bold=True, indent=False)
        add_p("POR TANTO, SOLICITO A S.S. se tenga por acompañada.", indent=False)

        buf = io.BytesIO(); doc.save(buf); buf.seek(0)
        return buf

# --- INTERFAZ STREAMLIT ---
if check_password():
    st.set_page_config(page_title="Generador Judicial Pro", layout="wide")
    
    # Manejo de Memoria de Sesión
    if "rpa_list" not in st.session_state: st.session_state.rpa_list = []
    if "adulto_list" not in st.session_state: st.session_state.adulto_list = []
    if "historial" not in st.session_state: st.session_state.historial = []
    if "auto_imp" not in st.session_state: st.session_state.auto_imp = ""

    st.title("⚖️ Analizador y Generador Jurídico RPA")
    st.sidebar.header("Opciones")
    if st.sidebar.button("🧹 Limpiar Todo"):
        st.session_state.rpa_list = []; st.session_state.adulto_list = []; st.session_state.auto_imp = ""; st.rerun()

    # 1. INDIVIDUALIZACIÓN
    st.header("1. Datos Generales")
    c1, c2, c3 = st.columns(3)
    def_nom = c1.text_input("Defensor/a", "IGNACIO BADILLA LARA")
    imp_nom = c2.text_input("Nombre Adolescente", value=st.session_state.auto_imp)
    juz_ej = c3.text_input("Juzgado Ejecución (Ej: SAN BERNARDO)")
    
    c4, c5 = st.columns(2)
    rit_pr = c4.text_input("RIT Ejecución")
    ruc_pr = c5.text_input("RUC Ejecución")

    # 2. MÓDULO RPA
    st.header("2. Causas RPA")
    up_rpa = st.file_uploader("Subir PDFs RPA (Análisis Contextual)", type="pdf", accept_multiple_files=True)
    if up_rpa:
        for f in up_rpa:
            if f.name not in [x.get('fn') for x in st.session_state.rpa_list]:
                res = MotorJudicialPro().analizar_documento(f)
                if "error" in res: st.warning(f"⚠️ {f.name}: {res['error']}")
                else:
                    st.session_state.rpa_list.append({"rit": res['rit'], "ruc": res['ruc'], "juzgado": res['juzgado'], "sancion": "", "fn": f.name})
                    if not st.session_state.auto_imp: st.session_state.auto_imp = res['imputado']

    for i, item in enumerate(st.session_state.rpa_list):
        cols = st.columns([2, 2, 2, 3, 0.5])
        item['rit'] = cols[0].text_input("RIT", item['rit'], key=f"rpa_rit_{i}")
        item['juzgado'] = cols[2].text_input("Juzgado", item['juzgado'], key=f"rpa_juz_{i}")
        item['sancion'] = cols[3].text_input("Sanción", item['sancion'], key=f"rpa_san_{i}")
        if cols[4].button("❌", key=f"del_rpa_{i}"): st.session_state.rpa_list.pop(i); st.rerun()

    # 3. MÓDULO ADULTO
    st.header("3. Condenas Adulto")
    up_ad = st.file_uploader("Subir PDFs Adulto (Análisis Contextual)", type="pdf", accept_multiple_files=True)
    if up_ad:
        for f in up_ad:
            if f.name not in [x.get('fn') for x in st.session_state.adulto_list]:
                res = MotorJudicialPro().analizar_documento(f)
                if "error" in res: st.warning(f"⚠️ {f.name}: {res['error']}")
                else: st.session_state.adulto_list.append({"rit": res['rit'], "ruc": res['ruc'], "juzgado": res['juzgado'], "pena": "", "fecha": "", "fn": f.name, "bytes": f.getvalue()})

    for i, item in enumerate(st.session_state.adulto_list):
        cols = st.columns([2, 2, 2, 2, 2, 0.5])
        item['rit'] = cols[0].text_input("RIT Adulto", item['rit'], key=f"ad_rit_{i}")
        item['juzgado'] = cols[2].text_input("Juzgado", item['juzgado'], key=f"ad_juz_{i}")
        item['pena'] = cols[3].text_input("Pena", item['pena'], key=f"ad_pena_{i}")
        item['fecha'] = cols[4].text_input("Fecha", item['fecha'], key=f"ad_fec_{i}")
        if cols[5].button("❌", key=f"del_ad_{i}"): st.session_state.adulto_list.pop(i); st.rerun()

    # 4. GENERACIÓN Y UNIÓN
    st.markdown("---")
    if st.button("🚀 PROCESAR Y GENERAR ESCRITO COMPLETO", use_container_width=True):
        datos = {
            "defensor": def_nom, "adolescente": imp_nom, "juzgado_ejecucion": juz_ej,
            "rit_principal": rit_pr, "ruc_principal": ruc_pr,
            "causas_rpa": st.session_state.rpa_list, "causas_adulto": st.session_state.adulto_list
        }
        word = MotorJudicialPro().generar_escrito(datos)
        st.session_state.historial.append({"Fecha": "10-02-2026", "Adolescente": imp_nom, "RIT": rit_pr})
        
        st.success("✅ Escrito generado correctamente.")
        st.download_button("⬇️ Descargar Word", word, f"Extincion_{imp_nom}.docx", use_container_width=True)
        
        if st.session_state.adulto_list:
            merged = fitz.open()
            for x in st.session_state.adulto_list:
                if "bytes" in x: merged.insert_pdf(fitz.open(stream=x['bytes'], filetype="pdf"))
            st.download_button("⬇️ Descargar Sentencias Unidas (PDF)", io.BytesIO(merged.tobytes()), "Sentencias_Unidas.pdf", use_container_width=True)

    # HISTORIAL
    with st.expander("📚 Ver Historial de Sesión"):
        st.table(st.session_state.historial)
