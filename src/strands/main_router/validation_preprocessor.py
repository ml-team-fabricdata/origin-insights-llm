import json
from strands import Agent
from src.strands.config.models import MODEL_NODE_EXECUTOR
from .state import MainRouterState
from src.strands.common.common_modules.validation import (
    validate_title, 
    validate_actor, 
    validate_director
)
VALIDATION_PREPROCESSOR_PROMPT = """You are a validation assistant. Your ONLY job is to call validation tools.

TASK: Identify the entity in the question and call the corresponding tool.

TOOLS AVAILABLE:
- validate_actor(name: str) - Use for actors/actresses
- validate_director(name: str) - Use for directors  
- validate_title(name: str) - Use for movies/TV shows

RULES:
1. If you see an actor name → CALL validate_actor("Name")
2. If you see a director name → CALL validate_director("Name")
3. If you see a movie/show name → CALL validate_title("Name")
4. If NO entity to validate → respond ONLY with: NO_VALIDATION_NEEDED
5. DO NOT provide explanations or additional text
6. DO NOT try to answer the question
7. ONLY call the tool or say NO_VALIDATION_NEEDED

EXAMPLES:
Question: "¿Cuál es la filmografía de Tom Hanks?"
Action: Call validate_actor("Tom Hanks")

Question: "películas de Spielberg"  
Action: Call validate_director("Steven Spielberg")

Question: "información sobre Inception"
Action: Call validate_title("Inception")

Question: "¿qué es el cine noir?"
Action: NO_VALIDATION_NEEDED

NOW: Analyze the question and call the appropriate tool immediately.
"""

ROUTING_MAP = {
    "business": "business_graph",
    "talent": "talent_graph",
    "content": "content_graph",
    "platform": "platform_graph",
    "common": "common_graph"
}


def _needs_user_input(validation_result: dict) -> bool:
    """Check if validation result requires user input (ambiguous)."""
    if not isinstance(validation_result, dict):
        return False
    return validation_result.get("status") == "ambiguous"


def _extract_entities(validation_result: dict, entity_type: str) -> dict:
    """Extract entities from validation result."""
    validated_entities = {
        "raw_validation": json.dumps(validation_result),
        "has_valid_entities": validation_result.get("status") == "ok"
    }
    
    if validation_result.get("status") != "ok":
        return validated_entities
    
    # Extract based on entity type
    if entity_type in ["actor", "director"]:
        entity_id = validation_result.get("id")
        entity_name = validation_result.get("name")
        
        if entity_id:
            validated_entities[f"{entity_type}_id"] = entity_id
            validated_entities[f"{entity_type}_name"] = entity_name
            print(f"[VALIDATION] Extracted {entity_type}_id: {entity_id}, name: {entity_name}")
    
    elif entity_type == "title":
        title_uid = validation_result.get("uid")
        title_name = validation_result.get("title")
        
        if title_uid:
            validated_entities["title_uid"] = title_uid
            validated_entities["title_name"] = title_name
            print(f"[VALIDATION] Extracted title_uid: {title_uid}, title: {title_name}")
    
    return validated_entities


