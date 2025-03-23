# Sistema de Extracción y Resumen de Becas Educativas

Este proyecto implementa un sistema automático para la extracción de información sobre becas educativas publicadas en el Boletín Oficial del Estado (BOE) y la generación de resúmenes estructurados, incluyendo no solo los datos numéricos sino también sus significados y contextos.

## Objetivo

El objetivo principal es desarrollar un sistema que combine técnicas de extracción de información (comprensión del lenguaje) con modelos de generación de texto (generación de lenguaje). El sistema:

1. Extrae información estructurada de documentos PDF de convocatorias de becas
2. Mantiene el contexto completo de cada dato extraído (no solo números sino también su significado)
3. Organiza esta información en formato JSON 
4. Genera un resumen completo que describe de manera clara toda la información relevante

## Características

- **Procesamiento de PDFs**: Extracción de texto a partir de archivos PDF
- **Extracción de información completa**:
  - Año académico de la convocatoria con su descripción
  - Tipos de estudios elegibles con descripciones completas
  - Cuantías de las becas con sus descripciones y condiciones
  - Umbrales de renta familiar para cada tamaño de familia
  - Plazos de solicitud con todas sus condiciones
  - Requisitos académicos detallados por tipo de estudio
- **Salida estructurada**: Datos organizados en JSON preservando todo el contexto
- **Resumen contextualizado**: Generación de un resumen en formato Markdown que incluye tanto los datos como su significado

## Estructura del Proyecto

```
proyecto-becas/
├── complete_extractor.py       # Biblioteca principal de extracción
├── demo_script.py              # Script de demostración
├── corpus/                     # Directorio para los PDFs de becas
│   ├── ayudas_21-22.pdf
│   ├── ayudas_20-21.pdf
│   └── ...
│
└── output/                     # Directorio para los resultados
    ├── becas_datos.json        # Datos estructurados con contexto completo
    └── becas_resumen.md        # Resumen generado
```

## Requisitos

- Python 3.7 o superior
- Bibliotecas:
  - PyPDF2 (para la extracción de texto de PDFs)
  - re (expresiones regulares)
  - json (para el manejo de datos)
  - os, datetime (utilitarias)

## Instalación

1. Clona este repositorio o descarga los archivos
2. Instala las dependencias:
   ```
   pip install PyPDF2
   ```
3. Crea los directorios necesarios:
   ```
   mkdir -p corpus output
   ```

## Uso

1. **Preparación**: Coloca los PDFs de convocatorias de becas en el directorio `corpus/`

2. **Ejecución del script de demostración**:
   ```
   python demo_script.py
   ```

3. **Examina los resultados**:
   - Revisa el archivo JSON generado que contiene los datos estructurados con contexto completo
   - Lee el resumen en formato Markdown que presenta la información de forma legible

4. **Uso de la biblioteca en tu propio código**:
   ```python
   from complete_extractor import analyze_pdf, generate_summary, save_to_json
   
   # Analizar un PDF de convocatoria de becas
   resultado = analyze_pdf("ruta/al/archivo.pdf")
   
   # Guardar los datos extraídos en JSON
   save_to_json([resultado], "datos_becas.json")
   
   # Generar un resumen legible
   resumen = generate_summary([resultado])
   with open("resumen.md", "w", encoding="utf-8") as f:
       f.write(resumen)
   ```

## Información Extraída

El sistema extrae y organiza la siguiente información con su contexto completo:

1. **Información básica**:
   - Año académico con descripción
   - Identificación del documento

2. **Estudios elegibles**:
   - Descripción de las secciones universitarias y no universitarias
   - Lista completa de estudios con sus descripciones exactas

3. **Cuantías de las becas**:
   - Descripción de cada componente de beca
   - Montos con sus contextos y condiciones
   - Casos especiales (como becas para ciclos formativos de grado básico)
   - Fórmulas de cálculo cuando aplican

4. **Criterios de elegibilidad**:
   - Umbrales de renta familiar con descripción por cada tamaño de familia
   - Información adicional para familias numerosas
   - Requisitos académicos detallados por área de conocimiento

5. **Información sobre solicitudes**:
   - Plazos con descripciones completas
   - Condiciones específicas
   - Casos excepcionales

## Ejemplo de Datos Extraídos

El sistema extrae datos estructurados como el siguiente ejemplo:

```json
{
  "scholarship_amounts": {
    "description": "Cuantías y componentes de las becas",
    "components": [
      {
        "type": "Cuantía fija ligada a la renta",
        "amount": "1700.00",
        "amount_description": "1.700,00 euros",
        "full_description": "Cuantía fija ligada a la renta del solicitante: 1.700,00 euros"
      }
    ]
  }
}
```

## Limitaciones y Mejoras Futuras

- El sistema está optimizado para convocatorias de becas del Ministerio de Educación español
- La extracción depende de patrones y estructuras específicas de estos documentos
- Mejoras futuras:
  - Implementar técnicas de NLP más avanzadas para aumentar la robustez
  - Añadir soporte para otros tipos de documentos
  - Desarrollar una interfaz web para facilitar su uso
  - Agregar análisis comparativo entre diferentes años

## Notas Importantes

Este sistema no solo extrae datos, sino que conserva su significado completo, lo cual es fundamental para entender la información en su contexto. Por ejemplo, no solo extrae el valor "1700.00", sino que preserva que es la "Cuantía fija ligada a la renta del solicitante" expresada en euros, lo que permite generar resúmenes mucho más informativos y útiles.
