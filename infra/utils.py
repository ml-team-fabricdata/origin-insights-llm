# infra/utils.py
import os
import json
import logging

logger = logging.getLogger(__name__)

def load_jsonl(filename: str):
    """
    Carga un archivo JSONL desde /src/data dentro del contenedor.
    Devuelve una lista de diccionarios.
    """
    base_dir = os.path.dirname(os.path.abspath(__file__))
    data_path = os.path.join(base_dir, "..", "src", "data", filename)
    data_path = os.path.abspath(data_path)

    if not os.path.exists(data_path):
        logger.error(f"Archivo no encontrado: {data_path}")
        raise FileNotFoundError(f"Archivo no encontrado: {data_path}")

    with open(data_path, "r", encoding="utf-8") as f:
        return [json.loads(line) for line in f]

def get_data_dir():
    """Devuelve la ruta absoluta a la carpeta /src/data"""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.abspath(os.path.join(base_dir, "..", "src", "data"))