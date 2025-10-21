import json
from typing import Dict, Any, Optional, List
from .state import MainRouterState

REQUIRED_FIELDS = {
    "answer": str,
    "selected_graph": str,
}

OPTIONAL_FIELDS = {
    "domain_graph_status": str,
    "routing_confidence": (int, float),
    "validated_entities": (dict, type(None)),
    "parallel_results": (list, type(None)),
}

RESPONSE_SCHEMAS = {
    "standard": {
        "required": ["answer"],
        "min_answer_length": 50,
        "max_answer_length": 5000,
        "allowed_statuses": ["success", "not_my_scope", "needs_clarification", "error"]
    },
    "parallel": {
        "required": ["answer", "parallel_results"],
        "min_answer_length": 50,
        "max_answer_length": 5000,
    },
    "validated": {
        "required": ["answer", "validated_entities"],
        "min_answer_length": 50,
        "max_answer_length": 5000,
    }
}


def validate_field_type(value: Any, expected_type) -> bool:
    if isinstance(expected_type, tuple):
        return isinstance(value, expected_type)
    return isinstance(value, expected_type)


def validate_answer_content(answer: str, min_length: int = 50, max_length: int = 5000) -> Dict[str, Any]:
    errors = []
    
    if not answer:
        errors.append("Answer is empty or None")
        return {"valid": False, "errors": errors}
    
    if not isinstance(answer, str):
        errors.append(f"Answer must be string, got {type(answer).__name__}")
        return {"valid": False, "errors": errors}
    
    answer_length = len(answer.strip())
    
    if answer_length < min_length:
        errors.append(f"Answer too short: {answer_length} chars (min: {min_length})")
    
    if answer_length > max_length:
        errors.append(f"Answer too long: {answer_length} chars (max: {max_length})")
    
    if answer.strip() and not any(c.isalnum() for c in answer):
        errors.append("Answer contains no alphanumeric characters")
    
    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "length": answer_length
    }


def validate_json_structure(data: Any) -> Dict[str, Any]:
    errors = []
    
    try:
        json.dumps(data)
    except (TypeError, ValueError) as e:
        errors.append(f"Data not JSON serializable: {str(e)}")
    
    return {
        "valid": len(errors) == 0,
        "errors": errors
    }


def validate_domain_status(status: Optional[str]) -> Dict[str, Any]:
    errors = []
    
    allowed_statuses = ["success", "not_my_scope", "needs_clarification", "error"]
    
    if status and status not in allowed_statuses:
        errors.append(f"Invalid domain_graph_status: '{status}'. Allowed: {allowed_statuses}")
    
    return {
        "valid": len(errors) == 0,
        "errors": errors
    }


def validate_parallel_results(results: Optional[List[Dict]]) -> Dict[str, Any]:
    errors = []
    
    if results is None:
        return {"valid": True, "errors": []}
    
    if not isinstance(results, list):
        errors.append(f"parallel_results must be list, got {type(results).__name__}")
        return {"valid": False, "errors": errors}
    
    for i, result in enumerate(results):
        if not isinstance(result, dict):
            errors.append(f"parallel_results[{i}] must be dict, got {type(result).__name__}")
            continue
        
        required_keys = ["graph", "confidence", "status"]
        for key in required_keys:
            if key not in result:
                errors.append(f"parallel_results[{i}] missing required key: '{key}'")
    
    return {
        "valid": len(errors) == 0,
        "errors": errors
    }


def validate_validated_entities(entities: Optional[Dict]) -> Dict[str, Any]:
    errors = []
    
    if entities is None:
        return {"valid": True, "errors": []}
    
    if not isinstance(entities, dict):
        errors.append(f"validated_entities must be dict, got {type(entities).__name__}")
        return {"valid": False, "errors": errors}
    
    return {
        "valid": True,
        "errors": []
    }


async def schema_checker_node(state: MainRouterState) -> MainRouterState:
    print("\n" + "="*80)
    print("SCHEMA CHECKER")
    print("="*80)
    
    all_errors = []
    warnings = []
    
    answer = state.get("answer", "")
    answer_validation = validate_answer_content(
        answer,
        min_length=RESPONSE_SCHEMAS["standard"]["min_answer_length"],
        max_length=RESPONSE_SCHEMAS["standard"]["max_answer_length"]
    )
    
    if not answer_validation["valid"]:
        all_errors.extend(answer_validation["errors"])
        print("[SCHEMA] Answer validation failed:")
        for error in answer_validation["errors"]:
            print(f"    - {error}")
    else:
        print(f"[SCHEMA] Answer valid ({answer_validation['length']} chars)")
    
    selected_graph = state.get("selected_graph")
    if not selected_graph:
        all_errors.append("Missing required field: 'selected_graph'")
        print("[SCHEMA] Missing 'selected_graph'")
    else:
        print(f"[SCHEMA] selected_graph: {selected_graph}")
    
    domain_status = state.get("domain_graph_status")
    status_validation = validate_domain_status(domain_status)
    if not status_validation["valid"]:
        all_errors.extend(status_validation["errors"])
        print(f"[SCHEMA] Invalid domain_graph_status: {domain_status}")
    else:
        print(f"[SCHEMA] domain_graph_status: {domain_status}")
    
    if state.get("parallel_execution"):
        parallel_results = state.get("parallel_results")
        parallel_validation = validate_parallel_results(parallel_results)
        if not parallel_validation["valid"]:
            warnings.extend(parallel_validation["errors"])
            print("[SCHEMA] parallel_results issues:")
            for error in parallel_validation["errors"]:
                print(f"    - {error}")
        else:
            print(f"[SCHEMA] parallel_results valid ({len(parallel_results or [])} results)")
    
    validated_entities = state.get("validated_entities")
    if validated_entities:
        entities_validation = validate_validated_entities(validated_entities)
        if not entities_validation["valid"]:
            warnings.extend(entities_validation["errors"])
            print("[SCHEMA] validated_entities issues:")
            for error in entities_validation["errors"]:
                print(f"    - {error}")
        else:
            print("[SCHEMA] validated_entities valid")
    
    json_validation = validate_json_structure({
        "answer": answer,
        "selected_graph": selected_graph,
        "domain_graph_status": domain_status
    })
    
    if not json_validation["valid"]:
        all_errors.extend(json_validation["errors"])
        print("[SCHEMA] JSON serialization failed")
    else:
        print("[SCHEMA] JSON serializable")
    
    schema_valid = len(all_errors) == 0
    
    print(f"\n[SCHEMA] {'PASSED' if schema_valid else 'FAILED'}")
    print(f"[SCHEMA] Errors: {len(all_errors)}, Warnings: {len(warnings)}")
    print("="*80 + "\n")
    
    if not schema_valid:
        error_message = f"Schema validation failed: {'; '.join(all_errors)}"
        return {
            **state,
            "schema_valid": False,
            "schema_errors": all_errors,
            "schema_warnings": warnings,
            "error": error_message
        }
    
    return {
        **state,
        "schema_valid": True,
        "schema_errors": [],
        "schema_warnings": warnings
    }


def should_validate_schema(state: MainRouterState) -> bool:
    if state.get("answer"):
        return True
    
    if state.get("error"):
        return False
    
    if state.get("needs_clarification"):
        return False
    
    return False