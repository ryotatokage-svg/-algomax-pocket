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
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=15m&range=5d"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        try:
            with urllib.request.urlopen(req, timeout=15) as res:
                raw = json.loads(res.read().decode("utf-8"))
                result = raw["chart"]["result"][0]
                quote = result["indicators"]["quote"][0]
                closes = [c for c in quote["close"] if c is not None]
                highs = [h for h in quote["high"] if h is not None]
                lows = [l for l in quote["low"] if l is not None]
                if len(closes) >= 60:
                    return closes, highs, lows, symbol
        except Exception as e:
            print(f"Fetch failed for {symbol}:", e)
    raise RuntimeError("XAUUSDの15分足データを取得できませんでした")


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
    ema50_now = calc_ema(closes, 50)

    ema9_prev = calc_ema(closes[:-1], 9)
    ema21_prev = calc_ema(closes[:-1], 21)
    ema21_3ago = calc_ema(closes[:-3], 21)
    ema50_3ago = calc_ema(closes[:-3], 50)

    rsi = round(calc_rsi(closes, 14), 1)
    atr = max(round(calc_atr(highs, lows, closes, 14), 2), 4.0)

    ema21_slope = ema21_now - ema21_3ago
    ema50_slope = ema50_now - ema50_3ago

    prev_signal = (row.get("signal") or "WAIT").upper()
    prev_entry = float(row.get("entry_price") or 0)
    prev_tp = float(row.get("tp_price") or 0)
    prev_sl = float(row.get("sl_price") or 0)
    topic = (row.get("ntfy_topic") or "").strip()

    signal = "WAIT"
    entry_price = prev_entry
    tp_price = prev_tp
    sl_price = prev_sl
    reason = f"[15m] RSI={rsi} / EMA9={ema9_now:.2f}, EMA21={ema21_now:.2f}, EMA50={ema50_now:.2f}（トレンド発生待ち）"
    notify_msg = None
    notify_priority = "urgent"

    # 1. 保有中トレンドの継続・転換（トレンド転換サインまで引っ張る）判定
    if prev_signal == "BUY":
        trend_reversed = (ema9_now < ema21_now and ema9_prev < ema21_prev) or (
            price < ema21_now and ema21_slope < 0
        )
        if trend_reversed:
            signal = "TP_EXIT"
            reason = (
                f"[15m] 上昇トレンド転換サイン（現在値 {price} / EMA9 {ema9_now:.2f} / "
                f"EMA21 {ema21_now:.2f} / RSI {rsi}）"
            )
            notify_msg = (
                f"【XAUUSD 15m 利確サイン】上昇トレンド転換を検知！BUY決済検討｜"
                f"現在値: {price}（EMA21: {ema21_now:.2f} / RSI: {rsi}）"
            )
        else:
            new_sl = max(prev_sl, round(ema21_now - atr * 1.2, 2))
            signal = "BUY"
            sl_price = new_sl
            reason = (
                f"[15m] 上昇トレンド継続中・利益伸ばし中（現在値 {price} / "
                f"目安SL: {sl_price} / RSI: {rsi}）"
            )

    elif prev_signal == "SELL":
        trend_reversed = (ema9_now > ema21_now and ema9_prev > ema21_prev) or (
            price > ema21_now and ema21_slope > 0
        )
        if trend_reversed:
            signal = "TP_EXIT"
            reason = (
                f"[15m] 下降トレンド転換サイン（現在値 {price} / EMA9 {ema9_now:.2f} / "
                f"EMA21 {ema21_now:.2f} / RSI {rsi}）"
            )
            notify_msg = (
                f"【XAUUSD 15m 利確サイン】下降トレンド転換を検知！SELL決済検討｜"
                f"現在値: {price}（EMA21: {ema21_now:.2f} / RSI: {rsi}）"
            )
        else:
            new_sl = (
                min(prev_sl, round(ema21_now + atr * 1.2, 2))
                if prev_sl > 0
                else round(ema21_now + atr * 1.2, 2)
            )
            signal = "SELL"
            sl_price = new_sl
            reason = (
                f"[15m] 下降トレンド継続中・利益伸ばし中（現在値 {price} / "
                f"目安SL: {sl_price} / RSI: {rsi}）"
            )

    # 2. 新規トレンドエントリー判定（15分足の順張り・トレンド継続）
    if signal in ("WAIT", "TP_EXIT"):
        up_trend = (
            price > ema9_now > ema21_now > ema50_now
            and ema21_slope > 0
            and ema50_slope >= 0
            and 50 <= rsi <= 72
        )
        down_trend = (
            price < ema9_now < ema21_now < ema50_now
            and ema21_slope < 0
            and ema50_slope <= 0
            and 28 <= rsi <= 50
        )

        if up_trend and prev_signal != "BUY":
            signal = "BUY"
            entry_price = price
            tp_price = round(price + atr * 4.0, 2)
            sl_price = round(min(price - atr * 1.5, ema21_now - atr * 0.5), 2)
            reason = f"[15m] 上昇トレンド検知（EMA9>21>50・傾き上昇・RSI={rsi}）"
            notify_msg = (
                f"【XAUUSD 15m BUYサイン】上昇トレンド検知！エントリー目安: {entry_price} / "
                f"参考TP: {tp_price} / 目安SL: {sl_price}（RSI: {rsi}）"
            )

        elif down_trend and prev_signal != "SELL":
            signal = "SELL"
            entry_price = price
            tp_price = round(price - atr * 4.0, 2)
            sl_price = round(max(price + atr * 1.5, ema21_now + atr * 0.5), 2)
            reason = f"[15m] 下降トレンド検知（EMA9<21<50・傾き下降・RSI={rsi}）"
            notify_msg = (
                f"【XAUUSD 15m SELLサイン】下降トレンド検知！エントリー目安: {entry_price} / "
                f"参考TP: {tp_price} / 目安SL: {sl_price}（RSI: {rsi}）"
            )
        else:
            signal = "WAIT"
            entry_price = 0
            tp_price = 0
            sl_price = 0
            reason = (
                f"[15m] RSI={rsi} / EMA9={ema9_now:.2f}, EMA21={ema21_now:.2f}, EMA50={ema50_now:.2f}"
                f"（傾き21:{ema21_slope:+.2f} / トレンド待ち）"
            )

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
        send_ntfy(topic, f"ALGOMAX XAUUSD 15m: {signal}", notify_msg, priority=notify_priority)


if __name__ == "__main__":
    analyze()
