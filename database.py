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

def create_tables(): # создаем таблицу History
    with db:
        db.create_tables([History])
    print("Таблица History создана или уже существует.") # Для отладки

def save_query(user_id, query): # сохранение запросов в таблицу History
    try:
        History.create(user_id=user_id, query=query[:255])
    except Exception as e:
        print(f"Ошибка при сохранении запроса: {e}")

def get_history(user_id, limit=5): # извлечение сохраненных запросов из таблицы History
    try:
        return History.select().where(History.user_id == user_id).order_by(History.timestamp.desc()).limit(limit)
    except Exception as e:
        print(f"Ошибка при получении истории: {e}")
        return []

if __name__ == '__main__':
    create_tables()
