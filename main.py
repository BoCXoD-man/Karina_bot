
import os
import threading
import time

import telebot
from telebot.types import Message, ReplyKeyboardRemove as Rkr
from pybit.unified_trading import HTTP

# ENV переменные
TOKEN = os.getenv("BOT_TOKEN")
id_admin = os.getenv("bot_admin")
BYBIT_API_KEY = os.getenv("BYBIT_API_KEY")
BYBIT_API_SECRET = os.getenv("BYBIT_API_SECRET")

bybit = HTTP(
    api_key=BYBIT_API_KEY,
    api_secret=BYBIT_API_SECRET,
    testnet=False
)

bot = telebot.TeleBot(TOKEN)
clear_kb = Rkr()
active_trackers = {}

@bot.message_handler(commands=['start', 'menu'])
def handle_commands(mes: Message):
    if mes.chat.id != int(id_admin):
        bot.send_message(mes.chat.id, "Доступ запрещен")
        return
    bot.send_message(mes.chat.id,
        "/start - начать работу\n"
        "/info - информация о разработчике\n"
        "/calc - калькулятор риска\n"
        "/b - лимитный ордер\n"
        "/track <coin> - следить за позицией\n"
        "/cancel <coin> - остановить слежение"
    )

@bot.message_handler(commands=['info'])
def handle_info(mes: Message):
    if mes.chat.id != int(id_admin):
        bot.send_message(mes.chat.id, "Доступ запрещен")
        return
    bot.send_message(mes.chat.id, "Бот разработан Манаевой Кариной\nПочта: sowa_sidit_na_vetke@mail.ru")

@bot.message_handler(commands=['calc'])
def handle_calc(message: Message):
    if message.chat.id != int(id_admin):
        bot.send_message(message.chat.id, "Доступ запрещен")
        return
    try:
        args = message.text.split()[1:]
        if len(args) != 3:
            bot.reply_to(message, "Формат: /calc buy|sell <вход> <SL>")
            return
        side, entry, stop = args
        entry = float(entry)
        stop = float(stop)
        response = calculate_position(side, entry, stop)
        bot.reply_to(message, response)
    except Exception as e:
        bot.reply_to(message, f"Ошибка: {e}")

@bot.message_handler(commands=["b"])
def handle_order(message: Message):
    if message.chat.id != int(id_admin):
        bot.send_message(message.chat.id, "Доступ запрещен")
        return
    try:
        args = message.text.split()[1:]
        if len(args) != 5:
            bot.reply_to(message, "Формат: /b buy|sell coin entry stop_loss take_profit")
            return
        side = args[0].lower()
        coin = args[1]
        entry_price = float(args[2])
        stop_loss = float(args[3])
        take_profit = float(args[4])
        result = place_limit_order_with_tp_sl(side, entry_price, stop_loss, take_profit, coin)
        bot.reply_to(message, result)
    except Exception as e:
        bot.reply_to(message, f"Ошибка в команде: {e}")

@bot.message_handler(commands=["track"])
def handle_tracking(message: Message):
    if message.chat.id != int(id_admin):
        bot.send_message(message.chat.id, "Доступ запрещен")
        return
    args = message.text.split()[1:]
    if len(args) != 1:
        bot.send_message(message.chat.id, "Формат: /track <coin>")
        return
    coin = args[0].lower()
    if coin in active_trackers:
        bot.send_message(message.chat.id, f"{coin.upper()} уже отслеживается.")
        return
    active_trackers[coin] = True
    thread = threading.Thread(target=tracking_loop, args=(coin, message.chat.id), daemon=True)
    thread.start()
    bot.send_message(message.chat.id, f"Начато отслеживание {coin.upper()}")

@bot.message_handler(commands=["cancel"])
def handle_cancel(message: Message):
    if message.chat.id != int(id_admin):
        bot.send_message(message.chat.id, "Доступ запрещен")
        return
    args = message.text.split()[1:]
    if len(args) != 1:
        bot.send_message(message.chat.id, "Формат: /cancel <coin>")
        return
    coin = args[0].lower()
    if coin not in active_trackers:
        bot.send_message(message.chat.id, f"{coin.upper()} не отслеживается.")
        return
    active_trackers.pop(coin, None)
    bot.send_message(message.chat.id, f"Мониторинг {coin.upper()} остановлен.")

