import os
TOKEN = os.getenv("BOT_TOKEN")

import telebot
from telebot.types import Message, ReplyKeyboardMarkup as RKM, KeyboardButton as KB
from telebot.types import InlineKeyboardMarkup as IKM, InlineKeyboardButton as IB
from telebot.types import ReplyKeyboardRemove as Rkr

TOKEN = os.getenv("BOT_TOKEN")


# Блок создания бота
bot = telebot.TeleBot(TOKEN)
clear_kb = Rkr() # Удаление  клавиатуры


# ===БЛОК обработки команд===
@bot.message_handler(commands=['menu', 'start'])
def handle_commands(mes: Message):
    """
    Обработчик команд:
    /menu и /start  - вызовет основное меню команд.
    
    """
    text = """Добро пожаловать!
    Тут будет потом инструкция о том, как пользоваться приложением и команды, чтобы облегчить работу с ботом.
    /start - начать работу с ботом
    /info - информация о разработчике"""
    bot.send_message(mes.chat.id, text)

@bot.message_handler(commands=['info'])
def handle_commands(mes: Message):
    """
    Обработчик команд:
    /info  - выведет информацию о разработчике.
    """
    text = """Бот разработан Манаевой Кариной
    Почта: sowa_sidit_na_vetke@mail.ru"""
    bot.send_message(mes.chat.id, text)


if __name__ == '__main__':
    bot.polling()
