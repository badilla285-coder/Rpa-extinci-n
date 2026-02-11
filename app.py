import streamlit as st
import fitz  # PyMuPDF
from docx import Document
from docx.shared import Pt, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
import io
import re

# --- CONFIGURACIÓN Y SEGURIDAD ---
def check_password():
    if "password_correct" not in st.session_state:
        st.title("🔐 Acceso Sistema Judicial")
        col_m, col_p = st.columns(2)
        email = col_m.text_input("Correo electrónico")
        password = col_p.text_input("Contraseña", type="password")
        if st.button("Ingresar"):
            if email == "badilla285@gmail.com" and password == "nacho2026":
                st.session_state["password_correct"] = True
                st.rerun()
            else:
                st.error("Credenciales incorrectas")
        return False
    return True

class GeneradorPro:
    def __init__(self):
        self.fuente = "Cambria"
        self.size = 12

    def extraer_datos_pdf(self, file):
        """Extrae RIT, RUC y Tribunal de un PDF judicial chileno."""
        texto = ""
        # Resetear puntero del archivo para lectura
        file.seek(0)
        with fitz.open(stream=file.read(), filetype="pdf") as doc:
            for pagina in doc:
                texto += pagina.get_text()
        
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
        style = doc.styles['Normal']
        style.font.name = self.fuente
        style.font.size = Pt(self.size)

        for section in doc.sections:
            section.left_margin = Inches(1.2)
            section.right_margin = Inches(1.0)

        def add_p(texto, bold=False, indent=True):
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            if indent: 
                p.paragraph_format.first_line_indent = Inches(0.5)
            
            # Dividir texto para aplicar negritas si es necesario
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
        
        comp = (f"\n{data['individualizacion']['defensor'].upper()}, Postulante, Defensoría Penal Pública San Bernardo, "
                f"en representación de {data['individualizacion']['adolescente'].upper()}, en causa RIT: {data['individualizacion']['rit']}, "
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
    if "causas_rpa" not in st.session_state: st.session_state.causas_rpa = []
    if "condenas_adulto" not in st.session_state: st.session_state.condenas_adulto = []
    
    menu = st.sidebar.radio("Navegación", ["Generador", "Historial"])

    if menu == "Generador":
        gp = GeneradorPro()
        
        # 1. Individualización
        st.subheader("1. Individualización (Causa de Ejecución)")
        c1, c2, c3, c4 = st.columns(4)
        defensor = c1.text_input("Defensor/Postulante", "IGNACIO BADILLA LARA")
        adolescente = c2.text_input("Adolescente / Imputado")
        juzgado_e = c3.text_input("Juzgado (que conoce ejecución)", "San Bernardo")
        rit_e = c4.text_input("RIT Principal")
        ruc_e = c1.text_input("RUC Principal")

        # 2. Causas RPA con Relleno Inteligente
        st.markdown("---")
        st.subheader("2. Causas RPA Sancionadas")
        pdf_rpa = st.file_uploader("Adjuntar sentencias RPA para relleno automático", type="pdf", accept_multiple_files=True, key="up_rpa")
        
        if pdf_rpa:
            for file in pdf_rpa:
                if file.name not in [c.get('filename') for c in st.session_state.causas_rpa]:
                    datos = gp.extraer_datos_pdf(file)
                    st.session_state.causas_rpa.append({
                        "rit": datos["rit"], "ruc": datos["ruc"], "juzgado": datos["tribunal"], "sancion": "", "filename": file.name
                    })

        for i, causa in enumerate(st.session_state.causas_rpa):
            cols = st.columns([2, 2, 2, 3, 1])
            causa["rit"] = cols[0].text_input(f"RIT", causa["rit"], key=f"rit_rpa_{i}")
            causa["ruc"] = cols[1].text_input(f"RUC", causa["ruc"], key=f"ruc_rpa_{i}")
            causa["juzgado"] = cols[2].text_input(f"Juzgado", causa["juzgado"], key=f"juz_rpa_{i}")
            causa["sancion"] = cols[3].text_input(f"Sanción (Pena)", causa["sancion"], key=f"san_rpa_{i}")
            if cols[4].button("🗑️", key=f"del_rpa_{i}"):
                st.session_state.causas_rpa.pop(i)
                st.rerun()

        if st.button("➕ Añadir Causa RPA Manual"):
            st.session_state.causas_rpa.append({"rit": "", "ruc": "", "juzgado": "", "sancion": "", "filename": "manual"})
            st.rerun()

        # 3. Condenas Adulto con Relleno Inteligente
        st.markdown("---")
        st.subheader("3. Fundamento: Condenas Adulto")
        pdf_adulto = st.file_uploader("Adjuntar sentencia ADULTO para relleno automático", type="pdf", accept_multiple_files=True, key="up_adulto")
        
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

        # 4. Generación
        st.markdown("---")
        if st.button("🚀 GENERAR ESCRITO COMPLETO", use_container_width=True):
            if not adolescente or not rit_e:
                st.error("Faltan datos de individualización (Adolescente o RIT principal)")
            else:
                data_final = {
                    "individualizacion": {"defensor": defensor, "adolescente": adolescente, "juzgado": juzgado_e, "rit": rit_e, "ruc": ruc_e},
                    "causas_rpa": st.session_state.causas_rpa,
                    "condenas_adulto": st.session_state.condenas_adulto
                }
                
                docx_buffer = gp.crear_docx(data_final)
                st.session_state.historial.append({"Fecha": "10-02-2026", "Imputado": adolescente, "RIT": rit_e})
                
                st.success("Escrito generado correctamente.")
                st.download_button("⬇️ Descargar Escrito (WORD)", docx_buffer, f"Extincion_{adolescente}.docx", use_container_width=True)
                
                if st.session_state.condenas_adulto:
                    pdf_final = fitz.open()
                    for cond in st.session_state.condenas_adulto:
                        if "bytes" in cond:
                            pdf_ad = fitz.open(stream=cond["bytes"], filetype="pdf")
                            pdf_final.insert_pdf(pdf_ad)
                    out_pdf = io.BytesIO(pdf_final.tobytes())
                    st.download_button("⬇️ Descargar Sentencias Adulto Unidas (PDF)", out_pdf, "Sentencias_Adulto_Adjuntas.pdf", use_container_width=True)

    elif menu == "Historial":
        st.subheader("📚 Historial de la Sesión")
        if st.session_state.historial:
            st.dataframe(st.session_state.historial, use_container_width=True)
        else:
            st.info("No se han generado escritos en esta sesión.")
