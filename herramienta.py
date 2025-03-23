#!/usr/bin/env python3
"""
Herramienta para probar patrones de extracción en textos extraídos de PDFs.
Permite verificar si los patrones de expresiones regulares funcionan correctamente
para extraer información de los textos.

Uso:
python pattern_tester.py --input ./output --text-files "*_pymupdf.txt"
"""

import os
import re
import glob
import argparse
from pathlib import Path

def test_pattern(text, pattern_name, pattern, description):
    """Prueba un patrón y muestra los resultados."""
    print(f"\n{'-'*80}")
    print(f"Patrón: {pattern_name}")
    print(f"Descripción: {description}")
    print(f"Expresión regular: {pattern}")
    print(f"{'-'*80}")
    
    try:
        matches = re.findall(pattern, text, re.DOTALL | re.IGNORECASE)
        if matches:
            print(f"✅ Encontradas {len(matches)} coincidencias:")
            for i, match in enumerate(matches[:5], 1):
                if isinstance(match, tuple):
                    groups = match
                    print(f"  {i}. Grupos encontrados:")
                    for j, group in enumerate(groups, 1):
                        preview = group.replace('\n', ' ')[:100]
                        print(f"     Grupo {j}: {preview}...")
                else:
                    preview = match.replace('\n', ' ')[:100]
                    print(f"  {i}. {preview}...")
            
            if len(matches) > 5:
                print(f"  ... y {len(matches) - 5} más")
        else:
            print("❌ No se encontraron coincidencias con este patrón.")
    except Exception as e:
        print(f"❌ Error al aplicar el patrón: {str(e)}")
    
    return matches

def test_academic_year_pattern(text):
    """Prueba patrones para extraer el año académico."""
    patterns = [
        (r'CURSO ACADÉMICO (\d{4}-\d{4})', "Patrón para 'CURSO ACADÉMICO YYYY-YYYY'"),
        (r'curso académico (\d{4}-\d{4})', "Patrón para 'curso académico YYYY-YYYY'"),
        (r'para el curso (\d{4}-\d{4})', "Patrón para 'para el curso YYYY-YYYY'"),
        (r'BECAS.*?(\d{4}-\d{4})', "Patrón para 'BECAS... YYYY-YYYY'"),
        (r'BECAS.*?CURSO.*?(\d{4}-\d{4})', "Patrón para 'BECAS... CURSO... YYYY-YYYY'")
    ]
    
    print("\n=== PRUEBA DE PATRONES: AÑO ACADÉMICO ===")
    
    for pattern, description in patterns:
        matches = test_pattern(text, "Año Académico", pattern, description)
        if matches:
            print("\n✅ Se encontró al menos un año académico!")
            return True
    
    print("\n❌ No se pudo encontrar el año académico en el texto.")
    return False

def test_scholarship_amounts_pattern(text):
    """Prueba patrones para extraer montos de becas."""
    patterns = [
        (r'(?:Artículo\s+\d+\.\s+Cuantías de las becas|CUANTÍAS DE LAS BECAS).*?(?=Artículo\s+\d+\.)', 
         "Patrón para sección completa de cuantías"),
        (r'Las cuantías.*?serán las siguientes:.*?(?=Artículo\s+\d+\.)', 
         "Patrón para sección que comienza con 'Las cuantías...'"),
        (r'(?:[A-F]\))([^A-F\)]+)(?=[A-F]\)|$)', 
         "Patrón para componentes con letras mayúsculas (A), B), C)...)"),
        (r'Cuantía fija ligada a la renta.*?(\d+[,.]\d+)\s*euros', 
         "Patrón para 'Cuantía fija ligada a la renta'")
    ]
    
    print("\n=== PRUEBA DE PATRONES: MONTOS DE BECAS ===")
    
    # Primero buscar la sección completa
    section_found = False
    section_text = ""
    
    for i in range(2):
        pattern, description = patterns[i]
        matches = test_pattern(text, "Sección de Cuantías", pattern, description)
        if matches and matches[0].strip():
            section_found = True
            section_text = matches[0]
            print("\n✅ Sección de cuantías encontrada!")
            
            # Mostrar las primeras líneas de la sección
            preview_lines = section_text.split('\n')[:10]
            print("\nVista previa de la sección:")
            for line in preview_lines:
                print(f"  {line.strip()}")
            
            if len(section_text.split('\n')) > 10:
                print("  ...")
            
            break
    
    if not section_found:
        print("\n❌ No se pudo encontrar la sección de cuantías de becas.")
        # Buscar en todo el texto las cuantías específicas
        section_text = text
    
    # Ahora buscar componentes específicos en la sección encontrada
    component_patterns = [
        (r'[Bb]eca.*?matrícula.*?(?:\.|$)', "Beca de matrícula"),
        (r'[Cc]uantía.*?renta.*?(\d+[,.]\d+)\s*euros', "Cuantía ligada a renta"),
        (r'[Cc]uantía.*?residencia.*?(\d+[,.]\d+)\s*euros', "Cuantía ligada a residencia"),
        (r'[Cc]uantía.*?excelencia.*?(\d+[,.]\d+).*?(\d+[,.]\d+).*?(\d+)\s*euros', "Cuantía ligada a excelencia"),
        (r'[Bb]eca básica.*?(\d+[,.]\d+)\s*euros', "Beca básica"),
        (r'[Cc]uantía variable.*?mínimo.*?(\d+[,.]\d+)\s*euros', "Cuantía variable mínima")
    ]
    
    print("\n--- Buscando componentes específicos ---")
    components_found = 0
    
    for pattern, description in component_patterns:
        matches = test_pattern(section_text, "Componente de Beca", pattern, description)
        if matches:
            components_found += 1
    
    if components_found > 0:
        print(f"\n✅ Se encontraron {components_found} componentes de beca!")
        return True
    else:
        print("\n❌ No se pudieron identificar los componentes de beca específicos.")
        return False

