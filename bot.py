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

# v6.1 パラメータ設定
ATR_LENGTH = 14
ATR_MULTIPLIER = 3.5
MIN_MOVE_PERCENT = 0.30
RSI_LENGTH = 14
SELL_RSI = 52.0
BUY_RSI = 48.0
MIN_BARS_BETWEEN = 12
SL_ATR = 1.5
TP_FALLBACK_ATR = 2.0
TP_EXTENSION_ATR = 1.5
REVERSAL_ATR = 3.5
MIN_BARS_AFTER_EXTREME = 5


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
        safe_title = title.encode("ascii", "ignore").decode("ascii").strip() or "ZERO SIGNAL"
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


def fetch_candles_15m():
    for symbol in ["XAUUSD=X", "GC=F"]:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=15m&range=5d"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        try:
            with urllib.request.urlopen(req, timeout=15) as res:
                raw = json.loads(res.read().decode("utf-8"))
                result = raw["chart"]["result"][0]
                quote = result["indicators"]["quote"][0]
                opens, highs, lows, closes = [], [], [], []
                for o, h, l, c in zip(quote["open"], quote["high"], quote["low"], quote["close"]):
                    if None not in (o, h, l, c):
                        opens.append(float(o))
                        highs.append(float(h))
                        lows.append(float(l))
                        closes.append(float(c))
                if len(closes) >= 80:
                    return opens, highs, lows, closes, symbol
        except Exception as e:
            print(f"Fetch failed for {symbol}:", e)
    raise RuntimeError("15分足データを取得できませんでした")


def ema_series(values, period):
    k = 2.0 / (period + 1)
    out = [None] * len(values)
    if len(values) < period:
        return out
    prev = sum(values[:period]) / period
    out[period - 1] = prev
    for i in range(period, len(values)):
        prev = values[i] * k + prev * (1 - k)
        out[i] = prev
    return out


def rsi_series(values, period=14):
    out = [None] * len(values)
    if len(values) <= period:
        return out
    gains, losses = [], []
    for i in range(1, period + 1):
        diff = values[i] - values[i - 1]
        gains.append(max(diff, 0.0))
        losses.append(max(-diff, 0.0))
    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period
    out[period] = 100.0 if avg_loss == 0 else 100.0 - (100.0 / (1.0 + avg_gain / avg_loss))
    for i in range(period + 1, len(values)):
        diff = values[i] - values[i - 1]
        gain = max(diff, 0.0)
        loss = max(-diff, 0.0)
        avg_gain = (avg_gain * (period - 1) + gain) / period
        avg_loss = (avg_loss * (period - 1) + loss) / period
        out[i] = 100.0 if avg_loss == 0 else 100.0 - (100.0 / (1.0 + avg_gain / avg_loss))
    return out


def atr_series(highs, lows, closes, period=14):
    out = [None] * len(closes)
    if len(closes) <= period:
        return out
    trs = [None] * len(closes)
    for i in range(1, len(closes)):
        trs[i] = max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i - 1]),
            abs(lows[i] - closes[i - 1]),
        )
    first_atr = sum(trs[1 : period + 1]) / period
    out[period] = first_atr
    prev = first_atr
    for i in range(period + 1, len(closes)):
        prev = (prev * (period - 1) + trs[i]) / period
        out[i] = prev
    return out


