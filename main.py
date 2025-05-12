import os

import telebot
from telebot.types import Message, ReplyKeyboardMarkup as RKM, KeyboardButton as KB
from telebot.types import InlineKeyboardMarkup as IKM, InlineKeyboardButton as IB
from telebot.types import ReplyKeyboardRemove as Rkr

from pybit.unified_trading import HTTP

# Для локальных тестов
# from config import TOKEN, id_admin, BYBIT_API_KEY, BYBIT_API_SECRET


TOKEN = os.getenv("BOT_TOKEN")
id_admin = os.getenv("bot_admin")
BYBIT_API_KEY = os.getenv("BYBIT_API_KEY")
BYBIT_API_SECRET = os.getenv("BYBIT_API_SECRET")

bybit = HTTP(
    api_key=BYBIT_API_KEY,
    api_secret=BYBIT_API_SECRET,
    testnet=False  # False — для реального рынка
)


# Блок создания бота
bot = telebot.TeleBot(TOKEN) 
clear_kb = Rkr() # Удаление  клавиатуры


# ===БЛОК обработки команд===
@bot.message_handler(commands=['menu', 'start'])
def handle_commands(mes: Message):
    if mes.chat.id != int(id_admin): 
        bot.send_message(mes.chat.id,"Доступ запрещен")
        return
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
    if mes.chat.id != int(id_admin): 
        bot.send_message(mes.chat.id,f"{mes.chat.id}, {id_admin}"+"Доступ запрещен")
        return
    """
    Обработчик команд:
    /info  - выведет информацию о разработчике.
    """
    text = """Бот разработан Манаевой Кариной
    Почта: sowa_sidit_na_vetke@mail.ru
"""
    bot.send_message(mes.chat.id, text)

@bot.message_handler(commands=['log'])
def handle_commands(mes: Message):
    if mes.chat.id != int(id_admin):
         bot.send_message(mes.chat.id, "Доступ запрещен")
         return
    """
    Обработчик команд:
    /info  - выведет информацию о разработчике.
    """
    text = """Вышла новая версия"""
    bot.send_message(mes.chat.id, text)

@bot.message_handler(commands=['calc'])
def handle_calc(message: Message):
    if message.chat.id != int(id_admin):
        bot.send_message(message.chat.id, "Доступ запрещен")
        return
    try:
        # Пример: /calc buy 1.2345 1.2000
        args = message.text.split()[1:]
        if len(args) != 3:
            bot.reply_to(message, "Формат: /calc buy|sell <цена входа> <стоп-лосс>")
            return

        side, entry, stop = args
        entry = float(entry)
        stop = float(stop)

        response = calculate_position(side, entry, stop)
        bot.reply_to(message, response)
    except Exception as e:
        bot.reply_to(message, f"Ошибка: {e}")

# Обработчик /b: /b buy eth 3000 2900 3300
@bot.message_handler(commands=["b"])
def handle_order(message: Message):
    if message.chat.id != int(id_admin):
        bot.send_message(message.chat.id, "Доступ запрещен")
        return
    try:
        args = message.text.split()[1:]
        if len(args) != 5:
            bot.reply_to(message, "Формат: /b buy|sell coin entry_price stop_loss take_profit\n"
                                  "Пример: /b buy eth 3000 2900 3300")
            return

        side = args[0].lower()
        coin = args[1]
        entry_price = float(args[2])
        stop_loss = float(args[3])
        take_profit = float(args[4])

        result = place_limit_order_with_risk_control(
            side, entry_price, stop_loss, take_profit, coin
        )
        bot.reply_to(message, result)
    except Exception as e:
        bot.reply_to(message, f"Ошибка в команде: {e}")

def calculate_position(side: str, entry_price: float, stop_loss: float, max_loss: float = 5.0) -> str:
    try:
        # Проверка направления сделки
        if side.lower() not in ['buy', 'sell']:
            return "Укажите 'buy' (покупка) или 'sell' (продажа)."

        # Расчёт разницы между входом и стоп-лоссом
        delta = abs(entry_price - stop_loss)

        if delta == 0:
            return "Цена входа и стоп-лосс не могут быть одинаковыми."

        # Количество монет
        quantity = max_loss / delta

        return (f"{'Покупка' if side.lower() == 'buy' else 'Продажа'}\n"
                f"Цена входа: {entry_price}\n"
                f"Стоп-лосс: {stop_loss}\n"
                f"Риск: ${max_loss}\n"
                f"Объём позиции: {quantity:.4f} монет")
    except Exception as e:
        return f"Ошибка в расчётах: {e}"
        
def place_limit_order_with_risk_control(side, entry_price, stop_loss, take_profit,
                                        coin: str, risk_usd=5.0):
    try:
        symbol = coin.upper() + "USDT"

        # Получаем информацию о символе (в т.ч. шаг объема qty_step)
        info = bybit.get_instruments_info(
            category="linear",
            symbol=symbol
        )
        symbol_info = info.get("result", {}).get("list", [{}])[0]
        qty_step = float(symbol_info.get("lotSizeFilter", {}).get("qtyStep", 0.001))

        if not qty_step:
            return f"Не удалось получить qtyStep для {symbol}."

        # Расчёт объёма позиции по риску
        price_diff = abs(entry_price - stop_loss)
        if price_diff == 0:
            return "Ошибка: цена входа и стоп-лосс совпадают."

        raw_qty = risk_usd / price_diff
        # Округляем вниз до ближайшего шага (qty_step)
        precision = abs(str(qty_step).find('.') - len(str(qty_step))) if '.' in str(qty_step) else 0
        rounded_qty = (int(raw_qty / qty_step)) * qty_step
        rounded_qty = round(rounded_qty, precision)

        if rounded_qty == 0:
            return f"Рассчитанное количество ({raw_qty}) слишком мало для торговли {symbol}."

        # Создание лимитного ордера
        order = bybit.place_order(
            category="linear",
            symbol=symbol,
            side="Buy" if side == "buy" else "Sell",
            order_type="Limit",
            price=entry_price,
            qty=rounded_qty,
            time_in_force="GoodTillCancel",
            reduce_only=False,
            close_on_trigger=False
        )

        order_id = order.get("result", {}).get("orderId")
        if not order_id:
            return f"Не удалось создать ордер: {order}"

        # Установка SL/TP
        bybit.set_trading_stop(
            category="linear",
            symbol=symbol,
            stop_loss=str(stop_loss),
            take_profit=str(take_profit),
            position_idx=0
        )

        return (f"✅ Ордер создан по {symbol}:\n"
                f"{side.upper()} @ {entry_price}\n"
                f"Объём: {quantity}\n"
                f"SL: {stop_loss}, TP: {take_profit}")
    except Exception as e:
        return f"Ошибка: {e}"
        
if __name__ == '__main__':
    bot.polling()