def test_income_thresholds_pattern(text):
    """Prueba patrones para extraer umbrales de renta."""
    patterns = [
        (r'(?:Artículo\s+\d+\.\s+Umbrales de renta|UMBRALES DE RENTA).*?(?=Artículo\s+\d+\.)', 
         "Patrón para sección completa de umbrales de renta"),
        (r'Umbral 1:.*?Familias de .*?euros', 
         "Patrón para Umbral 1 con al menos una familia"),
        (r'Familias de (\w+) miembros?:\s+(\d+[.,]\d+)', 
         "Patrón para cada tamaño de familia")
    ]
    
    print("\n=== PRUEBA DE PATRONES: UMBRALES DE RENTA ===")
    
    # Primero buscar la sección completa
    section_found = False
    section_text = ""
    
    pattern, description = patterns[0]
    matches = test_pattern(text, "Sección de Umbrales", pattern, description)
    if matches and matches[0].strip():
        section_found = True
        section_text = matches[0]
        print("\n✅ Sección de umbrales encontrada!")
            
        # Mostrar las primeras líneas de la sección
        preview_lines = section_text.split('\n')[:10]
        print("\nVista previa de la sección:")
        for line in preview_lines:
            print(f"  {line.strip()}")
            
        if len(section_text.split('\n')) > 10:
            print("  ...")
    
    if not section_found:
        print("\n❌ No se pudo encontrar la sección de umbrales de renta.")
        # Buscar en todo el texto los umbrales específicos
        section_text = text
    
    # Ahora buscar umbrales específicos
    thresholds_found = False
    
    # Probar con patrón para familias
    pattern, description = patterns[2]
    matches = test_pattern(section_text, "Tamaños de familia", pattern, description)
    if matches:
        print(f"\n✅ Se encontraron {len(matches)} tamaños de familia!")
        thresholds_found = True
    
    return thresholds_found

def test_application_deadlines_pattern(text):
    """Prueba patrones para extraer plazos de solicitud."""
    patterns = [
        (r'(?:Los plazos para presentar la solicitud|plazos? de presentación).*?(?:A\).*?B\).*?)(?:\d{1,2}\.|Artículo|$)', 
         "Patrón para sección completa de plazos"),
        (r'A\).*?(\d{1,2}[ \t]+de[ \t]+\w+[ \t]+de[ \t]+\d{4}|El[ \t]+\d{1,2}[ \t]+de[ \t]+\w+[ \t]+de[ \t]+\d{4})', 
         "Patrón para fecha de plazo universitario"),
        (r'B\).*?(\d{1,2}[ \t]+de[ \t]+\w+[ \t]+de[ \t]+\d{4}|El[ \t]+\d{1,2}[ \t]+de[ \t]+\w+[ \t]+de[ \t]+\d{4})', 
         "Patrón para fecha de plazo no universitario")
    ]
    
    print("\n=== PRUEBA DE PATRONES: PLAZOS DE SOLICITUD ===")
    
    # Buscar la sección completa
    section_found = False
    section_text = ""
    
    pattern, description = patterns[0]
    matches = test_pattern(text, "Sección de Plazos", pattern, description)
    if matches and matches[0].strip():
        section_found = True
        section_text = matches[0]
        print("\n✅ Sección de plazos encontrada!")
            
        # Mostrar las primeras líneas de la sección
        preview_lines = section_text.split('\n')[:10]
        print("\nVista previa de la sección:")
        for line in preview_lines:
            print(f"  {line.strip()}")
            
        if len(section_text.split('\n')) > 10:
            print("  ...")
    
    if not section_found:
        print("\n❌ No se pudo encontrar la sección de plazos de solicitud.")
        # Buscar en todo el texto las fechas específicas
        section_text = text
    
    # Ahora buscar fechas específicas
    deadlines_found = 0
    
    for i in range(1, 3):
        pattern, description = patterns[i]
        matches = test_pattern(section_text, "Fecha de Plazo", pattern, description)
        if matches:
            deadlines_found += 1
    
    if deadlines_found > 0:
        print(f"\n✅ Se encontraron {deadlines_found} fechas de plazos!")
        return True
    else:
        print("\n❌ No se pudieron identificar las fechas de plazos específicas.")
        return False

