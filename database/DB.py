import sqlite3

DB_NAME = 'student_finances.db'

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    # Таблица расходов
    cursor.execute('''
                   CREATE TABLE IF NOT EXISTS expenses (
                                                           id INTEGER PRIMARY KEY AUTOINCREMENT,
                                                           amount REAL,
                                                           category TEXT,
                                                           desc TEXT,
                                                           date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                   )
                   ''')
    # Таблица истории сообщений (для памяти ИИ)
    cursor.execute('''
                   CREATE TABLE IF NOT EXISTS history (
                                                          id INTEGER PRIMARY KEY AUTOINCREMENT,
                                                          role TEXT,
                                                          content TEXT,
                                                          date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                   )
                   ''')
    conn.commit()
    conn.close()


# Инициализируем базу при запуске файла
if __name__ == "__main__":
    init_db()
    print("База данных готова!")