import os
import logging
from telebot import TeleBot
from keyboards.my_keyboard import main_keyboard, search_subkeyboard
from database import create_tables, get_history # <-- ИМПОРТ

from handlers.movie_name_search_handler import register_movie_name_handlers
from handlers.movie_rating_search_handler import register_movie_rating_handlers
from handlers.movie_budget_search_handler import register_movie_budget_handlers

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

user_states = {}

def register_handlers(bot: TeleBot):
    create_tables()

    @bot.message_handler(commands=['start'])
    def start(message):
        logger.info(f'User {message.from_user.id} started the bot')
        bot.send_message(
            message.chat.id,
            f"Привет, {message.from_user.first_name}! Меня зовут TeleBot. Я умею искать информацию о фильмах или сериалах, а также предоставлю историю твоих запросов!",
            reply_markup=main_keyboard()
        )

    @bot.message_handler(func=lambda m: m.text == "Назад", chat_types=['private'])
    def back_to_main(message):
        logger.info(f'User {message.from_user.id} ({message.from_user.first_name}) вернулся в основное меню')
        if message.chat.id in user_states:
            del user_states[message.chat.id]
        bot.send_message(message.chat.id, "С чего начнем?", reply_markup=main_keyboard())

    @bot.message_handler(func=lambda m: m.text == "История запросов", chat_types=['private'])
    def history_command(message):
        logger.info(f'User {message.from_user.id} ({message.from_user.first_name}) запросил историю')
        user_id = message.from_user.id
        history_records = get_history(user_id, limit=7)

        if history_records:
            response_text = "Ваши последние запросы:\n\n"
            for i, record in enumerate(history_records, 1):
                formatted_time = record.timestamp.strftime('%d.%m.%Y %H:%M')
                response_text += f"*{i}.* `{record.query}` (_{formatted_time}_)\n"
            bot.send_message(message.chat.id, response_text, parse_mode='Markdown')
        else:
            bot.send_message(message.chat.id, "История запросов пуста.")


    @bot.message_handler(func=lambda m: m.text == "Поиск фильма/сериала", chat_types=['private'])
    def search_menu(message):
        logger.info(f'User {message.from_user.id} ({message.from_user.first_name}) выбрал поиск фильма/сериала')
        bot.send_message(message.chat.id, "Выберите способ поиска:", reply_markup=search_subkeyboard())


    register_movie_name_handlers(bot, user_states)
    register_movie_rating_handlers(bot, user_states)
    register_movie_budget_handlers(bot, user_states)

    logger.info("All handlers registered successfully.")
