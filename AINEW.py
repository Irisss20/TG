import asyncio
import logging
import os

from datetime import datetime

from aiogram import Bot, Dispatcher, F, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

from dotenv import load_dotenv
from google import genai
from google.genai import types

import date as d
import net as n
from database.DB import get_conn

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
API = os.getenv("API")
SYS_INSTRUCTIONS = os.getenv("SYS_INSTRUCTIONS", "")

client = genai.Client(api_key=API)

router = Router()


# =========================
# DB
# =========================


def ensure_user(tg_user_id: int):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT OR IGNORE INTO users (tg_user_id, created_at) VALUES (?, ?)",
        (tg_user_id, datetime.now().isoformat())
    )
    conn.commit()
    conn.close()


def save_expense(tg_user_id: int, raw_text: str):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO expenses (tg_user_id, raw_text, created_at) VALUES (?, ?, ?)",
        (tg_user_id, raw_text, datetime.now().isoformat())
    )
    conn.commit()
    conn.close()


def save_income(tg_user_id: int, raw_text: str):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO incomes (tg_user_id, raw_text, created_at) VALUES (?, ?, ?)",
        (tg_user_id, raw_text, datetime.now().isoformat())
    )
    conn.commit()
    conn.close()


def save_profile_style(tg_user_id: int, spending_style: str):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
                INSERT INTO profiles (tg_user_id, spending_style, updated_at)
                VALUES (?, ?, ?)
                    ON CONFLICT(tg_user_id) DO UPDATE SET
                    spending_style=excluded.spending_style,
                                                   updated_at=excluded.updated_at
                """, (tg_user_id, spending_style, datetime.now().isoformat()))
    conn.commit()
    conn.close()


def save_consultation_message(tg_user_id: int, role: str, text: str):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO consultations (tg_user_id, role, text, created_at) VALUES (?, ?, ?, ?)",
        (tg_user_id, role, text, datetime.now().isoformat())
    )
    conn.commit()
    conn.close()


def get_recent_expenses(tg_user_id: int, limit: int = 20):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
                SELECT raw_text, created_at
                FROM expenses
                WHERE tg_user_id = ?
                ORDER BY id DESC
                    LIMIT ?
                """, (tg_user_id, limit))
    rows = cur.fetchall()
    conn.close()
    return rows


def get_recent_incomes(tg_user_id: int, limit: int = 20):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
                SELECT raw_text, created_at
                FROM incomes
                WHERE tg_user_id = ?
                ORDER BY id DESC
                    LIMIT ?
                """, (tg_user_id, limit))
    rows = cur.fetchall()
    conn.close()
    return rows


def get_profile_style(tg_user_id: int):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
                SELECT spending_style
                FROM profiles
                WHERE tg_user_id = ?
                """, (tg_user_id,))
    row = cur.fetchone()
    conn.close()
    return row["spending_style"] if row else ""


def get_consult_history(tg_user_id: int, limit: int = 12):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
                SELECT role, text
                FROM consultations
                WHERE tg_user_id = ?
                ORDER BY id DESC
                    LIMIT ?
                """, (tg_user_id, limit))
    rows = cur.fetchall()
    conn.close()
    return list(reversed(rows))


# =========================
# FSM
# =========================
class FinanceForm(StatesGroup):
    waiting_expenses = State()
    waiting_income = State()
    waiting_spending_style = State()
    waiting_consult_question = State()


# =========================
# Keyboard
# =========================
def main_menu():
    kb = InlineKeyboardBuilder()
    kb.button(text="Внести расходы", callback_data="add_expenses")
    kb.button(text="Посмотреть отчет", callback_data="show_report")
    kb.button(text="Посмотреть все траты", callback_data="show_expenses")
    kb.button(text="Посоветоваться", callback_data="consult")
    kb.adjust(1)
    return kb.as_markup()


# =========================
# AI helpers
# =========================
def build_hidden_time() -> str:
    date_value, time_value = d.get_internet_time()
    return f"\n{date_value} {time_value}\n"


def build_context_block(tg_user_id: int) -> str:
    expenses = get_recent_expenses(tg_user_id, limit=10)
    incomes = get_recent_incomes(tg_user_id, limit=10)
    spending_style = get_profile_style(tg_user_id)

    expenses_text = "\n".join(
        [f"- {row['created_at']}: {row['raw_text']}" for row in expenses]
    ) or "Нет данных"

    incomes_text = "\n".join(
        [f"- {row['created_at']}: {row['raw_text']}" for row in incomes]
    ) or "Нет данных"

    return f"""
