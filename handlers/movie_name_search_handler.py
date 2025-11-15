import os
import requests
import logging
from telebot import TeleBot
from keyboards.my_keyboard import search_subkeyboard
from database import save_query

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

DEFAULT_LIMIT = 10

def register_movie_name_handlers(bot: TeleBot, user_states: dict):

    @bot.message_handler(func=lambda m: m.text == "Поиск фильма/сериала")
    def search_menu(message):
        logger.info(f'User {message.from_user.id} открыл меню поиска')
        bot.send_message(message.chat.id, "Выберите способ поиска:", reply_markup=search_subkeyboard())

    @bot.message_handler(func=lambda m: m.text == "По названию")
    def ask_movie_name(message):
        logger.info(f'User {message.from_user.id} выбрал поиск по названию')
        bot.send_message(message.chat.id, "Введите название фильма/сериала:")
        user_states[message.chat.id] = 'waiting_for_movie_name'

    @bot.message_handler(func=lambda m: user_states.get(m.chat.id) == 'waiting_for_movie_name')
    def search_by_name(message):
        movie_name_query = message.text.strip()
        if message.chat.id in user_states:
            del user_states[message.chat.id]
        logger.info(f'User {message.from_user.id} ищет фильм: {movie_name_query}')

        user_id = message.from_user.id
        save_query(user_id, f"Поиск по названию: '{movie_name_query}'")


        api_key = os.getenv("POISKINO_API_KEY")
        if not api_key:
            logger.error("API ключ не найден")
            bot.send_message(message.chat.id, "Ошибка: API ключ не настроен. Обратитесь к администратору.")
            return

        url = "https://api.poiskkino.dev/v1.4/movie/search"

        headers = {
            "X-API-KEY": api_key,
            "Accept": "application/json"
        }
        params = {
            "query": movie_name_query,
            "page": 1,
            "limit": DEFAULT_LIMIT,
        }

        try:
            response = requests.get(url, headers=headers, params=params, timeout=15)
            response.raise_for_status()

            if not response.text.strip():
                raise ValueError("API вернул пустой ответ или ответ без содержимого.")

            data = response.json()
            results = data.get("docs", [])

            if results:
                found_item = None
                processed_movie_name_query = movie_name_query.lower().strip()

                for item_candidate in results:
                    title_candidate = item_candidate.get("name") or item_candidate.get("alternativeName") or ""
                    processed_title_candidate = title_candidate.lower().strip()

                    if processed_title_candidate == processed_movie_name_query:
                        found_item = item_candidate
                        logger.info(f"Найдено точное совпадение для '{movie_name_query}': {title_candidate}")
                        break

                if not found_item:
                    found_item = results[0]
                    first_result_title = found_item.get("name", found_item.get("alternativeName", "Название неизвестно"))
                    logger.info(f"Для '{movie_name_query}' точное совпадение не найдено. Возвращаем первый результат: {first_result_title}")

                if found_item:
                    title = found_item.get("name", found_item.get("alternativeName", "Название неизвестно"))
                    year = found_item.get("year", "Год неизвестен")
                    description = found_item.get("description", "Описание отсутствует")
                    rating_kp = found_item.get("rating", {}).get("kp", "Неизвестен")
                    rating_imdb = found_item.get("rating", {}).get("imdb", "Неизвестен")

                    budget_data = found_item.get("budget")
                    budget_display = "Бюджет неизвестен"
                    if budget_data and budget_data.get("value") is not None:
                        budget_value = budget_data["value"]
                        budget_currency = budget_data.get("currency", "")
                        budget_display = f"{budget_value:,.0f} {budget_currency}".replace(",", " ")

                    poster_url = found_item.get("poster", {}).get("url")

                    message_text = f"🎬 *{title}* ({year})\n"
                    message_text += f"⭐ Рейтинг Кинопоиска: {rating_kp}\n"
                    if rating_imdb != "Неизвестен": # только если IMDb доступен
                        message_text += f"IMDb: {rating_imdb}\n"
                    message_text += f"💰 Бюджет: {budget_display}\n\n"
                    message_text += f"{description}"

                    if poster_url:
                        try:
                            # Добавляем markup_reply=main_keyboard() для возврата основных кнопок
                            bot.send_photo(chat_id=message.chat.id, photo=poster_url, caption=message_text, parse_mode='Markdown', reply_markup=search_subkeyboard())
                            logger.info(f"Отправлено фото и информация для '{title}'")
                        except Exception as photo_e:
                            logger.error(f"Ошибка при отправке фото для '{title}' (URL: {poster_url}): {photo_e}. Отправляем только текст.")
                            bot.send_message(message.chat.id, message_text, parse_mode='Markdown', reply_markup=search_subkeyboard())
                    else:
                        bot.send_message(message.chat.id, message_text, parse_mode='Markdown', reply_markup=search_subkeyboard())
                        logger.info(f"Отправлена информация для '{title}' (без фото, т.к. URL отсутствует).")
                else:
                    bot.send_message(message.chat.id, "К сожалению, не удалось извлечь информацию о фильме, хотя результаты были получены.", reply_markup=search_subkeyboard())
            else:
                logger.info(f"По запросу '{movie_name_query}' ничего не найдено.")
                bot.send_message(message.chat.id, f"К сожалению, по запросу «{movie_name_query}» ничего не найдено.", reply_markup=search_subkeyboard())

        except requests.exceptions.HTTPError as http_err:
            status_code = http_err.response.status_code
            logger.error(f"HTTP ошибка запроса для '{movie_name_query}': {status_code} - {http_err.response.text}")
            if status_code == 401:
                bot.send_message(message.chat.id, "Ошибка авторизации: проверьте API ключ.", reply_markup=search_subkeyboard())
            elif status_code == 404:
                bot.send_message(message.chat.id, "Ресурс API не найден. Возможно, изменена структура URL.", reply_markup=search_subkeyboard())
            else:
                bot.send_message(message.chat.id, f"Ошибка сервера ({status_code}) при поиске. Попробуйте ещё раз.", reply_markup=search_subkeyboard())
        except requests.exceptions.ConnectionError as conn_err:
            logger.error(f"Ошибка соединения с API для '{movie_name_query}': {conn_err}")
            bot.send_message(message.chat.id, "Не удалось подключиться к серверу поиска фильмов. Проверьте ваше интернет-соединение или попробуйте позже.", reply_markup=search_subkeyboard())
        except requests.exceptions.Timeout as timeout_err:
            logger.error(f"Таймаут запроса к API для '{movie_name_query}': {timeout_err}")
            bot.send_message(message.chat.id, "Сервер поиска фильмов слишком долго не отвечал. Пожалуйста, попробуйте ещё раз.", reply_markup=search_subkeyboard())
        except requests.exceptions.RequestException as req_err:
            logger.error(f"Общая ошибка запроса к API для '{movie_name_query}': {req_err}")
            bot.send_message(message.chat.id, "Произошла ошибка при обращении к серверу поиска фильмов. Пожалуйста, попробуйте ещё раз.", reply_markup=search_subkeyboard())
        except ValueError as val_err:
            logger.error(f"Ошибка обработки данных от API для '{movie_name_query}': {val_err}")
            bot.send_message(message.chat.id, f"Произошла ошибка при обработке данных от сервера: {val_err}.", reply_markup=search_subkeyboard())
        except Exception as e:
            logger.exception(f"Неизвестная ошибка в search_by_name для '{movie_name_query}': {e}")
            bot.send_message(message.chat.id, "Произошла непредвиденная ошибка. Пожалуйста, попробуйте еще раз.", reply_markup=search_subkeyboard())
#