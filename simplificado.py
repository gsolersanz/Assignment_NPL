#!/usr/bin/env python3
"""
Versión simplificada del extractor de información sobre becas
"""

import os
import json
from datetime import datetime

def save_to_json(data, output_path):
    """Guarda los datos extraídos en un archivo JSON."""
    try:
        with open(output_path, 'w', encoding='utf-8') as file:
            json.dump(data, file, ensure_ascii=False, indent=2)
        print(f"Datos guardados en {output_path}")
        return True
    except Exception as e:
        print(f"Error al guardar JSON: {e}")
        return False

def process_text_corpus(txt_dir):
    """Procesa todos los archivos de texto en un directorio."""
    results = []
    
    # Verificar si el directorio existe
    if not os.path.exists(txt_dir):
        print(f"Error: El directorio {txt_dir} no existe")
        return results
    
    # Listar todos los archivos en el directorio
    all_files = os.listdir(txt_dir)
    print(f"Archivos encontrados en {txt_dir}: {all_files}")
    
    # Filtrar archivos de texto
    txt_files = [f for f in all_files if f.endswith('.txt')]
    print(f"Archivos de texto encontrados: {txt_files}")
    
    # Procesar cada archivo
    for filename in txt_files:
        txt_path = os.path.join(txt_dir, filename)
        print(f"Procesando: {txt_path}")
        
        # Leer contenido del archivo
        try:
            with open(txt_path, 'r', encoding='utf-8') as f:
                text = f.read()
                content_preview = text[:100] + "..." if len(text) > 100 else text
                print(f"Contenido leído ({len(text)} caracteres). Vista previa: {content_preview}")
        except Exception as e:
            print(f"Error leyendo archivo {txt_path}: {e}")
            continue
        
        # Extraer identificador del archivo
        file_id = os.path.splitext(filename)[0]
        if "_text" in file_id:
            file_id = file_id.replace("_text", "")
        
        # Crear resultado simple
        result = {
            "id": file_id,
            "filename": file_id + ".pdf",
            "valid": True,
            "content_length": len(text),
            "processing_timestamp": datetime.now().isoformat()
        }
        
        results.append(result)
    
    return results

def main():
    """Función principal."""
    import sys
    
    # Definir directorios por defecto
    input_dir = "./corpus"
    output_dir = "./output"
    
    # Procesar argumentos si se proporcionan
    if len(sys.argv) > 1:
        input_dir = sys.argv[1]
    if len(sys.argv) > 2:
        output_dir = sys.argv[2]
    
    print(f"Usando directorio de entrada: {input_dir}")
    print(f"Usando directorio de salida: {output_dir}")
    
    # Crear directorio de salida si no existe
    if not os.path.exists(output_dir):
        try:
            os.makedirs(output_dir)
            print(f"Directorio de salida creado: {output_dir}")
        except Exception as e:
            print(f"Error al crear directorio de salida: {e}")
            return
    
    # Procesar archivos
    print(f"Procesando archivos de texto de {input_dir}...")
    data = process_text_corpus(input_dir)
    
    if not data:
        print("No se encontraron resultados para guardar.")
        return
    
    # Guardar datos en JSON
    output_json = os.path.join(output_dir, "becas_datos_simple.json")
    success = save_to_json(data, output_json)
    
    if success:
        print("¡Procesamiento completado con éxito!")
    else:
        print("Procesamiento completado con errores.")

if __name__ == "__main__":
    main()