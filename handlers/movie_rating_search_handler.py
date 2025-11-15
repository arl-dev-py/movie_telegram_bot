import os
import requests
import logging
from telebot import TeleBot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from keyboards.my_keyboard import search_subkeyboard
from database import save_query

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

DEFAULT_LIMIT = 5

def register_movie_rating_handlers(bot: TeleBot, user_states: dict):

    @bot.message_handler(func=lambda m: m.text == "По рейтингу") # обработчик кнопки "По рейтингу"
    def ask_min_rating(message):
        bot.send_message(message.chat.id, "Введите минимальный рейтинг Кинопоиска (например, 7.5):")
        user_states[message.chat.id] = 'waiting_for_min_rating'

    @bot.message_handler(func=lambda m: user_states.get(m.chat.id) == 'waiting_for_min_rating') # обработчик состояния пользователь, реализация поиска фильма по рейтингу
    def process_rating_input(message):
        try:
            min_rating_str = message.text.replace(',', '.')
            min_rating = float(min_rating_str)
            if not 0 <= min_rating <= 10:
                raise ValueError("Рейтинг должен быть от 0 до 10.")

            user_id = message.from_user.id
            save_query(user_id, f"Рейтинг от {min_rating}")

            if message.chat.id in user_states:
                del user_states[message.chat.id]

            bot.send_message(message.chat.id, f"Ищу фильмы с рейтингом Кинопоиска от {min_rating}...", reply_markup=search_subkeyboard())
            search_movies_by_rating(bot, message.chat.id, min_rating, 1)
        except ValueError as e:
            logger.warning(f"Некорректный ввод рейтинга от {message.from_user.id}: {message.text}. Ошибка: {e}")
            bot.send_message(message.chat.id, f"Некорректный рейтинг: {e}\nПожалуйста, введите число от 0 до 10.", reply_markup=search_subkeyboard())
        except Exception as e:
            logger.exception(f"Непредвиденная ошибка при обработке рейтинга от {message.from_user.id}: {e}")
            bot.send_message(message.chat.id, "Произошла непредвиденная ошибка. Пожалуйста, попробуйте еще раз.", reply_markup=search_subkeyboard())

    def search_movies_by_rating(bot: TeleBot, chat_id, min_rating, page=1):
        api_key = os.getenv("POISKINO_API_KEY")
        if not api_key:
            logger.error("API ключ не найден")
            bot.send_message(chat_id, "Ошибка: API ключ не настроен. Обратитесь к администратору.", reply_markup=search_subkeyboard())
            return

        url = "https://api.poiskkino.dev/v1.4/movie"
        headers = {
            "X-API-KEY": api_key,
            "Accept": "application/json"
        }
        params = {
            "rating.kp": f"{min_rating}-10",
            "page": page,
            "limit": DEFAULT_LIMIT,
            "sortField": "rating.kp",
            "sortType": -1
        }

        try:
            response = requests.get(url, headers=headers, params=params, timeout=15)
            response.raise_for_status()

            if not response.text.strip():
                raise ValueError("API вернул пустой ответ или ответ без содержимого.")

            data = response.json()
            movies = data.get("docs", [])
            total_movies = data.get("total", 0)

            if movies:
                for movie in movies:
                    title = movie.get("name", movie.get("alternativeName", "Название неизвестно"))
                    year = movie.get("year", "Год неизвестен")
                    rating_kp = movie.get("rating", {}).get("kp", "Неизвестен")
                    description = movie.get("description", "Описание отсутствует")
                    poster_url = movie.get("poster", {}).get("url")

                    message_text = f"🎬 *{title}* ({year})\n⭐ Рейтинг Кинопоиска: {rating_kp}\n\n{description}"

                    try:
                        if poster_url:
                            bot.send_photo(chat_id=chat_id, photo=poster_url, caption=message_text, parse_mode='Markdown')
                        else:
                            bot.send_message(chat_id=chat_id, text=message_text, parse_mode='Markdown')
                    except Exception as e:
                        logger.error(f"Ошибка при отправке информации о фильме '{title}' (chat_id: {chat_id}): {e}")
                        bot.send_message(chat_id=chat_id, text=message_text, parse_mode='Markdown')

                if total_movies > DEFAULT_LIMIT:
                   create_pagination_keyboard(bot, chat_id, min_rating, page, total_movies)
            else:
                bot.send_message(chat_id, f"По запросу ничего не найдено: не найдено фильмов с рейтингом выше {min_rating}.", reply_markup=search_subkeyboard())

        except requests.exceptions.HTTPError as http_err:
            status_code = http_err.response.status_code
            logger.error(f"HTTP ошибка запроса для рейтинга '{min_rating}' (page {page}): {status_code} - {http_err.response.text}")
            if status_code == 401:
                bot.send_message(chat_id, "Ошибка авторизации: проверьте API ключ.", reply_markup=search_subkeyboard())
            elif status_code == 404:
                bot.send_message(chat_id, "Ресурс API не найден. Возможно, изменена структура URL.", reply_markup=search_subkeyboard())
            else:
                bot.send_message(chat_id, f"Ошибка сервера ({status_code}) при поиске по рейтингу. Попробуйте ещё раз.", reply_markup=search_subkeyboard())
        except requests.exceptions.ConnectionError as conn_err:
            logger.error(f"Ошибка соединения с API для рейтинга '{min_rating}' (page {page}): {conn_err}")
            bot.send_message(chat_id, "Не удалось подключиться к серверу поиска фильмов. Проверьте ваше интернет-соединение или попробуйте позже.", reply_markup=search_subkeyboard())
        except requests.exceptions.Timeout as timeout_err:
            logger.error(f"Таймаут запроса к API для рейтинга '{min_rating}' (page {page}): {timeout_err}")
            bot.send_message(chat_id, "Сервер поиска фильмов слишком долго не отвечал. Пожалуйста, попробуйте ещё раз.", reply_markup=search_subkeyboard())
        except requests.exceptions.RequestException as req_err:
            logger.error(f"Общая ошибка запроса к API для рейтинга '{min_rating}' (page {page}): {req_err}")
            bot.send_message(chat_id, "Произошла ошибка при обращении к серверу поиска фильмов. Пожалуйста, попробуйте ещё раз.", reply_markup=search_subkeyboard())
        except ValueError as val_err:
            logger.error(f"Ошибка обработки данных от API для рейтинга '{min_rating}' (page {page}): {val_err}")
            bot.send_message(chat_id, f"Произошла ошибка при обработке данных от сервера: {val_err}.", reply_markup=search_subkeyboard())
        except Exception as e:
            logger.exception(f"Неизвестная ошибка в search_movies_by_rating для '{min_rating}' (page {page}): {e}")
            bot.send_message(chat_id, "Произошла непредвиденная ошибка. Пожалуйста, попробуйте еще раз.", reply_markup=search_subkeyboard())

    def create_pagination_keyboard(bot: TeleBot, chat_id, min_rating, current_page, total_movies): # создание InLine клавиатуры для вывода результатов фильмов
        keyboard = InlineKeyboardMarkup()
        buttons = []

        total_pages = (total_movies + DEFAULT_LIMIT - 1) // DEFAULT_LIMIT

        if current_page > 1:
            buttons.append(InlineKeyboardButton("⬅️ Назад", callback_data=f'rating_page:{min_rating}:{current_page - 1}'))

        buttons.append(InlineKeyboardButton(f"Стр. {current_page}/{total_pages}", callback_data="ignore_me"))

        if current_page < total_pages:
            buttons.append(InlineKeyboardButton("Вперед ➡️", callback_data=f'rating_page:{min_rating}:{current_page + 1}'))

        keyboard.add(*buttons)
        bot.send_message(chat_id, "Листайте результаты:", reply_markup=keyboard)

    @bot.callback_query_handler(func=lambda call: call.data.startswith('rating_page:'))
    def rating_page_callback(call): # реализация InLine клавиатуры
        bot.answer_callback_query(call.id)
        try:
            _, min_rating_str, page_str = call.data.split(':')
            min_rating = float(min_rating_str)
            page = int(page_str)
            try:
                bot.delete_message(call.message.chat.id, call.message.message_id)
            except Exception as delete_err:
                logger.warning(f"Не удалось удалить сообщение с пагинацией: {delete_err}")
            bot.send_message(call.message.chat.id, f"Загружаю страницу {page} для рейтинга {min_rating}...", reply_markup=search_subkeyboard())

            search_movies_by_rating(bot, call.message.chat.id, min_rating, page)

        except Exception as e:
            logger.error(f"Ошибка при обработке callback 'rating_page:': {e}")
            bot.send_message(call.message.chat.id, "Произошла ошибка при переходе на другую страницу.", reply_markup=search_subkeyboard())
#