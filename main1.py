import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from datetime import datetime, timedelta
import pytz

# Настройки бота
TOKEN = ""
ADMIN_CHAT_ID = "" 
ADMIN_CHAT_ID1 = "" 
TIMEZONE = pytz.timezone('Europe/Moscow')

bot = telebot.TeleBot(TOKEN)

# Хранилища данных
user_restrictions = {}
user_question_count = {}  # Счетчик вопросов для каждого пользователя
MAX_QUESTIONS = 3  # Максимальное количество вопросов, которое может задать пользователь


# Обработчик команды /start
@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "Привет! Здесь ты можешь задать мне вопрос. Используй команду /to_send для этого.")


# Обработчик команды /to_send
@bot.message_handler(commands=['to_send'])
def ask_to_send_question(message):
    user_id = message.from_user.id

    # Проверка ограничений (временных)
    if user_id in user_restrictions:
        if datetime.now(TIMEZONE) < user_restrictions[user_id]:
            time_left = user_restrictions[user_id] - datetime.now(TIMEZONE)
            bot.reply_to(message,
                         f"Вы не можете задавать вопросы ещё {time_left.seconds // 3600} ч. {(time_left.seconds % 3600) // 60} мин.")
            return

    # Проверка количества активных вопросов
    if user_id in user_question_count and user_question_count[user_id] >= MAX_QUESTIONS:
        bot.reply_to(message, f"Вы задали максимальное количество вопросов ({MAX_QUESTIONS}). Пожалуйста, дождитесь ответов.")
        return

    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("Да", callback_data="send_yes"),
        InlineKeyboardButton("Нет", callback_data="send_no")
    )
    bot.send_message(message.chat.id, "Задать вопрос Дмитрию?", reply_markup=markup)


# Обработчик callback-ов
@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    user_id = call.from_user.id
    chat_id = call.message.chat.id

    # Удаляем кнопки сразу после нажатия
    try:
        bot.edit_message_reply_markup(chat_id, call.message.message_id, reply_markup=None)
    except:
        pass

    if call.data == "send_yes":
        markup = InlineKeyboardMarkup()
        markup.add(
            InlineKeyboardButton("Да", callback_data="anon_yes"),
            InlineKeyboardButton("Нет", callback_data="anon_no")
        )
        bot.send_message(chat_id, "Хотите задать вопрос анонимно?", reply_markup=markup)

    elif call.data in ["anon_yes", "anon_no"]:
        is_anonymous = call.data == "anon_yes"
        
        # Создаем клавиатуру с кнопкой "Назад"
        reply_markup = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        reply_markup.add(KeyboardButton("Назад"))
        
        msg = bot.send_message(chat_id, "Пожалуйста, введите ваш вопрос:", reply_markup=reply_markup)
        bot.register_next_step_handler(msg, process_question, is_anonymous)

    elif call.data.startswith("answer_"):
        parts = call.data.split("_")
        original_message_id = parts[1]
        user_id_to_answer = int(parts[2])

        bot.send_message(call.message.chat.id, "Введите ваш ответ:")
        bot.register_next_step_handler(call.message, process_answer, user_id_to_answer)


# Обработчик текстовых сообщений (для ответа)
def process_answer(message, user_id_to_answer):
    chat_id = message.chat.id
    answer = message.text

    remaining_questions = MAX_QUESTIONS - user_question_count[user_id_to_answer]
    bot.send_message(user_id_to_answer, f"Ответ на ваш вопрос:\n\n{answer}")

    if user_id_to_answer in user_question_count:
        user_question_count[user_id_to_answer] -= 1
        if user_question_count[user_id_to_answer] < 0:
            user_question_count[user_id_to_answer] = 0 
        remaining_questions = MAX_QUESTIONS - user_question_count[user_id_to_answer]
        bot.send_message(chat_id, f"Ответ отправлен пользователю. У него осталось {remaining_questions} вопроса(ов).")
    else:
        bot.send_message(chat_id, "Ответ отправлен пользователю.") 


# Обработчик вопроса
def process_question(message, is_anonymous):
    # Проверяем, не нажал ли пользователь кнопку "Назад"
    if message.text == "Назад":
        bot.send_message(message.chat.id, "Отправка вопроса отменена.", reply_markup=telebot.types.ReplyKeyboardRemove())
        return
    
    user_id = message.from_user.id
    chat_id = message.chat.id
    question = message.text

    # Увеличиваем счетчик вопросов
    if user_id not in user_question_count:
        user_question_count[user_id] = 0
    user_question_count[user_id] += 1

    # Формируем сообщение для админа
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("Ответить", callback_data=f"answer_{message.message_id}_{user_id}"))

    if is_anonymous:
        user_info = f"От: @{message.from_user.username}" if message.from_user.username else f"ID: {user_id}"
        text = f"Анонимный вопрос:\n\n{question}\n\n{user_info}"
    else:
        user_info = f"От: @{message.from_user.username}" if message.from_user.username else f"ID: {user_id}"
        text = f"Вопрос (не анонимно):\n\n{question}\n\n{user_info}"

    bot.send_message(ADMIN_CHAT_ID, text, reply_markup=markup)
    bot.send_message(ADMIN_CHAT_ID1, text, reply_markup=markup)
    bot.send_message(chat_id, "Ваш вопрос отправлен! Вы можете задать ещё {} вопроса(ов).".format(MAX_QUESTIONS - user_question_count[user_id]),
                    reply_markup=telebot.types.ReplyKeyboardRemove())


if __name__ == "__main__":
    print("Бот запущен...")
    bot.infinity_polling()
