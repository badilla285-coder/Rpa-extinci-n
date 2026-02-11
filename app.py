import streamlit as st
import fitz  # PyMuPDF
from docx import Document
from docx.shared import Pt, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
import io
import re

# --- CONFIGURACIÓN Y SEGURIDAD ---
def check_password():
    def password_entered():
        if st.session_state["email"] == "badilla285@gmail.com" and st.session_state["password"] == "nacho2026":
            st.session_state["password_correct"] = True
            del st.session_state["password"]
            del st.session_state["email"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.title("🔐 Acceso Sistema Judicial")
        st.text_input("Correo electrónico", key="email")
        st.text_input("Contraseña", type="password", key="password")
        st.button("Ingresar", on_click=password_entered)
        return False
    elif not st.session_state["password_correct"]:
        st.error("Credenciales incorrectas")
        return False
    return True

# --- LÓGICA DE EXTRACCIÓN Y PROCESAMIENTO ---
class GeneradorPro:
    def __init__(self):
        self.fuente = "Cambria"
        self.size = 12

    def extraer_datos_pdf(self, file):
        texto = ""
        with fitz.open(stream=file.read(), filetype="pdf") as doc:
            for pagina in doc:
                texto += pagina.get_text()
        
        # Búsqueda inteligente
        rit = re.search(r"RIT[:\s]+(\d+-\d{4})", texto, re.I)
        ruc = re.search(r"RUC[:\s]+(\d{10}-\w)", texto, re.I)
        trib = re.search(r"Juzgado de Garantía de\s+([a-zA-Z\s]+)", texto, re.I)
        
        return {
            "rit": rit.group(1) if rit else "",
            "ruc": ruc.group(1) if ruc else "",
            "tribunal": trib.group(1).strip() if trib else "",
            "texto_completo": texto
        }

    def crear_docx(self, data):
        doc = Document()
        # Estilo Base
        style = doc.styles['Normal']
        style.font.name = self.fuente
        style.font.size = Pt(self.size)

        for section in doc.sections:
            section.left_margin = Inches(1.2)
            section.right_margin = Inches(1.0)

        def add_p(texto, bold=False, indent=True):
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            if indent: p.paragraph_format.first_line_indent = Inches(0.5)
            run = p.add_run(texto)
            run.bold = bold
            run.font.name = self.fuente
            run.font.size = Pt(self.size)
            return p

        # 1. SUMA
        table = doc.add_table(rows=1, cols=2)
        p_suma = table.cell(0, 1).paragraphs[0]
        p_suma.alignment = WD_ALIGN_PARAGRAPH.LEFT
        r_suma = p_suma.add_run("EN LO PRINCIPAL: SOLICITA EXTINCIÓN DE SANCIÓN RPA;\nOTROSÍ: ACOMPAÑA DOCUMENTOS.")
        r_suma.bold = True

        # 2. CUERPO
        add_p(f"\nS.J.L. DE GARANTÍA DE {data['individualizacion']['juzgado'].upper()}", bold=True, indent=False)
        
        comp = (f"\n{data['individualizacion']['defensor'].upper()}, Defensor Penal Público, en representación de "
                f"{data['individualizacion']['adolescente'].upper()}, en causa RIT: {data['individualizacion']['rit']}, "
                f"RUC: {data['individualizacion']['ruc']}, a S.S. respetuosamente digo:")
        add_p(comp, indent=False)

        add_p("\nQue, vengo en solicitar que declare la extinción de las sanciones de la Ley 20.084, en virtud del "
              "artículo 25 ter y 25 quinquies del referido cuerpo legal.", bold=True)

        add_p("\nI. CAUSAS RPA SANCIONADAS", bold=True, indent=False)
        for causa in data['causas_rpa']:
            txt_causa = f"Causa RIT: {causa['rit']}, RUC: {causa['ruc']}, del Juzgado de {causa['juzgado']}, sancionado a {causa['sancion']}."
            add_p(txt_causa)

        add_p("\nII. FUNDAMENTO DE EXTINCIÓN (CONDENA ADULTO)", bold=True, indent=False)
        for cond in data['condenas_adulto']:
            txt_cond = (f"Consta condena como adulto en causa RIT: {cond['rit']}, RUC: {cond['ruc']} del Juzgado de {cond['juzgado']}, "
                        f"donde se impuso la pena de {cond['pena']}. Atendido que dicha sanción reviste una mayor gravedad, "
                        "se configuran los presupuestos legales para la extinción de pleno derecho.")
            add_p(txt_cond)

        add_p("\nPOR TANTO,", indent=False)
        add_p("SOLICITO A S.S. acceder a lo solicitado extinguiendo de pleno derecho las sanciones RPA individualizadas.")

        add_p("\nOTROSÍ: Acompaña sentencias de adulto causas " + ", ".join([f"RIT {c['rit']}" for c in data['condenas_adulto']]) + ".", bold=True, indent=False)
        add_p("POR TANTO, SOLICITO A S.S. tenerlas por acompañadas.")

        target = io.BytesIO()
        doc.save(target)
        target.seek(0)
        return target

# --- INTERFAZ ---
if check_password():
    st.set_page_config(page_title="Generador Pro", layout="wide")
    st.title("⚖️ Generador de Extinciones Jurídicas")
    
    if "historial" not in st.session_state: st.session_state.historial = []
    
    menu = st.sidebar.radio("Navegación", ["Generador", "Historial"])

    if menu == "Generador":
        gp = GeneradorPro()
        
        # 1. Individualización
        st.subheader("1. Individualización")
        c1, c2, c3, c4 = st.columns(4)
        defensor = c1.text_input("Defensor", "IGNACIO BADILLA LARA")
        adolescente = c2.text_input("Adolescente")
        juzgado_e = c3.text_input("Juzgado (Ejecución)")
        rit_e = c4.text_input("RIT Principal")
        ruc_e = c1.text_input("RUC Principal")

        # 2. Causas RPA
        st.subheader("2. Causas RPA Sancionadas")
        if "causas_rpa" not in st.session_state: st.session_state.causas_rpa = [{"rit": "", "ruc": "", "juzgado": "", "sancion": ""}]
        
        for i, causa in enumerate(st.session_state.causas_rpa):
            with st.container():
                cols = st.columns([2, 2, 2, 3, 1])
                causa["rit"] = cols[0].text_input(f"RIT", causa["rit"], key=f"rit_rpa_{i}")
                causa["ruc"] = cols[1].text_input(f"RUC", causa["ruc"], key=f"ruc_rpa_{i}")
                causa["juzgado"] = cols[2].text_input(f"Juzgado", causa["juzgado"], key=f"juz_rpa_{i}")
                causa["sancion"] = cols[3].text_input(f"Sanción", causa["sancion"], key=f"san_rpa_{i}")
                if cols[4].button("🗑️", key=f"del_rpa_{i}"):
                    st.session_state.causas_rpa.pop(i)
                    st.rerun()

        if st.button("➕ Añadir Causa RPA"):
            st.session_state.causas_rpa.append({"rit": "", "ruc": "", "juzgado": "", "sancion": ""})
            st.rerun()

        # 3. Condenas Adulto (Con lectura Inteligente)
        st.subheader("3. Fundamento: Condenas Adulto")
        pdf_adulto = st.file_uploader("Adjuntar sentencia adulto para relleno rápido", type="pdf", accept_multiple_files=True)
        
        if "condenas_adulto" not in st.session_state: st.session_state.condenas_adulto = []

        if pdf_adulto:
            for file in pdf_adulto:
                if file.name not in [c.get('filename') for c in st.session_state.condenas_adulto]:
                    datos = gp.extraer_datos_pdf(file)
                    st.session_state.condenas_adulto.append({
                        "rit": datos["rit"], "ruc": datos["ruc"], "juzgado": datos["tribunal"], "pena": "", "filename": file.name, "bytes": file.getvalue()
                    })

        for i, cond in enumerate(st.session_state.condenas_adulto):
            cols = st.columns([2, 2, 2, 3, 1])
            cond["rit"] = cols[0].text_input(f"RIT Adulto", cond["rit"], key=f"rit_ad_{i}")
            cond["ruc"] = cols[1].text_input(f"RUC Adulto", cond["ruc"], key=f"ruc_ad_{i}")
            cond["juzgado"] = cols[2].text_input(f"Juzgado Adulto", cond["juzgado"], key=f"juz_ad_{i}")
            cond["pena"] = cols[3].text_input(f"Pena Adulto", cond["pena"], key=f"pen_ad_{i}")
            if cols[4].button("🗑️", key=f"del_ad_{i}"):
                st.session_state.condenas_adulto.pop(i)
                st.rerun()

        # 4. Generación Final
        if st.button("🚀 GENERAR ESCRITO Y UNIR DOCUMENTOS"):
            data_final = {
                "individualizacion": {"defensor": defensor, "adolescente": adolescente, "juzgado": juzgado_e, "rit": rit_e, "ruc": ruc_e},
                "causas_rpa": st.session_state.causas_rpa,
                "condenas_adulto": st.session_state.condenas_adulto
            }
            
            # Generar Word
            docx_buffer = gp.crear_docx(data_final)
            
            # Unir con PDFs (Merge)
            pdf_final = fitz.open()
            # Nota: Para unir Word se requiere conversión o adjuntar solo los PDFs de adultos
            for cond in st.session_state.condenas_adulto:
                if "bytes" in cond:
                    pdf_ad = fitz.open(stream=cond["bytes"], filetype="pdf")
                    pdf_final.insert_pdf(pdf_ad)
            
            # Descarga
            st.session_state.historial.append({"fecha": "Hoy", "adolescente": adolescente, "rit": rit_e})
            st.success("Escrito preparado.")
            st.download_button("⬇️ Descargar Word del Escrito", docx_buffer, f"Extincion_{adolescente}.docx")
            
            if len(st.session_state.condenas_adulto) > 0:
                out_pdf = io.BytesIO(pdf_final.tobytes())
                st.download_button("⬇️ Descargar PDFs de Adulto Consolidados", out_pdf, "Sentencias_Adjuntas.pdf")

    elif menu == "Historial":
        st.subheader("Historial de Escritos Generados")
        if st.session_state.historial:
            st.table(st.session_state.historial)
        else:
            st.write("No hay registros en esta sesión.")
