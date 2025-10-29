from app.strands.infrastructure.database.connection import db
from app.util.embeddings import embeddings_generator


def save_message(session_id, question, answer):
    """Guarda mensaje en la BD para mantener el historial"""
    conn = db.get_connection()
    cursor = conn.cursor()
    try:
        content = f"QUESTION:\n{question}\n\n\nANSWER:\n{answer}"
        embedding = embeddings_generator.get_embedding(content)
        cursor.execute(
            "INSERT INTO ms.chat_message (session_id, question, answer, embedding) VALUES (%s, %s, %s, %s)",
            (session_id, question, answer, str(embedding))
        )
        conn.commit()
    finally:
        cursor.close()


def load_messages(session_id, context=None, limit=5):
    """
    Carga los mensajes de la sesion.
    Si se provee contexto, agrega los mensajes mas relevantes ademas de los mas recientes.
    """
    conn = db.get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT count(1) FROM ms.chat_message WHERE session_id = %s", (session_id,))

        # Busca los mas relevantes si se provee contexto
        relevant = []
        if context and cursor.fetchone()[0] > limit:
            embedding = embeddings_generator.get_embedding(context)
            cursor.execute(
                "SELECT question, answer FROM ms.chat_message WHERE session_id = %s ORDER BY embedding <=> %s LIMIT %s",
                (session_id, str(embedding), limit)
            )
            relevant = cursor.fetchall()

        # Busca los mas recientes
        cursor.execute(
            "SELECT question, answer FROM ms.chat_message WHERE session_id = %s ORDER BY created_at DESC LIMIT %s",
            (session_id, limit)
        )
        latest = cursor.fetchall()[::-1]  # mas antiguos primero

        messages = []
        for question, answer in (relevant + latest):
            messages.append({"role": "user", "content": [{"text": str(question)}]})
            messages.append({"role": "assistant", "content": [{"text": str(answer)}]})
        return messages
    finally:
        cursor.close()
