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

prompt = "дай отчет"

net_info = n.get_web_info(prompt + hidden)
currency_kg = n.get_currency()

def start_markus():

    past_history = db_m.load_chat_history(limit=20)

    chat = client.chats.create(
        model='gemini-3.1-flash-lite-preview',
        config=types.GenerateContentConfig(
            system_instruction="Ты Маркус, финансовый ассистент. Если пользователь говорит о трате, ОБЯЗАТЕЛЬНО используй инструмент add_expense. Если пользователь сказал невнятно, то переспроси",
            tools=[db_m.add_expense], # ПОДКЛЮЧАЕМ ИНСТРУМЕНТ
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=False) # ВКЛЮЧАЕМ АВТО-ВЫЗОВ
        ),
        history=past_history
    )
    return chat
