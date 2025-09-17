# Standard library imports
import os
import random
import sys
import time

# Path setup
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

# Third party imports
import streamlit as st
from langchain_core.messages import AIMessage, HumanMessage, trim_messages

# Local imports
from core.agent import get_agent
from core.supervisor import get_events_last_message

class ChatBot:
    """
    Clase principal del chatbot con gestión de conversación y métricas
    """

    SQL_MAX_RESULTS = 20
    VERBOSE = True

    def __init__(self, model_api='bedrock'):
        """
        Inicializar chatbot con configuración de agente
        
        Args:
            model_api (str, optional): API del modelo de IA
        """
        self._agent = get_agent(model_api=model_api)
        self._history = []

    def answer_question(self, user_input):
        """
        Procesar pregunta del usuario con métricas de tiempo
        
        Args:
            user_input (str): Consulta del usuario
        
        Returns:
            Tuple[str, float]: Respuesta y tiempo de ejecución
        """
        start_time = time.time()
        
        # Gestionar historial de conversación - mínimo para velocidad extrema
        self._history = trim_messages(
            messages=self._history, 
            strategy="last", 
            start_on="human", 
            include_system=True, 
            max_tokens=5000,  # Mínimo para velocidad extrema
            token_counter=len
        )
        self._history.append(HumanMessage(user_input))

        # Obtener respuesta del agente
        last_message = get_events_last_message(
            self._agent, 
            {"messages": self._history}, 
            verbose=self.VERBOSE
        )
        self._history.append(AIMessage(last_message))
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        return last_message, execution_time
            

    def clear_history(self):
        """
        Limpiar el historial de conversación
        """
        self._history = []

def generate_movie_questions():
    """
    Generar preguntas de ejemplo para el chatbot
    
    Returns:
        List[str]: Lista de preguntas sugeridas
    """
    example_questions = [
        "¿Cuál fue el rating de Avengers Endgame?",
        "Top 5 películas de Marvel en 2022",
        "Directores más populares en 2023",
        "Series de ciencia ficción con mejor puntuación",
        "Películas de Christopher Nolan"
    ]
    return random.sample(example_questions, 3)

