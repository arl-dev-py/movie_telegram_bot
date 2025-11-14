# database.py
from peewee import *
import datetime
import os

db = SqliteDatabase('history.db')

class History(Model):
    user_id = IntegerField()
    query = TextField()
    timestamp = DateTimeField(default=datetime.datetime.now)

    class Meta:
        database = db

def create_tables():
    with db:
        db.create_tables([History])
    print("Таблица History создана или уже существует.") # Для отладки

def save_query(user_id, query):
    """Сохраняет запрос пользователя в историю."""
    try:
        History.create(user_id=user_id, query=query[:255]) # Ограничим длину запроса на всякий случай
    except Exception as e:
        print(f"Ошибка при сохранении запроса: {e}")

def get_history(user_id, limit=5): # Изменим лимит по умолчанию на 5 для более компактного вывода
    """
    Возвращает последние `limit` запросов пользователя из истории.

    Args:
        user_id: ID пользователя Telegram.
        limit: Максимальное количество возвращаемых запросов.

    Returns:
        Список объектов History, отсортированных по времени в обратном порядке (от новых к старым).
    """
    try:
        return History.select().where(History.user_id == user_id).order_by(History.timestamp.desc()).limit(limit)
    except Exception as e:
        print(f"Ошибка при получении истории: {e}")
        return []

if __name__ == '__main__':
    create_tables()
