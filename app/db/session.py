from app.strands.infrastructure.database.connection import db


def session_exists(session_id):
    conn = db.get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT 1 FROM ms.oi_chat_session WHERE id = %s", (session_id,))
        return cursor.fetchone() is not None
    finally:
        cursor.close()


def create_session(session_id, user_id, title):
    conn = db.get_connection()
    cursor = conn.cursor()
    try:
        sessions_exists = session_exists(session_id)
        if not sessions_exists:
            cursor.execute(
                "INSERT INTO ms.oi_chat_session (id, user_id, title) VALUES (%s, %s, %s)",
                (session_id, user_id, title)
            )
            conn.commit()
    finally:
        cursor.close()
