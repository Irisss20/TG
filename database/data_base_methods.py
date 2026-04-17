import sqlite3
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_NAME = os.path.join(BASE_DIR, "database", "../student_finances.db")


def add_expense(amount: float, category: str, desc: str) -> str:
    """
    Записывает расход пользователя в базу данных.
    Аргументы:
    amount: сумма потраченных денег (число)
    category: категория (Еда, Транспорт, Учеба, Развлечения, Другое)
    desc: краткое описание покупки
    """
    try:
        conn = sqlite3.connect('database/student_finances.db')
        cursor = conn.cursor()
        cursor.execute('INSERT INTO expenses (amount, category, desc) VALUES (?, ?, ?)',
                       (amount, category, desc))
        conn.commit()
        conn.close()
        return f"Успешно записано: {amount} руб. в категорию {category}"
    except Exception as e:
        return f"Ошибка при записи: {e}"

def get_all_expenses():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT SUM(amount) FROM expenses')
    total = cursor.fetchone()[0]
    conn.close()
    return total if total else 0

def save_user_profile(data):
    """
    Эта функция только вносит данные.
    Она ожидает на вход уже готовый словарь (dict).
    """
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()


        cursor.execute('''
                       INSERT INTO user_profile
                       (balance, income_date, income_amount, planned_expenses, mandatory_payments)
                       VALUES (?, ?, ?, ?, ?)
                       ''', (
                           data.get('balance', 0),
                           data.get('income_date', ''),
                           data.get('income_amount', 0),
                           data.get('planned_expenses', 0),
                           data.get('mandatory_payments', 0)
                       ))

        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Ошибка при сохранении в БД: {e}")
        return False


def get_user_profile():
    """
    Достает сохраненные данные профиля из базы.
    """
    try:
        conn = sqlite3.connect(DB_NAME)
        # Это заставит sqlite возвращать данные, к которым можно обращаться по именам колонок
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute('SELECT * FROM user_profile LIMIT 1')
        row = cursor.fetchone()

        conn.close()

        if row:
            # Превращаем результат в обычный словарь Python
            return dict(row)
        return None # Если в базе еще ничего нет
    except Exception as e:
        print(f"Ошибка при чтении из БД: {e}")
        return None


def save_chat_message(role, content):
    """Сохраняет сообщение в базу"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('INSERT INTO chat_history (role, content) VALUES (?, ?)', (role, content))
    conn.commit()
    conn.close()

def load_chat_history(limit=20):
    """Загружает последние N сообщений для инициализации чата"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT role, content FROM chat_history ORDER BY id DESC LIMIT ?', (limit,))
    rows = cursor.fetchall()
    conn.close()

    # Форматируем для Gemini: [{"role": "user", "parts": ["текст"]}, ...]
    history = []
    for role, content in reversed(rows):
        history.append({"role": role, "parts": [{"text": content}]})
    return history