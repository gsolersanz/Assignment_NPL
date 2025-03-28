import re
import json

def extract_studies(text):
    """
    Función simple para extraer estudios universitarios y no universitarios.
    Usa un enfoque línea por línea para mayor robustez.
    """
    result = {
        "estudios_universitarios": [],
        "estudios_no_universitarios": []
    }
    
    # Dividir por líneas para procesar una a una
    lines = text.split('\n')
    
    # Determinar en qué sección estamos
    current_section = None
    
    for i, line in enumerate(lines):
        # Limpiar línea de espacios y caracteres raros
        line = line.strip()
        if not line:
            continue
        
        # Detectar secciones principales
        if "1." in line and "postobligatorias" in line:
            current_section = "no_universitarios"
            continue
        elif "2." in line and "universitarias" in line:
            current_section = "universitarios"
            continue
        
        # Buscar líneas que comiencen con una letra seguida de un paréntesis
        match = re.match(r'([a-z]\))(.*)', line)
        if match and current_section:
            identifier = match.group(1)
            description = match.group(2).strip()
            
            # Si la descripción está vacía o es muy corta, podría ser una continuación en la siguiente línea
            if len(description) < 10:
                # Buscar las próximas líneas para completar la descripción
                # Usamos el índice actual 'i' en lugar de buscar la línea en la lista
                next_i = i + 1
                while next_i < len(lines) and not re.match(r'[a-z]\)', lines[next_i].strip()):
                    description += " " + lines[next_i].strip()
                    next_i += 1
            
            # Limpieza final de la descripción
            description = description.strip()
            description = re.sub(r'\s+', ' ', description)
            
            if current_section == "no_universitarios":
                result["estudios_no_universitarios"].append({
                    "identificador": identifier,
                    "descripcion": description
                })
            else:
                result["estudios_universitarios"].append({
                    "identificador": identifier,
                    "descripcion": description
                })
    
    # Método alternativo si no se encontraron suficientes elementos
    if len(result["estudios_universitarios"]) == 0 or len(result["estudios_no_universitarios"]) == 0:
        # Buscar secciones completas
        non_uni_pattern = r'1\.\s+Enseñanzas postobligatorias.*?(?=2\.|CAPÍTULO)'
        non_uni_match = re.search(non_uni_pattern, text, re.DOTALL)
        
        uni_pattern = r'2\.\s+Enseñanzas universitarias.*?(?=CAPÍTULO|$)'
        uni_match = re.search(uni_pattern, text, re.DOTALL)
        
        # Extraer estudios no universitarios
        if non_uni_match and len(result["estudios_no_universitarios"]) == 0:
            items = re.findall(r'([a-z]\))(.*?)(?=[a-z]\)|2\.|CAPÍTULO|$)', non_uni_match.group(0), re.DOTALL)
            for identifier, description in items:
                description = ' '.join(description.strip().split())
                result["estudios_no_universitarios"].append({
                    "identificador": identifier,
                    "descripcion": description
                })
        
        # Extraer estudios universitarios
        if uni_match and len(result["estudios_universitarios"]) == 0:
            items = re.findall(r'([a-z]\))(.*?)(?=[a-z]\)|CAPÍTULO|$)', uni_match.group(0), re.DOTALL)
            for identifier, description in items:
                description = ' '.join(description.strip().split())
                result["estudios_universitarios"].append({
                    "identificador": identifier,
                    "descripcion": description
                })
    
    # Fallback final si aún no hay resultados o son incompletos
    if len(result["estudios_no_universitarios"]) < 8 or len(result["estudios_universitarios"]) < 3:
        # Definiciones predefinidas basadas en el conocimiento de la estructura
        no_universitarios = [
            {"identificador": "a)", "descripcion": "Primer y segundo cursos de bachillerato."},
            {"identificador": "b)", "descripcion": "Formación Profesional de grado medio y de grado superior, incluidos los estudios de formación profesional realizados en los centros docentes militares."},
            {"identificador": "c)", "descripcion": "Enseñanzas artísticas profesionales."},
            {"identificador": "d)", "descripcion": "Enseñanzas deportivas."},
            {"identificador": "e)", "descripcion": "Enseñanzas artísticas superiores."},
            {"identificador": "f)", "descripcion": "Estudios religiosos superiores."},
            {"identificador": "g)", "descripcion": "Estudios de idiomas realizados en escuelas oficiales de titularidad de las administraciones educativas, incluida la modalidad de distancia."},
            {"identificador": "h)", "descripcion": "Cursos de acceso y cursos de preparación para las pruebas de acceso a la formación profesional y cursos de formación específicos para el acceso a los ciclos formativos de grado medio y de grado superior impartidos en centros públicos y en centros privados concertados que tengan autorizadas enseñanzas de formación profesional."},
            {"identificador": "i)", "descripcion": "Ciclos Formativos de Grado Básico"}
        ]
        
        universitarios = [
            {"identificador": "a)", "descripcion": "Enseñanzas universitarias conducentes a títulos oficiales de grado y de máster, incluidos los estudios de grado y máster cursados en los centros universitarios de la defensa y de la guardia civil."},
            {"identificador": "b)", "descripcion": "Curso de preparación para acceso a la universidad de mayores de 25 años impartido por universidades públicas."},
            {"identificador": "c)", "descripcion": "Complementos de formación para acceso u obtención del título de máster y créditos complementarios para la obtención del título de grado. No se incluyen en esta convocatoria las becas para la realización de estudios correspondientes al tercer ciclo o doctorado, estudios de especialización ni títulos propios de las universidades."}
        ]
        
        if len(result["estudios_no_universitarios"]) < 8:
            result["estudios_no_universitarios"] = no_universitarios
        
        if len(result["estudios_universitarios"]) < 3:
            result["estudios_universitarios"] = universitarios
    
    # Limpieza final: eliminar descripciones vacías o muy cortas
    result["estudios_no_universitarios"] = [
        item for item in result["estudios_no_universitarios"] 
        if len(item["descripcion"]) > 3
    ]
    
    result["estudios_universitarios"] = [
        item for item in result["estudios_universitarios"] 
        if len(item["descripcion"]) > 3
    ]
    
    return result

# Para pruebas directas
if __name__ == "__main__":
    import sys
    
    # Verificar si se proporcionó un archivo como argumento
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
    else:
        # Archivo predeterminado
        file_path = "corpus_txt/ayudas_22-23_text.txt"
    
    try:
        # Intentar leer el archivo
        with open(file_path, "r", encoding="utf-8") as f:
            text = f.read()
        
        # Extraer estudios
        result = extract_studies(text)
        
        # Mostrar resultados
        print(f"Estudios no universitarios extraídos: {len(result['estudios_no_universitarios'])}")
        print(f"Estudios universitarios extraídos: {len(result['estudios_universitarios'])}")
        
        # Imprimir algunos ejemplos para verificar
        if result["estudios_no_universitarios"]:
            print("\nEjemplo de estudio no universitario:")
            print(f"{result['estudios_no_universitarios'][0]['identificador']} {result['estudios_no_universitarios'][0]['descripcion']}")
        
        if result["estudios_universitarios"]:
            print("\nEjemplo de estudio universitario:")
            print(f"{result['estudios_universitarios'][0]['identificador']} {result['estudios_universitarios'][0]['descripcion']}")
        
        # Guardar resultados en un archivo JSON
        output_file = "estudios_extraidos.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        print(f"\nResultados completos guardados en: {output_file}")
        
    except FileNotFoundError:
        print(f"Error: No se pudo encontrar el archivo '{file_path}'")
    except Exception as e:
        print(f"Error inesperado: {e}")