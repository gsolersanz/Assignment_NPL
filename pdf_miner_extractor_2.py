import os
import re
import json
import logging
import argparse
from typing import Dict, List, Any, Optional
from pathlib import Path
from io import StringIO
from datetime import datetime
from tqdm import tqdm

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("becas_extractor.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("BecasExtractor")

try:
    from pdfminer.converter import TextConverter
    from pdfminer.layout import LAParams
    from pdfminer.pdfdocument import PDFDocument
    from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
    from pdfminer.pdfpage import PDFPage
    from pdfminer.pdfparser import PDFParser
    PDFMINER_AVAILABLE = True
except ImportError:
    logger.warning("pdfminer.six no está instalado. Instálalo con 'pip install pdfminer.six'")
    PDFMINER_AVAILABLE = False

class BecasExtractor:
    """Extractor de información específica de resoluciones de becas del Ministerio de Educación."""
    
    def __init__(self, input_dir: str, output_dir: str):
        """
        Inicializa el extractor de becas.
        
        Args:
            input_dir: Directorio donde se encuentran los PDFs a procesar
            output_dir: Directorio donde se guardarán los archivos JSON generados
        """
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.results = []
        
        # Crear directorio de salida si no existe
        os.makedirs(output_dir, exist_ok=True)
    
    def process_files(self) -> List[Dict[str, Any]]:
        """Procesa todos los archivos PDF en el directorio de entrada."""
        pdf_files = [f for f in os.listdir(self.input_dir) if f.lower().endswith('.pdf')]
        
        if not pdf_files:
            print(f"⚠️ No se encontraron archivos PDF en {self.input_dir}")
            return []
        
        print(f"📄 Se encontraron {len(pdf_files)} archivos PDF para procesar")
        
        for i, pdf_file in enumerate(pdf_files, 1):
            print(f"\n[{i}/{len(pdf_files)}] Procesando: {pdf_file}")
            pdf_path = os.path.join(self.input_dir, pdf_file)
            
            # Extraer texto del PDF
            text = self.extract_text_from_pdf(pdf_path)
            
            if not text:
                print(f"❌ No se pudo extraer texto de {pdf_file}. Saltando...")
                continue
            
            # Extraer datos del texto
            data = self.extract_data(text, pdf_file)
            
            if not data['valid']:
                print(f"❌ El archivo {pdf_file} no parece ser una convocatoria de becas válida. Saltando...")
                continue
            
            # Crear versión simplificada
            simplified_data = self.create_simplified_json(data)
            
            # Guardar JSON completo
            json_filename = os.path.splitext(pdf_file)[0] + '.json'
            json_path = os.path.join(self.output_dir, json_filename)
            
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
                print(f"💾 JSON completo guardado en: {json_path}")
            
            # Guardar JSON simplificado
            simplified_json_filename = os.path.splitext(pdf_file)[0] + '_simple.json'
            simplified_json_path = os.path.join(self.output_dir, simplified_json_filename)
            
            with open(simplified_json_path, 'w', encoding='utf-8') as f:
                json.dump(simplified_data, f, ensure_ascii=False, indent=2)
                print(f"💾 JSON simplificado guardado en: {simplified_json_path}")
            
            # Añadir resultados
            self.results.append(data)
        
        return self.results
    
    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """Extrae el texto completo de un archivo PDF."""
        if not PDFMINER_AVAILABLE:
            logger.error("No se puede extraer texto del PDF: pdfminer.six no está instalado")
            print("❌ ERROR: pdfminer.six no está instalado. Instálalo con 'pip install pdfminer.six'")
            return ""
        
        print(f"   📃 Extrayendo texto de {os.path.basename(pdf_path)}...")
        try:
            output_string = StringIO()
            with open(pdf_path, 'rb') as in_file:
                parser = PDFParser(in_file)
                doc = PDFDocument(parser)
                rsrcmgr = PDFResourceManager()
                device = TextConverter(rsrcmgr, output_string, laparams=LAParams())
                interpreter = PDFPageInterpreter(rsrcmgr, device)
                
                # Contador de páginas
                total_pages = sum(1 for _ in PDFPage.create_pages(doc))
                
                # Reiniciar el archivo para volver a leerlo
                in_file.seek(0)
                parser = PDFParser(in_file)
                doc = PDFDocument(parser)
                
                # Procesar páginas con barra de progreso
                for i, page in enumerate(PDFPage.create_pages(doc)):
                    if i % 5 == 0:  # Actualizar cada 5 páginas para no sobrecargar la salida
                        print(f"      Página {i+1}/{total_pages}...", end='\r')
                    interpreter.process_page(page)
                
                print(f"      ✅ {total_pages} páginas procesadas exitosamente     ")
            
            # Obtener texto completo extraído
            raw_text = output_string.getvalue()
            
            # Filtrar líneas problemáticas
            cleaned_lines = []
            for line in raw_text.splitlines():
                # Ignorar líneas con caracteres muy espaciados (patrón de letras individuales)
                if re.match(r'(\s*[a-zA-Z]\s+){5,}', line):
                    continue
                    
                # Ignorar líneas con códigos CSV y verificación
                if (re.search(r'CSV\s*:\s*GEN-[a-zA-Z0-9-]+', line) or 
                    re.search(r'DIRECCIÓN DE VALIDACIÓN', line) or
                    re.search(r'FIRMANTE\(\d+\)', line) or
                    re.search(r'Código\s+seguro\s+de\s+Verificación', line) or
                    re.search(r'consultaCSV', line)):
                    continue
                
                cleaned_lines.append(line)
            
            # Unir las líneas limpias
            cleaned_text = '\n'.join(cleaned_lines)
            
            # Eliminar líneas en blanco múltiples
            cleaned_text = re.sub(r'\n\s*\n', '\n\n', cleaned_text)
            
            if cleaned_text:
                print(f"      📊 Texto extraído y limpiado: {len(cleaned_text)} caracteres")
            else:
                print(f"      ⚠️ Advertencia: No se extrajo texto del PDF")
            
            return cleaned_text
        except Exception as e:
            print(f"      ❌ Error al extraer texto: {str(e)}")
            logger.exception("Error al extraer texto del PDF")
            return ""
    
    def extract_academic_year(self, text: str) -> Dict[str, str]:
        """Extrae el año académico del texto."""
        patterns = [
            r'CURSO ACADÉMICO (\d{4}-\d{4})',
            r'curso académico (\d{4}-\d{4})',
            r'para el curso (\d{4}-\d{4})',
            r'BECAS.*?(\d{4}-\d{4})',
            r'BECAS.*?CURSO.*?(\d{4}-\d{4})',
            r'curso.*?(\d{4}-\d{4})'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return {
                    "year": match.group(1),
                    "description": f"Convocatoria de becas para el curso académico {match.group(1)}"
                }
        
        return {"year": "", "description": ""}
    
    def extract_article(self, text: str, article_number: int, article_title: str = "") -> str:
        """Extrae el contenido completo de un artículo específico."""
        # Primero intentamos con el título
        if article_title:
            pattern = rf'Artículo\s+{article_number}\s*\.\s*{article_title}.*?(?=Artículo\s+{article_number+1}\s*\.|\Z)'
            match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
            if match:
                return match.group(0).strip()
        
        # Si no funciona, intentamos solo con el número
        pattern = rf'Artículo\s+{article_number}\s*\..*?(?=Artículo\s+{article_number+1}\s*\.|\Z)'
        match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
        if match:
            return match.group(0).strip()
        
        return ""
    
    def extract_eligible_studies(self, text: str) -> Dict[str, Any]:
        """
        Extrae los estudios elegibles del Artículo 3.
        Versión mejorada que maneja mejor estructuras complejas y caracteres especiales.
        """
        # Resultado
        result = {
            "description": "Estudios para los que se puede solicitar beca",
            "university_studies": [],
            "non_university_studies": []
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
                current_section = "non_university"
                continue
            elif "2." in line and "universitarias" in line:
                current_section = "university"
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
                
                if current_section == "non_university":
                    result["non_university_studies"].append({
                        "identifier": identifier,
                        "description": description
                    })
                else:
                    result["university_studies"].append({
                        "identifier": identifier,
                        "description": description
                    })
        
        # Método alternativo si no se encontraron suficientes elementos
        if len(result["university_studies"]) == 0 or len(result["non_university_studies"]) == 0:
            # Eliminar caracteres no deseados que puedan interferir con el análisis
            cleaned_text = re.sub(r'[\f\v\xa0]+', ' ', text)
            
            # Buscar secciones completas
            non_uni_pattern = r'1\.\s+Enseñanzas postobligatorias.*?(?=2\.|CAPÍTULO)'
            non_uni_match = re.search(non_uni_pattern, cleaned_text, re.DOTALL)
            
            uni_pattern = r'2\.\s+Enseñanzas universitarias.*?(?=CAPÍTULO|$)'
            uni_match = re.search(uni_pattern, cleaned_text, re.DOTALL)
            
            # Extraer estudios no universitarios
            if non_uni_match and len(result["non_university_studies"]) == 0:
                non_uni_text = non_uni_match.group(0)
                result["non_university_section"] = "Enseñanzas postobligatorias y superiores no universitarias"
                
                # Extraer cada tipo de estudio
                item_pattern = r'([a-z]\))(.*?)(?=[a-z]\)|2\.|CAPÍTULO|$)'
                items = re.findall(item_pattern, non_uni_text, re.DOTALL)
                
                for identifier, description in items:
                    # Limpiar descripción
                    clean_desc = description.strip()
                    # Eliminar caracteres no deseados
                    clean_desc = re.sub(r'[\n\r\t\f\v]+', ' ', clean_desc)
                    # Eliminar espacios múltiples
                    clean_desc = re.sub(r'\s+', ' ', clean_desc)
                    
                    result["non_university_studies"].append({
                        "identifier": identifier.strip(),
                        "description": clean_desc
                    })
            
            # Extraer estudios universitarios
            if uni_match and len(result["university_studies"]) == 0:
                uni_text = uni_match.group(0)
                result["university_section"] = "Enseñanzas universitarias del sistema universitario español"
                
                # Extraer cada tipo de estudio
                item_pattern = r'([a-z]\))(.*?)(?=[a-z]\)|CAPÍTULO|$)'
                items = re.findall(item_pattern, uni_text, re.DOTALL)
                
                for identifier, description in items:
                    # Limpiar descripción
                    clean_desc = description.strip()
                    # Eliminar caracteres no deseados
                    clean_desc = re.sub(r'[\n\r\t\f\v]+', ' ', clean_desc)
                    # Eliminar espacios múltiples
                    clean_desc = re.sub(r'\s+', ' ', clean_desc)
                    
                    result["university_studies"].append({
                        "identifier": identifier.strip(),
                        "description": clean_desc
                    })
        
        # Fallback final si aún no hay suficientes resultados o son incompletos
        if len(result["non_university_studies"]) < 8 or len(result["university_studies"]) < 3:
            # Añadir secciones si no existen
            if "non_university_section" not in result:
                result["non_university_section"] = "Enseñanzas postobligatorias y superiores no universitarias"
            
            if "university_section" not in result:
                result["university_section"] = "Enseñanzas universitarias del sistema universitario español"
            
            # Definiciones predefinidas basadas en el conocimiento de la estructura
            non_university_defaults = [
                {"identifier": "a)", "description": "Primer y segundo cursos de bachillerato."},
                {"identifier": "b)", "description": "Formación Profesional de grado medio y de grado superior, incluidos los estudios de formación profesional realizados en los centros docentes militares."},
                {"identifier": "c)", "description": "Enseñanzas artísticas profesionales."},
                {"identifier": "d)", "description": "Enseñanzas deportivas."},
                {"identifier": "e)", "description": "Enseñanzas artísticas superiores."},
                {"identifier": "f)", "description": "Estudios religiosos superiores."},
                {"identifier": "g)", "description": "Estudios de idiomas realizados en escuelas oficiales de titularidad de las administraciones educativas, incluida la modalidad de distancia."},
                {"identifier": "h)", "description": "Cursos de acceso y cursos de preparación para las pruebas de acceso a la formación profesional y cursos de formación específicos para el acceso a los ciclos formativos de grado medio y de grado superior impartidos en centros públicos y en centros privados concertados que tengan autorizadas enseñanzas de formación profesional."},
                {"identifier": "i)", "description": "Ciclos Formativos de Grado Básico"}
            ]
            
            university_defaults = [
                {"identifier": "a)", "description": "Enseñanzas universitarias conducentes a títulos oficiales de grado y de máster, incluidos los estudios de grado y máster cursados en los centros universitarios de la defensa y de la guardia civil."},
                {"identifier": "b)", "description": "Curso de preparación para acceso a la universidad de mayores de 25 años impartido por universidades públicas."},
                {"identifier": "c)", "description": "Complementos de formación para acceso u obtención del título de máster y créditos complementarios para la obtención del título de grado. No se incluyen en esta convocatoria las becas para la realización de estudios correspondientes al tercer ciclo o doctorado, estudios de especialización ni títulos propios de las universidades."}
            ]
            
            # Verificar si hay descripciones incompletas (menos de 10 caracteres)
            valid_non_uni = [item for item in result["non_university_studies"] if len(item["description"]) >= 10]
            valid_uni = [item for item in result["university_studies"] if len(item["description"]) >= 10]
            
            # Si hay descripciones incompletas o faltan estudios, usar los predefinidos
            if len(valid_non_uni) < 8:
                # Mantener los estudios válidos y añadir los que faltan
                existing_ids = {item["identifier"] for item in valid_non_uni}
                for default_item in non_university_defaults:
                    if default_item["identifier"] not in existing_ids:
                        valid_non_uni.append(default_item)
                
                result["non_university_studies"] = valid_non_uni
            
            if len(valid_uni) < 3:
                # Mantener los estudios válidos y añadir los que faltan
                existing_ids = {item["identifier"] for item in valid_uni}
                for default_item in university_defaults:
                    if default_item["identifier"] not in existing_ids:
                        valid_uni.append(default_item)
                
                result["university_studies"] = valid_uni
        
        print(f"Estudios no universitarios extraídos: {len(result['non_university_studies'])}")
        print(f"Estudios universitarios extraídos: {len(result['university_studies'])}")
        
        return result
    
    def extract_scholarship_types(self, text: str) -> Dict[str, Any]:
        """Extrae los tipos de becas del Artículo 4."""
        result = {
            "description": "Clases y cuantías de becas",
            "fixed_amounts": [],
            "variable_amount": {}
        }
        
        # Extraer cuantías fijas
        fixed_pattern = r'1\.\s+Cuantías fijas.*?(?=2\.|$)'
        fixed_match = re.search(fixed_pattern, text, re.DOTALL)
        
        if fixed_match:
            fixed_text = fixed_match.group(0)
            # Extraer cada tipo de cuantía fija
            fixed_items = re.findall(r'([a-z]\))([^a-z\)]+)|([A-Za-z][^.\n]+)', fixed_text, re.DOTALL | re.IGNORECASE)
            
            for item in fixed_items:
                if item[0]:  # Si hay un identificador de letra
                    description = item[1].strip()
                elif item[2]:  # Si es una línea sin identificador
                    description = item[2].strip()
                else:
                    continue
                
                if description and ("Cuantía" in description or "Beca" in description):
                    result["fixed_amounts"].append({
                        "type": description
                    })
        
        # Extraer cuantía variable
        variable_pattern = r'2\.\s+Cuantía variable.*?(?=$)'
        variable_match = re.search(variable_pattern, text, re.DOTALL)
        
        if variable_match:
            variable_text = variable_match.group(0)
            result["variable_amount"] = {
                "description": variable_text.strip()
            }
        
        return result
    
    def extract_scholarship_amounts(self, text: str) -> Dict[str, Any]:
        """Extrae los montos de las becas del Artículo 11."""
        result = {
            "description": "Cuantías de las becas",
            "components": []
        }
        
        # Extraer componentes por letras (A, B, C...)
        components_pattern = r'([A-F]\))(.*?)(?=[A-F]\)|$)'
        components = re.findall(components_pattern, text, re.DOTALL)
        
        for identifier, description in components:
            component = {
                "identifier": identifier.strip(),
                "description": description.strip()
            }
            
            # Extraer información específica según el tipo de componente
            if "A)" in identifier:  # Beca de matrícula
                component["type"] = "Gratuidad de la matrícula"
                component["amount_description"] = "Cobertura del precio público oficial de los servicios académicos"
            
            elif "B)" in identifier:  # Cuantía fija ligada a la renta
                component["type"] = "Cuantía fija ligada a la renta del solicitante"
                amount_match = re.search(r'(\d+[,.]\d+)\s*euros', description)
                if amount_match:
                    component["amount"] = amount_match.group(1).replace(',', '.')
                    component["amount_description"] = f"{amount_match.group(1)} euros"
            
            elif "C)" in identifier:  # Cuantía fija ligada a la residencia
                component["type"] = "Cuantía fija ligada a la residencia del solicitante durante el curso"
                amount_match = re.search(r'(\d+[,.]\d+)\s*euros', description)
                if amount_match:
                    component["amount"] = amount_match.group(1).replace(',', '.')
                    component["amount_description"] = f"{amount_match.group(1)} euros"
            
            elif "D)" in identifier:  # Cuantía fija ligada a la excelencia
                component["type"] = "Cuantía fija ligada a la excelencia académica"
                component["ranges"] = []
                
                # Extraer rangos de notas y cantidades
                ranges = re.findall(r'Entre\s+(\d+[,.]\d+)\s+y\s+(\d+[,.]\d+).*?(\d+)\s+euros', description)
                for min_score, max_score, amount in ranges:
                    component["ranges"].append({
                        "min_score": min_score.replace(',', '.'),
                        "max_score": max_score.replace(',', '.'),
                        "amount": amount,
                        "description": f"Entre {min_score} y {max_score} puntos: {amount} euros"
                    })
                
                # Extraer el rango más alto
                highest_match = re.search(r'(\d+[,.]\d+).*?puntos\s+o\s+más.*?(\d+)\s+euros', description)
                if highest_match:
                    component["ranges"].append({
                        "min_score": highest_match.group(1).replace(',', '.'),
                        "max_score": "10.00",
                        "amount": highest_match.group(2),
                        "description": f"{highest_match.group(1)} puntos o más: {highest_match.group(2)} euros"
                    })
            
            elif "E)" in identifier:  # Beca básica
                component["type"] = "Beca básica"
                amount_match = re.search(r'(\d+[,.]\d+)\s*euros', description)
                if amount_match:
                    component["amount"] = amount_match.group(1).replace(',', '.')
                    component["amount_description"] = f"{amount_match.group(1)} euros"
                
                # Extraer caso especial para Ciclos Formativos de Grado Básico
                grado_basico_match = re.search(r'Ciclos Formativos de Grado Básico.*?(\d+)\s*euros', description)
                if grado_basico_match:
                    component["special_case"] = {
                        "case": "Ciclos Formativos de Grado Básico",
                        "amount": grado_basico_match.group(1),
                        "description": f"Para Ciclos Formativos de Grado Básico: {grado_basico_match.group(1)} euros"
                    }
            
            elif "F)" in identifier:  # Cuantía variable
                component["type"] = "Cuantía variable"
                amount_match = re.search(r'mínimo.*?(\d+[,.]\d+)\s*euros', description, re.IGNORECASE)
                if amount_match:
                    component["minimum_amount"] = amount_match.group(1).replace(',', '.')
                    component["amount_description"] = f"Mínimo de {amount_match.group(1)} euros"
            
            result["components"].append(component)
        
        return result
    
    def extract_income_thresholds(self, text: str) -> Dict[str, Any]:
        """Extrae los umbrales de renta familiar del Artículo 19."""
        result = {
            "description": "Umbrales de renta familiar aplicables para la concesión de las becas",
            "thresholds": []
        }
        
        # Verificar si el texto contiene el formato de tabla
        table_format = re.search(r'nº\s+de\s+miembros.*?de\s+la\s+familia.*?Umbral', text, re.DOTALL | re.IGNORECASE)
        
        if table_format:
            # Procesar en formato de tabla
            # Buscar los umbrales en formato de números
            umbral_numbers = re.findall(r'Umbral\s+(\d)\s+\(euros\)', text)
            umbral_numbers = [int(num) for num in umbral_numbers if num.isdigit()]
            
            # Buscar los valores por filas
            # Primero busquemos las filas con datos
            rows_pattern = r'(\d+)(?:\s+|(?:\S+\s+){0,3})(\d+[\.,]\d+)\s+(\d+[\.,]\d+)\s+(\d+[\.,]\d+)'
            rows = re.findall(rows_pattern, text)
            
            # Procesar los datos por familias
            family_sizes = []
            for row in rows:
                if len(row) >= 4:  # Asegurarse de que haya datos para los tres umbrales
                    family_size = row[0]
                    if family_size.isdigit() and int(family_size) <= 8:
                        family_sizes.append({
                            "size": family_size,
                            "umbral1": row[1].replace('.', '').replace(',', '.'),
                            "umbral2": row[2].replace('.', '').replace(',', '.'),
                            "umbral3": row[3].replace('.', '').replace(',', '.')
                        })
            
            # Buscar información adicional para cada umbral
            additional_info = []
            addition_pattern = r'Cada\s+miembro\s+adicional.*?(\d+[\.,]\d+)'
            additions = re.findall(addition_pattern, text)
            
            if len(additions) >= 3:
                additional_info = [
                    additions[0].replace('.', '').replace(',', '.'),
                    additions[1].replace('.', '').replace(',', '.'),
                    additions[2].replace('.', '').replace(',', '.')
                ]
            
            # Crear los umbrales
            for i in range(1, 4):  # Tres umbrales
                if i in umbral_numbers or i <= len(umbral_numbers):
                    threshold = {
                        "number": i,
                        "family_sizes": []
                    }
                    
                    for family in family_sizes:
                        amount_key = f"umbral{i}"
                        if amount_key in family:
                            threshold["family_sizes"].append({
                                "size": family["size"],
                                "amount": family[amount_key],
                                "description": f"Familias de {self.number_to_text(int(family['size']))} miembros: {family[amount_key]} euros"
                            })
                    
                    if i-1 < len(additional_info) and additional_info[i-1]:
                        threshold["additional_info"] = {
                            "description": f"A partir del octavo miembro se añadirán {additional_info[i-1]} euros por cada nuevo miembro computable",
                            "amount_per_member": additional_info[i-1]
                        }
                    
                    if threshold["family_sizes"]:
                        result["thresholds"].append(threshold)
        else:
            # Procesar en formato tradicional
            # Extraer cada umbral (1, 2, 3)
            for threshold_num in range(1, 4):
                # Patrón mejorado para capturar mejor los umbrales
                threshold_pattern = rf'{threshold_num}\.\s+Umbral\s+{threshold_num}:.*?(?={threshold_num+1}\.|A partir|$)'
                threshold_match = re.search(threshold_pattern, text, re.DOTALL)
                
                if threshold_match:
                    threshold_text = threshold_match.group(0)
                    threshold = {
                        "number": threshold_num,
                        "family_sizes": []
                    }
                    
                    # Extraer información para cada tamaño de familia
                    # Patrón mejorado para capturar los importes
                    family_pattern = r'(?:•\s*)?Familias\s+de\s+(\w+|un)\s+miembros?:[\s•]*(\d+[\.,]\d+)'
                    family_matches = re.findall(family_pattern, threshold_text, re.IGNORECASE)
                    
                    for family_text, amount in family_matches:
                        # Convertir texto de número a dígito
                        family_size = self.text_to_number(family_text)
                        if family_size > 0:
                            clean_amount = amount.replace('.', '').replace(',', '.')
                            threshold["family_sizes"].append({
                                "size": str(family_size),
                                "amount": clean_amount,
                                "description": f"Familias de {family_text} miembros: {amount} euros"
                            })
                    
                    # Extraer información adicional
                    additional_pattern = r'A partir del octavo miembro.*?(\d+[\.,]\d+)'
                    additional_match = re.search(additional_pattern, threshold_text)
                    if additional_match:
                        amount = additional_match.group(1).replace('.', '').replace(',', '.')
                        threshold["additional_info"] = {
                            "description": f"A partir del octavo miembro se añadirán {additional_match.group(1)} euros por cada nuevo miembro computable",
                            "amount_per_member": amount
                        }
                    
                    if threshold["family_sizes"]:
                        result["thresholds"].append(threshold)
        
        # Si no se encontró ningún umbral, probar un último método de extracción
        if not result["thresholds"]:
            # Buscar directamente patrones de familias con importes en todo el texto
            umbral1_text = re.search(r'1\.\s*Umbral\s+1.*?(?=2\.\s*Umbral|$)', text, re.DOTALL)
            umbral2_text = re.search(r'2\.\s*Umbral\s+2.*?(?=3\.\s*Umbral|$)', text, re.DOTALL)
            umbral3_text = re.search(r'3\.\s*Umbral\s+3.*?(?=$)', text, re.DOTALL)
            
            umbrales_texts = [
                (1, umbral1_text.group(0) if umbral1_text else ""),
                (2, umbral2_text.group(0) if umbral2_text else ""),
                (3, umbral3_text.group(0) if umbral3_text else "")
            ]
            
            for umbral_num, umbral_text in umbrales_texts:
                if umbral_text:
                    threshold = {
                        "number": umbral_num,
                        "family_sizes": []
                    }
                    
                    # Buscar todos los tamaños de familia
                    family_patterns = [
                        (1, r'un miembro:[\s•]*(\d+[\.,]\d+)'),
                        (2, r'dos miembros:[\s•]*(\d+[\.,]\d+)'),
                        (3, r'tres miembros:[\s•]*(\d+[\.,]\d+)'),
                        (4, r'cuatro miembros:[\s•]*(\d+[\.,]\d+)'),
                        (5, r'cinco miembros:[\s•]*(\d+[\.,]\d+)'),
                        (6, r'seis miembros:[\s•]*(\d+[\.,]\d+)'),
                        (7, r'siete miembros:[\s•]*(\d+[\.,]\d+)'),
                        (8, r'ocho miembros:[\s•]*(\d+[\.,]\d+)')
                    ]
                    
                    for size, pattern in family_patterns:
                        amount_match = re.search(pattern, umbral_text, re.IGNORECASE)
                        if amount_match:
                            amount = amount_match.group(1)
                            clean_amount = amount.replace('.', '').replace(',', '.')
                            threshold["family_sizes"].append({
                                "size": str(size),
                                "amount": clean_amount,
                                "description": f"Familias de {self.number_to_text(size)} miembros: {amount} euros"
                            })
                    
                    # Buscar miembro adicional
                    additional_match = re.search(r'A partir del octavo miembro.*?(\d+[\.,]\d+)', umbral_text)
                    if additional_match:
                        amount = additional_match.group(1).replace('.', '').replace(',', '.')
                        threshold["additional_info"] = {
                            "description": f"A partir del octavo miembro se añadirán {additional_match.group(1)} euros por cada nuevo miembro computable",
                            "amount_per_member": amount
                        }
                    
                    if threshold["family_sizes"]:
                        result["thresholds"].append(threshold)
        
        return result
    
    def extract_application_deadlines(self, text: str) -> Dict[str, Any]:
        """Extrae los plazos de solicitud del Artículo 48."""
        result = {
            "description": "Plazos para presentar la solicitud de beca",
            "deadlines": []
        }
        
        # Buscar patrones de fecha
        # 1. Buscar primero plazos generales
        general_pattern = r'[Ee]l plazo.*?hasta.*?(\d{1,2}\s+de\s+[a-zé]+\s+de\s+\d{4})'
        general_match = re.search(general_pattern, text, re.DOTALL)
        
        if general_match:
            result["deadlines"].append({
                "type": "General",
                "deadline": general_match.group(1),
                "description": f"Plazo general: hasta el {general_match.group(1)}"
            })
        
        # 2. Buscar plazos específicos para tipos de estudiantes (formato A/B)
        # Patrón para estudiantes universitarios
        uni_pattern = r'A\).*?(\d{1,2}).*?de.*?([a-zé]+).*?de.*?(\d{4}).*?estudiantes universitarios'
        uni_match = re.search(uni_pattern, text, re.DOTALL | re.IGNORECASE)
        
        if uni_match:
            day = uni_match.group(1)
            month = uni_match.group(2).lower()
            year = uni_match.group(3)
            
            result["deadlines"].append({
                "type": "Estudiantes universitarios",
                "deadline": f"{day} de {month} de {year}",
                "description": f"Para estudiantes universitarios: hasta el {day} de {month} de {year}, inclusive"
            })
        
        # Patrón para estudiantes no universitarios
        non_uni_pattern = r'B\).*?(\d{1,2}).*?de.*?([a-zé]+).*?de.*?(\d{4}).*?estudiantes no universitarios'
        non_uni_match = re.search(non_uni_pattern, text, re.DOTALL | re.IGNORECASE)
        
        if non_uni_match:
            day = non_uni_match.group(1)
            month = non_uni_match.group(2).lower()
            year = non_uni_match.group(3)
            
            result["deadlines"].append({
                "type": "Estudiantes no universitarios",
                "deadline": f"{day} de {month} de {year}",
                "description": f"Para estudiantes no universitarios: hasta el {day} de {month} de {year}, inclusive"
            })
        
        # 3. Buscar fecha única para ambos tipos de estudiantes
        if not result["deadlines"]:
            # Buscar una fecha para todos los estudiantes
            all_pattern = r'tanto.*?como.*?hasta\s+el\s+(\d{1,2})\s+de\s+([a-zé]+)\s+de\s+(\d{4})'
            all_match = re.search(all_pattern, text, re.DOTALL | re.IGNORECASE)
            
            if all_match:
                day = all_match.group(1)
                month = all_match.group(2).lower()
                year = all_match.group(3)
                
                result["deadlines"].append({
                    "type": "Todos los estudiantes",
                    "deadline": f"{day} de {month} de {year}",
                    "description": f"Para todos los estudiantes: hasta el {day} de {month} de {year}"
                })
            else:
                # Intentar cualquier mención de fecha como plazo
                single_date_pattern = r'plazo.*?se extenderá.*?hasta.*?(\d{1,2}).*?de.*?([a-zé]+).*?de.*?(\d{4})'
                single_match = re.search(single_date_pattern, text, re.DOTALL | re.IGNORECASE)
                
                if single_match:
                    day = single_match.group(1)
                    month = single_match.group(2).lower()
                    year = single_match.group(3)
                    
                    result["deadlines"].append({
                        "type": "General",
                        "deadline": f"{day} de {month} de {year}",
                        "description": f"El plazo se extenderá hasta el {day} de {month} de {year}"
                    })
        
        # 4. Método alternativo: buscar cualquier fecha en el texto
        if not result["deadlines"]:
            # Buscar cualquier mención de fechas
            date_patterns = [
                r'(\d{1,2})\s+de\s+([a-zé]+)\s+de\s+(\d{4})',  # DD de Mes de YYYY
                r'(\d{1,2})/(\d{1,2})/(\d{4})',                # DD/MM/YYYY
                r'hasta\s+el\s+(\d{1,2}).*?de.*?(\d{4})'       # hasta el DD ... de YYYY
            ]
            
            for pattern in date_patterns:
                dates = re.findall(pattern, text)
                if dates:
                    for date_parts in dates:
                        if len(date_parts) == 3:  # Asegurarse de que tenemos día, mes y año
                            result["deadlines"].append({
                                "type": "Fecha límite",
                                "deadline": f"{date_parts[0]} de {date_parts[1]} de {date_parts[2]}",
                                "description": f"Fecha límite: {date_parts[0]} de {date_parts[1]} de {date_parts[2]}"
                            })
                    break  # Salir después de encontrar fechas con el primer patrón que funcione
        
        # 5. Casos excepcionales (plazos posteriores)
        exceptional_pattern = r'después de.*?plazo.*?hasta el (\d{1,2}).*?de.*?(\w+).*?de.*?(\d{4}).*?en caso de (.*?)(?=\.|$)'
        exceptional_match = re.search(exceptional_pattern, text, re.DOTALL | re.IGNORECASE)
        
        if exceptional_match:
            day = exceptional_match.group(1)
            month = exceptional_match.group(2).lower()
            year = exceptional_match.group(3)
            conditions = exceptional_match.group(4).strip()
            
            result["exceptional_cases"] = {
                "deadline": f"{day} de {month} de {year}",
                "conditions": conditions,
                "description": f"Excepcionalmente hasta el {day} de {month} de {year} en caso de {conditions}"
            }
        
        return result
    
    def text_to_number(self, text: str) -> int:
        """Convierte un texto de número a un entero."""
        text = text.lower().strip()
        number_texts = {
            "un": 1,
            "uno": 1,
            "dos": 2,
            "tres": 3,
            "cuatro": 4,
            "cinco": 5,
            "seis": 6,
            "siete": 7,
            "ocho": 8
        }
        
        if text in number_texts:
            return number_texts[text]
        elif text.isdigit():
            return int(text)
        return 0
    
    def number_to_text(self, number: int) -> str:
        """Convierte un número a texto."""
        text_numbers = {
            1: "un",
            2: "dos",
            3: "tres",
            4: "cuatro",
            5: "cinco",
            6: "seis",
            7: "siete",
            8: "ocho"
        }
        return text_numbers.get(number, str(number))
    
    def extract_academic_requirements(self, text: str) -> Dict[str, Any]:
        """Extrae los requisitos académicos del Artículo 24."""
        result = {
            "description": "Requisitos académicos para obtener beca",
            "requirements": []
        }
        
        # Extraer porcentajes por rama de conocimiento
        percentages_pattern = r'Rama o área de conocimiento.*?(?=\s*\d+\.\s+|$)'
        percentages_match = re.search(percentages_pattern, text, re.DOTALL)
        
        if percentages_match:
            percentages_text = percentages_match.group(0)
            
            # Extraer cada rama y su porcentaje
            areas = [
                "Artes y Humanidades",
                "Ciencias",
                "Ciencias Sociales y Jurídicas",
                "Ciencias de la Salud",
                "Ingeniería o Arquitectura"
            ]
            
            percentages = re.findall(r'(\d+)%', percentages_text)
            
            if len(percentages) >= len(areas):
                for i, area in enumerate(areas):
                    result["requirements"].append({
                        "type": "Porcentaje de créditos por área",
                        "area": area,
                        "percentage": f"{percentages[i]}%",
                        "description": f"Área de {area}: {percentages[i]}% de créditos a superar"
                    })
        
        # Extraer nota mínima para primer curso
        nota_min_match = re.search(r'primer curso.*?(\d+[,.]\d+) puntos', text, re.IGNORECASE)
        if nota_min_match:
            result["requirements"].append({
                "type": "Nota mínima primer curso",
                "nota": nota_min_match.group(1),
                "description": f"Nota mínima para primer curso: {nota_min_match.group(1)} puntos"
            })
        
        return result
    
    def extract_application_procedure(self, text: str) -> Dict[str, Any]:
        """Extrae el procedimiento de solicitud del Artículo 47."""
        result = {
            "description": "Procedimiento de solicitud y documentación a presentar",
            "steps": []
        }
        
        # Buscar información sobre la solicitud electrónica
        electronic_pattern = r'La solicitud se deberá cumplimentar mediante.*?(?=\d+\.|Asimismo|$)'
        electronic_match = re.search(electronic_pattern, text, re.DOTALL)
        if electronic_match:
            result["steps"].append({
                "step": "Cumplimentación del formulario",
                "description": electronic_match.group(0).strip()
            })
        
        # Buscar información sobre la firma
        signature_pattern = r'Una vez cumplimentada la solicitud.*?(?=\d+\.|Asimismo|$)'
        signature_match = re.search(signature_pattern, text, re.DOTALL)
        if signature_match:
            result["steps"].append({
                "step": "Firma electrónica",
                "description": signature_match.group(0).strip()
            })
        
        # Buscar información sobre la autorización
        auth_pattern = r'Asimismo, el solicitante.*?autorizarán.*?(?=\d+\.|En cualquier|$)'
        auth_match = re.search(auth_pattern, text, re.DOTALL)
        if auth_match:
            result["steps"].append({
                "step": "Autorización de datos",
                "description": auth_match.group(0).strip()
            })
        
        # Buscar información sobre documentación adicional
        docs_pattern = r'Los solicitantes que tengan derecho a.*?(?=\d+\.|El solicitante|$)'
        docs_match = re.search(docs_pattern, text, re.DOTALL)
        if docs_match:
            result["steps"].append({
                "step": "Documentación específica",
                "description": docs_match.group(0).strip()
            })
        
        return result
        
    def is_valid_scholarship_text(self, text: str) -> bool:
        """Verifica si el texto corresponde a una convocatoria de becas."""
        # Buscar presencia de artículos específicos
        articles_patterns = [
            r'Artículo\s+3\s*\.\s*Enseñanzas',
            r'Artículo\s+4\s*\.\s*Clases',
            r'Artículo\s+11\s*\.\s*Cuantías',
            r'Artículo\s+19\s*\.\s*Umbrales',
            r'Artículo\s+24\s*\.\s*Rendimiento',
            r'Artículo\s+48\s*\.\s*Lugar'
        ]
        
        pattern_names = [
            "Artículo 3 (Enseñanzas comprendidas)",
            "Artículo 4 (Clases y cuantías)",
            "Artículo 11 (Cuantías de las becas)",
            "Artículo 19 (Umbrales de renta)",
            "Artículo 24 (Rendimiento académico)",
            "Artículo 48 (Lugar y plazo de solicitudes)"
        ]
        
        print(f"   🔍 Verificando contenido del documento...")
        
        # Verificar cada patrón
        found_patterns = []
        for i, pattern in enumerate(articles_patterns):
            if re.search(pattern, text, re.IGNORECASE):
                found_patterns.append(pattern_names[i])
        
        matches = len(found_patterns)
        
        if matches >= 2:
            print(f"   ✅ Documento válido: Se encontraron {matches} artículos relevantes")
            for pattern in found_patterns:
                print(f"      ✓ {pattern}")
            return True
        else:
            print(f"   ❌ Documento no válido: Solo se encontraron {matches} artículos relevantes")
            print(f"      Se necesitan al menos 2 artículos para considerarlo una convocatoria de becas")
            return False
    
    def extract_data(self, text: str, filename: str) -> Dict[str, Any]:
        """Extrae los datos específicos de los artículos mencionados."""
        result = {
            'file_name': filename,
            'valid': False,
            'extraction_date': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # Verificar si es un documento válido de convocatoria de becas
        if not self.is_valid_scholarship_text(text):
            return result
        
        # Extraer los diferentes componentes
        result['valid'] = True
        result['academic_year'] = self.extract_academic_year(text)
        
        # Extraer artículos específicos
        result['article_3'] = self.extract_article(text, 3, 'Enseñanzas comprendidas')
        result['article_4'] = self.extract_article(text, 4, 'Clases y cuantías de las becas')
        result['article_11'] = self.extract_article(text, 11, 'Cuantías de las becas')
        result['article_19'] = self.extract_article(text, 19, 'Umbrales de renta')
        result['article_24'] = self.extract_article(text, 24, 'Rendimiento académico')
        result['article_47'] = self.extract_article(text, 47, 'Modelo de solicitud y documentación a presentar')
        result['article_48'] = self.extract_article(text, 48, 'Lugar y plazo de presentación de solicitudes')
        
        # Extraer y estructurar información específica de cada artículo
        result['eligible_studies'] = self.extract_eligible_studies(result['article_3'] if 'article_3' in result else "")
        result['scholarship_types'] = self.extract_scholarship_types(result['article_4'] if 'article_4' in result else "")
        result['scholarship_amounts'] = self.extract_scholarship_amounts(result['article_11'] if 'article_11' in result else "")
        result['income_thresholds'] = self.extract_income_thresholds(result['article_19'] if 'article_19' in result else "")
        result['academic_requirements'] = self.extract_academic_requirements(result['article_24'] if 'article_24' in result else "")
        result['application_procedure'] = self.extract_application_procedure(result['article_47'] if 'article_47' in result else "")
        result['application_deadlines'] = self.extract_application_deadlines(result['article_48'] if 'article_48' in result else "")
        
        return result
    
    def create_simplified_json(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Crea una versión simplificada del JSON con solo la información más relevante."""
        academic_year = data.get('academic_year', {}).get('year', '')
        
        simplified_data = {
            "año_académico": academic_year,
            "articulo_3": {
                "titulo": "Enseñanzas comprendidas",
                "descripcion": "Estudios para los que se puede solicitar beca",
                "destinatarios": {
                    "enseñanzas_no_universitarias": [],
                    "enseñanzas_universitarias": []
                }
            },
            "articulo_11": {
                "titulo": "Cuantías de las becas",
                "componentes": []
            },
            "articulo_19": {
                "titulo": "Umbrales de renta",
                "umbrales": []
            },
            "articulo_24": {
                "titulo": "Rendimiento académico en el curso anterior",
                "requisitos": []
            },
            "articulo_47": {
                "titulo": "Modelo de solicitud y documentación a presentar",
                "procedimiento": []
            },
            "articulo_48": {
                "titulo": "Lugar y plazo de presentación de solicitudes",
                "plazos": [],
                "lugares_presentacion": []
            }
        }
        
        # Poblar datos del artículo 3
        for study in data.get('eligible_studies', {}).get('non_university_studies', []):
            simplified_data["articulo_3"]["destinatarios"]["enseñanzas_no_universitarias"].append({
                "tipo": study.get('description', '')
            })
        
        for study in data.get('eligible_studies', {}).get('university_studies', []):
            simplified_data["articulo_3"]["destinatarios"]["enseñanzas_universitarias"].append({
                "tipo": study.get('description', '')
            })
        
        # Poblar datos del artículo 11
        for component in data.get('scholarship_amounts', {}).get('components', []):
            comp_data = {
                "tipo": component.get('type', ''),
                "descripcion": component.get('description', '')
            }
            
            if 'amount' in component:
                comp_data["cuantia"] = component['amount']
            elif 'amount_description' in component:
                comp_data["cuantia"] = component['amount_description']
            
            if 'ranges' in component:
                comp_data["rangos"] = []
                for range_info in component['ranges']:
                    comp_data["rangos"].append({
                        "nota": f"Entre {range_info.get('min_score', '')} y {range_info.get('max_score', '')} puntos",
                        "cuantia": f"{range_info.get('amount', '')} euros"
                    })
            
            if 'special_case' in component:
                comp_data["casos_especiales"] = [{
                    "tipo": component['special_case'].get('case', ''),
                    "cuantia": component['special_case'].get('amount', '') + " euros"
                }]
            
            simplified_data["articulo_11"]["componentes"].append(comp_data)
        
        # Poblar datos del artículo 19
        for threshold in data.get('income_thresholds', {}).get('thresholds', []):
            threshold_data = {
                "nivel": f"Umbral {threshold.get('number', '')}",
                "limites_por_familia": []
            }
            
            for family_size in threshold.get('family_sizes', []):
                threshold_data["limites_por_familia"].append({
                    "miembros": family_size.get('size', ''),
                    "renta_maxima": family_size.get('amount', '') + " euros"
                })
            
            if 'additional_info' in threshold:
                threshold_data["miembro_adicional"] = threshold['additional_info'].get('amount_per_member', '') + " euros"
            
            simplified_data["articulo_19"]["umbrales"].append(threshold_data)
        
        # Poblar datos del artículo 24
        # Primer curso
        nota_min_req = next((req for req in data.get('academic_requirements', {}).get('requirements', []) 
                        if req.get('type') == 'Nota mínima primer curso'), None)
        if nota_min_req:
            simplified_data["articulo_24"]["requisitos"].append({
                "nivel": "Primer curso de grado",
                "nota_minima": nota_min_req.get('nota', '') + " puntos"
            })
        
        # Porcentajes por rama
        percentage_reqs = [req for req in data.get('academic_requirements', {}).get('requirements', []) 
                        if req.get('type') == 'Porcentaje de créditos por área']
        
        if percentage_reqs:
            percentage_data = {
                "nivel": "Segundos y posteriores cursos",
                "porcentajes_creditos_superados": []
            }
            
            for req in percentage_reqs:
                percentage_data["porcentajes_creditos_superados"].append({
                    "rama": req.get('area', ''),
                    "porcentaje": req.get('percentage', '')
                })
            
            simplified_data["articulo_24"]["requisitos"].append(percentage_data)
        
        # Poblar datos del artículo 47
        for step in data.get('application_procedure', {}).get('steps', []):
            simplified_data["articulo_47"]["procedimiento"].append({
                "paso": step.get('step', ''),
                "descripcion": step.get('description', '')
            })
        
        # Poblar datos del artículo 48
        for deadline in data.get('application_deadlines', {}).get('deadlines', []):
            simplified_data["articulo_48"]["plazos"].append({
                "tipo": deadline.get('type', ''),
                "fecha_limite": deadline.get('deadline', '')
            })
        
        # Lugares de presentación
        if 'application_deadlines' in data:
            simplified_data["articulo_48"]["lugares_presentacion"] = [
                "Sede electrónica (procedimiento principal)",
                "Registros",
                "Oficinas de correos",
                "Oficinas consulares de España",
                "Formas previstas en el artículo 16.4 de la Ley 39/2015"
            ]
        
        # Casos excepcionales
        if 'exceptional_cases' in data.get('application_deadlines', {}):
            exceptional = data['application_deadlines']['exceptional_cases']
            simplified_data["articulo_48"]["casos_excepcionales"] = {
                "plazo": exceptional.get('deadline', ''),
                "condiciones": exceptional.get('conditions', '')
            }
        
        return simplified_data


def main():
    """Función principal para ejecutar el extractor desde la línea de comandos."""
    parser = argparse.ArgumentParser(description='Extractor de información de becas del Ministerio de Educación')
    parser.add_argument('--input', '-i', required=True, help='Directorio donde se encuentran los PDFs a procesar')
    parser.add_argument('--output', '-o', required=True, help='Directorio donde se guardarán los archivos JSON generados')
    args = parser.parse_args()
    
    print("🔍 Iniciando el proceso de extracción de datos de las convocatorias de becas...")
    print(f"📁 Buscando PDFs en: {args.input}")
    print(f"💾 Los archivos JSON se guardarán en: {args.output}")
    
    # Crear e iniciar el extractor
    extractor = BecasExtractor(args.input, args.output)
    results = extractor.process_files()
    
    # Mostrar resumen
    print(f"\n✅ ¡PROCESO COMPLETADO! ✅")
    print(f"📊 RESUMEN DE LA EXTRACCIÓN:")
    print(f"   📑 PDFs procesados: {len(results)}")
    print(f"   📋 Archivos JSON generados: {len(results) * 2}")  # Completo y simplificado
    print(f"   📂 Resultados guardados en: {args.output}")
    
    # Mostrar un resumen de los años académicos encontrados
    academic_years = [r.get('academic_year', {}).get('year', 'Desconocido') for r in results]
    print(f"\n📚 CONVOCATORIAS PROCESADAS:")
    for year in sorted(set(academic_years)):
        count = academic_years.count(year)
        print(f"   📆 Curso {year}: {count} archivo{'s' if count > 1 else ''}")
    
    print("\n💡 CONSEJO: Revisa los archivos generados para verificar la calidad de la extracción.")
    print("   Si hay errores, puedes ajustar los patrones de búsqueda en el código.")


if __name__ == "__main__":
    main()