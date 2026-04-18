import sqlite3
import os
import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_NAME = os.path.join(BASE_DIR, "database", "../student_finances.db")

from datetime import datetime

def get_survival_info():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # 1. Берем данные профиля
    cursor.execute('SELECT balance, income_date, mandatory_payments, planned_expenses FROM user_profile LIMIT 1')
    profile = cursor.fetchone()

    # 2. Берем сумму уже совершенных трат из таблицы expenses
    cursor.execute('SELECT SUM(amount) FROM expenses')
    total_spent = cursor.fetchone()[0] or 0
    conn.close()

    if not profile:
        return "Профиль не заполнен. Вызови /start"

    initial_balance, income_date_str, mandatory, planned = profile

    # ТЕКУЩИЙ РЕАЛЬНЫЙ БАЛАНС (за вычетом того, что уже потратили)
    current_balance = initial_balance - total_spent

    # СВОБОДНЫЕ ДЕНЬГИ (минус обязательные платежи и планы)
    free_money = current_balance - mandatory - planned

    # СЧИТАЕМ ДНИ ДО СТИПЕНДИИ
    # Допустим, income_date_str это просто число месяца (например "25")
    today = datetime.now()
    try:
        income_day = int(income_date_str)
        if income_day > today.day:
            days_left = income_day - today.day
        else:
            # Если день уже прошел в этом месяце, значит стипа в следующем
            days_left = 30 - today.day + income_day
    except:
        days_left = 7 # Заглушка, если дата кривая

    # ДНЕВНОЙ ЛИМИТ
    daily_limit = free_money / days_left if days_left > 0 else free_money

    return {
        "current_balance": round(current_balance, 2),
        "days_left": days_left,
        "daily_limit": round(daily_limit, 2),
        "free_money": round(free_money, 2)
    }


def get_expenses_report(category: str = None, month: int = None) -> str:
    """
    Получает отчет по расходам.
    Можно фильтровать по категории и по номеру месяца.

    category: Название категории (Еда, Транспорт и т.д.)
    month: Номер месяца (1-12), за который нужен отчет.
    """
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()

        # Базовый запрос
        query = "SELECT SUM(amount) FROM expenses WHERE 1=1"
        params = []

        # Добавляем фильтр по категории, если она есть
        if category:
            query += " AND category = ?"
            params.append(category)

        # Добавляем фильтр по месяцу (используем встроенную функцию SQLite strftime)
        if month:
            # Превращаем число месяца в формат '01', '02' и т.д.
            month_str = f"{month:02d}"
            query += " AND strftime('%m', date) = ?"
            params.append(month_str)

        cursor.execute(query, params)
        total = cursor.fetchone()[0]
        conn.close()

        # Формируем человечный ответ для Маркуса
        msg = "Твой отчет:"
        if month: msg += f" за {month}-й месяц"
        if category: msg += f" в категории '{category}'"

        if total:
            return f"{msg}: {total} сом."
        else:
            return f"{msg}: данных пока нет."

    except Exception as e:
        return f"Ошибка при расчете отчета: {e}"

def add_expense(amount: float, category: str, desc: str) -> str:
    """
    Записывает расход пользователя в базу данных.
    Аргументы:
    amount: сумма потраченных денег (число)
    category: категория (Еда, Транспорт, Учеба, Развлечения, Другое)
    desc: краткое описание покупки
    """
    try:
        conn = sqlite3.connect(DB_NAME)
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