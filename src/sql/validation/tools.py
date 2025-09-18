from langchain_core.tools import Tool
import asyncio
import concurrent.futures
from src.sql.core.validation import validate_title, validate_actor, validate_director

def run_async_safe(coro):
    """
    Ejecuta corrutina de forma segura, manejando tanto contextos 
    con loop activo como sin loop.
    """
    try:
        # Intentar obtener el loop actual
        loop = asyncio.get_running_loop()
        
        # Si hay loop activo, ejecutar en thread separado
        def run_in_new_thread():
            return asyncio.run(coro)
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(run_in_new_thread)
            try:
                return future.result(timeout=30)  # Timeout de seguridad
            except concurrent.futures.TimeoutError:
                return {"status": "error", "message": "Operation timed out"}
                
    except RuntimeError:
        # No hay loop activo, usar asyncio.run directamente
        try:
            return asyncio.run(coro)
        except Exception as e:
            return {"status": "error", "message": f"Async execution failed: {str(e)}"}
    except Exception as e:
        return {"status": "error", "message": f"Unexpected error: {str(e)}"}

def validate_title_sync(title: str) -> str:
    """Wrapper síncrono para validar títulos"""
    try:
        result = run_async_safe(validate_title(title))
        return str(result) if result else '{"status": "error", "message": "No result returned"}'
    except Exception as e:
        return f'{{"status": "error", "message": "Title validation failed: {str(e)}"}}'

def validate_actor_sync(name: str) -> str:
    """Wrapper síncrono para validar actores"""
    try:
        result = run_async_safe(validate_actor(name))
        return str(result) if result else '{"status": "error", "message": "No result returned"}'
    except Exception as e:
        return f'{{"status": "error", "message": "Actor validation failed: {str(e)}"}}'

def validate_director_sync(name: str) -> str:
    """Wrapper síncrono para validar directores"""
    try:
        result = run_async_safe(validate_director(name))
        return str(result) if result else '{"status": "error", "message": "No result returned"}'
    except Exception as e:
        return f'{{"status": "error", "message": "Director validation failed: {str(e)}"}}'

# =============================================================================
# VALIDATION TOOLS
# =============================================================================

VALIDATE_TITLE_TOOL = Tool.from_function(
    func=validate_title_sync,
    name="validate_title",
    description=(
        "MANDATORY: Validates movie/TV show titles and returns validation status. "
        "CRITICAL: If status='ambiguous', you MUST show the list of options to the user "
        "and STOP processing until the user selects one. Do NOT continue with queries "
        "until user disambiguation. If status='resolved', you can continue with the returned UID."
    )
)

VALIDATE_ACTOR_TOOL = Tool.from_function(
    func=validate_actor_sync,
    name="validate_actor", 
    description=(
        "MANDATORY: Validates ACTOR names and returns validation status. "
        "CRITICAL: If status='ambiguous', you MUST show the list of options to the user "
        "and STOP processing until the user selects one. Do NOT continue until user chooses. "
        "If status='resolved' or status='ok', you can continue with the returned ID."
    )
)

VALIDATE_DIRECTOR_TOOL = Tool.from_function(
    func=validate_director_sync,
    name="validate_director",
    description=(
        "MANDATORY: Validates DIRECTOR names and returns validation status. "
        "CRITICAL: If status='ambiguous', you MUST show the list of options to the user "
        "and STOP processing until the user selects one. Do NOT continue until user chooses. "
        "If status='resolved' or status='ok', you can continue with the returned ID."
    )
)

# =============================================================================
# ALL TOOLS EXPORT
# =============================================================================

ALL_SQL_TOOLS = [
    VALIDATE_TITLE_TOOL,
    VALIDATE_ACTOR_TOOL,
    VALIDATE_DIRECTOR_TOOL
]