Последние расходы:
{expenses_text}

Последние доходы:
{incomes_text}

Привычки трат пользователя:
{spending_style or "Нет описания"}
""".strip()


def build_consult_history_for_model(tg_user_id: int) -> str:
    rows = get_consult_history(tg_user_id, limit=10)
    if not rows:
        return "Истории консультаций пока нет."

    result = []
    for row in rows:
        result.append(f"{row['role']}: {row['text']}")
    return "\n".join(result)


def ask_gemini(prompt: str, tg_user_id: int, use_web=False) -> str:
    hidden = build_hidden_time()
    context_block = build_context_block(tg_user_id)

    extra_web = ""
    if use_web:
        net_info = n.get_web_info(prompt + hidden)
        currency_kg = n.get_currency()
        extra_web = f"\nВеб-информация:\n{net_info}\n\nКурс валют:\n{currency_kg}\n"

    final_prompt = f"""
Системный скрытый контекст времени:
{hidden}

Контекст пользователя:
{context_block}

Дополнительные данные:
{extra_web}

Запрос пользователя:
{prompt}
""".strip()

    response = client.models.generate_content(
        model="gemini-3.1-flash-lite-preview",
        config=types.GenerateContentConfig(
            system_instruction=hidden + SYS_INSTRUCTIONS
        ),
        contents=final_prompt
    )
    return response.text


def ask_gemini_consult_chat(user_text: str, tg_user_id: int) -> str:
    hidden = build_hidden_time()
    context_block = build_context_block(tg_user_id)
    consult_history = build_consult_history_for_model(tg_user_id)

    prompt = f"""
Скрытый контекст времени:
{hidden}

Финансовый контекст пользователя:
{context_block}

История прошлых консультаций:
{consult_history}

Новый вопрос пользователя:
{user_text}
""".strip()

    response = client.models.generate_content(
        model="gemini-3.1-flash-lite-preview",
        config=types.GenerateContentConfig(
            system_instruction=hidden + SYS_INSTRUCTIONS
        ),
        contents=prompt
    )
    return response.text


# =========================
# Handlers
# =========================
@router.message(CommandStart())
async def start_handler(message: Message, state: FSMContext):
    ensure_user(message.from_user.id)
    await state.clear()
    await message.answer(
        "Привет. Я помогу собрать траты, доходы и дать финансовую выжимку.\n\n"
        "Выбери действие:",
        reply_markup=main_menu()
    )


@router.callback_query(F.data == "add_expenses")
async def add_expenses_callback(callback: CallbackQuery, state: FSMContext):
    await state.set_state(FinanceForm.waiting_expenses)
    await callback.message.answer(
        "Напиши свои расходы за день или период одним сообщением.\n"
        "Например: еда 500, такси 300, кофе 150"
    )
    await callback.answer()


@router.message(FinanceForm.waiting_expenses)
async def process_expenses(message: Message, state: FSMContext):
    await state.update_data(expenses_text=message.text)
    await message.answer("Теперь напиши доход за день или период одним сообщением.")
    await state.set_state(FinanceForm.waiting_income)


@router.message(FinanceForm.waiting_income)
async def process_income(message: Message, state: FSMContext):
    await state.update_data(income_text=message.text)
    await message.answer(
        "Теперь опиши примерно, как происходят траты: импульсивно, по плану, часто доставка, много мелких покупок и т.д."
    )
    await state.set_state(FinanceForm.waiting_spending_style)


@router.message(FinanceForm.waiting_spending_style)
async def process_spending_style(message: Message, state: FSMContext):
    data = await state.get_data()

    expenses_text = data.get("expenses_text", "")
    income_text = data.get("income_text", "")
    spending_style = message.text

    tg_user_id = message.from_user.id

    save_expense(tg_user_id, expenses_text)
    save_income(tg_user_id, income_text)
    save_profile_style(tg_user_id, spending_style)

    prompt = f"""
