import sqlite3

DB_NAME = 'database/student_finances.db'

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    # Таблица для сообщений
    cursor.execute('''
                   CREATE TABLE IF NOT EXISTS chat_history (
                                                               id INTEGER PRIMARY KEY AUTOINCREMENT,
                                                               role TEXT, -- 'user' или 'model'
                                                               content TEXT,
                                                               timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                   )
                   ''')
    conn.commit()
    conn.close()

