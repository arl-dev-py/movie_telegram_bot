import os
from dotenv import load_dotenv
import telebot
from handlers.__init__ import register_handlers


load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
bot = telebot.TeleBot(TOKEN)

register_handlers(bot)


if __name__ == '__main__':
    print("Бот запущен...")
    bot.polling(none_stop=True)