async def validation_preprocessor_node(state: MainRouterState) -> MainRouterState:
    """
    Validates entities in the user's question using an Agent with structured tools.
    The Agent will identify the entity type and call the appropriate validation tool.
    """
    print("\n" + "="*80)
    print("VALIDATION PREPROCESSOR")
    print("="*80)
    print(f"Question: {state['question']}")
    
    # Skip if already validated
    if state.get("validation_done", False):
        print("[VALIDATION] Already validated, skipping...")
        return state
    
    # Skip if validation not required for this graph
    if state.get("skip_validation", False):
        print("[VALIDATION] Validation not required for this graph, skipping...")
        return {
            **state,
            "validation_done": True,
            "validation_status": "resolved",
            "needs_validation": False,
            "validated_entities": {"status": "skipped"}
        }
    
    print("[VALIDATION] Executing validation with Agent...")
    
    # Create Agent with validation tools
    validation_agent = Agent(
        name="validation_agent",
        system_prompt=VALIDATION_PREPROCESSOR_PROMPT,
        model=MODEL_NODE_EXECUTOR,
        tools=[validate_title, validate_actor, validate_director]
    )
    
    try:
        # Run agent with the question
        result = await validation_agent.arun(state['question'])
        
        # Extract validation result from agent response
        validation_result = None
        entity_type = None
        
        # Check if agent called a tool
        if hasattr(result, 'tool_calls') and result.tool_calls:
            tool_call = result.tool_calls[0]
            validation_result = tool_call.result
            
            # Determine entity type from tool name
            tool_name = tool_call.name
            if "actor" in tool_name:
                entity_type = "actor"
            elif "director" in tool_name:
                entity_type = "director"
            elif "title" in tool_name:
                entity_type = "title"
            
            print(f"[VALIDATION] Tool called: {tool_name}")
            print(f"[VALIDATION] Entity type: {entity_type}")
            print(f"[VALIDATION] Result: {json.dumps(validation_result, indent=2)}")
        
        # Check if no validation needed
        else:
            # Agent didn't call tools - check message
            message_text = ""
            if hasattr(result, 'message'):
                if isinstance(result.message, dict):
                    message_text = str(result.message.get('content', ''))
                else:
                    message_text = str(result.message)
            elif hasattr(result, 'content'):
                message_text = str(result.content)
            else:
                message_text = str(result)
            
            print(f"[VALIDATION] Agent response (no tool call): {message_text[:200]}")
            
            if "NO_VALIDATION_NEEDED" in message_text.upper():
                print("[VALIDATION] No validation needed")
                return {
                    **state,
                    "validation_done": True,
                    "validation_status": "resolved",
                    "needs_validation": False,
                    "validated_entities": {"status": "no_validation_needed"}
                }
            else:
                # Agent provided explanation instead of calling tool - this is an error
                print(f"[VALIDATION] ERROR: Agent didn't call tool, provided text instead")
                return {
                    **state,
                    "validation_done": True,
                    "validation_status": "error",
                    "needs_user_input": True,
                    "validation_message": "Validation agent failed to call appropriate tool",
                    "validated_entities": {"status": "error", "message": "No tool called"}
                }
        
        # Handle case where no validation result was obtained
        if not validation_result or not isinstance(validation_result, dict):
            print(f"[VALIDATION] ERROR: Invalid result format: {validation_result}")
            return {
                **state,
                "validation_done": True,
                "validation_status": "error",
                "needs_user_input": True,
                "validation_message": "Could not validate entity",
                "validated_entities": {"status": "error", "message": "Invalid result format"}
            }
        
        # Check for ambiguity
        if _needs_user_input(validation_result):
            print("[VALIDATION] Ambiguity detected - requires user input")
            print("="*80 + "\n")
            
            return {
                **state,
                "validation_done": True,
                "validation_status": "ambiguous",
                "needs_user_input": True,
                "needs_validation": True,
                "validation_message": validation_result,
                "validated_entities": {
                    "status": "ambiguous",
                    "message": validation_result
                }
            }
        
        # Check for not found
        if validation_result.get("status") == "not_found":
            print("[VALIDATION] Entity not found")
            print("="*80 + "\n")
            
            return {
                **state,
                "validation_done": True,
                "validation_status": "not_found",
                "needs_user_input": True,
                "needs_validation": True,
                "validation_message": validation_result,
                "validated_entities": {
                    "status": "not_found",
                    "message": validation_result
                }
            }
        
        # Extract entities
        validated_entities = _extract_entities(validation_result, entity_type)
        
        print("[VALIDATION] Validation completed successfully")
        print("="*80 + "\n")
        
        return {
            **state,
            "validation_done": True,
            "validation_status": "resolved",
            "needs_validation": True,
            "validated_entities": validated_entities
        }
    
    except Exception as e:
        print(f"[VALIDATION] ERROR: {str(e)}")
        print("="*80 + "\n")
        
        return {
            **state,
            "validation_done": True,
            "validation_status": "error",
            "needs_user_input": True,
            "validation_message": f"Validation error: {str(e)}",
            "validated_entities": {"status": "error", "message": str(e)}
        }


def should_validate(state: MainRouterState) -> str:
    """Router function to determine next node after validation."""
    if state.get("needs_user_input", False):
        return "END"
    
    if state.get("validation_done", False):
        selected = state.get("selected_graph", "common")
        return ROUTING_MAP.get(selected, "common_graph")
    
    return "validation_preprocessor"