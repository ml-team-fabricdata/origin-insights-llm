"""Parameter validation and normalization for graph nodes."""

from typing import Dict, Any, TypedDict
from src.strands.infrastructure.validators.legacy import (
    resolve_country_iso,
    resolve_content_type,
    resolve_platform_name,
    get_region_iso_list
)


class ValidationResult(TypedDict):
    valid: bool
    errors: list[str]
    warnings: list[str]
    normalized_params: Dict[str, Any]


def validate_and_normalize_fields(params: Dict[str, Any]) -> ValidationResult:
    errors = []
    warnings = []
    normalized = dict(params)
    
    country_field = params.get("country") or params.get("iso_alpha2") or params.get("countries_iso")
    if country_field:
        region_isos = get_region_iso_list(country_field)
        if region_isos:
            if len(region_isos) == 1:
                normalized["country"] = region_isos[0]
                normalized["iso_alpha2"] = region_isos[0]
            else:
                normalized["country_list"] = region_isos
                warnings.append(f"Region '{country_field}' expanded to {len(region_isos)} countries")
        else:
            resolved_country = resolve_country_iso(country_field)
            if resolved_country:
                normalized["country"] = resolved_country
                normalized["iso_alpha2"] = resolved_country
                if "countries_iso" in normalized:
                    normalized["countries_iso"] = resolved_country
            else:
                errors.append(f"Invalid country or region: '{country_field}'")
    
    type_field = params.get("type") or params.get("content_type")
    if type_field:
        resolved_type = resolve_content_type(type_field)
        if resolved_type:
            normalized["type"] = resolved_type
            normalized["content_type"] = resolved_type
        else:
            warnings.append(f"Non-standard content type: '{type_field}'")
    
    platform_field = params.get("platform_name")
    if platform_field:
        resolved_platform = resolve_platform_name(platform_field)
        if resolved_platform:
            normalized["platform_name"] = resolved_platform
        else:
            errors.append(f"Invalid platform name: '{platform_field}'")
    
    return ValidationResult(
        valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
        normalized_params=normalized
    )


async def validation_node(state: Dict[str, Any]) -> Dict[str, Any]:
    if state.get("validation_done"):
        return state
    
    params_to_validate = {}
    
    param_keys = [
        "country", "iso_alpha2", "countries_iso",
        "type", "content_type",
        "platform_name",
        "uid", "limit"
    ]
    
    for key in param_keys:
        if key in state and state[key] is not None:
            params_to_validate[key] = state[key]
    
    if "params" in state and isinstance(state["params"], dict):
        params_to_validate.update(state["params"])
    if "filters" in state and isinstance(state["filters"], dict):
        params_to_validate.update(state["filters"])
    
    result = validate_and_normalize_fields(params_to_validate)
    
    updated_state = {**state, "validation_done": True}
    
    if result["valid"]:
        updated_state.update(result["normalized_params"])
        
        if result["warnings"]:
            print(f"[VALIDATION] Warnings: {', '.join(result['warnings'])}")
        else:
            print("[VALIDATION] All fields validated successfully")
    else:
        error_msg = "; ".join(result["errors"])
        print(f"[VALIDATION] Validation failed: {error_msg}")
        
        updated_state["validation_error"] = error_msg
        updated_state["validation_errors"] = result["errors"]
        updated_state["answer"] = f"Validation error: {error_msg}"
    
    return updated_state


def create_validation_edge(state: Dict[str, Any]) -> str:
    if state.get("validation_error"):
        return "format_response"
    return "continue"


param_validation_node = validation_node