def test_academic_requirements_pattern(text):
    """Prueba patrones para extraer requisitos académicos."""
    patterns = [
        (r'[Pp]ara la concesión de beca.*?primer curso de estudios de grado.*?(\d[,.]\d+).*?puntos', 
         "Patrón para nota mínima de primer curso universitario"),
        (r'[Pp]ara obtener beca los solicitantes de segundos y posteriores cursos.*?deberán haber superado.*?porcentajes', 
         "Patrón para sección de porcentajes por área"),
        (r'([A-Za-záéíóúñÁÉÍÓÚÑ\s\/]+)\s+(\d+)%', 
         "Patrón para área y porcentaje")
    ]
    
    print("\n=== PRUEBA DE PATRONES: REQUISITOS ACADÉMICOS ===")
    
    requirements_found = 0
    
    for pattern, description in patterns:
        matches = test_pattern(text, "Requisito Académico", pattern, description)
        if matches:
            requirements_found += 1
    
    if requirements_found > 0:
        print(f"\n✅ Se encontraron {requirements_found} patrones de requisitos académicos!")
        return True
    else:
        print("\n❌ No se pudieron identificar los requisitos académicos específicos.")
        return False

def interactive_menu(text_files):
    """Muestra un menú interactivo para elegir archivo y patrones."""
    if not text_files:
        print("No se encontraron archivos de texto para analizar.")
        return
    
    # Menú para elegir archivo
    print("\n=== ARCHIVOS DISPONIBLES ===")
    for i, file in enumerate(text_files, 1):
        print(f"{i}. {os.path.basename(file)}")
    
    file_choice = -1
    while file_choice < 1 or file_choice > len(text_files):
        try:
            file_choice = int(input(f"\nSelecciona un archivo (1-{len(text_files)}): "))
        except ValueError:
            print("Por favor, introduce un número válido.")
    
    selected_file = text_files[file_choice - 1]
    print(f"\nArchivo seleccionado: {os.path.basename(selected_file)}")
    
    with open(selected_file, 'r', encoding='utf-8', errors='ignore') as f:
        text = f.read()
    
    print(f"\nLongitud del texto: {len(text)} caracteres")
    print(f"Primeros 200 caracteres: {text[:200].replace(chr(10), ' ')}...")
    
    # Menú para elegir patrones
    while True:
        print("\n=== PATRONES DISPONIBLES ===")
        print("1. Año académico")
        print("2. Montos de becas")
        print("3. Umbrales de renta")
        print("4. Plazos de solicitud")
        print("5. Requisitos académicos")
        print("6. Probar todos los patrones")
        print("7. Seleccionar otro archivo")
        print("8. Salir")
        
        pattern_choice = -1
        while pattern_choice < 1 or pattern_choice > 8:
            try:
                pattern_choice = int(input("\nSelecciona una opción (1-8): "))
            except ValueError:
                print("Por favor, introduce un número válido.")
        
        if pattern_choice == 1:
            test_academic_year_pattern(text)
        elif pattern_choice == 2:
            test_scholarship_amounts_pattern(text)
        elif pattern_choice == 3:
            test_income_thresholds_pattern(text)
        elif pattern_choice == 4:
            test_application_deadlines_pattern(text)
        elif pattern_choice == 5:
            test_academic_requirements_pattern(text)
        elif pattern_choice == 6:
            print("\n======= EJECUTANDO TODAS LAS PRUEBAS DE PATRONES =======")
            test_academic_year_pattern(text)
            test_scholarship_amounts_pattern(text)
            test_income_thresholds_pattern(text)
            test_application_deadlines_pattern(text)
            test_academic_requirements_pattern(text)
        elif pattern_choice == 7:
            return interactive_menu