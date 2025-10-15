from strands import Agent
from src.strands.platform.prompt_platform import PLATFORM_PROMPT
from src.strands.utils.config import MODEL_CLASSIFIER
from src.strands.utils.supervisor_helpers import (
    main_supervisor,
    create_route_from_supervisor,
    format_response
)
from .state import State


async def platform_classifier(state: State) -> State:
    if state.get("classification_done"):
        return state
    
    agent = Agent(
        model=MODEL_CLASSIFIER,
        system_prompt=PLATFORM_PROMPT
    )

    response = await agent.invoke_async(state['question'])
    
    if isinstance(response, dict):
        decision = str(response.get('message', response)).strip().upper()
    else:
        decision = str(getattr(response, "message", response)).strip().upper()
    
    if decision not in ["AVAILABILITY", "PRESENCE"]:
        if "AVAILABILITY" in decision:
            decision = "AVAILABILITY"
        elif "PRESENCE" in decision:
            decision = "PRESENCE"
        else:
            decision = "PRESENCE"
    
    task = decision.lower()
    
    return {
        **state,
        "task": task,
        "classification_done": True
    }


route_from_main_supervisor = create_route_from_supervisor("platform_node")