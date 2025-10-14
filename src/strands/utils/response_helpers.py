"""
Helper functions for extracting and processing Agent responses.

Eliminates code duplication across the codebase.
"""

from typing import Any, Union


def extract_message(response: Any) -> str:
    """
    Extract the message from an Agent response.
    
    Handles both dict and object responses.
    
    Args:
        response: Response from Agent.invoke_async()
        
    Returns:
        The message string
        
    Examples:
        >>> extract_message({'message': 'Hello'})
        'Hello'
        >>> extract_message(SomeObject(message='Hello'))
        'Hello'
    """
    if isinstance(response, dict):
        return str(response.get('message', response))
    return str(getattr(response, "message", response))


def extract_decision(response: Any) -> str:
    """
    Extract and normalize a classification decision.
    
    Converts to uppercase and strips whitespace.
    
    Args:
        response: Response from Agent.invoke_async()
        
    Returns:
        Normalized decision string (uppercase, stripped)
        
    Examples:
        >>> extract_decision({'message': 'actors'})
        'ACTORS'
        >>> extract_decision({'message': '  Directors  '})
        'DIRECTORS'
    """
    message = extract_message(response)
    return message.strip().upper()


def extract_content_from_response(response: Any) -> str:
    """
    Extract content from various response formats.
    
    Handles:
    - Dict with 'content' key
    - Dict with 'message' key
    - Object with 'content' attribute
    - Object with 'message' attribute
    - String responses
    
    Args:
        response: Response from Agent or LLM
        
    Returns:
        The content string
    """
    if isinstance(response, str):
        return response
    
    if isinstance(response, dict):
        # Try 'content' first, then 'message'
        if 'content' in response:
            content = response['content']
            # Handle nested content structure
            if isinstance(content, list) and len(content) > 0:
                if isinstance(content[0], dict) and 'text' in content[0]:
                    return content[0]['text']
            return str(content)
        return str(response.get('message', response))
    
    # Try object attributes
    if hasattr(response, 'content'):
        return str(response.content)
    if hasattr(response, 'message'):
        return str(response.message)
    
    # Fallback
    return str(response)


def validate_decision(
    decision: str,
    valid_options: list[str],
    fallback: str = None
) -> str:
    """
    Validate a decision against valid options.
    
    If decision is not in valid_options, tries to extract
    a valid option from the decision string.
    
    Args:
        decision: The decision to validate
        valid_options: List of valid decision strings
        fallback: Fallback value if no valid option found
        
    Returns:
        A valid decision string
        
    Examples:
        >>> validate_decision('ACTORS', ['ACTORS', 'DIRECTORS'])
        'ACTORS'
        >>> validate_decision('The answer is ACTORS', ['ACTORS', 'DIRECTORS'])
        'ACTORS'
        >>> validate_decision('unknown', ['ACTORS', 'DIRECTORS'], 'ACTORS')
        'ACTORS'
    """
    decision_upper = decision.upper()
    
    # Exact match
    if decision_upper in valid_options:
        return decision_upper
    
    # Try to extract from string
    for option in valid_options:
        if option.upper() in decision_upper:
            return option.upper()
    
    # Fallback
    if fallback:
        return fallback
    
    # Return first valid option as last resort
    return valid_options[0] if valid_options else decision_upper
