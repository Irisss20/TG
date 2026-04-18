import AI
import database.data_base_methods as db_m

def main():
    # Запускаем сессию
    chat_session = AI.start_markus()

    print("--- Маркус ОНЛАЙН (пиши 'exit' для выхода) ---")

    while True:
        user_input = input("Вы: ")
        if user_input.lower() == 'exit':
            break

        # 1. СРАЗУ сохраняем вопрос пользователя в базу
        db_m.save_chat_message("user", user_input)

        # 2. Отправляем в ИИ
        response = chat_session.send_message(user_input)

        # 3. Сохраняем ответ ИИ в базу
        db_m.save_chat_message("model", response.text)

        # 4. Выводим ответ
        print(f"Маркус: {response.text}")
        print("-" * 30)

if __name__ == "__main__":
    main()