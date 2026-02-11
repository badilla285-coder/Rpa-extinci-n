import fitz  # PyMuPDF
from docx import Document
from docx.shared import Pt, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH

class GeneradorJuridico:
    def __init__(self):
        self.fuente = "Century Gothic"
        self.tamaño_cuerpo = 11

    def leer_sentencia(self, ruta_pdf):
        """Extrae el texto íntegro para cumplir con la no reducción de info."""
        try:
            texto = ""
            with fitz.open(ruta_pdf) as doc:
                for pagina in doc:
                    texto += pagina.get_text("text")
            return texto if texto else "[No se pudo extraer texto del PDF]"
        except:
            return "[Error al leer el archivo PDF]"

    def aplicar_estilo(self, parrafo, negrita=False, alineacion=WD_ALIGN_PARAGRAPH.JUSTIFY):
        parrafo.alignment = alineacion
        run = parrafo.runs[0] if parrafo.runs else parrafo.add_run()
        run.font.name = self.fuente
        run.font.size = Pt(self.tamaño_cuerpo)
        run.bold = negrita
        return run

    def crear_escrito(self, datos, texto_sentencia):
        doc = Document()
        
        # Configuración de márgenes profesionales
        for section in doc.sections:
            section.left_margin = Inches(1.2)
            section.right_margin = Inches(1.0)

        # Encabezado DPP
        h = doc.add_paragraph("Defensoría\nSin defensa no hay Justicia")
        self.aplicar_estilo(h, alineacion=WD_ALIGN_PARAGRAPH.LEFT)

        # SUMA
        suma = doc.add_paragraph()
        run_s = suma.add_run("EN LO PRINCIPAL: SOLICITA EXTINCIÓN;\n")
        run_s.bold = True
        run_s.font.size = Pt(12)
        run_o = suma.add_run("OTROSÍ: ACOMPAÑA DOCUMENTO.")
        run_o.bold = True
        self.aplicar_estilo(suma, alineacion=WD_ALIGN_PARAGRAPH.LEFT)

        # Tribunal
        t = doc.add_paragraph(f"\nJUZGADO DE GARANTÍA DE {datos.get('tribunal', 'SAN BERNARDO').upper()}")
        self.aplicar_estilo(t, negrita=True)

        # Comparecencia
        c = doc.add_paragraph(
            f"\n{datos.get('nombre', 'IGNACIO BADILLA LARA')}, Postulante, Defensoría Penal Pública, "
            f"en representación de {datos.get('imputado', '________________')}, en causa RIT: {datos.get('rit_rpa', '____')}, "
            f"RUC: {datos.get('ruc_rpa', '____')}, a S.S., respetuosamente digo:"
        )
        self.aplicar_estilo(c)

        # Cuerpo Normativo
        p1 = doc.add_paragraph(
            "\nQue, vengo en solicitar que declare la extinción de las sanciones de la Ley de "
            "Responsabilidad Penal Adolescente, en virtud del artículo 25 ter y 25 quinquies de la Ley 20.084."
        )
        self.aplicar_estilo(p1)

        # Causa RPA
        p2 = doc.add_paragraph(f"\n1. RIT: {datos.get('rit_rpa', '____')}, RUC: {datos.get('ruc_rpa', '____')}: ")
        self.aplicar_estilo(p2, negrita=True)
        p2.add_run(f"Sancionado por el Juzgado de Garantía de {datos.get('comuna_rpa', '____')} a la pena de {datos.get('pena_rpa', '____')}.")

        # Causa Adulto (Aquí va el texto ÍNTEGRO de la sentencia)
        p3 = doc.add_paragraph("\n2. SENTENCIA DE ADULTO (TRANSCRIPCIÓN ÍNTEGRA):")
        self.aplicar_estilo(p3, negrita=True)
        
        # Insertamos el texto extraído sin resumir
        p_texto = doc.add_paragraph(texto_sentencia)
        self.aplicar_estilo(p_texto)

        # Fundamento Jurídico Robusto (Copiado del modelo Alarcón)
        p4 = doc.add_paragraph(
            "\nSe hace presente que el artículo 25 ter en su inciso tercero establece que se "
            "considerará más grave el delito o conjunto de ellos que tuviere asignada en la ley una "
            "mayor pena de conformidad con las reglas generales. En el presente caso, la sanción "
            "impuesta como adulto reviste una mayor gravedad, configurándose así los presupuestos para la extinción."
        )
        self.aplicar_estilo(p4)

        # Petitoria
        p5 = doc.add_paragraph("\nPOR TANTO,")
        self.aplicar_estilo(p5)
        p6 = doc.add_paragraph("SOLICITO A S.S. acceder a lo solicitado extinguiendo de pleno derecho la sanción referida.")
        self.aplicar_estilo(p6)

        nombre_archivo = f"Extincion_{datos.get('imputado', 'Escrito')}.docx"
        doc.save(nombre_archivo)
        print(f"Archivo generado con éxito: {nombre_archivo}")

# --- USO PRÁCTICO ---
if __name__ == "__main__":
    app = GeneradorJuridico()
    
    # 1. Lee el PDF (Asegúrate de que el nombre del archivo sea igual al que tienes)
    texto = app.leer_sentencia("sentencia_ejemplo.pdf") 
    
    # 2. Datos para rellenar
    mis_datos = {
        "imputado": "JUAN PEREZ",
        "rit_rpa": "1587-2018",
        "ruc_rpa": "1800174694-0",
        "pena_rpa": "2 años de libertad asistida especial",
        "tribunal": "San Bernardo"
    }
    
    app.crear_escrito(mis_datos, texto)
