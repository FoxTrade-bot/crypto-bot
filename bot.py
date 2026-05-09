import requests
import time
import json
import os
from datetime import datetime
import threading

# ===== КОНФИГУРАЦИЯ =====
TOKEN = "8672028530:AAHgvTc6ZjxEvTckYPLP5FEeln3_RhJ71_8"
ADMIN_ID = "1539611049"
FIXED_ACCOUNT = 1000

# ===== ВСЕ 62 МОНЕТЫ =====
SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT",
    "ADAUSDT", "AVAXUSDT", "DOTUSDT", "LINKUSDT", "MATICUSDT",
    "UNIUSDT", "ATOMUSDT", "ETCUSDT", "FILUSDT", "APTUSDT",
    "ARBUSDT", "OPUSDT", "SUIUSDT", "NEARUSDT", "LTCUSDT",
    "BCHUSDT", "XLMUSDT", "VETUSDT", "ALGOUSDT", "EGLDUSDT",
    "DOGEUSDT", "SHIBUSDT", "PEPEUSDT", "BONKUSDT", "WIFUSDT", "FLOKIUSDT",
    "TRUMPUSDT", "NOTUSDT", "PENGUUSDT", "PNUTUSDT", "DOGSUSDT",
    "MEWUSDT", "POPCATUSDT", "NEIROUSDT", "MYROUSDT", "MUMUUSDT",
    "BRETTUSDT", "MOGUSDT", "MEMEUSDT", "AIDOGEUSDT",
    "FARTCOINUSDT", "BROCCOLIUSDT", "PONKEUSDT", "PIPPINUSDT",
    "GIGGLEUSDT", "USELESSUSDT", "WHITEWHALEUSDT", "CLANKERUSDT",
    "FOURUSDT", "ZORAUSDT", "NOICEUSDT", "LMTSUSDT", "DEGENUSDT",
    "BNKRUSDT", "VIRTUALUSDT", "BNLIFEUSDT", "HAJIMIUSDT"
]

# Глобальные переменные
last_update_id = 0
bot_running = True
last_signal_time = {}

# ===== ФУНКЦИЯ ОТПРАВКИ СООБЩЕНИЙ =====
def send_message(chat_id, text, keyboard=None):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    data = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML"
    }
    if keyboard:
        data["reply_markup"] = keyboard
    try:
        response = requests.post(url, json=data, timeout=10)
        return response.json()
    except Exception as e:
        print(f"Ошибка отправки: {e}")
        return None

# ===== РЫНОЧНЫЕ ДАННЫЕ =====
def get_market_data(symbol):
    try:
        url = f"https://api.binance.com/api/v3/ticker/24hr?symbol={symbol}"
        response = requests.get(url, timeout=10)
        data = response.json()
        
        if 'priceChangePercent' not in data:
            return None
            
        price = float(data['lastPrice'])
        change = float(data['priceChangePercent'])
        volume = float(data['quoteVolume'])
        high = float(data['highPrice'])
        low = float(data['lowPrice'])
        
        # Расчет RSI
        if change <= -5:
            rsi = 25
        elif change <= -3:
            rsi = 30
        elif change <= -1:
            rsi = 40
        elif change >= 5:
            rsi = 75
        elif change >= 3:
            rsi = 70
        elif change >= 1:
            rsi = 60
        else:
            rsi = 50
        
        vol_ratio = min(volume / 10000000, 5) if volume > 0 else 1
        volatility = ((high - low) / price) * 100
        
        return {
            "price": price,
            "rsi": rsi,
            "change": change,
            "vol_ratio": vol_ratio,
            "volatility": volatility
        }
    except Exception as e:
        print(f"Ошибка получения {symbol}: {e}")
        return None

# ===== FEAR & GREED INDEX =====
def get_fear_greed():
    try:
        url = "https://api.alternative.me/fng/"
        response = requests.get(url, timeout=10)
        data = response.json()
        
        if data and data.get('data'):
            value = int(data['data'][0]['value'])
            if value <= 25:
                status = "😨 ЭКСТРЕМАЛЬНЫЙ СТРАХ"
            elif value <= 45:
                status = "😐 СТРАХ"
            elif value <= 55:
                status = "😐 НЕЙТРАЛЬНО"
            elif value <= 75:
                status = "😊 ЖАДНОСТЬ"
            else:
                status = "🤑 ЭКСТРЕМАЛЬНАЯ ЖАДНОСТЬ"
            return f"{status} ({value}/100)", value
    except Exception as e:
        print(f"Ошибка Fear&Greed: {e}")
    
    return "😐 НЕЙТРАЛЬНО (50/100)", 50

