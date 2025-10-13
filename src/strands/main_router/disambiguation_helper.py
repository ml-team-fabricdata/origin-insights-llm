"""
Helper functions for handling disambiguation (ambiguous validation results).
"""

import json
import re
from typing import Dict, Any, Optional, List


def parse_disambiguation_response(validation_message: str) -> Optional[List[Dict[str, Any]]]:
    """
    Parsea el mensaje de validación para extraer las opciones.
    
    Args:
        validation_message: Mensaje del LLM con las opciones
        
    Returns:
        Lista de opciones parseadas o None si no se puede parsear
        
    Example:
        >>> msg = "Multiple matches found for The Matrix. Please choose:\\n1. The Matrix (1999)\\n2. The Matrix (2016)"
        >>> options = parse_disambiguation_response(msg)
        >>> # [{"index": 1, "text": "The Matrix (1999)"}, {"index": 2, "text": "The Matrix (2016)"}]
    """
    options = []
    
    # Buscar líneas con formato "1. Option text"
    pattern = r'(\d+)\.\s+(.+?)(?:\n|$)'
    matches = re.findall(pattern, validation_message)
    
    for match in matches:
        index, text = match
        options.append({
            "index": int(index),
            "text": text.strip()
        })
    
    return options if options else None


def extract_entity_from_choice(
    choice_index: int,
    validation_message: str,
    validated_entities: Dict[str, Any]
) -> Optional[Dict[str, Any]]:
    """
    Extrae la entidad seleccionada basándose en el índice elegido por el usuario.
    
    Args:
        choice_index: Índice elegido por el usuario (1-based)
        validation_message: Mensaje original con las opciones
        validated_entities: Resultado de validación con las opciones
        
    Returns:
        Entidad resuelta o None si no se encuentra
        
    Example:
        >>> entity = extract_entity_from_choice(1, msg, validated_entities)
        >>> # {"type": "title", "uid": "123", "title": "The Matrix (1999)", "year": 1999}
    """
    # Intentar extraer del validated_entities si tiene estructura
    if isinstance(validated_entities, dict):
        options = validated_entities.get("options", [])
        
        # Si hay opciones en formato estructurado
        if options and isinstance(options, list):
            if 0 < choice_index <= len(options):
                selected = options[choice_index - 1]
                
                # Determinar tipo de entidad
                entity_type = None
                if "uid" in selected:
                    entity_type = "title"
                elif "id" in selected and "n_titles" in selected:
                    entity_type = "director"  # Directors tienen n_titles
                elif "id" in selected:
                    entity_type = "actor"
                
                return {
                    "type": entity_type,
                    **selected
                }
    
    # Fallback: parsear del mensaje
    options = parse_disambiguation_response(validation_message)
    if options and 0 < choice_index <= len(options):
        selected_text = options[choice_index - 1]["text"]
        
        # Intentar extraer información básica del texto
        # Formato típico: "Title (Year)" o "Name (details)"
        match = re.match(r'(.+?)\s*\((\d{4})\)', selected_text)
        if match:
            name, year = match.groups()
            return {
                "type": "title",
                "title": name.strip(),
                "year": int(year)
            }
        
        # Si no tiene año, asumir que es persona
        return {
            "type": "person",
            "name": selected_text.strip()
        }
    
    return None


def format_disambiguation_message(validation_result: Dict[str, Any]) -> str:
    """
    Formatea el mensaje de desambiguación de manera clara para el usuario.
    
    Args:
        validation_result: Resultado de validación con status="ambiguous"
        
    Returns:
        Mensaje formateado para el usuario
    """
    if validation_result.get("status") != "ambiguous":
        return "No disambiguation needed."
    
    options = validation_result.get("options", [])
    if not options:
        return "Multiple matches found, but no options available."
    
    # Determinar tipo de entidad
    entity_type = "item"
    if "uid" in options[0]:
        entity_type = "title"
    elif "id" in options[0]:
        entity_type = "person"
    
    lines = [f"Multiple {entity_type}s found. Please choose:"]
    
    for i, option in enumerate(options, 1):
        if entity_type == "title":
            title = option.get("title", "Unknown")
            year = option.get("year", "")
            type_info = option.get("type", "")
            line = f"{i}. {title}"
            if year:
                line += f" ({year})"
            if type_info:
                line += f" - {type_info}"
        else:
            name = option.get("name", "Unknown")
            n_titles = option.get("n_titles")
            line = f"{i}. {name}"
            if n_titles:
                line += f" ({n_titles} titles)"
        
        lines.append(line)
    
    lines.append("\nPlease reply with the number of your choice (1-{}).".format(len(options)))
    
    return "\n".join(lines)


# Example usage
if __name__ == "__main__":
    # Test parsing
    msg = """Multiple matches found for The Matrix. Please choose:
1. The Matrix (1999)
2. The Matrix (2016)
3. The Matrix (2004)

Could you specify which version?"""
    
    options = parse_disambiguation_response(msg)
    print("Parsed options:", options)
    
    # Test extraction
    validated = {
        "status": "ambiguous",
        "options": [
            {"uid": "123", "title": "The Matrix", "year": 1999, "type": "movie"},
            {"uid": "456", "title": "The Matrix", "year": 2016, "type": "tv"},
        ]
    }
    
    entity = extract_entity_from_choice(1, msg, validated)
    print("Extracted entity:", entity)
    
    # Test formatting
    formatted = format_disambiguation_message(validated)
    print("\nFormatted message:")
    print(formatted)
