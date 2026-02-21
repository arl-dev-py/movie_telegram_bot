# Movie Telegram Bot (@MyFirstExampleTgBot)

Telegram-бот для поиска фильмов и сериалов через **PoiskKino API**. 

**Функции:**
- Поиск по названию, рейтингу, описанию, бюджету, постерам
- Удобная Reply-клавиатура 
- История запросов в **Peewee** БД
- Inline-режим поиска


![img.png](img.png)

## Быстрый запуск

1. Клонировать репозиторий
git clone https://github.com/arl-dev-py/movie_telegram_bot.git
cd movie_telegram_bot

2. Установить зависимости
pip install -r requirements.txt

3. Создать файл .env
cp .env.example .env

Отредактируйте .env:
BOT_TOKEN=ваш_токен_от_BotFather
POISKINO_API_KEY=ключ_от_@poiskkinodev_bot

4. Запустить бота
python main.py

Готово! Найдите @MyFirstExampleTgBot в Telegram.

## Команды бота

/start  — Главное меню + история поиска
Поиск — Название фильма/сериала
Рейтинг — Топ фильмы
Популярное — В тренде
