from telebot import types

def main_keyboard(): # Reply клавиатура основного меню
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(types.KeyboardButton('Поиск фильма/сериала'),
                 types.KeyboardButton('История запросов'))
    return keyboard

def search_subkeyboard(): # Reply клавиатура подменю
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(types.KeyboardButton('По названию'),
                 types.KeyboardButton('По рейтингу'),
                 types.KeyboardButton('По бюджету'),
                 types.KeyboardButton('Назад'))
    return keyboard