#!/usr/bin/env python3
"""
Extractor de información sobre becas educativas del Ministerio de Educación
utilizando PyMuPDF (fitz) para la extracción de texto de PDFs.
"""

import os
import re
import json
import fitz  # PyMuPDF
from datetime import datetime

def extract_text_from_pdf(pdf_path):
    """Extrae el texto de un archivo PDF usando PyMuPDF."""
    try:
        doc = fitz.open(pdf_path)
        text = ""
        for page in doc:
            text += page.get_text() + "\n"
        return text
    except Exception as e:
        print(f"Error extrayendo texto de {pdf_path}: {e}")
        return ""

def is_valid_scholarship_pdf(text):
    """Verifica si el PDF es una convocatoria de becas válida con la estructura esperada."""
    # Comprobar patrones clave que debe tener una convocatoria de becas
    key_patterns = [
        r'RESOLUCI[ÓO]N.*BECAS',
        r'Artículo.*?Enseñanzas comprendidas',
        r'Artículo.*?Cuantías de las becas',
        r'Artículo.*?Umbrales de renta'
    ]
    
    # Verificar si al menos 2 de los patrones clave se encuentran
    matches = sum(1 for pattern in key_patterns if re.search(pattern, text, re.IGNORECASE | re.DOTALL))
    return matches >= 2

