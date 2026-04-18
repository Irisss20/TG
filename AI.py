import json
import os
import date as d
import net as n
from google import genai
from google.genai import types
from dotenv import load_dotenv
import database.data_base_methods as db_m


load_dotenv()
API = os.getenv('API')
sys_ins = os.getenv('SYS_INSTRUCTIONS')
client = genai.Client(api_key=API)

#############################################################################
def extract_report(user_response_text): # функция для работы другой функции
    """
    Превращает ответы пользователя на 4 вопроса в структурированный JSON
    """
    prompt = f"""
    Пользователь ответил на вопросы о своих финансах: "{user_response_text}"
    
    Твоя задача — извлечь данные и вернуть СТРОГО JSON с ключами:
    - balance (число: текущий остаток)
    - income_date (строка: дата следующего дохода)
    - income_amount (число: сумма дохода)
    - planned_expenses (число: сумма планируемых трат)
    - mandatory_payments (число: сумма обязательных платежей)
    
    Если каких-то данных нет, ставь 0. Не пиши никакого текста, только JSON.
    """

    response = client.models.generate_content(
        model='gemini-3.1-flash-lite-preview',
        config=types.GenerateContentConfig(
            response_mime_type="application/json" # ГАРАНТИЯ ЧИСТОГО JSON
        ),
        contents=prompt
    )

    # Превращаем строку из ответа ИИ в настоящий словарь Python
    return json.loads(response.text)
#############################################################################


date, time = d.get_internet_time()
hidden = f"\n {date} {time} "
currency_kg = n.get_currency()

def start_markus():
    # 1. Получаем финансовую сводку из базы
    stats = db_m.get_survival_info()

    if isinstance(stats, dict):
        survival_context = f"""
        ВНИМАНИЕ, ТВОИ ГРАНИЦЫ:
        - Реальный остаток: {stats['current_balance']} руб.
        - Дней до стипендии: {stats['days_left']}.
        - ТВОЙ ЖЕСТКИЙ ЛИМИТ В ДЕНЬ: {stats['daily_limit']} руб.
        - Денег на жизнь после всех выплат: {stats['free_money']} руб.
        """
    else:
        survival_context = "Данные профиля не заполнены. Срочно требуй от пользователя заполнить баланс и дату стипендии!"

    # 2. Загружаем историю сообщений для памяти
    past_history = db_m.load_chat_history(limit=20)

    # 3. Создаем единую системную инструкцию (личность + цифры)
    full_system_instruction = f"""
    Ты Маркус — финансовый надзиратель и ассистент студента. 
    
    {survival_context}
    
    ТВОИ ПРАВИЛА:
    1. Если пользователь хочет купить что-то, что превышает ДНЕВНОЙ ЛИМИТ, ты ДОЛЖЕН ругаться, иронизировать и предупреждать о голодной смерти.
    2. Если баланс близок к нулю, отвечай только капсом и паникуй.
    3. Твоя цель — чтобы пользователь дожил до стипендии.
    4. Хвали только за супер-экономию.
    5. Для записи трат ВСЕГДА используй инструмент add_expense.
    6. Для отчетов ВСЕГДА используй инструмент get_expenses_report.
    """

    # 4. Создаем чат-сессию (один раз со всеми настройками)
    chat = client.chats.create(
        model='gemini-3.1-flash-lite-preview',
        config=types.GenerateContentConfig(
            system_instruction=sys_ins + hidden,
            tools=[db_m.add_expense, db_m.get_expenses_report],
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=False)
        ),
        history=past_history
    )

    return chat
