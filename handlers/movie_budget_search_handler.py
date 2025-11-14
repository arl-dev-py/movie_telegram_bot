import os
import requests
import logging
from telebot import TeleBot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from keyboards.my_keyboard import search_subkeyboard
from database import save_query

logger = logging.getLogger(__name__)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

DEFAULT_LIMIT = 5

def register_movie_budget_handlers(bot: TeleBot, user_states: dict):

    @bot.message_handler(func=lambda m: m.text == "По бюджету")
    def ask_min_budget(message):
        bot.send_message(message.chat.id, "Введите минимальный бюджет фильма в миллионах долларов (например, 50):")
        user_states[message.chat.id] = 'waiting_for_min_budget'

    @bot.message_handler(func=lambda m: user_states.get(m.chat.id) == 'waiting_for_min_budget')
    def process_budget_input(message):
        try:
            min_budget_str = message.text.replace(',', '.')
            min_budget_input = float(min_budget_str)
            min_budget_usd = int(min_budget_input * 1_000_000)
            if min_budget_input < 0:
                raise ValueError("Бюджет не может быть отрицательным.")

            user_id = message.from_user.id
            save_query(user_id, f"Бюджет от ${min_budget_input} млн.")

            if message.chat.id in user_states:
                del user_states[message.chat.id]
            bot.send_message(message.chat.id, f"Ищу фильмы с бюджетом от ${min_budget_usd:,}...", reply_markup=search_subkeyboard())
            _search_movies_by_budget(bot, message.chat.id, min_budget_usd, 1)
        except ValueError as e:
            logger.warning(f"Некорректный ввод бюджета от {message.from_user.id}: {message.text}. Ошибка: {e}")
            bot.send_message(message.chat.id, f"Некорректный бюджет: {e}\nПожалуйста, введите положительное число.", reply_markup=search_subkeyboard())
        except Exception as e:
            logger.exception(f"Непредвиденная ошибка при обработке бюджета от {message.from_user.id}: {e}")
            bot.send_message(message.chat.id, "Произошла непредвиденная ошибка. Пожалуйста, попробуйте еще раз.", reply_markup=search_subkeyboard())

    def _search_movies_by_budget(bot: TeleBot, chat_id, min_budget_usd, page=1):
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
            "budget.value": [min_budget_usd],
            "page": page,
            "limit": DEFAULT_LIMIT,
            "sortField": "budget.value",
            "sortType": -1
        }
        try:
            response = requests.get(url, headers=headers, params=params, timeout=15)
            if response.status_code != 200:
                logger.error(f"API вернул статус {response.status_code}. Ответ API: {response.text}")
            response.raise_for_status()
            if not response.text.strip():
                raise ValueError("API вернул пустой ответ или ответ без содержимого.")
            data = response.json()
            movies = data.get("docs", [])
            filtered_movies = [m for m in movies if m.get("budget") and m["budget"].get("value") is not None]
            total_movies = data.get("total", 0)
            if filtered_movies:
                for i, movie in enumerate(filtered_movies):
                    try:
                        title = movie.get("name", movie.get("alternativeName", "Название неизвестно"))
                        year = movie.get("year", "Год неизвестен")
                        budget_obj = movie.get("budget", {})
                        budget_value = budget_obj.get("value")
                        budget_currency = budget_obj.get("currency")
                        formatted_budget = "Неизвестен"
                        if budget_value is not None:
                            if budget_currency == "USD":
                                formatted_budget = f"${budget_value:,}"
                            elif budget_currency == "RUB":
                                formatted_budget = f"₽{budget_value:,}"
                            elif budget_currency == "EUR":
                                formatted_budget = f"€{budget_value:,}"
                            else:
                                formatted_budget = f"{budget_value:,} {budget_currency if budget_currency else ''}".strip()
                        description = movie.get("description", "Описание отсутствует")
                        poster_url = movie.get("poster", {}).get("url")
                        message_text = f"🎬 *{title}* ({year})\n💰 Бюджет: {formatted_budget}\n\n{description}"
                        try:
                            if poster_url:
                                bot.send_photo(chat_id=chat_id, photo=poster_url, caption=message_text, parse_mode='Markdown')
                            else:
                                bot.send_message(chat_id=chat_id, text=message_text, parse_mode='Markdown')
                        except Exception as e:
                            logger.error(f"Ошибка при отправке информации о фильме '{title}' (chat_id: {chat_id}): {e}")
                            bot.send_message(chat_id=chat_id, text=message_text, parse_mode='Markdown')
                    except Exception as e:
                        logger.exception(f"Ошибка при обработке фильма '{movie.get('name', 'Название неизвестно')}': {e}")
                        continue
                if total_movies > DEFAULT_LIMIT:
                    create_pagination_keyboard(bot, chat_id, min_budget_usd, page, total_movies)
            else:
                bot.send_message(chat_id, f"По запросу ничего не найдено: не найдено фильмов с бюджетом от ${min_budget_usd:,}.", reply_markup=search_subkeyboard())
        except requests.exceptions.HTTPError as http_err:
            status_code = http_err.response.status_code
            logger.error(f"HTTP ошибка запроса для бюджета '{min_budget_usd}' (page {page}): {status_code} - {http_err.response.text}")
            if status_code == 400:
                bot.send_message(chat_id, f"Ошибка запроса к API (Код 400): Возможно, неверный формат параметра бюджета. Ответ API: {http_err.response.text}", reply_markup=search_subkeyboard())
            elif status_code == 401:
                bot.send_message(chat_id, "Ошибка авторизации: проверьте API ключ.", reply_markup=search_subkeyboard())
            elif status_code == 404:
                bot.send_message(chat_id, "Ресурс API не найден. Возможно, изменена структура URL.", reply_markup=search_subkeyboard())
            else:
                bot.send_message(chat_id, f"Ошибка сервера ({status_code}) при поиске по бюджету. Попробуйте ещё раз.", reply_markup=search_subkeyboard())
        except requests.exceptions.ConnectionError as conn_err:
            logger.error(f"Ошибка соединения с API для бюджета '{min_budget_usd}' (page {page}): {conn_err}")
            bot.send_message(chat_id, "Не удалось подключиться к серверу поиска фильмов. Проверьте ваше интернет-соединение или попробуйте позже.", reply_markup=search_subkeyboard())
        except requests.exceptions.Timeout as timeout_err:
            logger.error(f"Таймаут запроса к API для бюджета '{min_budget_usd}' (page {page}): {timeout_err}")
            bot.send_message(chat_id, "Сервер поиска фильмов слишком долго не отвечал. Пожалуйста, попробуйте ещё раз.", reply_markup=search_subkeyboard())
        except requests.exceptions.RequestException as req_err:
            logger.error(f"Общая ошибка запроса к API для бюджета '{min_budget_usd}' (page {page}): {req_err}")
            bot.send_message(chat_id, "Произошла ошибка при обращении к серверу поиска фильмов. Пожалуйста, попробуйте ещё раз.", reply_markup=search_subkeyboard())
        except ValueError as val_err:
            logger.error(f"Ошибка обработки данных от API для бюджета '{min_budget_usd}' (page {page}): {val_err}")
            bot.send_message(chat_id, f"Произошла ошибка при обработке данных от сервера: {val_err}.", reply_markup=search_subkeyboard())
        except Exception as e:
            logger.exception(f"Неизвестная ошибка в _search_movies_by_budget для '{min_budget_usd}' (page {page}): {e}")
            bot.send_message(chat_id, "Произошла непредвиденная ошибка. Пожалуйста, попробуйте еще раз.", reply_markup=search_subkeyboard())

    def create_pagination_keyboard(bot: TeleBot, chat_id, min_budget_usd, current_page, total_movies):
        keyboard = InlineKeyboardMarkup()
        buttons = []

        total_pages = (total_movies + DEFAULT_LIMIT - 1) // DEFAULT_LIMIT

        if current_page > 1:
            buttons.append(InlineKeyboardButton("⬅️ Назад", callback_data=f'budget_page:{min_budget_usd}:{current_page - 1}'))

        buttons.append(InlineKeyboardButton(f"Стр. {current_page}/{total_pages}", callback_data="ignore_me"))

        if current_page < total_pages:
            buttons.append(InlineKeyboardButton("Вперед ➡️", callback_data=f'budget_page:{min_budget_usd}:{current_page + 1}'))

        keyboard.add(*buttons)
        bot.send_message(chat_id, "Листайте результаты:", reply_markup=keyboard)

    @bot.callback_query_handler(func=lambda call: call.data.startswith('budget_page:'))
    def budget_page_callback(call):
        bot.answer_callback_query(call.id)
        try:
            _, min_budget_usd_str, page_str = call.data.split(':')
            min_budget_usd = int(min_budget_usd_str)
            page = int(page_str)
            try:
                bot.delete_message(call.message.chat.id, call.message.message_id)
            except Exception as delete_err:
                logger.warning(f"Не удалось удалить сообщение с пагинацией: {delete_err}")
            bot.send_message(call.message.chat.id, f"Загружаю страницу {page} для бюджета ${min_budget_usd:,}...", reply_markup=search_subkeyboard())
            _search_movies_by_budget(bot, call.message.chat.id, min_budget_usd, page)
        except Exception as e:
            logger.error(f"Ошибка при обработке callback 'budget_page:': {e}")
            bot.send_message(call.message.chat.id, "Произошла ошибка при переходе на другую страницу.", reply_markup=search_subkeyboard())