def calculate_position(side: str, entry_price: float, stop_loss: float, max_loss: float = 5.0) -> str:
    delta = abs(entry_price - stop_loss)
    if delta == 0:
        return "Вход и SL не могут совпадать"
    quantity = max_loss / delta
    return f"{side.upper()} @ {entry_price}, SL: {stop_loss}, Risk: ${max_loss}, Qty: {quantity:.4f}"

def place_limit_order_with_tp_sl(side, entry_price, stop_loss, take_profit, coin, risk_usd=5.0):
    symbol = coin.upper() + "USDT"
    try:
        info = bybit.get_instruments_info(category="linear", symbol=symbol)
        sym = info["result"]["list"][0]
        qty_step = float(sym["lotSizeFilter"]["qtyStep"])
        diff = abs(entry_price - stop_loss)
        if diff == 0:
            return "Ошибка: стоп совпадает с входом"
        raw_qty = risk_usd / diff
        precision = str(qty_step)[::-1].find('.')
        qty = round(int(raw_qty / qty_step) * qty_step, precision)
        if qty == 0:
            return f"Qty слишком мало: {raw_qty:.6f}"
        pos_idx = 1 if side == "buy" else 2
        order = bybit.place_order(
            category="linear", symbol=symbol, side=side.capitalize(), order_type="Limit",
            price=entry_price, qty=qty, time_in_force="GTC", position_idx=pos_idx,
            take_profit=str(take_profit), stop_loss=str(stop_loss), reduce_only=False, close_on_trigger=False
        )
        order_id = order.get("result", {}).get("orderId")
        if not order_id:
            return f"Ошибка создания: {order}"
        return f"Ордер размещён: {side.upper()} {symbol} @ {entry_price}, Qty: {qty}"
    except Exception as e:
        return f"Ошибка: {e}"

def tracking_loop(coin: str, chat_id: int):
    symbol = coin.upper() + "USDT"
    while active_trackers.get(coin):
        try:
            pos_data = bybit.get_positions(category="linear", symbol=symbol)
            position = pos_data["result"]["list"][0]
            size = float(position["size"])
            if size == 0:
                bot.send_message(chat_id, f"{symbol}: позиция закрыта.")
                active_trackers.pop(coin, None)
                break
            entry_price = float(position["entryPrice"])
            take_profit = float(position["takeProfit"]) if position["takeProfit"] else None
            if not take_profit:
                bot.send_message(chat_id, f"{symbol}: TP не установлен.")
                active_trackers.pop(coin, None)
                break
            side = "buy" if position["side"] == "Buy" else "sell"
            ticker = bybit.get_ticker(category="linear", symbol=symbol)
            current_price = float(ticker["result"]["list"][0]["lastPrice"])
            tp_distance = abs(take_profit - entry_price)
            half_tp = entry_price + (tp_distance * 0.5 if side == "buy" else -tp_distance * 0.5)
            hit_half = current_price >= half_tp if side == "buy" else current_price <= half_tp
            if hit_half:
                qty_to_close = round(size * 0.5, 4)
                entry_price_with_fee = entry_price * (1.001 if side == "buy" else 0.999)
                bybit.place_order(
                    category="linear", symbol=symbol,
                    side="Sell" if side == "buy" else "Buy",
                    order_type="Market", qty=qty_to_close,
                    reduce_only=True, close_on_trigger=True
                )
                bybit.set_trading_stop(
                    category="linear", symbol=symbol,
                    stop_loss=str(round(entry_price_with_fee, 4))
                )
                bot.send_message(chat_id,
                    f"{symbol}: 50% TP достигнута\n"
                    f"Закрыто: {qty_to_close}, SL: {entry_price_with_fee:.2f}")
                active_trackers.pop(coin, None)
                break
            time.sleep(15)
        except Exception as e:
            bot.send_message(chat_id, f"{symbol} ошибка мониторинга: {e}")
            active_trackers.pop(coin, None)
            break

if __name__ == '__main__':
    bot.polling()