# ===== РАСЧЕТ ОЦЕНКИ =====
def calculate_score(data, signal_type):
    score = 50
    
    if signal_type == "LONG":
        if data['rsi'] <= 30:
            score += 30
        elif data['rsi'] <= 40:
            score += 15
            
        if data['change'] < -3:
            score += 20
        elif data['change'] < -1:
            score += 10
    else:
        if data['rsi'] >= 70:
            score += 30
        elif data['rsi'] >= 60:
            score += 15
            
        if data['change'] > 3:
            score += 20
        elif data['change'] > 1:
            score += 10
    
    if data['vol_ratio'] > 2:
        score += 15
    elif data['vol_ratio'] > 1.5:
        score += 10
    
    # Временной бонус
    hour = datetime.now().hour
    if 13 <= hour <= 18:
        score += 10
    elif hour <= 6 or hour >= 22:
        score -= 10
    
    return min(100, max(0, score))

# ===== ПОИСК ЛУЧШЕГО СИГНАЛА =====
def find_best_signal():
    best_signal = None
    best_score = 0
    
    for symbol in SYMBOLS:
        data = get_market_data(symbol)
        if not data:
            continue
        
        # LONG
        long_score = calculate_score(data, "LONG")
        if long_score > best_score and long_score >= 50:
            best_score = long_score
            best_signal = (symbol, data, "LONG", long_score)
        
        # SHORT
        short_score = calculate_score(data, "SHORT")
        if short_score > best_score and short_score >= 50:
            best_score = short_score
            best_signal = (symbol, data, "SHORT", short_score)
    
    return best_signal

# ===== ФОРМАТИРОВАНИЕ ЦЕНЫ =====
def format_price(price):
    if price >= 1:
        return f"${price:.4f}"
    elif price >= 0.00001:
        return f"${price:.8f}"
    else:
        return f"${price:.10f}"

# ===== ОТПРАВКА СИГНАЛА =====
def send_signal(chat_id):
    # Проверка на флуд (5 минут)
    now = time.time()
    if str(chat_id) in last_signal_time:
        if now - last_signal_time[str(chat_id)] < 300:
            wait = int(300 - (now - last_signal_time[str(chat_id)]))
            send_message(chat_id, f"⚠️ Подожди {wait} секунд перед следующим сигналом")
            return
    
    send_message(chat_id, f"🔍 Анализ {len(SYMBOLS)} монет...")
    
    result = find_best_signal()
    
    if not result:
        send_message(chat_id, "⚠️ Сейчас нет подходящих сигналов\nПопробуй через 5-10 минут")
        return
    
    symbol, data, signal_type, final_score = result
    symbol_clean = symbol.replace('USDT', '')
    
    # Определяем качество
    if final_score >= 80:
        quality = "🏆 ОТЛИЧНЫЙ"
    elif final_score >= 65:
        quality = "✅ ХОРОШИЙ"
    else:
        quality = "📈 СРЕДНИЙ"
    
    # Расчет плеча
    if final_score >= 85:
        leverage = 25
    elif final_score >= 75:
        leverage = 20
    elif final_score >= 65:
        leverage = 18
    elif final_score >= 55:
        leverage = 15
    else:
        leverage = 12
    
    entry = data['price']
    position_size = FIXED_ACCOUNT * 0.15
    tp_pct = 6
    sl_pct = 4
    
    if signal_type == "LONG":
        tp = round(entry * (1 + tp_pct / 100), 8)
        sl = round(entry * (1 - sl_pct / 100), 8)
        risk_reward = (tp_pct * leverage) / (sl_pct * leverage)
    else:
        tp = round(entry * (1 - tp_pct / 100), 8)
        sl = round(entry * (1 + sl_pct / 100), 8)
    
    direction = "🟢 LONG ⬆️" if signal_type == "LONG" else "🔴 SHORT ⬇️"
    
    # Fear & Greed
    fear_greed_text, fear_greed_value = get_fear_greed()
    
    # BTC анализ
    btc = get_market_data("BTCUSDT")
    if btc:
        btc_change = btc['change']
        if btc_change > 1:
            btc_status = "🟢 БЫЧИЙ"
        elif btc_change < -1:
            btc_status = "🔴 МЕДВЕЖИЙ"
        else:
            btc_status = "🟡 НЕЙТРАЛЬНЫЙ"
    else:
        btc_change = 0
        btc_status = "🟡 НЕЙТРАЛЬНЫЙ"
    
    # Создаем сообщение
    msg = f"""{direction} · {quality}

<b>{symbol_clean}</b>

💰 Вход: {format_price(entry)}
🎯 TP: {format_price(tp)}
🛑 SL: {format_price(sl)}

📊 Параметры:
• Плечо: {leverage}x
• Размер: ${position_size:.0f}
• Потенциал: +{tp_pct * leverage:.0f}%
• Риск: -{sl_pct * leverage:.0f}%

📈 Данные:
RSI: {data['rsi']:.0f}
24ч: {data['change']:+.1f}%
Объем: x{data['vol_ratio']:.1f}

📰 Рынок:
{fear_greed_text}
BTC: {btc_change:+.1f}% ({btc_status})

🧠 Качество: {final_score:.0f}%

⚡️ При +1.5% → SL в безубыток
⚡️ При +2% → зафиксируй 30-50%

⏰ {datetime.now().strftime('%H:%M:%S')} UTC"""
    
    send_message(chat_id, msg)
    last_signal_time[str(chat_id)] = now
    print(f"✅ Сигнал отправлен: {symbol_clean} {signal_type} | {final_score:.0f}%")

