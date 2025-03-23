#!/usr/bin/env python3
"""
Script de prueba para la extracción de información de becas.
Se centra en probar cada una de las funciones de extracción por separado
para facilitar la depuración.
"""

import os
import json
import fitz  # PyMuPDF
from pymupdf_extractor import (
    extract_text_from_pdf,
    extract_academic_year,
    extract_eligible_studies,
    extract_scholarship_amounts,
    extract_income_thresholds,
    extract_application_deadlines,
    extract_academic_requirements
)

def extract_and_test(pdf_path):
    """Extrae texto del PDF y prueba cada función de extracción."""
    # Extraer texto del PDF
    print(f"Extrayendo texto de: {pdf_path}")
    text = extract_text_from_pdf(pdf_path)
    
    # Guardar texto para referencia
    output_dir = "./output"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    pdf_name = os.path.splitext(os.path.basename(pdf_path))[0]
    text_path = os.path.join(output_dir, f"{pdf_name}_text.txt")
    with open(text_path, 'w', encoding='utf-8') as f:
        f.write(text)
    print(f"Texto guardado en: {text_path}")
    
    print("\n" + "=" * 80)
    print(" RESULTADOS DE EXTRACCIÓN ".center(80, "="))
    print("=" * 80)
    
    # Probar cada función de extracción
    print("\n1. Año académico:")
    academic_year = extract_academic_year(text)
    print(json.dumps(academic_year, indent=2, ensure_ascii=False))
    
    print("\n2. Estudios elegibles:")
    eligible_studies = extract_eligible_studies(text)
    # Mostrar solo un resumen, ya que puede ser muy extenso
    print(f"  Descripción: {eligible_studies.get('description')}")
    print(f"  Estudios universitarios: {len(eligible_studies.get('university_studies', []))} programas")
    print(f"  Estudios no universitarios: {len(eligible_studies.get('non_university_studies', []))} programas")
    
    print("\n3. Cuantías de becas:")
    scholarship_amounts = extract_scholarship_amounts(text)
    print(f"  Descripción: {scholarship_amounts.get('description')}")
    print(f"  Componentes: {len(scholarship_amounts.get('components', []))} encontrados")
    for component in scholarship_amounts.get('components', [])[:3]:  # Mostrar solo los 3 primeros
        print(f"    - {component.get('type')}: {component.get('amount_description', '')}")
    if len(scholarship_amounts.get('components', [])) > 3:
        print(f"    ... y {len(scholarship_amounts.get('components', [])) - 3} más")
    
    print("\n4. Umbrales de renta:")
    income_thresholds = extract_income_thresholds(text)
    print(f"  Descripción: {income_thresholds.get('description')}")
    print(f"  Umbrales: {len(income_thresholds.get('thresholds', []))} encontrados")
    for threshold in income_thresholds.get('thresholds', []):
        print(f"    - Umbral {threshold.get('number')}: {len(threshold.get('family_sizes', []))} tamaños de familia")
    
    print("\n5. Plazos de solicitud:")
    application_deadlines = extract_application_deadlines(text)
    print(f"  Descripción: {application_deadlines.get('description')}")
    print(f"  Plazos: {len(application_deadlines.get('deadlines', []))} encontrados")
    for deadline in application_deadlines.get('deadlines', []):
        print(f"    - {deadline.get('type')}: {deadline.get('deadline')}")
    
    print("\n6. Requisitos académicos:")
    academic_requirements = extract_academic_requirements(text)
    print(f"  Descripción: {academic_requirements.get('description')}")
    print(f"  Requisitos: {len(academic_requirements.get('requirements', []))} encontrados")
    for req in academic_requirements.get('requirements', []):
        print(f"    - {req.get('type')}: {req.get('description')}")
    
    # Guardar resultados completos en JSON
    results = {
        "academic_year": academic_year,
        "eligible_studies": eligible_studies,
        "scholarship_amounts": scholarship_amounts,
        "income_thresholds": income_thresholds,
        "application_deadlines": application_deadlines,
        "academic_requirements": academic_requirements,
    }
    
    results_path = os.path.join(output_dir, f"{pdf_name}_results.json")
    with open(results_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\nResultados guardados en: {results_path}")

def main():
    # Comprobar que existe el directorio de corpus
    corpus_dir = "./corpus"
    if not os.path.exists(corpus_dir):
        print(f"Error: No se encuentra el directorio {corpus_dir}")
        print("Crea este directorio y coloca allí tus archivos PDF de becas.")
        return
    
    # Listar PDFs disponibles
    pdf_files = [f for f in os.listdir(corpus_dir) if f.lower().endswith('.pdf')]
    if not pdf_files:
        print(f"No se encontraron archivos PDF en {corpus_dir}")
        return
    
    print("PDFs disponibles:")
    for i, pdf_file in enumerate(pdf_files, 1):
        print(f"{i}. {pdf_file}")
    
    # Permitir elegir un PDF para procesar
    choice = 0
    while choice < 1 or choice > len(pdf_files):
        try:
            choice = int(input(f"\nSelecciona un PDF para analizar (1-{len(pdf_files)}): "))
        except ValueError:
            print("Por favor, introduce un número válido.")
    
    selected_pdf = pdf_files[choice - 1]
    pdf_path = os.path.join(corpus_dir, selected_pdf)
    
    # Extraer información del PDF seleccionado
    extract_and_test(pdf_path)

if __name__ == "__main__":
    main()