Пользователь ввел новые данные.

Расходы:
{expenses_text}

Доход:
{income_text}

Как происходят траты:
{spending_style}

Сделай краткий, понятный финансовый разбор:
1. Что видно по тратам
2. Где возможны слабые места
3. Что можно улучшить
4. Краткий совет без морализаторства
""".strip()

    await message.answer("Принял. Делаю разбор...")

    try:
        answer = ask_gemini(prompt, tg_user_id, use_web=False)
        await message.answer(answer, reply_markup=main_menu())
    except Exception as e:
        await message.answer(f"Ошибка при обращении к ИИ: {e}")

    await state.clear()


@router.callback_query(F.data == "show_report")
async def show_report_callback(callback: CallbackQuery, state: FSMContext):
    tg_user_id = callback.from_user.id
    context_block = build_context_block(tg_user_id)

    prompt = f"""
На основе этих данных пользователя сделай отчет:
{context_block}

Формат:
- краткая сводка
- что съедает деньги
- на что обратить внимание
- 3 практических совета
""".strip()

    await callback.message.answer("Готовлю отчет...")

    try:
        answer = ask_gemini(prompt, tg_user_id, use_web=False)
        await callback.message.answer(answer, reply_markup=main_menu())
    except Exception as e:
        await callback.message.answer(f"Ошибка при создании отчета: {e}")

    await callback.answer()


@router.callback_query(F.data == "show_expenses")
async def show_expenses_callback(callback: CallbackQuery):
    tg_user_id = callback.from_user.id
    rows = get_recent_expenses(tg_user_id, limit=20)

    if not rows:
        await callback.message.answer("Пока нет сохраненных трат.", reply_markup=main_menu())
        await callback.answer()
        return

    text = "\n\n".join(
        [f"{idx + 1}. {row['created_at']}\n{row['raw_text']}" for idx, row in enumerate(rows)]
    )

    if len(text) > 3500:
        text = text[:3500] + "\n\n... список обрезан"

    await callback.message.answer(f"Последние траты:\n\n{text}", reply_markup=main_menu())
    await callback.answer()


@router.callback_query(F.data == "consult")
async def consult_callback(callback: CallbackQuery, state: FSMContext):
    await state.set_state(FinanceForm.waiting_consult_question)
    await callback.message.answer(
        "Напиши вопрос. Например:\n"
        "- почему у меня утекают деньги?\n"
        "- нормально ли столько тратить на еду?\n"
        "- как лучше распределять доход?"
    )
    await callback.answer()


@router.message(FinanceForm.waiting_consult_question)
async def process_consult_question(message: Message, state: FSMContext):
    tg_user_id = message.from_user.id
    user_text = message.text

    save_consultation_message(tg_user_id, "user", user_text)
    await message.answer("Думаю над ответом...")

    try:
        answer = ask_gemini_consult_chat(user_text, tg_user_id)
        save_consultation_message(tg_user_id, "model", answer)
        await message.answer(answer, reply_markup=main_menu())
    except Exception as e:
        await message.answer(f"Ошибка при консультации: {e}", reply_markup=main_menu())

    await state.clear()


# =========================
# Main
# =========================
async def main():
    logging.basicConfig(level=logging.INFO)

    init_db()

    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )

    dp = Dispatcher()
    dp.include_router(router)

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
