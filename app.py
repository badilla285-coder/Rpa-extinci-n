import fitz  # PyMuPDF
from docx import Document
from docx.shared import Pt, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
import os

class GeneradorJuridico:
    def __init__(self):
        self.fuente = "Century Gothic"
        self.tamaño_cuerpo = 11

    def leer_sentencia(self, ruta_pdf):
        """Extrae el texto íntegro. Si es imagen, avisa para evitar omisiones."""
        try:
            if not os.path.exists(ruta_pdf):
                return f"[ERROR: El archivo {ruta_pdf} no se encuentra en el servidor]"
            
            texto = ""
            with fitz.open(ruta_pdf) as doc:
                for pagina in doc:
                    texto += f"\n--- Página {pagina.number + 1} ---\n"
                    texto += pagina.get_text("text")
            
            if not texto.strip() or len(texto) < 50:
                return "[ADVERTENCIA: El PDF parece ser una imagen escaneada. La transcripción automática no es posible sin OCR.]"
            
            return texto
        except Exception as e:
            return f"[Error crítico al leer el PDF: {str(e)}]"

    def aplicar_estilo(self, parrafo, negrita=False, alineacion=WD_ALIGN_PARAGRAPH.JUSTIFY):
        parrafo.alignment = alineacion
        run = parrafo.runs[0] if parrafo.runs else parrafo.add_run()
        run.font.name = self.fuente
        run.font.size = Pt(self.tamaño_cuerpo)
        run.bold = negrita
        return run

    def crear_escrito(self, datos, texto_sentencia):
        doc = Document()
        
        # Configuración de márgenes (estándar judicial chileno)
        for section in doc.sections:
            section.left_margin = Inches(1.2)
            section.right_margin = Inches(1.0)

        # 1. ENCABEZADO
        h = doc.add_paragraph("Defensoría Penal Pública\nSin defensa no hay Justicia")
        self.aplicar_estilo(h, alineacion=WD_ALIGN_PARAGRAPH.LEFT)

        # 2. SUMA
        suma_table = doc.add_table(rows=1, cols=2)
        suma_table.columns[0].width = Inches(3.5)
        cell = suma_table.cell(0, 1)
        p_suma = cell.paragraphs[0]
        run_s = p_suma.add_run("EN LO PRINCIPAL: SOLICITA EXTINCIÓN DE SANCIONES ART. 25 TER Y QUINQUIES LEY 20.084;\nOTROSÍ: ACOMPAÑA DOCUMENTO.")
        run_s.bold = True
        run_s.font.size = Pt(11)
        run_s.font.name = self.fuente

        # 3. TRIBUNAL
        t = doc.add_paragraph(f"\nS.J.L. DE GARANTÍA DE {datos.get('tribunal', 'SAN BERNARDO').upper()}")
        self.aplicar_estilo(t, negrita=True)

        # 4. COMPARECENCIA
        c = doc.add_paragraph(
            f"\n{datos.get('nombre', 'IGNACIO BADILLA LARA').upper()}, Postulante de la Corporación de Asistencia Judicial, "
            f"en representación de {datos.get('imputado', '________________')}, en causa RIT: {datos.get('rit_rpa', '____')}, "
            f"RUC: {datos.get('ruc_rpa', '____')}, a S.S. con respeto digo:"
        )
        self.aplicar_estilo(c)

        # 5. CUERPO - HECHOS Y DERECHO
        p1 = doc.add_paragraph(
            "\nQue, por este acto, vengo en solicitar se declare la extinción de pleno derecho de las sanciones "
            "impuestas en la causa RPA individualizada, por concurrir los presupuestos legales de los artículos 25 ter y 25 quinquies "
            "de la Ley 20.084, atendida la imposición de una pena de mayor gravedad como adulto."
        )
        self.aplicar_estilo(p1)

        # 6. ANTECEDENTES DE LA CAUSA RPA
        p2 = doc.add_paragraph(f"\nI. ANTECEDENTES CAUSA RPA (RIT: {datos.get('rit_rpa', '____')})")
        self.aplicar_estilo(p2, negrita=True)
        p2_det = doc.add_paragraph(f"Sancionado por el Tribunal de {datos.get('comuna_rpa', '____')} a la pena de {datos.get('pena_rpa', '____')}.")
        self.aplicar_estilo(p2_det)

        # 7. TRANSCRIPCIÓN ÍNTEGRA SENTENCIA ADULTO
        p3 = doc.add_paragraph("\nII. SENTENCIA CAUSA ADULTO - TRANSCRIPCIÓN ÍNTEGRA:")
        self.aplicar_estilo(p3, negrita=True)
        
        # Texto íntegro del PDF
        p_texto = doc.add_paragraph(texto_sentencia)
        self.aplicar_estilo(p_texto)

        # 8. FUNDAMENTOS JURÍDICOS
        p4 = doc.add_paragraph("\nIII. FUNDAMENTOS:")
        self.aplicar_estilo(p4, negrita=True)
        fundamento = (
            "El artículo 25 ter inciso tercero dispone que se considerará más grave el delito que tuviere asignada "
            "una mayor pena de conformidad con las reglas generales. Constatándose que mi representado se encuentra "
            "cumpliendo una sanción de mayor entidad, la pena anterior debe declararse extinguida por el solo ministerio de la ley."
        )
        self.aplicar_estilo(doc.add_paragraph(fundamento))

        # 9. PETITORIA
        p5 = doc.add_paragraph("\nPOR TANTO,")
        self.aplicar_estilo(p5)
        p6 = doc.add_paragraph("SOLICITO A S.S. tener por interpuesta la solicitud y declarar la extinción de la sanción referida.")
        self.aplicar_estilo(p6)

        nombre_archivo = f"Extincion_{datos.get('imputado', 'Escrito')}.docx"
        doc.save(nombre_archivo)
        return nombre_archivo

# --- USO ---
if __name__ == "__main__":
    app = GeneradorJuridico()
    # Cambia 'sentencia.pdf' por el nombre real de tu archivo
    texto_extraido = app.leer_sentencia("sentencia.pdf")
    
    mis_datos = {
        "nombre": "IGNACIO BADILLA LARA",
        "imputado": "JUAN PEREZ",
        "rit_rpa": "1587-2018",
        "ruc_rpa": "1800174694-0",
        "pena_rpa": "2 años de libertad asistida especial",
        "tribunal": "San Bernardo",
        "comuna_rpa": "San Bernardo"
    }
    
    archivo = app.crear_escrito(mis_datos, texto_extraido)
    print(f"Escrito generado: {archivo}")