# ===== ГЛАВНОЕ МЕНЮ =====
def send_main_menu(chat_id):
    keyboard = {
        "keyboard": [
            ["📊 /signal", "😨 /fear"],
            ["📈 /btc", "❓ /help"]
        ],
        "resize_keyboard": True
    }
    
    text = f"""🤖 <b>КРИПТО-СИГНАЛ БОТ</b>

📊 <b>Статистика:</b>
• Монет в анализе: {len(SYMBOLS)}
• Депозит: ${FIXED_ACCOUNT:,}
• Плечо: 12-25x (ИИ)

<b>Команды:</b>
📊 /signal - получить сигнал
😨 /fear - индекс страха и жадности
📈 /btc - анализ BTC
❓ /help - помощь"""
    
    send_message(chat_id, text, keyboard)

# ===== ОБРАБОТЧИК ОБНОВЛЕНИЙ =====
def get_updates():
    global last_update_id, bot_running
    
    while bot_running:
        try:
            url = f"https://api.telegram.org/bot{TOKEN}/getUpdates"
            params = {
                "offset": last_update_id + 1,
                "timeout": 30
            }
            
            response = requests.get(url, params=params, timeout=35)
            data = response.json()
            
            if data.get("ok") and data.get("result"):
                for update in data["result"]:
                    last_update_id = update["update_id"]
                    
                    if "message" in update:
                        msg = update["message"]
                        chat_id = msg["chat"]["id"]
                        
                        if "text" in msg:
                            text = msg["text"].strip()
                            print(f"📩 Получено сообщение от {chat_id}: {text}")
                            
                            if text == "/start":
                                send_main_menu(chat_id)
                            elif text == "/signal" or text == "📊 /signal":
                                send_signal(chat_id)
                            elif text == "/fear" or text == "😨 /fear":
                                fg_text, fg_value = get_fear_greed()
                                send_message(chat_id, f"📊 <b>ИНДЕКС СТРАХА И ЖАДНОСТИ</b>\n\n{fg_text}")
                            elif text == "/btc" or text == "📈 /btc":
                                btc = get_market_data("BTCUSDT")
                                if btc:
                                    msg_text = f"""📊 <b>BTC АНАЛИЗ</b>

💰 Цена: ${btc['price']:,.0f}
📈 24ч: {btc['change']:+.1f}%
🎯 RSI: {btc['rsi']:.0f}
📊 Объем: x{btc['vol_ratio']:.1f}"""
                                    send_message(chat_id, msg_text)
                                else:
                                    send_message(chat_id, "❌ Ошибка получения данных BTC")
                            elif text == "/help" or text == "❓ /help":
                                help_text = """❓ <b>ПОМОЩЬ</b>

<b>Команды:</b>
/signal - получить торговый сигнал
/fear - индекс страха и жадности
/btc - анализ BTC

<b>Как торговать:</b>
1. Получи сигнал
2. Открой позицию на бирже
3. Установи TP и SL
4. Соблюдай риск-менеджмент

<b>Советы:</b>
• Не рискуй более 2-5% депозита
• Всегда ставь стоп-лосс
• Фиксируй прибыль частями"""
                                send_message(chat_id, help_text)
                            else:
                                # Ответ на неизвестную команду
                                send_message(chat_id, "❓ Неизвестная команда. Используй /help")
            
            time.sleep(0.5)
            
        except Exception as e:
            print(f"❌ Ошибка в get_updates: {e}")
            time.sleep(5)

# ===== ЗАПУСК =====
def main():
    global bot_running
    
    print("=" * 50)
    print("🚀 КРИПТО-СИГНАЛ БОТ")
    print(f"📊 Монет: {len(SYMBOLS)}")
    print(f"😨 Fear & Greed: ВКЛ")
    print(f"🤖 Telegram бот: ВКЛ")
    print("=" * 50)
    
    # Запускаем поток для получения обновлений
    thread = threading.Thread(target=get_updates, daemon=True)
    thread.start()
    
    print("✅ Бот успешно запущен!")
    print("📡 Отправьте /start в Telegram")
    print("🛑 Для остановки нажмите Ctrl+C")
    print("=" * 50)
    
    try:
        while bot_running:
            time.sleep(1)
    except KeyboardInterrupt:
        bot_running = False
        print("\n🛑 Бот остановлен")

if __name__ == "__main__":
    main()
