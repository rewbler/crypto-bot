import requests
import numpy as np
import pandas as pd
import time
import os
from datetime import datetime

from sklearn.linear_model import HuberRegressor
from sklearn.metrics import r2_score

# =========================================================
# CONFIG
# =========================================================

TOP_COINS = 30
DAYS = 90

TELEGRAM_TOKEN = "SEU_TOKEN"
CHAT_ID = "SEU_CHAT_ID"

HEADERS = {"User-Agent": "Mozilla/5.0"}

# =========================================================
# TELEGRAM
# =========================================================

def send_telegram(msg):

    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        data = {"chat_id": CHAT_ID, "text": msg}
        requests.post(url, data=data)
    except:
        pass

# =========================================================
# SAFE REQUEST
# =========================================================

def safe_get(url, params=None):

    try:
        r = requests.get(url, params=params, headers=HEADERS, timeout=20)
        if r.status_code == 200:
            return r.json()
    except:
        pass

    return None

# =========================================================
# COINS
# =========================================================

def get_coins():

    url = "https://api.coingecko.com/api/v3/coins/markets"

    params = {
        "vs_currency": "usd",
        "order": "volume_desc",
        "per_page": TOP_COINS,
        "page": 1,
        "sparkline": False
    }

    return safe_get(url, params) or []

# =========================================================
# PRICES
# =========================================================

def get_prices(coin_id):

    url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart"

    params = {
        "vs_currency": "usd",
        "days": DAYS,
        "interval": "daily"
    }

    data = safe_get(url, params)

    if not data or "prices" not in data:
        return None

    return [p[1] for p in data["prices"]]

# =========================================================
# COMPRA FORTE
# =========================================================

def analyze(symbol, prices):

    prices = np.array(prices)

    if len(prices) < 30:
        return None

    log_returns = np.diff(np.log(prices))

    vol = np.std(log_returns)
    if vol == 0:
        return None

    sharpe = np.mean(log_returns) / vol

    X = np.arange(len(prices)).reshape(-1, 1)
    y = np.log(prices)

    model = HuberRegressor()
    model.fit(X, y)

    r2 = r2_score(y, model.predict(X))

    slope = model.coef_[0]
    trend = (np.exp(slope) - 1) * 100

    if (
        trend > 0 and
        r2 >= 0.55 and
        sharpe > 0 and
        vol < 0.20
    ):
        score = (trend * sharpe * r2) / (vol * 50)

        return {
            "symbol": symbol.upper(),
            "trend": trend,
            "r2": r2,
            "vol": vol,
            "score": score
        }

    return None

# =========================================================
# HISTÓRICO
# =========================================================

def save_log(data):

    df = pd.DataFrame(data)

    file = "signals_history.csv"

    if os.path.exists(file):
        old = pd.read_csv(file)
        df = pd.concat([old, df], ignore_index=True)

    df.to_csv(file, index=False)

# =========================================================
# MAIN
# =========================================================

def main():

    print("🤖 BOT AUTÔNOMO INICIADO")

    coins = get_coins()

    signals = []

    for c in coins:

        try:

            prices = get_prices(c["id"])

            if not prices:
                continue

            result = analyze(c["symbol"], prices)

            if result:

                msg = (
                    f"🚨 COMPRA FORTE\n"
                    f"{result['symbol']}\n"
                    f"Trend: {result['trend']:.2f}%\n"
                    f"Score: {result['score']:.2f}"
                )

                print(msg)

                send_telegram(msg)

                signals.append(result)

            time.sleep(1)

        except:
            continue

    if signals:
        save_log(signals)

    print("✔ Execução finalizada")

# =========================================================

main()