def main():
    """
    Función principal para la interfaz Streamlit
    """
    # Configuración de página
    st.set_page_config(
        page_title="🎬 Movie & Series Bot",
        page_icon="🎬",
        layout="wide"
    )
    
    # Título principal
    st.title("🎬 Movie & Series Intelligence Bot")
    st.markdown("### 🔍 Consulta nuestra base de datos optimizada de películas y series")
    
    # Inicializar chatbot en session state
    if 'chatbot' not in st.session_state:
        with st.spinner("🚀 Inicializando bot con agente optimizado..."):
            st.session_state.chatbot = ChatBot()
            st.session_state.conversation_history = []
            st.session_state.total_queries = 0
            st.session_state.avg_response_time = 0
    
    # Layout principal
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.subheader("💬 Haz tu consulta")
        
        # Input principal
        user_question = st.text_area(
            "Pregunta sobre películas, series, ratings, plataformas, cast, etc:",
            placeholder="Ej: ¿Cuál fue el rating de Avengers Endgame el 15 de abril de 2019?",
            height=120,
            key="main_query"
        )
        
        # Botones de acción
        col_btn1, col_btn2, col_btn3 = st.columns([1, 1, 1])
        
        with col_btn1:
            ask_button = st.button("🔍 Consultar", type="primary")
        
        with col_btn2:
            generate_button = st.button("💡 Generar Pregunta")
            
        with col_btn3:
            clear_button = st.button("🗑️ Limpiar Chat")
    
    with col2:
        st.subheader("📊 Estadísticas")
        
        if st.session_state.total_queries > 0:
            st.metric("Total Consultas", st.session_state.total_queries)
            st.metric("Tiempo Promedio", f"{st.session_state.avg_response_time:.1f}s")
        
        st.subheader("ℹ️ Información")
        st.info("""
        **Puedes consultar:**
        - 📈 Ratings por fecha
        - 📺 Plataformas disponibles  
        - 🎭 Cast y crew
        - 🏆 Rankings y top 10s
        - 📅 Fechas de estreno
        - 🎬 Metadatos de contenido
        """)
        
        # Estado del sistema
        st.subheader("⚡ Estado del Sistema")
        st.success("✅ Agente Optimizado Activo")
        st.success("✅ Cache Inteligente ON")
        st.success("✅ Límites Automáticos ON")
    
    # Generar pregunta de ejemplo
    if generate_button:
        example_questions = generate_movie_questions()
        st.subheader("💡 Preguntas Sugeridas")
        
        for i, question in enumerate(example_questions):
            if st.button(f"📝 {question}", key=f"suggestion_{i}"):
                st.session_state.main_query = question
                st.rerun()
    
    # Limpiar conversación
    if clear_button:
        st.session_state.chatbot.clear_history()
        st.session_state.conversation_history = []
        st.success("🗑️ Conversación limpiada")
    
    # Procesar consulta
    if ask_button and user_question.strip():
        with st.spinner("🔍 Consultando base de datos optimizada..."):
            # Añadir pregunta al historial
            st.session_state.conversation_history.append({
                "role": "user", 
                "content": user_question,
                "timestamp": time.time()
            })
            
            # Obtener respuesta usando la función original
            response, exec_time = st.session_state.chatbot.answer_question(user_question)
            
            # Añadir respuesta al historial
            st.session_state.conversation_history.append({
                "role": "assistant",
                "content": response,
                "timestamp": time.time(),
                "exec_time": exec_time
            })
            
            # Actualizar estadísticas
            st.session_state.total_queries += 1
            if exec_time > 0:
                current_avg = st.session_state.avg_response_time
                st.session_state.avg_response_time = (
                    (current_avg * (st.session_state.total_queries - 1) + exec_time) / 
                    st.session_state.total_queries
                )
            
            # Mostrar tiempo de respuesta
            if exec_time > 0:
                if exec_time < 3:
                    st.success(f"🚀 Respuesta ULTRA rápida: {exec_time:.2f} segundos")
                elif exec_time < 5:
                    st.success(f"⚡ Respuesta súper rápida: {exec_time:.2f} segundos")
                elif exec_time < 8:
                    st.info(f"✅ Respuesta rápida: {exec_time:.2f} segundos")
                elif exec_time < 12:
                    st.warning(f"⚠️ Respuesta lenta: {exec_time:.2f} segundos")
                else:
                    st.error(f"🐌 Muy lento: {exec_time:.2f} segundos - revisar optimizaciones")
    
    # Mostrar historial de conversación
    if st.session_state.conversation_history:
        st.subheader("💭 Historial de Conversación")
        
        # Mostrar últimas 8 interacciones
        recent_history = st.session_state.conversation_history[-16:]  # 8 pares pregunta-respuesta
        
        for i, message in enumerate(reversed(recent_history)):
            if message["role"] == "user":
                st.markdown(f"""
                <div style="background-color: #000000; padding: 15px; border-radius: 10px; margin: 10px 0; border-left: 4px solid #ffffff;">
                    <strong>🙋‍♂️ Tu pregunta:</strong><br>
                    {message["content"]}
                </div>
                """, unsafe_allow_html=True)
            else:
                exec_info = ""
                if "exec_time" in message and message["exec_time"] > 0:
                    exec_info = f" <small>(⚡ {message['exec_time']:.1f}s)</small>"
                
                st.markdown(f"""
                <div style="background-color: #000000; padding: 15px; border-radius: 10px; margin: 10px 0; border-left: 4px solid #ffffff;">
                    <strong>🤖 Respuesta del Bot:</strong>{exec_info}<br>
                    {message["content"]}
                </div>
                """, unsafe_allow_html=True)
    
    # Footer con información adicional
    st.markdown("---")
    col_footer1, col_footer2 = st.columns([1, 1])
    
    with col_footer1:
        st.markdown("**🎯 Bot optimizado para consultas de entretenimiento**")
        
    with col_footer2:
        if st.session_state.conversation_history:
            st.markdown(f"**📈 {len([m for m in st.session_state.conversation_history if m['role'] == 'user'])} consultas en esta sesión**")

if __name__ == '__main__':
    main()