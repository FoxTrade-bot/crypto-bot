import requests
import time
import threading
from datetime import datetime

TOKEN = "8672028530:AAHgvTc6ZjxEvTckYPLP5FEeln3_RhJ71_8"
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

last_update_id = 0
bot_running = True
last_signal_time = {}

def send_message(chat_id, text, keyboard=None):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    data = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    if keyboard:
        data["reply_markup"] = keyboard
    try:
        requests.post(url, json=data, timeout=10)
    except:
        pass

def get_market_data(symbol):
    try:
        r = requests.get(f"https://api.binance.com/api/v3/ticker/24hr?symbol={symbol}", timeout=10)
        d = r.json()
        if 'priceChangePercent' not in d:
            return None
        price = float(d['lastPrice'])
        change = float(d['priceChangePercent'])
        volume = float(d['quoteVolume'])
        
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
        return {"price": price, "rsi": rsi, "change": change, "vol_ratio": vol_ratio}
    except:
        return None

def get_fear_greed():
    try:
        r = requests.get("https://api.alternative.me/fng/", timeout=10)
        data = r.json()
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
    except:
        pass
    return "😐 НЕЙТРАЛЬНО (50/100)", 50

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
    return min(100, max(0, score))

def find_best_signal():
    best_signal = None
    best_score = 0
    for symbol in SYMBOLS:
        data = get_market_data(symbol)
        if not data:
            continue
        long_score = calculate_score(data, "LONG")
        if long_score > best_score and long_score >= 50:
            best_score = long_score
            best_signal = (symbol, data, "LONG", long_score)
        short_score = calculate_score(data, "SHORT")
        if short_score > best_score and short_score >= 50:
            best_score = short_score
            best_signal = (symbol, data, "SHORT", short_score)
    return best_signal

def format_price(price):
    if price >= 1:
        return f"${price:.4f}"
    if price >= 0.00001:
        return f"${price:.8f}"
    return f"${price:.10f}"

def send_signal(chat_id):
    now = time.time()
    if str(chat_id) in last_signal_time and now - last_signal_time[str(chat_id)] < 300:
        wait = int(300 - (now - last_signal_time[str(chat_id)]))
        send_message(chat_id, f"⚠️ Подожди {wait} секунд")
        return
    
    send_message(chat_id, f"🔍 Анализ {len(SYMBOLS)} монет...")
    result = find_best_signal()
    
    if not result:
        send_message(chat_id, "⚠️ Нет хороших сигналов\nПопробуй через 5-10 минут")
        return
    
    symbol, data, signal_type, final_score = result
    symbol_clean = symbol.replace('USDT', '')
    
    if final_score >= 80:
        quality = "🏆 ОТЛИЧНЫЙ"
    elif final_score >= 65:
        quality = "✅ ХОРОШИЙ"
    else:
        quality = "📈 СРЕДНИЙ"
    
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
    else:
        tp = round(entry * (1 - tp_pct / 100), 8)
        sl = round(entry * (1 + sl_pct / 100), 8)
    
    direction = "🟢 LONG ⬆️" if signal_type == "LONG" else "🔴 SHORT ⬇️"
    fear_greed_text, _ = get_fear_greed()
    
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
RSI: {data['rsi']:.0f} | 24ч: {data['change']:+.1f}%
Объем: x{data['vol_ratio']:.1f}

📰 Рынок:
{fear_greed_text}

🧠 Качество: {final_score:.0f}%

⚡️ При +1.5% → SL в безубыток
⚡️ При +2% → зафиксируй 30-50%

⏰ {datetime.now().strftime('%H:%M:%S')} UTC"""
    
    send_message(chat_id, msg)
    last_signal_time[str(chat_id)] = now
    print(f"✅ Сигнал: {symbol_clean} {signal_type} | {final_score:.0f}%")

def get_updates():
    global last_update_id, bot_running
    while bot_running:
        try:
            url = f"https://api.telegram.org/bot{TOKEN}/getUpdates"
            params = {"offset": last_update_id + 1, "timeout": 30}
            r = requests.get(url, params=params, timeout=35)
            data = r.json()
            
            if data.get("ok") and data.get("result"):
                for update in data["result"]:
                    last_update_id = update["update_id"]
                    if "message" in update:
                        msg = update["message"]
                        cid = msg["chat"]["id"]
                        if "text" in msg:
                            txt = msg["text"].strip()
                            print(f"📩 Получено: {txt}")
                            
                            if txt == "/start":
                                keyboard = {
                                    "keyboard": [["/signal", "/fear"], ["/btc", "/help"]],
                                    "resize_keyboard": True
                                }
                                send_message(cid, f"🤖 <b>КРИПТО-СИГНАЛ БОТ</b>\n\n📊 Монет: {len(SYMBOLS)}\n💰 Депозит: ${FIXED_ACCOUNT}\n\n/signal - сигнал\n/fear - страх и жадность\n/btc - анализ BTC", keyboard)
                            elif txt == "/signal":
                                send_signal(cid)
                            elif txt == "/fear":
                                fg_text, _ = get_fear_greed()
                                send_message(cid, f"📊 <b>ИНДЕКС СТРАХА И ЖАДНОСТИ</b>\n\n{fg_text}")
                            elif txt == "/btc":
                                btc = get_market_data("BTCUSDT")
                                if btc:
                                    send_message(cid, f"📊 <b>BTC АНАЛИЗ</b>\n\n💰 ${btc['price']:,.0f}\n📈 24ч: {btc['change']:+.1f}%\n🎯 RSI: {btc['rsi']:.0f}")
                                else:
                                    send_message(cid, "❌ Ошибка получения BTC")
                            elif txt == "/help":
                                send_message(cid, "❓ <b>ПОМОЩЬ</b>\n\n/signal - сигнал\n/fear - страх и жадность\n/btc - анализ BTC")
            time.sleep(1)
        except Exception as e:
            print(f"Ошибка: {e}")
            time.sleep(5)

def main():
    print("=" * 50)
    print("🚀 КРИПТО-СИГНАЛ БОТ")
    print(f"📊 Монет: {len(SYMBOLS)}")
    print("😨 Fear & Greed: ВКЛ")
    print("=" * 50)
    
    thread = threading.Thread(target=get_updates, daemon=True)
    thread.start()
    
    print("✅ Бот запущен!")
    print("📡 Отправьте /start в Telegram")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        global bot_running
        bot_running = False
        print("🛑 Бот остановлен")

if __name__ == "__main__":
    main()
