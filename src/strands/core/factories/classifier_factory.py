"""
Generic Classifier Factory

This module provides a factory function to create domain classifier functions,
eliminating code duplication across different domain graphs.

All domain classifiers follow the same pattern:
1. Check if already classified
2. Call LLM with domain-specific prompt
3. Parse and validate response
4. Normalize to valid option with fallback
5. Return updated state

This factory encapsulates that pattern.
"""

from typing import List, TypedDict, Dict, Any
from strands import Agent
from src.strands.config.models import MODEL_CLASSIFIER


def create_classifier(
    name: str,
    prompt: str,
    valid_options: List[str],
    verbose: bool = False
):
    """
    Factory function to create a domain classifier.
    
    Args:
        name: Classifier name (e.g., "business", "content")
        prompt: System prompt for the classifier
        valid_options: List of valid classification options (uppercase)
        verbose: Whether to print detailed logging
        
    Returns:
        Async classifier function that takes State and returns State
        
    Example:
        >>> business_classifier = create_classifier(
        ...     name="business",
        ...     prompt=BUSINESS_PROMPT,
        ...     valid_options=["PRICING", "RANKINGS", "INTELLIGENCE"],
        ...     verbose=True
        ... )
    """
    
    async def classifier(state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Classifier function created by factory.
        
        Args:
            state: Graph state with 'question' and other fields
            
        Returns:
            Updated state with 'task' and 'classification_done' set
        """
        
        if verbose:
            print(f"\n{'='*80}")
            print(f"[{name.upper()} CLASSIFIER] STARTING")
            print(f"{'='*80}")
            print(f"[{name.upper()} CLASSIFIER] Clasificando pregunta: {state['question']}")
            print(f"[{name.upper()} CLASSIFIER] tool_calls_count: {state.get('tool_calls_count', 0)}")
            print(f"[{name.upper()} CLASSIFIER] task: {state.get('task', 'None')}")
            print(f"[{name.upper()} CLASSIFIER] classification_done: {state.get('classification_done', False)}")
        
        # Skip if already classified
        if state.get("classification_done"):
            if verbose:
                print(f"[{name.upper()} CLASSIFIER] Ya clasificado, saltando...")
            return state
        
        if verbose:
            print(f"[{name.upper()} CLASSIFIER] Llamando al Agent con MODEL_CLASSIFIER: {MODEL_CLASSIFIER}")
            print(f"[{name.upper()} CLASSIFIER] Prompt: {prompt[:100]}...")
        
        # Call LLM with domain prompt
        agent = Agent(model=MODEL_CLASSIFIER, system_prompt=prompt)
        response = await agent.invoke_async(state['question'])
        
        if verbose:
            print(f"[{name.upper()} CLASSIFIER] Response type: {type(response)}")
        
        # Parse response
        if isinstance(response, dict):
            decision = str(response.get('message', response)).strip().upper()
        else:
            decision = str(getattr(response, "message", response)).strip().upper()
        
        if verbose:
            print(f"[{name.upper()} CLASSIFIER] Decision raw: '{decision}'")
        
        # Validate and normalize decision
        if decision not in valid_options:
            # Try to find a match within the response
            matched = False
            for option in valid_options:
                if option in decision:
                    decision = option
                    matched = True
                    break
            
            # Fall back to first option if no match
            if not matched:
                if verbose:
                    print(f"[{name.upper()} CLASSIFIER] Decision no válida, usando primera opción: {valid_options[0]}")
                decision = valid_options[0]
        
        task = decision.lower()
        
        if verbose:
            print(f"[{name.upper()} CLASSIFIER] Task final: {task}")
            print(f"{'='*80}\n")
        
        return {
            **state,
            "task": task,
            "classification_done": True
        }
    
    # Set function name for better debugging
    classifier.__name__ = f"{name}_classifier"
    classifier.__doc__ = f"""
    {name.title()} domain classifier.
    
    Valid options: {', '.join(valid_options)}
    
    Created by classifier_factory.create_classifier()
    """
    
    return classifier


def create_simple_classifier(
    name: str,
    prompt: str,
    valid_options: List[str]
):
    """
    Create a simple classifier without verbose logging.
    Alias for create_classifier with verbose=False.
    """
    return create_classifier(
        name=name,
        prompt=prompt,
        valid_options=valid_options,
        verbose=False
    )


def create_verbose_classifier(
    name: str,
    prompt: str,
    valid_options: List[str]
):
    """
    Create a verbose classifier with detailed logging.
    Alias for create_classifier with verbose=True.
    """
    return create_classifier(
        name=name,
        prompt=prompt,
        valid_options=valid_options,
        verbose=True
    )
