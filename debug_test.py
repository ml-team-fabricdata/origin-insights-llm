"""
🐛 Debug Test - Test individual para debugging

Ejecutar:
    python debug_test.py
"""

import asyncio
from src.strands.main_router.graph import process_question_main


async def debug_single_test():
    """Ejecuta un solo test para debugging."""
    
    print("""
    🐛 DEBUG TEST - Origin Insights LLM
    ====================================
    """)
    
    # Cambiar esta pregunta para testear diferentes casos
    question = "Validacion de Coppola"
    expected_graph = "validation_preprocessor"
    needs_validation = True
    
    print(f"❓ Pregunta: {question}")
    print(f"🎯 Grafo esperado: {expected_graph}")
    print(f"🔍 Validación esperada: {'Sí' if needs_validation else 'No'}")
    print("\n" + "="*80 + "\n")
    
    try:
        # Ejecutar pregunta
        result = await process_question_main(question, max_iterations=3)
        
        # Verificar resultados
        selected_graph = result.get('selected_graph', 'unknown')
        validation_done = result.get('validation_done', False)
        needs_validation_result = result.get('needs_validation', False)
        answer = result.get('answer', 'Sin respuesta')
        
        # Validar expectativas
        graph_match = selected_graph == expected_graph
        validation_match = needs_validation_result == needs_validation
        
        print("\n" + "="*80)
        print("📊 RESULTADO DEL TEST")
        print("="*80)
        print(f"✅ Grafo seleccionado: {selected_graph}")
        print(f"   Esperado: {expected_graph}")
        print(f"   Match: {'✅ SÍ' if graph_match else '❌ NO'}")
        print()
        print(f"✅ Validación realizada: {validation_done}")
        print(f"✅ Necesitaba validación: {needs_validation_result}")
        print(f"   Esperado: {needs_validation}")
        print(f"   Match: {'✅ SÍ' if validation_match else '❌ NO'}")
        print()
        print(f"✅ Re-routings: {result.get('rerouting_count', 0)}")
        
        if result.get('validated_entities'):
            print(f"\n🔍 Entidades validadas:")
            for key, value in result['validated_entities'].items():
                print(f"   • {key}: {value}")
        
        # Extraer respuesta correctamente
        if isinstance(answer, dict):
            answer_text = str(answer.get('content', [{}])[0].get('text', 'Sin respuesta'))
        else:
            answer_text = str(answer)
        
        print(f"\n💬 Respuesta completa:")
        print(f"{answer_text}")
        
        print("\n" + "="*80)
        print(f"🎯 TEST: {'✅ EXITOSO' if (graph_match and validation_match) else '❌ FALLIDO'}")
        print("="*80 + "\n")
        
        return result
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    asyncio.run(debug_single_test())
