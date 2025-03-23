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
    """Extractor de información de becas del Ministerio de Educación desde archivos de texto."""
    
    def __init__(self):
        self.results = []
    
    def process_files(self, input_dir: str) -> List[Dict[str, Any]]:
        """Procesa todos los archivos en el directorio de entrada."""
        if not os.path.exists(input_dir):
            logger.error(f"El directorio {input_dir} no existe")
            return []
        
        files = [f for f in os.listdir(input_dir) if f.endswith('.txt')]
        logger.info(f"Se encontraron {len(files)} archivos para procesar")
        
        for file_name in files:
            file_path = os.path.join(input_dir, file_name)
            logger.info(f"Procesando archivo: {file_name}")
            
            try:
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
        """Extrae los datos principales del texto."""
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
        result['eligible_studies'] = self.extract_eligible_studies(text)
        result['scholarship_amounts'] = self.extract_scholarship_amounts(text)
        result['income_thresholds'] = self.extract_income_thresholds(text)
        result['application_deadlines'] = self.extract_application_deadlines(text)
        result['academic_requirements'] = self.extract_academic_requirements(text)
        
        return result
    
    def is_valid_scholarship_text(self, text: str) -> bool:
        """Verifica si el texto corresponde a una convocatoria de becas."""
        key_patterns = [
            r'RESOLUCI[ÓO]N.*BECAS',
            r'Artículo.*?Enseñanzas comprendidas',
            r'Artículo.*?Cuantías de las becas',
            r'Artículo.*?Umbrales de renta',
            r'curso académico',
            r'CURSO ACADÉMICO'
        ]
        
        matches = sum(1 for pattern in key_patterns if re.search(pattern, text, re.IGNORECASE | re.DOTALL))
        return matches >= 2
    
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
        """Extrae los programas de estudio elegibles."""
        result = {
            "description": "Estudios para los que se puede solicitar beca",
            "university_studies": [],
            "non_university_studies": []
        }
        
        # Buscar la sección sobre estudios elegibles
        section_patterns = [
            r'(?:Artículo.*?Enseñanzas comprendidas|ENSEÑANZAS COMPRENDIDAS).*?(?=CAPÍTULO|Artículo\s+\d+[\.\s])',
            r'Enseñanzas comprendidas.*?(?=CAPÍTULO|Artículo\s+\d+\.)',
            r'Para el curso académico.*?se convocan becas.*?para las siguientes enseñanzas:.*?(?=CAPÍTULO|Artículo\s+\d+\.)'
        ]
        
        studies_section = ""
        for pattern in section_patterns:
            match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
            if match:
                studies_section = match.group(0)
                break
        
        if not studies_section:
            article3_pattern = r'Artículo 3\.\s+Enseñanzas comprendidas\.(.*?)(?=Artículo 4\.)'
            match = re.search(article3_pattern, text, re.DOTALL)
            if match:
                studies_section = match.group(1)
        
        if studies_section:
            # Extraer estudios no universitarios
            non_uni_pattern = r'1\.\s+Enseñanzas postobligatorias.*?(?=2\.\s+Enseñanzas|$)'
            non_uni_match = re.search(non_uni_pattern, studies_section, re.DOTALL)
            
            if non_uni_match:
                non_uni_text = non_uni_match.group(0)
                result["non_university_section"] = "Enseñanzas postobligatorias y superiores no universitarias"
                
                # Extraer cada tipo de estudio no universitario
                non_uni_items = re.findall(r'([a-z]\))([^a-z\)]+)(?=[a-z]\)|$)', non_uni_text, re.DOTALL)
                for identifier, description in non_uni_items:
                    result["non_university_studies"].append({
                        "identifier": identifier.strip(),
                        "description": description.strip()
                    })
            
            # Extraer estudios universitarios
            uni_pattern = r'2\.\s+Enseñanzas universitarias.*?(?=CAPÍTULO|Artículo|$)'
            uni_match = re.search(uni_pattern, studies_section, re.DOTALL)
            
            if uni_match:
                uni_text = uni_match.group(0)
                result["university_section"] = "Enseñanzas universitarias del sistema universitario español"
                
                # Extraer cada tipo de estudio universitario
                uni_items = re.findall(r'([a-z]\))([^a-z\)]+)(?=[a-z]\)|$)', uni_text, re.DOTALL)
                for identifier, description in uni_items:
                    result["university_studies"].append({
                        "identifier": identifier.strip(),
                        "description": description.strip()
                    })
        
        return result
    
    def extract_scholarship_amounts(self, text: str) -> Dict[str, Any]:
        """Extrae los montos de las becas."""
        result = {
            "description": "Cuantías y componentes de las becas",
            "components": []
        }
        
        # Buscar la sección de cuantías de becas
        section_patterns = [
            r'Artículo\s+\d+\.\s+Cuantías de las becas.*?(?=Artículo\s+\d+\.)',
            r'Las cuantías de las becas.*?serán las siguientes:.*?(?=Artículo\s+\d+\.)',
            r'Artículo\s+11\.\s+Cuantías.*?(?=Artículo\s+\d+\.)'
        ]
        
        amounts_section = ""
        for pattern in section_patterns:
            match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
            if match:
                amounts_section = match.group(0)
                break
        
        if not amounts_section:
            article11_pattern = r'Artículo\s+11\.(.*?)(?=Artículo\s+12\.)'
            match = re.search(article11_pattern, text, re.DOTALL)
            if match:
                amounts_section = match.group(1)
        
        if amounts_section:
            # Extraer cada componente de beca
            components = []
            
            # Beca de matrícula
            matricula_match = re.search(r'A\)\s*Gratuidad\s*de\s*la\s*matrícula.*?(?=B\)|$)', amounts_section, re.DOTALL)
            if matricula_match:
                components.append({
                    "type": "Beca de matrícula",
                    "amount_description": "Cobertura del precio público oficial de los servicios académicos"
                })
            
            # Cuantía fija ligada a la renta
            renta_match = re.search(r'B\)\s*Cuantía\s*fija\s*ligada\s*a\s*la\s*renta.*?(\d+[,.]\d+)\s*euros', 
                                    amounts_section, re.DOTALL)
            if renta_match:
                components.append({
                    "type": "Cuantía fija ligada a la renta",
                    "amount": renta_match.group(1).replace(',', '.'),
                    "amount_description": f"{renta_match.group(1)} euros"
                })
            
            # Cuantía fija ligada a la residencia
            residencia_match = re.search(r'C\)\s*Cuantía\s*fija\s*ligada\s*a\s*la\s*residencia.*?(\d+[,.]\d+)\s*euros', 
                                         amounts_section, re.DOTALL)
            if residencia_match:
                components.append({
                    "type": "Cuantía fija ligada a la residencia",
                    "amount": residencia_match.group(1).replace(',', '.'),
                    "amount_description": f"{residencia_match.group(1)} euros"
                })
            
            # Cuantía fija ligada a la excelencia académica
            excelencia_section = re.search(r'D\)\s*Cuantía\s*fija\s*ligada\s*a\s*la\s*excelencia.*?(?=E\)|$)', 
                                         amounts_section, re.DOTALL)
            if excelencia_section:
                excelencia_text = excelencia_section.group(0)
                excelencia_component = {
                    "type": "Cuantía fija ligada a la excelencia académica",
                    "ranges": []
                }
                
                # Extraer los rangos de excelencia
                ranges = re.findall(r'Entre\s+(\d+[,.]\d+)\s+y\s+(\d+[,.]\d+).*?(\d+)\s+euros', excelencia_text)
                for min_score, max_score, amount in ranges:
                    excelencia_component["ranges"].append({
                        "min_score": min_score.replace(',', '.'),
                        "max_score": max_score.replace(',', '.'),
                        "amount": amount,
                        "description": f"Entre {min_score} y {max_score} puntos: {amount} euros"
                    })
                
                # Añadir el rango más alto si existe
                highest_match = re.search(r'(\d+[,.]\d+).*?puntos\s+o\s+más.*?(\d+)\s+euros', excelencia_text)
                if highest_match:
                    excelencia_component["ranges"].append({
                        "min_score": highest_match.group(1).replace(',', '.'),
                        "max_score": "10.00",
                        "amount": highest_match.group(2),
                        "description": f"{highest_match.group(1)} puntos o más: {highest_match.group(2)} euros"
                    })
                
                components.append(excelencia_component)
            
            # Beca básica
            basica_match = re.search(r'E\)\s*Beca\s*básica.*?(\d+[,.]\d+)\s*euros', amounts_section, re.DOTALL)
            if basica_match:
                basica_component = {
                    "type": "Beca básica",
                    "amount": basica_match.group(1).replace(',', '.'),
                    "amount_description": f"{basica_match.group(1)} euros"
                }
                
                # Buscar caso especial para Ciclos Formativos de Grado Básico
                grado_basico_match = re.search(r'caso.*?(Ciclos Formativos de Grado Básico).*?(\d+[,.]\d+)\s*euros', 
                                              amounts_section, re.DOTALL | re.IGNORECASE)
                if grado_basico_match:
                    basica_component["special_case"] = {
                        "case": "Ciclos Formativos de Grado Básico",
                        "amount": grado_basico_match.group(2).replace(',', '.'),
                        "description": f"Para Ciclos Formativos de Grado Básico: {grado_basico_match.group(2)} euros"
                    }
                
                components.append(basica_component)
            
            # Cuantía variable
            variable_match = re.search(r'F\)\s*Cuantía\s*variable.*?mínimo.*?(\d+[,.]\d+)\s*euros', 
                                      amounts_section, re.DOTALL)
            if variable_match:
                variable_component = {
                    "type": "Cuantía variable",
                    "minimum_amount": variable_match.group(1).replace(',', '.'),
                    "amount_description": f"Mínimo de {variable_match.group(1)} euros"
                }
                
                # Buscar descripción de la fórmula
                formula_description = re.search(r'mediante la aplicación de la siguiente fórmula.*?(?=Artículo)', 
                                              text, re.DOTALL | re.IGNORECASE)
                if formula_description:
                    variable_component["formula_description"] = "Resultará de la ponderación de la nota media del expediente y la renta familiar"
                
                components.append(variable_component)
            
            result["components"] = components
        
        return result
    
    def extract_income_thresholds(self, text: str) -> Dict[str, Any]:
        """Extrae los umbrales de renta familiar."""
        result = {
            "description": "Umbrales de renta familiar aplicables para la concesión de las becas",
            "thresholds": []
        }
        
        # Buscar la sección de umbrales de renta
        threshold_patterns = [
            r'Artículo\s+\d+\.\s+Umbrales de renta.*?(?=Artículo\s+\d+\.)',
            r'Los umbrales de renta familiar.*?(?=Artículo\s+\d+\.)'
        ]
        
        thresholds_section = ""
        for pattern in threshold_patterns:
            match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
            if match:
                thresholds_section = match.group(0)
                break
        
        if not thresholds_section:
            article19_pattern = r'Artículo\s+19\.(.*?)(?=Artículo\s+20\.)'
            match = re.search(article19_pattern, text, re.DOTALL)
            if match:
                thresholds_section = match.group(1)
        
        if thresholds_section:
            # Extraer umbrales específicos
            for threshold_num in range(1, 4):  # Umbrales 1, 2 y 3
                threshold = {
                    "number": threshold_num,
                    "family_sizes": []
                }
                
                threshold_pattern = rf'(?:Umbral {threshold_num}:|{threshold_num}\.\s+Umbral {threshold_num}:)(.*?)(?=(?:Umbral|{threshold_num+1}\.\s+Umbral|Artículo|A partir del octavo miembro))'
                threshold_match = re.search(threshold_pattern, thresholds_section, re.DOTALL)
                
                if threshold_match:
                    threshold_text = threshold_match.group(1)
                    
                    # Encontrar todos los tamaños de familia y cantidades
                    family_matches = re.findall(r'Familias de (\w+|\d+) miembros?:?\s*(\d+[.,]\d+)', threshold_text)
                    
                    for size_text, amount in family_matches:
                        size = self.convert_text_number(size_text)
                        threshold["family_sizes"].append({
                            "size": size,
                            "amount": amount.replace(',', '.'),
                            "description": f"Familias de {size} miembros: {amount} euros"
                        })
                    
                    # Extraer información adicional para miembros adicionales
                    additional_pattern = rf'A partir del octavo miembro.*?{threshold_num}.*?(\d+[.,]\d+)'
                    additional_match = re.search(additional_pattern, thresholds_section)
                    
                    if additional_match:
                        threshold["additional_info"] = {
                            "description": f"A partir del octavo miembro se añadirán {additional_match.group(1)} euros por cada nuevo miembro computable",
                            "amount_per_member": additional_match.group(1).replace(',', '.')
                        }
                    
                    if threshold["family_sizes"]:
                        result["thresholds"].append(threshold)
        
        return result
    
    def extract_application_deadlines(self, text: str) -> Dict[str, Any]:
        """Extrae los plazos de solicitud."""
        result = {
            "description": "Plazos para presentar la solicitud de beca",
            "deadlines": []
        }
        
        # Buscar la sección de plazos
        deadline_patterns = [
            r'Artículo\s+\d+\.\s+Lugar y plazo.*?(?=Artículo\s+\d+\.)',
            r'Los plazos para presentar la solicitud.*?(?=Artículo\s+\d+\.)'
        ]
        
        deadlines_section = ""
        for pattern in deadline_patterns:
            match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
            if match:
                deadlines_section = match.group(0)
                break
        
        if not deadlines_section:
            article48_pattern = r'Artículo\s+48\.(.*?)(?=Artículo\s+49\.)'
            match = re.search(article48_pattern, text, re.DOTALL)
            if match:
                deadlines_section = match.group(1)
        
        if deadlines_section:
            # Extraer plazos específicos
            
            # Plazo para estudiantes universitarios
            uni_pattern = r'A\)(.*?)(?=B\)|$)'
            uni_match = re.search(uni_pattern, deadlines_section, re.DOTALL)
            if uni_match:
                uni_text = uni_match.group(1).strip()
                date_match = re.search(r'(\d{1,2} de [a-zá-úñ]+ de \d{4})', uni_text, re.IGNORECASE)
                if date_match:
                    result["deadlines"].append({
                        "type": "Estudiantes universitarios",
                        "deadline": date_match.group(1),
                        "description": f"Para estudiantes universitarios: hasta el {date_match.group(1)}"
                    })
            
            # Plazo para estudiantes no universitarios
            non_uni_pattern = r'B\)(.*?)(?=\d+\.|Artículo|$)'
            non_uni_match = re.search(non_uni_pattern, deadlines_section, re.DOTALL)
            if non_uni_match:
                non_uni_text = non_uni_match.group(1).strip()
                date_match = re.search(r'(\d{1,2} de [a-zá-úñ]+ de \d{4})', non_uni_text, re.IGNORECASE)
                if date_match:
                    result["deadlines"].append({
                        "type": "Estudiantes no universitarios",
                        "deadline": date_match.group(1),
                        "description": f"Para estudiantes no universitarios: hasta el {date_match.group(1)}"
                    })
            
            # Casos excepcionales
            exceptional_pattern = r'podrán presentarse solicitudes.*?después de los plazos.*?hasta el (\d{1,2} de [a-zá-úñ]+ de \d{4}).*?en caso de (.*?)(?=$|Artículo)'
            exceptional_match = re.search(exceptional_pattern, deadlines_section, re.DOTALL | re.IGNORECASE)
            if exceptional_match:
                result["exceptional_cases"] = {
                    "deadline": exceptional_match.group(1),
                    "conditions": exceptional_match.group(2).strip(),
                    "description": f"Excepcionalmente hasta el {exceptional_match.group(1)} en caso de {exceptional_match.group(2).strip()}"
                }
        
        return result
    
    def extract_academic_requirements(self, text: str) -> Dict[str, Any]:
        """Extrae los requisitos académicos."""
        result = {
            "description": "Requisitos académicos para obtener beca",
            "requirements": []
        }
        
        # Buscar secciones de requisitos académicos
        academic_sections = [
            ("Requisitos generales", r'Artículo\s+\d+\.\s+Requisitos generales.*?(?=CAPÍTULO|Artículo\s+\d+\.)'),
            ("Rendimiento académico", r'Artículo\s+\d+\.\s+Rendimiento académico.*?(?=CAPÍTULO|Artículo\s+\d+\.)'),
            ("Número de créditos", r'Artículo\s+\d+\.\s+Número de créditos.*?(?=CAPÍTULO|Artículo\s+\d+\.)'),
            ("Carga lectiva superada", r'Artículo\s+\d+\.\s+Carga lectiva superada.*?(?=CAPÍTULO|Artículo\s+\d+\.)')
        ]
        
        for section_type, pattern in academic_sections:
            section_match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
            
            if section_match:
                section_text = section_match.group(0)
                
                # Extraer requisitos específicos según el tipo de sección
                if section_type == "Requisitos generales":
                    requirements = re.findall(r'([a-z]\))(.*?)(?=[a-z]\)|$)', section_text, re.DOTALL)
                    for identifier, req_text in requirements:
                        result["requirements"].append({
                            "type": "Requisito general",
                            "identifier": identifier.strip(),
                            "description": req_text.strip()
                        })
                
                elif section_type == "Rendimiento académico":
                    # Extraer porcentajes por rama de conocimiento para universitarios
                    percentages_match = re.search(r'Rama o área de conocimiento.*?(?=\s*\d+\.\s+)', section_text, re.DOTALL)
                    if percentages_match:
                        percentages_text = percentages_match.group(0)
                        percentages = re.findall(r'([A-Za-zñÑáéíóúÁÉÍÓÚ\s/]+)\s*\.\s*\.\s*\.\s*\.\s*\.\s*(\d+%)' , percentages_text)
                        
                        for area, percentage in percentages:
                            result["requirements"].append({
                                "type": "Porcentaje de créditos por área",
                                "area": area.strip(),
                                "percentage": percentage,
                                "description": f"Área de {area.strip()}: {percentage} de créditos a superar"
                            })
                    
                    # Extraer nota mínima para primer curso
                    nota_min_match = re.search(r'primer curso.*?(\d+[,.]\d+) puntos', section_text, re.IGNORECASE)
                    if nota_min_match:
                        result["requirements"].append({
                            "type": "Nota mínima primer curso",
                            "nota": nota_min_match.group(1),
                            "description": f"Nota mínima para primer curso: {nota_min_match.group(1)} puntos"
                        })
        
        return result
    
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
        
        # Sección de estudios elegibles
        eligible_studies = latest_data.get('eligible_studies', {})
        if eligible_studies:
            summary += f"## Estudios Elegibles\n\n"
            
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
        
        # Sección de cuantías de las becas
        scholarship_amounts = latest_data.get('scholarship_amounts', {})
        if scholarship_amounts and 'components' in scholarship_amounts:
            summary += f"## Cuantías de las Becas\n\n"
            
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
        
        # Sección de umbrales de renta
        income_thresholds = latest_data.get('income_thresholds', {})
        if income_thresholds and 'thresholds' in income_thresholds:
            summary += f"## Umbrales de Renta Familiar\n\n"
            
            for threshold in income_thresholds.get('thresholds', []):
                summary += f"### Umbral {threshold.get('number', '')}\n\n"
                
                for family_size in threshold.get('family_sizes', []):
                    summary += f"- {family_size.get('description', '')}\n"
                
                if 'additional_info' in threshold:
                    summary += f"\n*{threshold['additional_info'].get('description', '')}*\n"
                
                summary += "\n"
        
        # Sección de plazos de solicitud
        application_deadlines = latest_data.get('application_deadlines', {})
        if application_deadlines and 'deadlines' in application_deadlines:
            summary += f"## Plazos de Solicitud\n\n"
            
            for deadline in application_deadlines.get('deadlines', []):
                summary += f"- **{deadline.get('type', '')}**: {deadline.get('description', '')}\n"
            
            if 'exceptional_cases' in application_deadlines:
                summary += f"\n**Casos excepcionales**: {application_deadlines['exceptional_cases'].get('description', '')}\n"
            
            summary += "\n"
        
        # Sección de requisitos académicos
        academic_requirements = latest_data.get('academic_requirements', {})
        if academic_requirements and 'requirements' in academic_requirements:
            summary += f"## Requisitos Académicos\n\n"
            
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
        
        return summary

