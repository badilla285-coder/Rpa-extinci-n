import fitz  # PyMuPDF
from docx import Document
from docx.shared import Pt, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from datetime import datetime

class GeneradorExtincion:
    def __init__(self):
        self.fuente = "Century Gothic" # Fuente corporativa sugerida
        self.tamaño_fuente = 11

    def extraer_texto_pdf(self, ruta_pdf):
        """Lee el PDF y extrae TODO el texto sin resúmenes."""
        try:
            texto = ""
            with fitz.open(ruta_pdf) as doc:
                for pagina in doc:
                    texto += pagina.get_text("text")
            return texto
        except Exception as e:
            return f"Error al leer el archivo: {e}"

    def configurar_parrafo(self, parrafo, alineacion=None):
        """Aplica el formato de fuente estándar."""
        run = parrafo.runs[0] if parrafo.runs else parrafo.add_run()
        run.font.name = self.fuente
        run.font.size = Pt(self.tamaño_fuente)
        if alineacion:
            parrafo.alignment = alineacion
        return run

    def generar_word(self, datos, nombre_archivo="Escrito_Extincion.docx"):
        doc = Document()
        
        # Ajuste de márgenes
        sections = doc.sections
        for section in sections:
            section.top_margin = Inches(1)
            section.bottom_margin = Inches(1)
            section.left_margin = Inches(1.2)
            section.right_margin = Inches(1)

        # 1. ENCABEZADO
        header = doc.add_paragraph("Defensoría\nSin defensa no hay Justicia")
        self.configurar_parrafo(header, WD_ALIGN_PARAGRAPH.LEFT)

        # 2. SUMA (Negrita y Mayúscula)
        suma_p = doc.add_paragraph()
        suma_p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        run_suma = suma_p.add_run("EN LO PRINCIPAL: SOLICITA EXTINCIÓN;\n")
        run_suma.bold = True
        run_suma.font.name = self.fuente
        run_suma.font.size = Pt(12)
        run_otrosi = suma_p.add_run("OTROSÍ: ACOMPAÑA DOCUMENTO.")
        run_otrosi.bold = True
        run_otrosi.font.name = self.fuente

        # 3. TRIBUNAL
        tribunal = doc.add_paragraph(f"\nJUZGADO DE GARANTÍA DE {datos['comuna_tribunal'].upper()}")
        self.configurar_parrafo(tribunal, WD_ALIGN_PARAGRAPH.LEFT).bold = True

        # 4. COMPARECENCIA
        presentacion = doc.add_paragraph(
            f"\n{datos['nombre_abogado']}, {datos['cargo']}, Defensoría Penal Pública, "
            f"en representación de {datos['nombre_imputado']}, en causa RIT: {datos['rit_causa']}, "
            f"RUC: {datos['ruc_causa']}, a S.S., respetuosamente digo:"
        )
        self.configurar_parrafo(presentacion, WD_ALIGN_PARAGRAPH.JUSTIFY)

        # 5. CUERPO - SOLICITUD
        intro = doc.add_paragraph(
            "\nQue, vengo en solicitar que declare la extinción de las sanciones de la Ley de "
            "Responsabilidad Penal Adolescente, o en subsidio se fije día y hora para celebrar "
            "audiencia para debatir sobre la extinción de la pena respecto de mi representado, en "
            "virtud del artículo 25 ter y 25 quinquies de la Ley 20.084."
        )
        self.configurar_parrafo(intro, WD_ALIGN_PARAGRAPH.JUSTIFY)

        # 6. DETALLE CAUSA RPA (Sin resumir)
        doc.add_paragraph("\nMi representado fue condenado en la siguiente causa de la Ley RPA:")
        causa_rpa = doc.add_paragraph()
        run_rpa = self.configurar_parrafo(causa_rpa, WD_ALIGN_PARAGRAPH.JUSTIFY)
        run_rpa.add_text(f"1. RIT: {datos['rit_causa']}, RUC: {datos['ruc_causa']}: ")
        run_rpa.add_text(f"Condenado por el Juzgado de Garantía de {datos['comuna_rpa']} a la sanción de {datos['sancion_rpa']}. "
                         f"Dicha pena no se encuentra cumplida.")

        # 7. FUNDAMENTO (SENTENCIA ADULTO)
        doc.add_paragraph("\nEl fundamento de la extinción radica en la condena de mayor gravedad como adulto:")
        causa_adulto = doc.add_paragraph()
        run_adulto = self.configurar_parrafo(causa_adulto, WD_ALIGN_PARAGRAPH.JUSTIFY)
        run_adulto.add_text(f"2. {datos['info_sentencia_adulto']}") # Aquí entra el texto íntegro extraído

        # 8. FUNDAMENTOS JURÍDICOS (Basados en el modelo de Carlos Alarcón)
        fundamentos = doc.add_paragraph(
            "\nSe hace presente que el artículo 25 ter en su inciso tercero establece que se "
            "considerará más grave el delito o conjunto de ellos que tuviere asignada en la ley una "
            "mayor pena de conformidad con las reglas generales. En el presente caso, la sanción "
            "impuesta como adulto reviste una mayor gravedad, tanto por la naturaleza del ilícito "
            "como por la cuantía de la pena impuesta, configurándose así los presupuestos para la extinción."
        )
        self.configurar_parrafo(fundamentos, WD_ALIGN_PARAGRAPH.JUSTIFY)

        # 9. PETITORIA
        petitoria_p = doc.add_paragraph("\nPOR TANTO,")
        self.configurar_parrafo(petitoria_p)
        
        petitoria_final = doc.add_paragraph(
            "En mérito de lo expuesto, SOLICITO A S.S. acceder a lo solicitado extinguiendo "
            "de pleno derecho la sanción antes referida, o en subsidio se fije día y hora para celebrar "
            "audiencia para que se abra debate sobre la extinción de responsabilidad penal en la presente causa."
        )
        self.configurar_parrafo(petitoria_final, WD_ALIGN_PARAGRAPH.JUSTIFY)

        # 10. OTROSÍ
        otrosi_p = doc.add_paragraph(f"\nOTROSÍ: Acompaña sentencia de adulto de mi representado de la causa RIT: {datos['rit_adulto']}.")
        self.configurar_parrafo(otrosi_p, WD_ALIGN_PARAGRAPH.JUSTIFY).bold = True

        doc.save(nombre_archivo)
        return nombre_archivo

# --- EJEMPLO DE USO ---
if __name__ == "__main__":
    generador = GeneradorExtincion()
    
    # Supongamos que el usuario subió una sentencia
    # texto_extraido = generador.extraer_texto_pdf("sentencia_ejemplo.pdf")
    texto_extraido = "TRANSCRIPCIÓN ÍNTEGRA DE LA SENTENCIA DE ADULTO AQUÍ..."

    datos_usuario = {
        "comuna_tribunal": "San Bernardo",
        "nombre_abogado": "IGNACIO BADILLA LARA",
        "cargo": "Postulante",
        "nombre_imputado": "JUAN PÉREZ GONZÁLEZ",
        "rit_causa": "123-2023",
        "ruc_causa": "2300012345-K",
        "comuna_rpa": "San Bernardo",
        "sancion_rpa": "Libertad Asistida Especial por 1 año",
        "rit_adulto": "456-2024",
        "info_sentencia_adulto": texto_extraido # Aquí se inserta el texto sin resumir
    }

    archivo_final = generador.generar_word(datos_usuario)
    print(f"Éxito: Se ha generado el archivo {archivo_final}")
