import streamlit as st
from docx import Document
from docx.shared import Pt
import PyPDF2
import io

def crear_escrito(datos, texto_condena):
    doc = Document()
    style = doc.styles['Normal']
    style.font.name = 'Arial'
    style.font.size = Pt(12)

    p = doc.add_paragraph()
    p.add_run("SUMILLA: SOLICITA DECLARACIÓN DE EXTINCIÓN DE RESPONSABILIDAD PENAL.\n").bold = True
    p.add_run(f"RIT: {datos['rit']}\n")
    p.add_run(f"RUC: {datos['ruc']}\n")
    p.add_run(f"TRIBUNAL: {datos['juzgado']}\n")

    doc.add_paragraph("\nEN LO PRINCIPAL: SOLICITA DECLARACIÓN DE EXTINCIÓN; OTROSÍ: ACOMPAÑA DOCUMENTO.")
    
    p_juez = doc.add_paragraph()
    p_juez.add_run(f"\nS.J.L. DE GARANTÍA DE {datos['juzgado'].upper()}").bold = True

    cuerpo = doc.add_paragraph()
    cuerpo.add_run(f"\n{datos['nombre_defensor']}, abogado de la Defensoría Penal Pública, en representación del adolescente {datos['nombre_adolescente']}, en la causa RIT {datos['rit']}, a SS. con respeto digo:\n")
    
    cuerpo.add_run("\nQue, por este acto y de acuerdo a lo previsto en la Ley 20.084, vengo en solicitar se declare la extinción de la responsabilidad penal de mi representado en la presente causa. Esto, fundado en que el adolescente ha sido condenado por un tribunal de adultos a una pena privativa de libertad, lo cual hace incompatible la ejecución de la sanción en el sistema de responsabilidad penal adolescente, conforme a los principios de coherencia del sistema punitivo y las normas de extinción del Código Penal.\n")

    doc.add_paragraph("\nFUNDAMENTOS DE LA CONDENA DE ADULTO ADJUNTA:").bold = True
    doc.add_paragraph(texto_condena)
    
    p_final = doc.add_paragraph()
    p_final.add_run("\nPOR TANTO, de acuerdo a lo dispuesto en la Ley 20.084