def generate_individual_summary(data: Dict[str, Any], index: int) -> str:
    """Genera un resumen en formato Markdown para un solo documento."""
    if not data.get('valid', False):
        return f"# Resumen de Beca #{index}\n\nEl documento no contiene datos válidos de convocatoria de becas."
    
    summary = f"# Resumen de Beca #{index}: {data.get('file_name', '')}\n\n"
    
    # Sección de información general
    academic_year = data.get('academic_year', {})
    if academic_year:
        summary += f"## Información General\n\n"
        summary += f"{academic_year.get('description', '')}\n\n"
    
    # Sección de estudios elegibles
    eligible_studies = data.get('eligible_studies', {})
    if eligible_studies:
        summary += f"## Estudios Elegibles\n\n"
        
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
    
    # Sección de cuantías de las becas
    scholarship_amounts = data.get('scholarship_amounts', {})
    if scholarship_amounts and 'components' in scholarship_amounts:
        summary += f"## Cuantías de las Becas\n\n"
        
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
    
    # Sección de umbrales de renta
    income_thresholds = data.get('income_thresholds', {})
    if income_thresholds and 'thresholds' in income_thresholds:
        summary += f"## Umbrales de Renta Familiar\n\n"
        
        for threshold in income_thresholds.get('thresholds', []):
            summary += f"### Umbral {threshold.get('number', '')}\n\n"
            
            for family_size in threshold.get('family_sizes', []):
                summary += f"- {family_size.get('description', '')}\n"
            
            if 'additional_info' in threshold:
                summary += f"\n*{threshold['additional_info'].get('description', '')}*\n"
            
            summary += "\n"
    
    # Sección de plazos de solicitud
    application_deadlines = data.get('application_deadlines', {})
    if application_deadlines and 'deadlines' in application_deadlines:
        summary += f"## Plazos de Solicitud\n\n"
        
        for deadline in application_deadlines.get('deadlines', []):
            summary += f"- **{deadline.get('type', '')}**: {deadline.get('description', '')}\n"
        
        if 'exceptional_cases' in application_deadlines:
            summary += f"\n**Casos excepcionales**: {application_deadlines['exceptional_cases'].get('description', '')}\n"
        
        summary += "\n"
    
    # Sección de requisitos académicos
    academic_requirements = data.get('academic_requirements', {})
    if academic_requirements and 'requirements' in academic_requirements:
        summary += f"## Requisitos Académicos\n\n"
        
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