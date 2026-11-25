import json
import urllib.request
from datetime import datetime, timezone

SUPABASE_URL = "https://tnhvexohouzzycgzscxl.supabase.co"
SUPABASE_KEY = "sb_publishable_WsWNdDvKgO5Tcuu6U0X30g_Xk_-xRtn"

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation",
}


def get_status():
    req = urllib.request.Request(
        f"{SUPABASE_URL}/rest/v1/bot_status?id=eq.1&select=*",
        headers=HEADERS,
        method="GET",
    )
    with urllib.request.urlopen(req, timeout=15) as res:
        data = json.loads(res.read().decode("utf-8"))
        return data[0] if data else None


def update_status(payload):
    req = urllib.request.Request(
        f"{SUPABASE_URL}/rest/v1/bot_status?id=eq.1",
        data=json.dumps(payload).encode("utf-8"),
        headers=HEADERS,
        method="PATCH",
    )
    with urllib.request.urlopen(req, timeout=15) as res:
        return json.loads(res.read().decode("utf-8"))


def send_ntfy(topic, title, message, priority="high"):
    if not topic:
        return
    try:
        safe_title = title.encode("ascii", "ignore").decode("ascii").strip() or "ALGOMAX SIGNAL"
        req = urllib.request.Request(
            f"https://ntfy.sh/{topic}",
            data=message.encode("utf-8"),
            headers={
                "Title": safe_title,
                "Priority": priority,
            },
            method="POST",
        )
        urllib.request.urlopen(req, timeout=10).read()
    except Exception as e:
        print("ntfy error:", e)


def fetch_xauusd_candles():
    for symbol in ["XAUUSD=X", "GC=F"]:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=5m&range=1d"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        try:
            with urllib.request.urlopen(req, timeout=15) as res:
                raw = json.loads(res.read().decode("utf-8"))
                result = raw["chart"]["result"][0]
                quote = result["indicators"]["quote"][0]
                closes = [c for c in quote["close"] if c is not None]
                highs = [h for h in quote["high"] if h is not None]
                lows = [l for l in quote["low"] if l is not None]
                if len(closes) >= 30:
                    return closes, highs, lows, symbol
        except Exception as e:
            print(f"Fetch failed for {symbol}:", e)
    raise RuntimeError("XAUUSDの価格データを取得できませんでした")


def calc_ema(values, period):
    k = 2 / (period + 1)
    ema = sum(values[:period]) / period
    for v in values[period:]:
        ema = v * k + ema * (1 - k)
    return ema


def calc_rsi(values, period=14):
    gains, losses = [], []
    for i in range(1, len(values)):
        diff = values[i] - values[i - 1]
        gains.append(max(diff, 0))
        losses.append(max(-diff, 0))
    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def calc_atr(highs, lows, closes, period=14):
    trs = []
    for i in range(1, len(closes)):
        tr = max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i - 1]),
            abs(lows[i] - closes[i - 1]),
        )
        trs.append(tr)
    return sum(trs[-period:]) / period


def analyze():
    row = get_status()
    if not row:
        print("No row found")
        return

    if not row.get("is_active"):
        print("Bot is stopped (is_active=false). Skipping.")
        return

    closes, highs, lows, sym = fetch_xauusd_candles()
    price = round(closes[-1], 2)
    ema9_now = calc_ema(closes, 9)
    ema21_now = calc_ema(closes, 21)
    ema9_prev = calc_ema(closes[:-1], 9)
    ema21_prev = calc_ema(closes[:-1], 21)
    rsi = round(calc_rsi(closes, 14), 1)
    atr = max(round(calc_atr(highs, lows, closes, 14), 2), 2.5)

    prev_signal = (row.get("signal") or "WAIT").upper()
    prev_entry = float(row.get("entry_price") or 0)
    prev_tp = float(row.get("tp_price") or 0)
    topic = (row.get("ntfy_topic") or "").strip()

    signal = "WAIT"
    entry_price = prev_entry
    tp_price = prev_tp
    sl_price = float(row.get("sl_price") or 0)
    reason = f"RSI={rsi} / EMA9={ema9_now:.2f}, EMA21={ema21_now:.2f}（明確なクロス待ち）"
    notify_msg = None

    # 1. Check Take-Profit (利確タイミング判定)
    if prev_signal == "BUY" and prev_tp > 0:
        if price >= prev_tp or rsi >= 72:
            signal = "TP_EXIT"
            reason = f"買いポジション利確タイミング到達（現在値 {price} / RSI {rsi}）"
            notify_msg = f"【XAUUSD 利確タイミング】BUY決済目安に到達！現在値: {price}（目標TP: {prev_tp} / RSI: {rsi}）"
        else:
            signal = "BUY"
            reason = f"BUY継続中（目標TP: {prev_tp} / 損切りSL: {sl_price} / RSI: {rsi}）"

    elif prev_signal == "SELL" and prev_tp > 0:
        if price <= prev_tp or rsi <= 28:
            signal = "TP_EXIT"
            reason = f"売りポジション利確タイミング到達（現在値 {price} / RSI {rsi}）"
            notify_msg = f"【XAUUSD 利確タイミング】SELL決済目安に到達！現在値: {price}（目標TP: {prev_tp} / RSI: {rsi}）"
        else:
            signal = "SELL"
            reason = f"SELL継続中（目標TP: {prev_tp} / 損切りSL: {sl_price} / RSI: {rsi}）"

    # 2. Check New Entry Signal (新規エントリー判定)
    if signal in ("WAIT", "TP_EXIT"):
        if (ema9_prev <= ema21_prev and ema9_now > ema21_now and 45 <= rsi <= 68) or (
            ema9_now > ema21_now and 52 <= rsi <= 62 and prev_signal == "WAIT"
        ):
            signal = "BUY"
            entry_price = price
            tp_price = round(price + atr * 1.8, 2)
            sl_price = round(price - atr * 1.2, 2)
            reason = f"上昇トレンド発生（EMA9 > EMA21, RSI={rsi}）"
            notify_msg = f"【XAUUSD BUYサイン】買いエントリー目安: {entry_price} / 利確TP: {tp_price} / 損切りSL: {sl_price}"

        elif (ema9_prev >= ema21_prev and ema9_now < ema21_now and 32 <= rsi <= 55) or (
            ema9_now < ema21_now and 38 <= rsi <= 48 and prev_signal == "WAIT"
        ):
            signal = "SELL"
            entry_price = price
            tp_price = round(price - atr * 1.8, 2)
            sl_price = round(price + atr * 1.2, 2)
            reason = f"下降トレンド発生（EMA9 < EMA21, RSI={rsi}）"
            notify_msg = f"【XAUUSD SELLサイン】売りエントリー目安: {entry_price} / 利確TP: {tp_price} / 損切りSL: {sl_price}"
        else:
            signal = "WAIT"
            entry_price = 0
            tp_price = 0
            sl_price = 0

    now_iso = datetime.now(timezone.utc).isoformat()
    log_text = f"[{sym}] 現在値 {price} | 判定: {signal} | {reason}"

    update_status(
        {
            "current_price": price,
            "signal": signal,
            "entry_price": entry_price,
            "tp_price": tp_price,
            "sl_price": sl_price,
            "signal_reason": reason,
            "last_log": log_text,
            "updated_at": now_iso,
        }
    )
    print("Updated:", log_text)

    if notify_msg:
        send_ntfy(topic, f"ALGOMAX XAUUSD: {signal}", notify_msg, priority="urgent")


if __name__ == "__main__":
    analyze()
