# Standard library imports
import time, re
from typing import List, Optional, Dict, Tuple

from langchain_core.messages import AIMessage, ToolMessage
from core.thread_manager import get_new_thread_id, get_or_create_thread_id, ThreadRepository

def get_events_last_message(agent, state, thread_id=None, user_id=None, verbose=True):
    """
    Procesar eventos con thread_id dinámico
    
    Args:
        agent: Agente de LangGraph
        state: Estado con mensajes
        thread_id: Thread específico o None para crear uno nuevo
        user_id: ID del usuario para asociar al thread
        verbose: Mostrar logs detallados
    """
    regex_exp = re.compile(r'(te recomiendo|te sugiero|recomendaciones|sugerencias?|consejos?|tips?|curiosidades?|datos curiosos?|características|propiedades?|observaciones?|notas?|bonus|extra) ?:.*', re.I | re.DOTALL)

    # Generar thread_id si no se proporciona
    if not thread_id:
        thread_id = get_new_thread_id(user_id=user_id, session_type="chat")
        if verbose:
            print(f"🆕 Nuevo thread creado: {thread_id}")
    else:
        if verbose:
            print(f"📂 Usando thread existente: {thread_id}")

    print("ENTRA A GET EVENTS LAST MESSAGE")
    start_time = time.time()
    last_message = None

    config = {"configurable": {"thread_id": thread_id}}
    events = agent.stream(state, config=config, stream_mode="values")

    for event in events:
        msg = event["messages"][-1]
        last_message = msg.content

        tool_info = None
        if isinstance(msg, AIMessage):
            tcalls = msg.additional_kwargs.get("tool_calls") or getattr(msg, "tool_calls", None)
            if tcalls:
                tool_info = " | ".join(
                    f"CALL → {tc['name']}({tc.get('id','')})"
                    for tc in tcalls
                    if isinstance(tc, dict) and "name" in tc
                )
        elif isinstance(msg, ToolMessage):
            tool_info = f"RETURN ← {msg.name}"

        event["messages"] = msg
        step_time = round(time.time() - start_time, 2)

        if verbose:
            base = f"({agent.name:16}) Time: {step_time:5}s | {event}"
            print(base if not tool_info else base + f"  [{tool_info}]")

    st = agent.get_state(config)
    print(f"[DEBUG] Memoria thread_id={thread_id} tiene {len(st.values.get('messages', []))} mensajes")

    print("LAST_MESSAGE", last_message)
    last_message = regex_exp.sub('', last_message)
    print("NOW", last_message)

    return last_message or "No response generated", thread_id


class SessionManager:
    """Gestor de sesiones con thread_id dinámicos"""
    
    def __init__(self):
        self.repo = ThreadRepository()
        self.active_sessions = {}
    
    def create_session(self, user_id: Optional[str] = None, 
                      session_type: str = "chat",
                      use_daily: bool = False,
                      context: Optional[str] = None) -> str:
        """
        Crear nueva sesión con thread_id único
        
        Returns:
            thread_id generado
        """
        thread_id = get_or_create_thread_id(
            user_id=user_id,
            use_daily=use_daily,
            context=context
        )
        
        self.active_sessions[thread_id] = {
            'user_id': user_id,
            'created_at': time.time(),
            'last_activity': time.time(),
            'message_count': 0
        }
        
        return thread_id
    
    def get_or_create_session(self, user_id: str, continue_last: bool = False) -> str:
        """
        Obtener sesión existente o crear una nueva
        
        Args:
            user_id: ID del usuario
            continue_last: Si True, continúa la última sesión del usuario
        """
        if continue_last:
            user_threads = self.repo.get_user_threads(user_id, limit=1)
            if user_threads:
                return user_threads[0]['thread_id']
        
        return self.create_session(user_id=user_id)
    
    def process_with_session(self, agent, state, 
                            user_id: Optional[str] = None,
                            thread_id: Optional[str] = None,
                            continue_last: bool = False,
                            verbose: bool = True) -> Tuple[str, str]:
        """
        Procesar mensaje con gestión automática de sesión
        
        Returns:
            Tuple de (respuesta, thread_id)
        """
        # Determinar thread_id
        if thread_id:
            # Usar el proporcionado
            final_thread_id = thread_id
        elif user_id and continue_last:
            # Continuar última sesión del usuario
            final_thread_id = self.get_or_create_session(user_id, continue_last=True)
        else:
            # Crear nueva sesión
            final_thread_id = self.create_session(user_id=user_id)
        
        # Procesar
        response, used_thread_id = get_events_last_message(
            agent, 
            state, 
            thread_id=final_thread_id,
            user_id=user_id,
            verbose=verbose
        )
        
        # Actualizar estadísticas
        if final_thread_id in self.active_sessions:
            self.active_sessions[final_thread_id]['last_activity'] = time.time()
            self.active_sessions[final_thread_id]['message_count'] += 1
        
        return response, used_thread_id
    
    def get_session_info(self, thread_id: str) -> Optional[Dict]:
        """Obtener información de una sesión"""
        if thread_id in self.active_sessions:
            return self.active_sessions[thread_id]
        
        # Buscar en base de datos si no está en memoria
        exists = self.repo.get_thread_exists(thread_id)
        if exists:
            return {'thread_id': thread_id, 'exists_in_db': True}
        
        return None
    
    def list_recent_sessions(self, hours: int = 24) -> List[str]:
        """Listar sesiones recientes"""
        return self.repo.get_recent_threads(hours)


# Instancia global del gestor de sesiones
_session_manager = SessionManager()

def get_session_manager() -> SessionManager:
    """Obtener instancia del gestor de sesiones"""
    return _session_manager


# Función wrapper para compatibilidad con código existente
def process_message(agent, state, user_id=None, thread_id=None, verbose=True):
    """
    Wrapper simplificado para procesar mensajes con thread_id automático
    
    Ejemplos:
        # Nueva sesión para usuario
        response, thread_id = process_message(agent, state, user_id="user123")
        
        # Continuar sesión específica
        response, thread_id = process_message(agent, state, thread_id="existing_thread")
        
        # Sesión anónima nueva
        response, thread_id = process_message(agent, state)
    """
    if not thread_id and not user_id:
        # Sesión anónima
        thread_id = get_new_thread_id(session_type="anonymous")
    
    return get_events_last_message(agent, state, thread_id, user_id, verbose)


# Mantener compatibilidad con función original si es necesaria
def get_events_last_message_legacy(agent, state, thread_id="default", verbose=True):
    """Versión legacy para compatibilidad"""
    return get_events_last_message(agent, state, thread_id, None, verbose)[0]