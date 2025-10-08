#!/usr/bin/env python
# -*- coding: utf-8 -*-
# visualize_platform_graph.py - Visualiza el nuevo flujo del grafo Platform

import sys
from pathlib import Path
root_dir = Path(__file__).parent
sys.path.insert(0, str(root_dir))

from src.strands.platform.graph.graph import create_streaming_graph

def main():
    print("\n" + "="*70)
    print("FLUJO DEL GRAFO PLATFORM - PRICING & INTELLIGENCE")
    print("="*70 + "\n")
    
    print("""
    FLUJO IMPLEMENTADO (CON LOOP):
    
    START
      |
      v
    [main_supervisor] --> Decide: clasificar o formatear
      |
      +---> [SI necesita clasificación]
      |           |
      |           v
      |     [platform_classifier] --> Clasifica: PRICING o INTELLIGENCE
      |           |
      |           +------------------+------------------+
      |           |                                     |
      |           v                                     v
      |     [pricing_worker]                  [intelligence_worker]
      |           |                                     |
      |           +------------------+------------------+
      |                              |
      +<-----------------------------+ (VUELVE al supervisor)
      |
      +---> [SI pregunta respondida]
                         |
                         v
                  [format_response]
                         |
                         v
                        END
    
    
    DESCRIPCIÓN DE NODOS:
    
    1. main_supervisor (PUNTO CENTRAL):
       - Punto de entrada del grafo
       - Primera iteración: Envía a clasificar
       - Después de workers: Evalúa si la pregunta fue respondida
       - Si COMPLETO: Va a format_response
       - Si NECESITA_MÁS: Vuelve a platform_classifier (loop)
       
    2. platform_classifier:
       - Clasifica la pregunta en PRICING o INTELLIGENCE
       - PRICING: Preguntas sobre precios, tarifas, costos
       - INTELLIGENCE: Preguntas sobre disponibilidad, análisis, estadísticas
       
    3. pricing_worker:
       - Ejecuta tools relacionadas con precios
       - Después de ejecutar, VUELVE al supervisor
       
    4. intelligence_worker:
       - Ejecuta tools de análisis e insights
       - Después de ejecutar, VUELVE al supervisor
       
    5. format_response:
       - Formatea la respuesta final para el usuario
       - Usa Claude Sonnet 4 para dar formato amigable
    
    CARACTERÍSTICAS DEL LOOP:
    - Máximo de iteraciones configurable (default: 3)
    - El supervisor evalúa con LLM si los datos son suficientes
    - Previene loops infinitos con límite de iteraciones
    
    """)
    print("="*70)
    
    # Intentar generar diagrama Mermaid
    try:
        print("\nDIAGRAMA MERMAID:")
        print("="*70)
        graph = create_streaming_graph()
        mermaid_code = graph.get_graph().draw_mermaid()
        print(mermaid_code)
        print("="*70)
        print("\nCopia el código Mermaid en https://mermaid.live para visualizarlo")
    except Exception as e:
        print(f"[WARNING] No se pudo generar diagrama: {e}")
    
    print("\n" + "="*70)
    print("Para probar el grafo, ejecuta: python test_platform_graph.py")
    print("="*70 + "\n")

if __name__ == "__main__":
    main()