def extract_academic_year(text):
    """Extrae el año académico del texto."""
    patterns = [
        r'CURSO ACADÉMICO (\d{4}-\d{4})',
        r'curso académico (\d{4}-\d{4})',
        r'para el curso (\d{4}-\d{4})',
        r'BECAS.*?(\d{4}-\d{4})',
        r'BECAS.*?CURSO.*?(\d{4}-\d{4})'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return {
                "year": match.group(1),
                "description": f"Convocatoria de becas para el curso académico {match.group(1)}"
            }
    return None

def extract_eligible_studies(text):
    """Extrae los programas de estudio elegibles con su descripción completa."""
    # Buscar la sección sobre estudios elegibles
    patterns = [
        r'(?:Artículo.*?Enseñanzas comprendidas|ENSEÑANZAS COMPRENDIDAS).*?(?=CAPÍTULO|Artículo\s+\d+[\.\s](?!Enseñanzas))',
        r'Enseñanzas comprendidas.*?(?=CAPÍTULO|Artículo\s+\d+\.)',
        r'Para el curso académico.*?se convocan becas.*?para las siguientes enseñanzas:.*?(?=CAPÍTULO|Artículo\s+\d+\.)'
    ]
    
    result = {
        "description": "Estudios para los que se puede solicitar beca",
        "university_studies": [],
        "non_university_studies": []
    }
    
    studies_section = ""
    for pattern in patterns:
        match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
        if match:
            studies_section = match.group(0)
            break
    
    if studies_section:
        # Extraer la sección para estudios no universitarios
        non_uni_patterns = [
            r'1\.\s+Enseñanzas postobligatorias.*?(?=2\.\s+Enseñanzas|$)',
            r'[Ee]nseñanzas.*?no universitarias.*?(?=[Ee]nseñanzas.*?universitarias|$)'
        ]
        
        for pattern in non_uni_patterns:
            non_uni_match = re.search(pattern, studies_section, re.DOTALL)
            if non_uni_match:
                non_uni_text = non_uni_match.group(0)
                result["non_university_section"] = "Enseñanzas postobligatorias y superiores no universitarias del sistema educativo español"
                
                # Extraer cada tipo de estudio
                study_items = re.findall(r'([a-z]\))([^a-z\)]+)(?=[a-z]\)|$)', non_uni_text, re.DOTALL)
                if study_items:
                    for identifier, description in study_items:
                        result["non_university_studies"].append({
                            "identifier": identifier.strip(),
                            "description": description.strip()
                        })
                # Si no encuentra con el patrón anterior, buscar por líneas
                else:
                    lines = [line.strip() for line in non_uni_text.split('\n') if line.strip()]
                    for i, line in enumerate(lines):
                        if re.match(r'^[a-z]\)', line) or re.match(r'^-', line) or re.match(r'^\d+\.', line):
                            result["non_university_studies"].append({
                                "identifier": f"{i+1})",
                                "description": line.strip()
                            })
                break
        
        # Extraer la sección para estudios universitarios
        uni_patterns = [
            r'2\.\s+Enseñanzas universitarias.*?(?=CAPÍTULO|Artículo|$)',
            r'[Ee]nseñanzas.*?universitarias.*?(?=CAPÍTULO|Artículo|$)'
        ]
        
        for pattern in uni_patterns:
            uni_match = re.search(pattern, studies_section, re.DOTALL)
            if uni_match:
                uni_text = uni_match.group(0)
                result["university_section"] = "Enseñanzas universitarias del sistema universitario español"
                
                # Extraer cada tipo de estudio
                study_items = re.findall(r'([a-z]\))([^a-z\)]+)(?=[a-z]\)|$)', uni_text, re.DOTALL)
                if study_items:
                    for identifier, description in study_items:
                        result["university_studies"].append({
                            "identifier": identifier.strip(),
                            "description": description.strip()
                        })
                # Si no encuentra con el patrón anterior, buscar por líneas
                else:
                    lines = [line.strip() for line in uni_text.split('\n') if line.strip()]
                    for i, line in enumerate(lines):
                        if re.match(r'^[a-z]\)', line) or re.match(r'^-', line) or re.match(r'^\d+\.', line):
                            result["university_studies"].append({
                                "identifier": f"{i+1})",
                                "description": line.strip()
                            })
                break
    
    return result

def extract_scholarship_amounts(text):
    """Extrae los montos de las becas con descripciones completas."""
    # Buscar la sección sobre cuantías de las becas
    patterns = [
        r'(?:Artículo\s+\d+\.\s+Cuantías de las becas|CUANTÍAS DE LAS BECAS).*?(?=Artículo\s+\d+\.)',
        r'Las cuantías de las becas.*?serán las siguientes:.*?(?=Artículo\s+\d+\.)',
        r'cuantías.*?becas.*?serán.*?(?=Artículo\s+\d+\.)'
    ]
    
    amounts_section = ""
    for pattern in patterns:
        match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
        if match:
            amounts_section = match.group(0)
            break
    
    result = {
        "description": "Cuantías y componentes de las becas",
        "components": []
    }
    
    if not amounts_section:
        return result
        
    # Extraer la introducción
    intro_match = re.search(r'Las cuantías.*?serán las siguientes:', amounts_section, re.DOTALL)
    if intro_match:
        result["introduction"] = intro_match.group(0).strip()
    
    # Intentar diferentes patrones para extraer componentes
    # 1. Patrón por letras mayúsculas (A, B, C...)
    components_pattern = r'([A-F]\))([^A-F\)]+)(?=[A-F]\)|$)'
    components = re.findall(components_pattern, amounts_section, re.DOTALL)
    
    # 2. Si no encuentra con el patrón anterior, intentar otro basado en guiones o puntos
    if not components:
        components_pattern = r'[-•]\s*([^-•\n]+?):([^-•]+)(?=[-•]|$)'
        components_raw = re.findall(components_pattern, amounts_section, re.DOTALL)
        components = [(f"{i+1})", desc + ":" + val) for i, (desc, val) in enumerate(components_raw)]
    
    # 3. Si aún no hay componentes, buscar por líneas que contengan "euros"
    if not components:
        euro_lines = re.findall(r'([^\n]+?\d+[,.]\d+\s*euros[^\n]*)', amounts_section)
        components = [(f"{i+1})", line) for i, line in enumerate(euro_lines)]
    
    for identifier, description in components:
        component = {
            "identifier": identifier.strip(),
            "full_description": description.strip(),
            "type": ""
        }
        
        # Extraer el tipo de componente y montos
        if "matrícula" in description.lower():
            component["type"] = "Beca de matrícula"
            component["amount_description"] = "Cobertura del precio público oficial de los servicios académicos universitarios"
        elif "renta" in description.lower():
            component["type"] = "Cuantía fija ligada a la renta"
            amount_match = re.search(r'(\d+[,.]\d+)\s*euros', description)
            if amount_match:
                component["amount"] = amount_match.group(1).replace(',', '.')
                component["amount_description"] = f"{amount_match.group(1)} euros"
        elif "residencia" in description.lower():
            component["type"] = "Cuantía fija ligada a la residencia"
            amount_match = re.search(r'(\d+[,.]\d+)\s*euros', description)
            if amount_match:
                component["amount"] = amount_match.group(1).replace(',', '.')
                component["amount_description"] = f"{amount_match.group(1)} euros"
        elif "excelencia" in description.lower():
            component["type"] = "Cuantía fija ligada a la excelencia académica"
            component["ranges"] = []
            
            # Buscar rangos basados en patrones de puntos
            excellence_ranges = re.findall(r'([Ee]ntre|[Dd]e)\s+(\d+[,.]\d+)\s+y\s+(\d+[,.]\d+).*?(\d+)\s+euros', description)
            for _, min_score, max_score, amount in excellence_ranges:
                component["ranges"].append({
                    "min_score": min_score.replace(',', '.'),
                    "max_score": max_score.replace(',', '.'),
                    "amount": amount,
                    "description": f"Nota media entre {min_score} y {max_score} puntos: {amount} euros"
                })
            
            # Buscar el rango más alto
            highest_match = re.search(r'(\d+[,.]\d+).*?puntos? o más.*?(\d+)\s+euros', description)
            if highest_match:
                component["ranges"].append({
                    "min_score": highest_match.group(1).replace(',', '.'),
                    "max_score": "10.00",
                    "amount": highest_match.group(2),
                    "description": f"Nota media de {highest_match.group(1)} puntos o más: {highest_match.group(2)} euros"
                })
        elif "básica" in description.lower():
            component["type"] = "Beca básica"
            amount_match = re.search(r'(\d+[,.]\d+)\s*euros', description)
            if amount_match:
                component["amount"] = amount_match.group(1).replace(',', '.')
                component["amount_description"] = f"{amount_match.group(1)} euros"
            
            # Buscar casos especiales como Grado Básico
            basic_grade_match = re.search(r'[Gg]rado [Bb]ásico.*?(\d+[,.]\d+) euros', description)
            if basic_grade_match:
                component["special_case"] = {
                    "case": "Ciclos Formativos de Grado Básico",
                    "amount": basic_grade_match.group(1).replace(',', '.'),
                    "description": f"Para Ciclos Formativos de Grado Básico: {basic_grade_match.group(1)} euros"
                }
        elif "variable" in description.lower():
            component["type"] = "Cuantía variable"
            min_match = re.search(r'[Mm]ínimo.*?(\d+[,.]\d+)\s*euros', description)
            if min_match:
                component["minimum_amount"] = min_match.group(1).replace(',', '.')
                component["amount_description"] = f"Mínimo de {min_match.group(1)} euros"
        else:
            # Para componentes no identificados específicamente
            component["type"] = "Otro componente"
            amount_match = re.search(r'(\d+[,.]\d+)\s*euros', description)
            if amount_match:
                component["amount"] = amount_match.group(1).replace(',', '.')
                component["amount_description"] = f"{amount_match.group(1)} euros"
        
        result["components"].append(component)
    
    return result

def extract_income_thresholds(text):
    """Extrae los umbrales de renta familiar con descripciones completas."""
    # Buscar la sección sobre umbrales de renta
    patterns = [
        r'(?:Artículo\s+\d+\.\s+Umbrales de renta|UMBRALES DE RENTA).*?(?=Artículo\s+\d+\.)',
        r'Los umbrales de renta familiar.*?a continuación:.*?(?=Artículo\s+\d+\.)'
    ]
    
    thresholds_section = ""
    for pattern in patterns:
        match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
        if match:
            thresholds_section = match.group(0)
            break
    
    result = {
        "description": "Umbrales de renta familiar aplicables para la concesión de las becas",
        "thresholds": []
    }
    
    if not thresholds_section:
        return result
    
    # Extraer la introducción
    intro_match = re.search(r'Los umbrales de renta familiar aplicables.*?a continuación:', thresholds_section, re.DOTALL)
    if intro_match:
        result["introduction"] = intro_match.group(0).strip()
    
    # Extraer cada umbral
    for threshold_num in range(1, 4):  # Umbrales 1, 2 y 3
        threshold_patterns = [
            rf'{threshold_num}\.\s+Umbral {threshold_num}:(.*?)(?={threshold_num+1}\.\s+Umbral {threshold_num+1}:|Artículo|$)',
            rf'Umbral {threshold_num}:(.*?)(?=Umbral {threshold_num+1}:|Artículo|$)'
        ]
        
        threshold_text = ""
        for pattern in threshold_patterns:
            threshold_match = re.search(pattern, thresholds_section, re.DOTALL)
            if threshold_match:
                threshold_text = threshold_match.group(1)
                break
        
        if threshold_text:
            threshold = {
                "number": threshold_num,
                "family_sizes": []
            }
            
            # Extraer los montos por tamaño familiar
            family_patterns = [
                r'Familias de (\w+) miembros?:\s+(\d+[.,]\d+)',
                r'Familias de (\d+) miembros?:?\s+(\d+[.,]\d+)'
            ]
            
            family_sizes_found = False
            for pattern in family_patterns:
                family_matches = re.findall(pattern, threshold_text)
                if family_matches:
                    for size_text, amount in family_matches:
                        size = convert_text_number(size_text)
                        threshold["family_sizes"].append({
                            "size": size,
                            "amount": amount.replace(',', '.'),
                            "description": f"Familias de {size} miembros: {amount} euros"
                        })
                    family_sizes_found = True
                    break
            
            # Si no encuentra con los patrones anteriores, buscar líneas con números
            if not family_sizes_found:
                for line in threshold_text.split('\n'):
                    amount_match = re.search(r'(\d+)\s*miembros?:?\s+(\d+[.,]\d+)', line)
                    if amount_match:
                        size, amount = amount_match.groups()
                        threshold["family_sizes"].append({
                            "size": size,
                            "amount": amount.replace(',', '.'),
                            "description": f"Familias de {size} miembros: {amount} euros"
                        })
            
            # Extraer información adicional para familias numerosas
            additional_patterns = [
                r'A partir del octavo.*?(\d+[.,]\d+)',
                r'A partir del.*?miembro.*?(\d+[.,]\d+)'
            ]
            
            for pattern in additional_patterns:
                additional_match = re.search(pattern, threshold_text)
                if additional_match:
                    threshold["additional_info"] = {
                        "description": f"A partir del octavo miembro se añadirán {additional_match.group(1)} euros por cada nuevo miembro computable",
                        "amount_per_member": additional_match.group(1).replace(',', '.')
                    }
                    break
            
            if threshold["family_sizes"]:
                result["thresholds"].append(threshold)
    
    return result

def convert_text_number(text):
    """Convierte texto de número a dígitos."""
    text_to_num = {
        "un": "1", "uno": "1",
        "dos": "2",
        "tres": "3",
        "cuatro": "4",
        "cinco": "5",
        "seis": "6",
        "siete": "7",
        "ocho": "8"
    }
    # Si ya es un dígito, devolverlo tal cual
    if text.isdigit():
        return text
    return text_to_num.get(text.lower(), text)

def extract_application_deadlines(text):
    """Extrae los plazos de solicitud con descripciones completas."""
    # Buscar la sección sobre plazos de solicitud
    patterns = [
        r'(?:Artículo\s+\d+\.\s+Lugar y plazo|Los plazos para presentar la solicitud).*?(?=Artículo\s+\d+\.)',
        r'(?:plazos? de presentación|plazos? de solicitud).*?(?=Artículo\s+\d+\.)'
    ]
    
    deadlines_section = ""
    for pattern in patterns:
        match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
        if match:
            deadlines_section = match.group(0)
            break
    
    result = {
        "description": "Plazos para presentar la solicitud de beca",
        "deadlines": []
    }
    
    if not deadlines_section:
        return result
    
    # Extraer la introducción
    intro_patterns = [
        r'Los plazos para presentar la solicitud.*?:',
        r'El plazo.*?:',
        r'Los plazos.*?solicitud.*?:',
        r'Las solicitudes.*?deberán presentarse.*?:'
    ]
    
    for pattern in intro_patterns:
        intro_match = re.search(pattern, deadlines_section, re.DOTALL)
        if intro_match:
            result["introduction"] = intro_match.group(0).strip()
            break
    
    # Extraer plazo para estudiantes universitarios
    uni_deadline = None
    uni_patterns = [
        r'A\)(.*?)(?=B\)|$)',
        r'[Ee]studiantes universitarios.*?(\d{1,2}.*?\d{4})',
        r'[Ee]studiantes universitarios.*?hasta el.*?(\d{1,2}.*?\d{4})'
    ]
    
    for pattern in uni_patterns:
        uni_match = re.search(pattern, deadlines_section, re.DOTALL)
        if uni_match:
            uni_text = uni_match.group(1).strip()
            deadline_match = re.search(r'(\d{1,2}.*?\d{4})', uni_text)
            if deadline_match:
                uni_deadline = deadline_match.group(1).strip()
                result["deadlines"].append({
                    "type": "Estudiantes universitarios",
                    "deadline": uni_deadline,
                    "description": f"Para estudiantes universitarios: hasta el {uni_deadline}"
                })
                break
    
    # Extraer plazo para estudiantes no universitarios
    non_uni_deadline = None
    non_uni_patterns = [
        r'B\)(.*?)(?=\d+\.|Artículo|$)',
        r'[Ee]studiantes no universitarios.*?(\d{1,2}.*?\d{4})',
        r'[Ee]studiantes no universitarios.*?hasta el.*?(\d{1,2}.*?\d{4})'
    ]
    
    for pattern in non_uni_patterns:
        non_uni_match = re.search(pattern, deadlines_section, re.DOTALL)
        if non_uni_match:
            non_uni_text = non_uni_match.group(1).strip()
            deadline_match = re.search(r'(\d{1,2}.*?\d{4})', non_uni_text)
            if deadline_match:
                non_uni_deadline = deadline_match.group(1).strip()
                result["deadlines"].append({
                    "type": "Estudiantes no universitarios",
                    "deadline": non_uni_deadline,
                    "description": f"Para estudiantes no universitarios: hasta el {non_uni_deadline}"
                })
                break
    
    # Extraer información adicional sobre casos excepcionales
    exceptional_patterns = [
        r'Únicamente podrán presentarse solicitudes.*?después de los plazos señalados.*?hasta el (\d{1,2}.*?\d{4}).*?en caso de (.*?)(?=$|Artículo)',
        r'[Ee]xcepcionalmente.*?hasta el (\d{1,2}.*?\d{4}).*?en caso de (.*?)(?=$|Artículo)'
    ]
    
    for pattern in exceptional_patterns:
        exceptional_match = re.search(pattern, deadlines_section, re.DOTALL)
        if exceptional_match:
            result["exceptional_cases"] = {
                "deadline": exceptional_match.group(1).strip(),
                "conditions": exceptional_match.group(2).strip(),
                "description": f"Excepcionalmente hasta el {exceptional_match.group(1).strip()} en caso de {exceptional_match.group(2).strip()}"
            }
            break
    
    return result

def extract_academic_requirements(text):
    """Extrae los requisitos académicos con descripciones completas."""
    # Verificar si hay una sección específica de requisitos académicos
    req_section_patterns = [
        r'(?:Artículo\s+\d+\.\s+Requisitos académicos|REQUISITOS ACADÉMICOS).*?(?=Artículo\s+\d+\.)',
        r'Requisitos de carácter académico.*?(?=Artículo\s+\d+\.)'
    ]
    
    req_section = ""
    for pattern in req_section_patterns:
        section_match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
        if section_match:
            req_section = section_match.group(0)
            break
    
    # Si no se encuentra una sección específica, usar todo el texto
    if not req_section:
        req_section = text
    
    result = {
        "description": "Requisitos académicos para obtener beca",
        "requirements": []
    }
    
    # Requisitos para estudiantes de primer curso de universidad
    first_year_patterns = [
        r'[Pp]ara la concesión de beca a quienes se matriculen por primera vez de primer curso de estudios de grado.*?se requerirá.*?(\d[,.]\d+).*?puntos',
        r'primer curso de estudios de grado.*?(\d[,.]\d+).*?puntos',
        r'primer curso.*?nota.*?(\d[,.]\d+).*?puntos'
    ]
    
    for pattern in first_year_patterns:
        first_year_match = re.search(pattern, req_section, re.DOTALL)
        if first_year_match:
            result["requirements"].append({
                "type": "Primer curso de estudios de grado",
                "grade": first_year_match.group(1).replace(',', '.'),
                "description": f"Para estudiantes de primer curso de grado: nota mínima de {first_year_match.group(1)} puntos"
            })
            break
    
    # Requisitos para estudiantes de cursos posteriores (por rama de conocimiento)
    continuing_patterns = [
        r'[Pp]ara obtener beca los solicitantes de segundos y posteriores cursos.*?deberán haber superado.*?porcentajes.*?Rama o área de conocimiento.*?Porcentaje.*?superar',
        r'segundos y posteriores cursos.*?deberán haber superado'
    ]
    
    for pattern in continuing_patterns:
        continuing_match = re.search(pattern, req_section, re.DOTALL)
        if continuing_match:
            area_text = continuing_match.group(0)
            
            # Extraer las áreas y sus porcentajes
            areas = re.findall(r'([A-Za-záéíóúñÁÉÍÓÚÑ\s\/]+)\s+(\d+)%', area_text)
            
            for area, percentage in areas:
                result["requirements"].append({
                    "type": "Segundos y posteriores cursos",
                    "area": area.strip(),
                    "percentage": percentage,
                    "description": f"{area.strip()}: {percentage}% de créditos superados"
                })
            
            if areas:
                break
    
    # Requisito para estudios de máster
    master_patterns = [
        r'[Ll]os estudiantes de.*?másteres.*?deberán acreditar.*?nota media de (\d[,.]\d+)',
        r'[Pp]ara.*?máster.*?nota.*?(\d[,.]\d+)',
        r'másteres?.*?nota.*?(\d[,.]\d+)'
    ]
    
    for pattern in master_patterns:
        master_match = re.search(pattern, req_section)
        if master_match:
            result["requirements"].append({
                "type": "Estudios de máster",
                "grade": master_match.group(1).replace(',', '.'),
                "description": f"Para estudios de máster: nota media mínima de {master_match.group(1)} puntos"
            })
            break
    
    # Para estudiantes de ciclos formativos
    ciclos_patterns = [
        r'[Pp]ara obtener beca.*?ciclos formativos.*?deberán acreditar haber obtenido (\d[,.]\d+).*?puntos',
        r'ciclos formativos.*?(\d[,.]\d+).*?puntos'
    ]
    
    for pattern in ciclos_patterns:
        ciclos_match = re.search(pattern, req_section)
        if ciclos_match:
            result["requirements"].append({
                "type": "Ciclos formativos",
                "grade": ciclos_match.group(1).replace(',', '.'),
                "description": f"Para ciclos formativos: nota mínima de {ciclos_match.group(1)} puntos"
            })
            break
    
    return result

def analyze_pdf(pdf_path):
    """Analiza un PDF y extrae toda la información relevante sobre becas."""
    print(f"Procesando {pdf_path}...")
    text = extract_text_from_pdf(pdf_path)
    
    # Para depuración, guardar el texto extraído
    debug_path = os.path.splitext(pdf_path)[0] + "_text.txt"
    with open(debug_path, 'w', encoding='utf-8') as f:
        f.write(text)
    print(f"Texto extraído guardado en: {debug_path}")
    
    # Verificar si el PDF tiene la estructura esperada
    if not is_valid_scholarship_pdf(text):
        print(f"Advertencia: {pdf_path} no parece ser una convocatoria de becas válida")
        return {
            "id": os.path.splitext(os.path.basename(pdf_path))[0],
            "filename": os.path.basename(pdf_path),
            "valid": False,
            "error": "El documento no tiene la estructura esperada de una convocatoria de becas",
            "processing_timestamp": datetime.now().isoformat()
        }
    
    # Extraer identificador del archivo sin extensión
    file_id = os.path.splitext(os.path.basename(pdf_path))[0]
    
    # Extraer toda la información relevante
    academic_year = extract_academic_year(text)
    eligible_studies = extract_eligible_studies(text)
    scholarship_amounts = extract_scholarship_amounts(text)
    income_thresholds = extract_income_thresholds(text)
    application_deadlines = extract_application_deadlines(text)
    academic_requirements = extract_academic_requirements(text)
    
    # Crear el resultado estructurado
    result = {
        "id": file_id,
        "filename": os.path.basename(pdf_path),
        "valid": True,
        "academic_year": academic_year,
        "eligible_studies": eligible_studies,
        "scholarship_amounts": scholarship_amounts,
        "income_thresholds": income_thresholds,
        "application_deadlines": application_deadlines,
        "academic_requirements": academic_requirements,
        "processing_timestamp": datetime.now().isoformat()
    }
    
    return result

def process_pdf_corpus(pdf_dir):
    """Procesa todos los PDFs en un directorio y extrae información sobre becas."""
    results = []
    
    for filename in os.listdir(pdf_dir):
        if filename.endswith('.pdf'):
            pdf_path = os.path.join(pdf_dir, filename)
            result = analyze_pdf(pdf_path)
            results.append(result)
    
    return results

def save_to_json(data, output_path):
    """Guarda los datos extraídos en un archivo JSON."""
    with open(output_path, 'w', encoding='utf-8') as file:
        json.dump(data, file, ensure_ascii=False, indent=2)
    print(f"Datos guardados en {output_path}")

def generate_summary(data):
    """Genera un resumen a partir de los datos extraídos."""
    # Filtrar documentos no válidos
    valid_data = [item for item in data if item.get('valid', False)]
    
    if not valid_data:
        return "# Resumen de Becas Educativas\n\nNo se encontraron documentos válidos para analizar."
    
    # Ordenar por año académico
    sorted_data = sorted(valid_data, key=lambda x: x.get('academic_year', {}).get('year', ''))
    
    # Obtener el documento más reciente para el resumen principal
    latest_data = sorted_data[-1]
    
    summary = "# Resumen de Becas Educativas del Ministerio de Educación y Formación Profesional\n\n"
    
    # Sección de información general
    academic_year = latest_data.get('academic_year', {})
    if academic_year:
        summary += f"## Información General\n\n"
        summary += f"{academic_year.get('description', '')}\n\n"
    
    # Sección de estudios elegibles
    eligible_studies = latest_data.get('eligible_studies', {})
    if eligible_studies:
        summary += f"## Estudios Elegibles\n\n"
        summary += f"{eligible_studies.get('description', '')}\n\n"
        
        # Estudios no universitarios
        if 'non_university_studies' in eligible_studies and eligible_studies['non_university_studies']:
            summary += "### Estudios No Universitarios\n\n"
            if 'non_university_section' in eligible_studies:
                summary += f"{eligible_studies['non_university_section']}\n\n"
            
            for study in eligible_studies['non_university_studies']:
                summary += f"- {study.get('description', '')}\n"
            summary += "\n"
        
        # Estudios universitarios
        if 'university_studies' in eligible_studies and eligible_studies['university_studies']:
            summary += "### Estudios Universitarios\n\n"
            if 'university_section' in eligible_studies:
                summary += f"{eligible_studies['university_section']}\n\n"
            
            for study in eligible_studies['university_studies']:
                summary += f"- {study.get('description', '')}\n"
            summary += "\n"
    
    # Sección de cuantías de las becas
    scholarship_amounts = latest_data.get('scholarship_amounts', {})
    if scholarship_amounts:
        summary += f"## Cuantías de las Becas\n\n"
        summary += f"{scholarship_amounts.get('description', '')}\n\n"
        
        if 'introduction' in scholarship_amounts:
            summary += f"{scholarship_amounts['introduction']}\n\n"
        
        for component in scholarship_amounts.get('components', []):
            component_type = component.get('type', '')
            summary += f"### {component_type}\n\n"
            
            if 'amount_description' in component:
                summary += f"{component['amount_description']}\n\n"
            
            # Para componentes con rangos (como la excelencia académica)
            if 'ranges' in component:
                for range_info in component['ranges']:
                    summary += f"- {range_info.get('description', '')}\n"
                summary += "\n"
            
            # Para casos especiales (como la beca básica para grado básico)
            if 'special_case' in component:
                summary += f"**Caso especial**: {component['special_case'].get('description', '')}\n\n"
            
            # Para componentes con fórmulas (como la cuantía variable)
            if 'formula_description' in component:
                summary += f"**Nota**: {component['formula_description']}\n\n"
    
    # Sección de umbrales de renta
    income_thresholds = latest_data.get('income_thresholds', {})
    if income_thresholds:
        summary += f"## Umbrales de Renta Familiar\n\n"
        summary += f"{income_thresholds.get('description', '')}\n\n"
        
        if 'introduction' in income_thresholds:
            summary += f"{income_thresholds['introduction']}\n\n"
        
        for threshold in income_thresholds.get('thresholds', []):
            summary += f"### Umbral {threshold.get('number', '')}\n\n"
            
            for family_size in threshold.get('family_sizes', []):
                summary += f"- {family_size.get('description', '')}\n"
            
            if 'additional_info' in threshold:
                summary += f"\n*{threshold['additional_info'].get('description', '')}*\n"
            
            summary += "\n"
    
    # Sección de plazos de solicitud
    application_deadlines = latest_data.get('application_deadlines', {})
    if application_deadlines:
        summary += f"## Plazos de Solicitud\n\n"
        summary += f"{application_deadlines.get('description', '')}\n\n"
        
        if 'introduction' in application_deadlines:
            summary += f"{application_deadlines['introduction']}\n\n"
        
        for deadline in application_deadlines.get('deadlines', []):
            summary += f"- **{deadline.get('type', '')}**: {deadline.get('description', '')}\n"
        
        if 'exceptional_cases' in application_deadlines:
            summary += f"\n**Casos excepcionales**: {application_deadlines['exceptional_cases'].get('description', '')}\n"
        
        summary += "\n"
    
    # Sección de requisitos académicos
    academic_requirements = latest_data.get('academic_requirements', {})
    if academic_requirements:
        summary += f"## Requisitos Académicos\n\n"
        summary += f"{academic_requirements.get('description', '')}\n\n"
        
        # Agrupar requisitos por tipo
        requirements_by_type = {}
        for req in academic_requirements.get('requirements', []):
            req_type = req.get('type', 'Otros')
            if req_type not in requirements_by_type:
                requirements_by_type[req_type] = []
            requirements_by_type[req_type].append(req)
        
        # Mostrar requisitos agrupados
        for req_type, reqs in requirements_by_type.items():
            summary += f"### {req_type}\n\n"
            for req in reqs:
                summary += f"- {req.get('description', '')}\n"
            summary += "\n"
    
    # Comparación entre años (si hay más de un año)
    if len(sorted_data) > 1:
        summary += "## Evolución de las Becas\n\n"
        summary += "Comparación de las cuantías y requisitos a lo largo de los diferentes cursos académicos:\n\n"
        
        # Comparar cuantías de beca básica
        basic_grants = []
        for item in sorted_data:
            year = item.get('academic_year', {}).get('year', 'N/A')
            for component in item.get('scholarship_amounts', {}).get('components', []):
                if component.get('type', '') == 'Beca básica' and 'amount' in component:
                    basic_grants.append((year, component['amount']))
        
        if len(basic_grants) > 1:
            summary += "### Evolución de la Beca Básica\n\n"
            for year, amount in basic_grants:
                summary += f"- **{year}**: {amount} euros\n"
            summary += "\n"
        
        # Comparar cuantías ligadas a renta
        income_linked = []
        for item in sorted_data:
            year = item.get('academic_year', {}).get('year', 'N/A')
            for component in item.get('scholarship_amounts', {}).get('components', []):
                if component.get('type', '') == 'Cuantía fija ligada a la renta' and 'amount' in component:
                    income_linked.append((year, component['amount']))
        
        if len(income_linked) > 1:
            summary += "### Evolución de la Cuantía Ligada a la Renta\n\n"
            for year, amount in income_linked:
                summary += f"- **{year}**: {amount} euros\n"
            summary += "\n"
        
        # Comparar umbrales de renta (primer umbral, familia de 4 miembros)
        thresholds = []
        for item in sorted_data:
            year = item.get('academic_year', {}).get('year', 'N/A')
            for threshold in item.get('income_thresholds', {}).get('thresholds', []):
                if threshold.get('number') == 1:
                    for family in threshold.get('family_sizes', []):
                        if family.get('size') == '4':
                            thresholds.append((year, family.get('amount', 'N/A')))
        
        if len(thresholds) > 1:
            summary += "### Evolución del Umbral 1 de Renta (Familia de 4 miembros)\n\n"
            for year, amount in thresholds:
                summary += f"- **{year}**: {amount} euros\n"
            summary += "\n"
    
    # Nota final
    summary += "## Notas Adicionales\n\n"
    summary += "- La concesión de las becas está sujeta al cumplimiento de requisitos académicos y económicos establecidos en la convocatoria.\n"
    summary += "- Las solicitudes deben presentarse dentro de los plazos establecidos, aunque no coincidan con el plazo de matrícula.\n"
    summary += "- Para información completa, consulte la convocatoria oficial publicada en el Boletín Oficial del Estado.\n"
    
    return summary

def main():
    """Función principal para procesar el corpus de PDFs."""
    import argparse
    
    # Analizar argumentos de línea de comandos
    parser = argparse.ArgumentParser(description='Extrae información sobre becas de documentos PDF')
    parser.add_argument('--input', '-i', type=str, default='./corpus', help='Directorio que contiene los archivos PDF')
    parser.add_argument('--output', '-o', type=str, default='./output', help='Directorio de salida')
    args = parser.parse_args()
    
    # Crear directorio de salida si no existe
    if not os.path.exists(args.output):
        os.makedirs(args.output)
    
    # Procesar todos los PDFs
    print(f"Procesando archivos PDF de {args.input}...")
    data = process_pdf_corpus(args.input)
    
    # Guardar datos en JSON
    output_json = os.path.join(args.output, "becas_datos.json")
    save_to_json(data, output_json)
    
    # Generar y guardar el resumen
    summary = generate_summary(data)
    summary_path = os.path.join(args.output, "becas_resumen.md")
    with open(summary_path, 'w', encoding='utf-8') as file:
        file.write(summary)
    print(f"Resumen guardado en {summary_path}")
    
    print("¡Procesamiento completado!")

if __name__ == "__main__":
    main()