def run_zero_signal_simulation(opens, highs, lows, closes):
    n = len(closes)
    atr_arr = atr_series(highs, lows, closes, ATR_LENGTH)
    rsi_arr = rsi_series(closes, RSI_LENGTH)
    ema20_arr = ema_series(closes, 20)
    ema50_arr = ema_series(closes, 50)

    direction = 0
    extreme = None
    extreme_atr = None
    last_signal_bar = None
    last_signal = 0
    last_confidence = None

    tp1_price = None
    tp2_price = None
    sl_price = None
    active_trade = 0
    next_tp_trigger = None
    last_tp_update_bar = None

    reached_tp1 = False
    final_reversal_done = False
    favorable_extreme = None
    favorable_extreme_bar = None

    latest_event = "WAIT"
    latest_reason = "条件待機中"
    latest_notify = None

    for i in range(50, n):
        a = atr_arr[i]
        r = rsi_arr[i]
        r_prev = rsi_arr[i - 1]
        e20 = ema20_arr[i]
        e20_prev = ema20_arr[i - 1]
        e50 = ema50_arr[i]

        if None in (a, r, r_prev, e20, e20_prev, e50) or a <= 0:
            continue

        if direction == 0:
            direction = 1 if closes[i] >= e50 else -1
            extreme = highs[i] if direction == 1 else lows[i]
            extreme_atr = a

        spacing_ok = last_signal_bar is None or (i - last_signal_bar >= MIN_BARS_BETWEEN)

        buy_signal = False
        sell_signal = False
        tp_updated = False
        final_reversal_signal = False

        if direction == 1:
            if highs[i] > extreme:
                extreme = highs[i]
                extreme_atr = a
            drop_dist = extreme - closes[i]
            req_dist = max(extreme_atr * ATR_MULTIPLIER, extreme * MIN_MOVE_PERCENT / 100.0)
            if (
                drop_dist >= req_dist
                and r < SELL_RSI
                and r < r_prev
                and closes[i] < opens[i]
                and spacing_ok
            ):
                sell_signal = True
                dist_score = min((drop_dist / req_dist - 1.0) * 20.0, 20.0)
                rsi_score = min(abs(r - SELL_RSI) * 1.5, 15.0)
                candle_score = min((opens[i] - closes[i]) / a * 30.0, 15.0)
                last_confidence = round(max(0.0, min(100.0, 50.0 + dist_score + rsi_score + candle_score)), 1)
                direction = -1
                extreme = lows[i]
                extreme_atr = a
                last_signal = -1
                last_signal_bar = i

        elif direction == -1:
            if lows[i] < extreme:
                extreme = lows[i]
                extreme_atr = a
            rise_dist = closes[i] - extreme
            req_dist = max(extreme_atr * ATR_MULTIPLIER, extreme * MIN_MOVE_PERCENT / 100.0)
            if (
                rise_dist >= req_dist
                and r > BUY_RSI
                and r > r_prev
                and closes[i] > opens[i]
                and spacing_ok
            ):
                buy_signal = True
                dist_score = min((rise_dist / req_dist - 1.0) * 20.0, 20.0)
                rsi_score = min(abs(r - BUY_RSI) * 1.5, 15.0)
                candle_score = min((closes[i] - opens[i]) / a * 30.0, 15.0)
                last_confidence = round(max(0.0, min(100.0, 50.0 + dist_score + rsi_score + candle_score)), 1)
                direction = 1
                extreme = highs[i]
                extreme_atr = a
                last_signal = 1
                last_signal_bar = i

        if buy_signal:
            tp2_price = round(closes[i] + a * TP_FALLBACK_ATR, 2)
            tp1_price = round(closes[i] + (tp2_price - closes[i]) * 0.5, 2)
            sl_price = round(closes[i] - a * SL_ATR, 2)
            active_trade = 1
            next_tp_trigger = tp1_price
            last_tp_update_bar = None
            reached_tp1 = False
            final_reversal_done = False
            favorable_extreme = highs[i]
            favorable_extreme_bar = i

        elif sell_signal:
            tp2_price = round(closes[i] - a * TP_FALLBACK_ATR, 2)
            tp1_price = round(closes[i] - (closes[i] - tp2_price) * 0.5, 2)
            sl_price = round(closes[i] + a * SL_ATR, 2)
            active_trade = -1
            next_tp_trigger = tp1_price
            last_tp_update_bar = None
            reached_tp1 = False
            final_reversal_done = False
            favorable_extreme = lows[i]
            favorable_extreme_bar = i

        if active_trade == 1 and not reached_tp1 and tp1_price is not None and highs[i] >= tp1_price:
            reached_tp1 = True
        elif active_trade == -1 and not reached_tp1 and tp1_price is not None and lows[i] <= tp1_price:
            reached_tp1 = True

        if active_trade == 1 and reached_tp1:
            if favorable_extreme is None or highs[i] > favorable_extreme:
                favorable_extreme = highs[i]
                favorable_extreme_bar = i
        elif active_trade == -1 and reached_tp1:
            if favorable_extreme is None or lows[i] < favorable_extreme:
                favorable_extreme = lows[i]
                favorable_extreme_bar = i

        can_update_tp = (
            active_trade != 0
            and tp1_price is not None
            and tp2_price is not None
            and next_tp_trigger is not None
            and last_tp_update_bar != i
        )
        buy_momentum = closes[i] > e20 and e20 > e20_prev and r > 50 and r > r_prev and closes[i] > opens[i]
        sell_momentum = closes[i] < e20 and e20 < e20_prev and r < 50 and r < r_prev and closes[i] < opens[i]

        if can_update_tp and active_trade == 1 and highs[i] >= next_tp_trigger and buy_momentum:
            old_tp2 = tp2_price
            tp1_price = round(old_tp2, 2)
            tp2_price = round(max(old_tp2 + a * TP_EXTENSION_ATR, highs[i] + a * TP_EXTENSION_ATR), 2)
            next_tp_trigger = tp1_price
            last_tp_update_bar = i
            tp_updated = True

        elif can_update_tp and active_trade == -1 and lows[i] <= next_tp_trigger and sell_momentum:
            old_tp2 = tp2_price
            tp1_price = round(old_tp2, 2)
            tp2_price = round(min(old_tp2 - a * TP_EXTENSION_ATR, lows[i] - a * TP_EXTENSION_ATR), 2)
            next_tp_trigger = tp1_price
            last_tp_update_bar = i
            tp_updated = True

        bars_from_extreme = (i - favorable_extreme_bar) if favorable_extreme_bar is not None else 0
        buy_final_rev = (
            active_trade == 1
            and reached_tp1
            and not final_reversal_done
            and favorable_extreme is not None
            and bars_from_extreme >= MIN_BARS_AFTER_EXTREME
            and (favorable_extreme - closes[i]) >= a * REVERSAL_ATR
            and r < r_prev
            and r < 50
            and closes[i] < opens[i]
            and closes[i] < lows[i - 1]
            and closes[i] < e20
            and e20 < e20_prev
        )
        sell_final_rev = (
            active_trade == -1
            and reached_tp1
            and not final_reversal_done
            and favorable_extreme is not None
            and bars_from_extreme >= MIN_BARS_AFTER_EXTREME
            and (closes[i] - favorable_extreme) >= a * REVERSAL_ATR
            and r > r_prev
            and r > 50
            and closes[i] > opens[i]
            and closes[i] > highs[i - 1]
            and closes[i] > e20
            and e20 > e20_prev
        )
        final_reversal_signal = buy_final_rev or sell_final_rev
        if final_reversal_signal:
            final_reversal_done = True
            active_trade = 0

        if i == n - 1:
            conf_str = f"{last_confidence}%" if last_confidence is not None else "未判定"
            if buy_signal:
                latest_event = "BUY"
                latest_reason = f"[v6.1 15m] BUY反転検知（信頼度 {conf_str} / TP1:{tp1_price} / TP2:{tp2_price} / SL:{sl_price}）"
                latest_notify = f"【ZERO SIGNAL BUY】15m上昇反転！現在値:{round(closes[i],2)} / TP1:{tp1_price} / TP2:{tp2_price} / SL:{sl_price}（信頼度:{conf_str}）"
            elif sell_signal:
                latest_event = "SELL"
                latest_reason = f"[v6.1 15m] SELL反転検知（信頼度 {conf_str} / TP1:{tp1_price} / TP2:{tp2_price} / SL:{sl_price}）"
                latest_notify = f"【ZERO SIGNAL SELL】15m下降反転！現在値:{round(closes[i],2)} / TP1:{tp1_price} / TP2:{tp2_price} / SL:{sl_price}（信頼度:{conf_str}）"
            elif final_reversal_signal:
                latest_event = "TP_EXIT"
                latest_reason = f"[v6.1 15m] 最終利確候補を検知（極値 {round(favorable_extreme,2)} から反転 / 現在値 {round(closes[i],2)}）"
                latest_notify = f"【ZERO SIGNAL 最終利確候補】大きな反転を検出！利確を検討してください。現在値:{round(closes[i],2)} / 極値:{round(favorable_extreme,2)}"
            elif tp_updated:
                latest_event = "TP_UPDATE"
                latest_reason = f"[v6.1 15m] TP自動追従更新（新TP1:{tp1_price} / 新TP2:{tp2_price}）"
                latest_notify = f"【ZERO SIGNAL TP更新】トレンド継続でTPを更新！新TP1:{tp1_price} / 新TP2:{tp2_price}（現在値:{round(closes[i],2)}）"
            else:
                latest_event = "WAIT"
                state_txt = "最終利確候補" if final_reversal_done else ("利益追跡中" if reached_tp1 else ("監視中" if active_trade != 0 else "待機中"))
                latest_reason = f"[v6.1 15m] {state_txt} / RSI:{round(r,1)} / EMA20:{round(e20,2)} / 信頼度:{conf_str}"

    return {
        "price": round(closes[-1], 2),
        "event": latest_event,
        "entry_price": round(closes[-1], 2) if latest_event in ("BUY", "SELL") else 0,
        "tp_price": tp2_price if tp2_price is not None else 0,
        "sl_price": sl_price if sl_price is not None else 0,
        "reason": latest_reason,
        "notify_msg": latest_notify,
    }


def analyze():
    row = get_status()
    if not row:
        print("No row found")
        return
    if not row.get("is_active"):
        print("Bot is stopped (is_active=false). Skipping.")
        return

    opens, highs, lows, closes, sym = fetch_candles_15m()
    res = run_zero_signal_simulation(opens, highs, lows, closes)
    topic = (row.get("ntfy_topic") or "").strip()
    now_iso = datetime.now(timezone.utc).isoformat()
    log_text = f"[{sym}] 現在値 {res['price']} | 判定: {res['event']} | {res['reason']}"

    update_status(
        {
            "current_price": res["price"],
            "signal": res["event"],
            "entry_price": res["entry_price"],
            "tp_price": res["tp_price"],
            "sl_price": res["sl_price"],
            "signal_reason": res["reason"],
            "last_log": log_text,
            "updated_at": now_iso,
        }
    )
    print("Updated:", log_text)

    if res["notify_msg"]:
        send_ntfy(topic, f"ZERO SIGNAL: {res['event']}", res["notify_msg"], priority="urgent")


if __name__ == "__main__":
    analyze()
