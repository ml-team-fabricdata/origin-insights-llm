#!/usr/bin/env python
# -*- coding: utf-8 -*-
# test_platform_graph.py - Script para probar el grafo de platform

import sys
from pathlib import Path
root_dir = Path(__file__).parent
sys.path.insert(0, str(root_dir))

import asyncio
import time
from src.strands.platform import process_question

async def main():
    print("\n" + "="*60)
    print("TEST: PLATFORM GRAPH")
    print("="*60 + "\n")
    
    # Test 1: Pregunta de INTELLIGENCE
    print("[TEST 1] Pregunta de INTELLIGENCE")
    print("-" * 60)
    question1 = "donde puedo ver stranger things?"
    
    start = time.time()
    result1 = await process_question(question1, max_iterations=1)
    elapsed = time.time() - start
    
    print(f"\n[OK] Resultado Test 1:")
    print(f"  Pregunta: {result1.get('question', 'N/A')}")
    print(f"  Task: {result1.get('task', 'N/A')}")
    print(f"  Iteraciones: {result1.get('tool_calls_count', 0)}")
    print(f"  Status: {result1.get('status', 'N/A')}")
    print(f"  Tiempo: {elapsed:.2f}s")
    answer1 = result1.get('answer', 'N/A')
    print(f"  Respuesta: {str(answer1)[:200]}...")
    
    if result1.get('worker_errors'):
        print(f"  [WARNING] Errores: {result1['worker_errors']}")
    
    print("\n" + "="*60 + "\n")
    
    # Test 2: Pregunta de PRICING
    print("[TEST 2] Pregunta de PRICING")
    print("-" * 60)
    question2 = "donde esta disponible avatar??"
    
    start = time.time()
    result2 = await process_question(question2, max_iterations=1)
    elapsed = time.time() - start
    
    print(f"\n[OK] Resultado Test 2:")
    print(f"  Pregunta: {result2.get('question', 'N/A')}")
    print(f"  Task: {result2.get('task', 'N/A')}")
    print(f"  Iteraciones: {result2.get('tool_calls_count', 0)}")
    print(f"  Status: {result2.get('status', 'N/A')}")
    print(f"  Tiempo: {elapsed:.2f}s")
    answer2 = result2.get('answer', 'N/A')
    print(f"  Respuesta: {str(answer2)[:200]}...")
    
    if result2.get('worker_errors'):
        print(f"  [WARNING] Errores: {result2['worker_errors']}")
    
    print("\n" + "="*60)
    print("[SUCCESS] TESTS COMPLETADOS")
    print("="*60 + "\n")

if __name__ == "__main__":
    asyncio.run(main())
