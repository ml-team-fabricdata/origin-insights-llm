"""
Script para limpiar caché de Python y recargar módulos.
"""

import sys
import os
import shutil

def clear_pycache():
    """Elimina todos los archivos __pycache__ y .pyc"""
    print("🧹 Limpiando caché de Python...")
    
    count = 0
    for root, dirs, files in os.walk('.'):
        # Eliminar directorios __pycache__
        if '__pycache__' in dirs:
            pycache_path = os.path.join(root, '__pycache__')
            try:
                shutil.rmtree(pycache_path)
                count += 1
                print(f"   ✅ Eliminado: {pycache_path}")
            except Exception as e:
                print(f"   ❌ Error eliminando {pycache_path}: {e}")
        
        # Eliminar archivos .pyc
        for file in files:
            if file.endswith('.pyc'):
                pyc_path = os.path.join(root, file)
                try:
                    os.remove(pyc_path)
                    count += 1
                    print(f"   ✅ Eliminado: {pyc_path}")
                except Exception as e:
                    print(f"   ❌ Error eliminando {pyc_path}: {e}")
    
    print(f"\n✅ Limpieza completada: {count} archivos/directorios eliminados")
    print("\n⚠️  IMPORTANTE: Reinicia el kernel de Jupyter o el proceso de Python")
    print("   - Jupyter: Kernel → Restart Kernel")
    print("   - Python: Cierra y vuelve a abrir el terminal")


if __name__ == "__main__":
    clear_pycache()
