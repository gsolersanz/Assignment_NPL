import os
import re
import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("becas_extractor.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("BecasExtractor")

import os
import re
import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("becas_extractor.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("BecasExtractor")

class BecasExtractor:
    """Extractor de información específica de artículos de becas del Ministerio de Educación."""
    
    def __init__(self):
        self.results = []
    
    def process_files(self, input_dir: str) -> List[Dict[str, Any]]:
        """Procesa todos los archivos en el directorio de entrada."""
        if not os.path.exists(input_dir):
            logger.error(f"El directorio {input_dir} no existe")
            return []
        
        files = [f for f in os.listdir(input_dir) if f.endswith('.txt') or f.endswith('.pdf')]
        logger.info(f"Se encontraron {len(files)} archivos para procesar")
        
        for file_name in files:
            file_path = os.path.join(input_dir, file_name)
            logger.info(f"Procesando archivo: {file_name}")
            
            try:
                # Para archivos PDF, primero convertirlos a texto
                if file_name.endswith('.pdf'):
                    try:
                        import PyPDF2
                        with open(file_path, 'rb') as pdf_file:
                            # Usar PdfReader en lugar de PdfFileReader
                            pdf_reader = PyPDF2.PdfReader(pdf_file)
                            text = ""
                            for page_num in range(len(pdf_reader.pages)):
                                text += pdf_reader.pages[page_num].extract_text()
                    except ImportError:
                        logger.error("PyPDF2 no está instalado. No se pueden procesar archivos PDF.")
                        continue
                else:
                    with open(file_path, 'r', encoding='utf-8') as file:
                        text = file.read()
                    
                result = self.extract_data(text, file_name)
                if result['valid']:
                    self.results.append(result)
                    logger.info(f"Extracción exitosa para: {file_name}")
                else:
                    logger.warning(f"El archivo {file_name} no contiene datos válidos de convocatoria de becas")
            except Exception as e:
                logger.error(f"Error al procesar {file_name}: {str(e)}")
        
        return self.results
    
    def extract_data(self, text: str, file_name: str) -> Dict[str, Any]:
        """Extrae los datos específicos de los artículos mencionados."""
        result = {
            'file_name': file_name,
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
        result['article_48'] = self.extract_article(text, 48, 'Lugar y plazo de presentación de solicitudes')
        
        # Extraer y estructurar información específica de cada artículo
        result['eligible_studies'] = self.extract_eligible_studies(result['article_3'] if 'article_3' in result else "")
        result['scholarship_types'] = self.extract_scholarship_types(result['article_4'] if 'article_4' in result else "")
        result['scholarship_amounts'] = self.extract_scholarship_amounts(result['article_11'] if 'article_11' in result else "")
        result['income_thresholds'] = self.extract_income_thresholds(result['article_19'] if 'article_19' in result else "")
        result['academic_requirements'] = self.extract_academic_requirements(result['article_24'] if 'article_24' in result else "")
        result['application_deadlines'] = self.extract_application_deadlines(result['article_48'] if 'article_48' in result else "")
        
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
        
        matches = sum(1 for pattern in articles_patterns if re.search(pattern, text, re.IGNORECASE))
        return matches >= 2  # Si al menos hay 2 artículos, consideramos que es un documento válido
    
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
    
    def extract_eligible_studies(self, text: str) -> Dict[str, Any]:
        """Extrae los estudios elegibles del Artículo 3."""
        result = {
            "description": "Estudios para los que se puede solicitar beca",
            "university_studies": [],
            "non_university_studies": []
        }
        
        # Extraer estudios no universitarios (punto 1)
        non_uni_pattern = r'1\.\s+Enseñanzas postobligatorias.*?(?=2\.|$)'
        non_uni_match = re.search(non_uni_pattern, text, re.DOTALL)
        
        if non_uni_match:
            non_uni_text = non_uni_match.group(0)
            result["non_university_section"] = "Enseñanzas postobligatorias y superiores no universitarias"
            
            # Extraer cada tipo de estudio no universitario por letras (a, b, c...)
            non_uni_items = re.findall(r'([a-z]\))([^a-z\)]+)(?=[a-z]\)|$)', non_uni_text, re.DOTALL)
            for identifier, description in non_uni_items:
                result["non_university_studies"].append({
                    "identifier": identifier.strip(),
                    "description": description.strip()
                })
        
        # Extraer estudios universitarios (punto 2)
        uni_pattern = r'2\.\s+Enseñanzas universitarias.*?(?=$)'
        uni_match = re.search(uni_pattern, text, re.DOTALL)
        
        if uni_match:
            uni_text = uni_match.group(0)
            result["university_section"] = "Enseñanzas universitarias del sistema universitario español"
            
            # Extraer cada tipo de estudio universitario por letras (a, b, c...)
            uni_items = re.findall(r'([a-z]\))([^a-z\)]+)(?=[a-z]\)|$)', uni_text, re.DOTALL)
            for identifier, description in uni_items:
                result["university_studies"].append({
                    "identifier": identifier.strip(),
                    "description": description.strip()
                })
        
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
                
                if description and "Cuantía" in description or "Beca" in description:
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
                component["type"] = "Beca de matrícula"
                component["amount_description"] = "Cobertura del precio público oficial de los servicios académicos"
            
            elif "B)" in identifier:  # Cuantía fija ligada a la renta
                component["type"] = "Cuantía fija ligada a la renta"
                amount_match = re.search(r'(\d+[,.]\d+)\s*euros', description)
                if amount_match:
                    component["amount"] = amount_match.group(1).replace(',', '.')
                    component["amount_description"] = f"{amount_match.group(1)} euros"
            
            elif "C)" in identifier:  # Cuantía fija ligada a la residencia
                component["type"] = "Cuantía fija ligada a la residencia"
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
        
        # Extraer cada umbral (1, 2, 3)
        for threshold_num in range(1, 4):
            threshold_pattern = rf'{threshold_num}\.\s+Umbral\s+{threshold_num}:.*?(?={threshold_num+1}\.|A partir|$)'
            threshold_match = re.search(threshold_pattern, text, re.DOTALL)
            
            if threshold_match:
                threshold_text = threshold_match.group(0)
                threshold = {
                    "number": threshold_num,
                    "family_sizes": []
                }
                
                # Extraer información para cada tamaño de familia
                family_patterns = [
                    r'Familias de un miembro:\s*(\d+[.,]\d+)',
                    r'Familias de dos miembros:\s*(\d+[.,]\d+)',
                    r'Familias de tres miembros:\s*(\d+[.,]\d+)',
                    r'Familias de cuatro miembros:\s*(\d+[.,]\d+)',
                    r'Familias de cinco miembros:\s*(\d+[.,]\d+)',
                    r'Familias de seis miembros:\s*(\d+[.,]\d+)',
                    r'Familias de siete miembros:\s*(\d+[.,]\d+)',
                    r'Familias de ocho miembros:\s*(\d+[.,]\d+)'
                ]
                
                for i, pattern in enumerate(family_patterns, 1):
                    match = re.search(pattern, threshold_text)
                    if match:
                        amount = match.group(1).replace('.', '').replace(',', '.')
                        threshold["family_sizes"].append({
                            "size": str(i),
                            "amount": amount,
                            "description": f"Familias de {self.number_to_text(i)} miembros: {match.group(1)} euros"
                        })
                
                # Extraer información adicional
                additional_pattern = r'A partir del octavo miembro.*?(\d+[.,]\d+)'
                additional_match = re.search(additional_pattern, text)
                if additional_match:
                    threshold["additional_info"] = {
                        "description": f"A partir del octavo miembro se añadirán {additional_match.group(1)} euros por cada nuevo miembro computable",
                        "amount_per_member": additional_match.group(1).replace(',', '.')
                    }
                
                if threshold["family_sizes"]:
                    result["thresholds"].append(threshold)
        
        return result
    
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
    
    def extract_application_deadlines(self, text: str) -> Dict[str, Any]:
        """Extrae los plazos de solicitud del Artículo 48."""
        result = {
            "description": "Plazos para presentar la solicitud de beca",
            "deadlines": []
        }
        
        # Extraer plazos específicos
        # Plazo para estudiantes universitarios
        uni_pattern = r'A\)(.*?)(?=B\)|$)'
        uni_match = re.search(uni_pattern, text, re.DOTALL)
        if uni_match:
            uni_text = uni_match.group(1).strip()
            date_match = re.search(r'(\d{1,2}\s+de\s+[a-zá-úñ]+\s+de\s+\d{4})', uni_text, re.IGNORECASE)
            
            # Si no encuentra la fecha completa, buscar solo el día y mes
            if not date_match:
                date_match = re.search(r'(\d{1,2}\s+de\s+[a-zá-úñ]+)', uni_text, re.IGNORECASE)
            
            # Si aún no encuentra, buscar cualquier fecha con formato dd/mm/yyyy
            if not date_match:
                date_match = re.search(r'(\d{1,2}/\d{1,2}/\d{4})', uni_text)
            
            # Último intento: buscar cualquier día con un año
            if not date_match:
                date_match = re.search(r'(\d{1,2}.*?\d{4})', uni_text)
            
            deadline_date = date_match.group(1) if date_match else uni_text
            result["deadlines"].append({
                "type": "Estudiantes universitarios",
                "deadline": deadline_date,
                "description": f"Para estudiantes universitarios: hasta el {deadline_date}"
            })
        
        # Plazo para estudiantes no universitarios
        non_uni_pattern = r'B\)(.*?)(?=\d+\.|Artículo|$)'
        non_uni_match = re.search(non_uni_pattern, text, re.DOTALL)
        if non_uni_match:
            non_uni_text = non_uni_match.group(1).strip()
            date_match = re.search(r'(\d{1,2}\s+de\s+[a-zá-úñ]+\s+de\s+\d{4})', non_uni_text, re.IGNORECASE)
            
            # Si no encuentra la fecha completa, buscar solo el día y mes
            if not date_match:
                date_match = re.search(r'(\d{1,2}\s+de\s+[a-zá-úñ]+)', non_uni_text, re.IGNORECASE)
            
            # Si aún no encuentra, buscar cualquier fecha con formato dd/mm/yyyy
            if not date_match:
                date_match = re.search(r'(\d{1,2}/\d{1,2}/\d{4})', non_uni_text)
            
            # Último intento: buscar cualquier día con un año
            if not date_match:
                date_match = re.search(r'(\d{1,2}.*?\d{4})', non_uni_text)
            
            deadline_date = date_match.group(1) if date_match else non_uni_text
            result["deadlines"].append({
                "type": "Estudiantes no universitarios",
                "deadline": deadline_date,
                "description": f"Para estudiantes no universitarios: hasta el {deadline_date}"
            })
        
        # Casos excepcionales
        exceptional_pattern = r'2\.\s+.*?después de los plazos.*?hasta el (\d{1,2}.*?\d{4}).*?en caso de (.*?)(?=$|Artículo)'
        exceptional_match = re.search(exceptional_pattern, text, re.DOTALL | re.IGNORECASE)
        if exceptional_match:
            result["exceptional_cases"] = {
                "deadline": exceptional_match.group(1),
                "conditions": exceptional_match.group(2).strip(),
                "description": f"Excepcionalmente hasta el {exceptional_match.group(1)} en caso de {exceptional_match.group(2).strip()}"
            }
        
        return result
    
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
    
    def convert_text_number(self, text: str) -> str:
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
    
    def generate_summary(self, data: List[Dict[str, Any]]) -> str:
        """Genera un resumen en formato Markdown."""
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
        
        # Sección de estudios elegibles (Artículo 3)
        eligible_studies = latest_data.get('eligible_studies', {})
        if eligible_studies:
            summary += f"## Artículo 3: Estudios Elegibles\n\n"
            
            # Estudios no universitarios
            if 'non_university_studies' in eligible_studies and eligible_studies['non_university_studies']:
                summary += "### Estudios No Universitarios\n\n"
                for study in eligible_studies['non_university_studies']:
                    summary += f"- {study.get('description', '')}\n"
                summary += "\n"
            
            # Estudios universitarios
            if 'university_studies' in eligible_studies and eligible_studies['university_studies']:
                summary += "### Estudios Universitarios\n\n"
                for study in eligible_studies['university_studies']:
                    summary += f"- {study.get('description', '')}\n"
                summary += "\n"
        
        # Sección de tipos de becas (Artículo 4)
        scholarship_types = latest_data.get('scholarship_types', {})
        if scholarship_types:
            summary += f"## Artículo 4: Clases y Cuantías de las Becas\n\n"
            
            # Cuantías fijas
            if 'fixed_amounts' in scholarship_types and scholarship_types['fixed_amounts']:
                summary += "### Cuantías Fijas\n\n"
                for type_info in scholarship_types['fixed_amounts']:
                    summary += f"- {type_info.get('type', '')}\n"
                summary += "\n"
            
            # Cuantía variable
            if 'variable_amount' in scholarship_types and 'description' in scholarship_types['variable_amount']:
                summary += "### Cuantía Variable\n\n"
                summary += f"{scholarship_types['variable_amount']['description']}\n\n"
        
        # Sección de cuantías de las becas (Artículo 11)
        scholarship_amounts = latest_data.get('scholarship_amounts', {})
        if scholarship_amounts and 'components' in scholarship_amounts:
            scholarship_amounts = latest_data.get('scholarship_amounts', {})
        if scholarship_amounts and 'components' in scholarship_amounts:
            summary += f"## Artículo 11: Cuantías de las Becas\n\n"
            
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
        
        # Sección de umbrales de renta (Artículo 19)
        income_thresholds = latest_data.get('income_thresholds', {})
        if income_thresholds and 'thresholds' in income_thresholds:
            summary += f"## Artículo 19: Umbrales de Renta Familiar\n\n"
            
            for threshold in income_thresholds.get('thresholds', []):
                summary += f"### Umbral {threshold.get('number', '')}\n\n"
                
                for family_size in threshold.get('family_sizes', []):
                    summary += f"- {family_size.get('description', '')}\n"
                
                if 'additional_info' in threshold:
                    summary += f"\n*{threshold['additional_info'].get('description', '')}*\n"
                
                summary += "\n"
        
        # Sección de requisitos académicos (Artículo 24)
        academic_requirements = latest_data.get('academic_requirements', {})
        if academic_requirements and 'requirements' in academic_requirements:
            summary += f"## Artículo 24: Requisitos Académicos\n\n"
            
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
        
        # Sección de plazos de solicitud (Artículo 48)
        application_deadlines = latest_data.get('application_deadlines', {})
        if application_deadlines and 'deadlines' in application_deadlines:
            summary += f"## Artículo 48: Plazos de Solicitud\n\n"
            
            for deadline in application_deadlines.get('deadlines', []):
                summary += f"- **{deadline.get('type', '')}**: {deadline.get('description', '')}\n"
            
            if 'exceptional_cases' in application_deadlines:
                summary += f"\n**Casos excepcionales**: {application_deadlines['exceptional_cases'].get('description', '')}\n"
            
            summary += "\n"
        
        return summary

def generate_individual_summary(data: Dict[str, Any], index: int) -> str:
    """Genera un resumen en formato Markdown para un solo documento enfocado en artículos específicos."""
    if not data.get('valid', False):
        return f"# Resumen de Beca #{index}\n\nEl documento no contiene datos válidos de convocatoria de becas."
    
    summary = f"# Resumen de Beca #{index}: {data.get('file_name', '')}\n\n"
    
    # Sección de información general
    academic_year = data.get('academic_year', {})
    if academic_year:
        summary += f"## Información General\n\n"
        summary += f"{academic_year.get('description', '')}\n\n"
    
    # Artículo 3: Estudios elegibles
    eligible_studies = data.get('eligible_studies', {})
    if eligible_studies:
        summary += f"## Artículo 3: Estudios Elegibles\n\n"
        
        # Incluir texto completo del artículo si está disponible
        if 'article_3' in data and data['article_3']:
            summary += "```\n" + data['article_3'] + "\n```\n\n"
        
        # Mostrar datos estructurados
        # Estudios no universitarios
        if 'non_university_studies' in eligible_studies and eligible_studies['non_university_studies']:
            summary += "### Estudios No Universitarios\n\n"
            for study in eligible_studies['non_university_studies']:
                summary += f"- {study.get('identifier', '')} {study.get('description', '')}\n"
            summary += "\n"
        
        # Estudios universitarios
        if 'university_studies' in eligible_studies and eligible_studies['university_studies']:
            summary += "### Estudios Universitarios\n\n"
            for study in eligible_studies['university_studies']:
                summary += f"- {study.get('identifier', '')} {study.get('description', '')}\n"
            summary += "\n"
    
    # Artículo 4: Clases y cuantías de becas
    scholarship_types = data.get('scholarship_types', {})
    if scholarship_types:
        summary += f"## Artículo 4: Clases y Cuantías de las Becas\n\n"
        
        # Incluir texto completo del artículo si está disponible
        if 'article_4' in data and data['article_4']:
            summary += "```\n" + data['article_4'] + "\n```\n\n"
        
        # Mostrar datos estructurados
        # Cuantías fijas
        if 'fixed_amounts' in scholarship_types and scholarship_types['fixed_amounts']:
            summary += "### Cuantías Fijas\n\n"
            for type_info in scholarship_types['fixed_amounts']:
                summary += f"- {type_info.get('type', '')}\n"
            summary += "\n"
        
        # Cuantía variable
        if 'variable_amount' in scholarship_types and 'description' in scholarship_types['variable_amount']:
            summary += "### Cuantía Variable\n\n"
            summary += f"{scholarship_types['variable_amount']['description']}\n\n"
    
    # Artículo 11: Cuantías detalladas de las becas
    scholarship_amounts = data.get('scholarship_amounts', {})
    if scholarship_amounts and 'components' in scholarship_amounts:
        summary += f"## Artículo 11: Cuantías de las Becas\n\n"
        
        # Incluir texto completo del artículo si está disponible
        if 'article_11' in data and data['article_11']:
            summary += "```\n" + data['article_11'] + "\n```\n\n"
        
        # Mostrar datos estructurados
        for component in scholarship_amounts.get('components', []):
            component_type = component.get('type', '')
            identifier = component.get('identifier', '')
            summary += f"### {identifier} {component_type}\n\n"
            
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
    
    # Artículo 19: Umbrales de renta
    income_thresholds = data.get('income_thresholds', {})
    if income_thresholds and 'thresholds' in income_thresholds:
        summary += f"## Artículo 19: Umbrales de Renta Familiar\n\n"
        
        # Incluir texto completo del artículo si está disponible
        if 'article_19' in data and data['article_19']:
            summary += "```\n" + data['article_19'] + "\n```\n\n"
        
        # Mostrar datos estructurados
        for threshold in income_thresholds.get('thresholds', []):
            summary += f"### Umbral {threshold.get('number', '')}\n\n"
            
            for family_size in threshold.get('family_sizes', []):
                summary += f"- {family_size.get('description', '')}\n"
            
            if 'additional_info' in threshold:
                summary += f"\n*{threshold['additional_info'].get('description', '')}*\n"
            
            summary += "\n"
    
    # Artículo 24: Requisitos académicos
    academic_requirements = data.get('academic_requirements', {})
    if academic_requirements and 'requirements' in academic_requirements:
        summary += f"## Artículo 24: Requisitos Académicos\n\n"
        
        # Incluir texto completo del artículo si está disponible
        if 'article_24' in data and data['article_24']:
            summary += "```\n" + data['article_24'] + "\n```\n\n"
        
        # Mostrar datos estructurados
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
    
    # Artículo 48: Plazos de solicitud
    application_deadlines = data.get('application_deadlines', {})
    if application_deadlines and 'deadlines' in application_deadlines:
        summary += f"## Artículo 48: Plazos de Solicitud\n\n"
        
        # Incluir texto completo del artículo si está disponible
        if 'article_48' in data and data['article_48']:
            summary += "```\n" + data['article_48'] + "\n```\n\n"
        
        # Mostrar datos estructurados
        for deadline in application_deadlines.get('deadlines', []):
            summary += f"- **{deadline.get('type', '')}**: {deadline.get('description', '')}\n"
        
        if 'exceptional_cases' in application_deadlines:
            summary += f"\n**Casos excepcionales**: {application_deadlines['exceptional_cases'].get('description', '')}\n"
        
        summary += "\n"
    
    return summary

def main():
    """Función principal del programa."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Extractor de información de becas del Ministerio de Educación')
    parser.add_argument('--input', '-i', required=True, help='Directorio de entrada con archivos de texto')
    parser.add_argument('--output', '-o', required=True, help='Directorio de salida para los resultados')
    args = parser.parse_args()
    
    # Crear directorio de salida si no existe
    if not os.path.exists(args.output):
        os.makedirs(args.output)
    
    # Procesar archivos
    extractor = BecasExtractor()
    results = extractor.process_files(args.input)
    
    # Guardar resultados en JSON
    json_output_path = os.path.join(args.output, 'becas_datos.json')
    with open(json_output_path, 'w', encoding='utf-8') as json_file:
        json.dump(results, json_file, ensure_ascii=False, indent=2)
    
    # Generar resumen general en Markdown
    summary = extractor.generate_summary(results)
    markdown_output_path = os.path.join(args.output, 'becas_resumen.md')
    with open(markdown_output_path, 'w', encoding='utf-8') as md_file:
        md_file.write(summary)
    
    # Generar archivos Markdown numerados para cada documento
    individual_summaries = []
    for i, result in enumerate(results, 1):
        individual_summary = generate_individual_summary(result, i)
        individual_summary_path = os.path.join(args.output, f'beca_{i}.md')
        with open(individual_summary_path, 'w', encoding='utf-8') as md_file:
            md_file.write(individual_summary)
        individual_summaries.append(individual_summary_path)
    
    # Mostrar resumen de resultados
    logger.info(f"Procesamiento completado:")
    logger.info(f"- Documentos procesados: {len(results)}")
    logger.info(f"- Resultados guardados en: {json_output_path}")
    logger.info(f"- Resumen general generado en: {markdown_output_path}")
    logger.info(f"- Resúmenes individuales generados:")
    for i, path in enumerate(individual_summaries, 1):
        logger.info(f"  {i}. {path}")

if __name__ == "__main__":
    main()