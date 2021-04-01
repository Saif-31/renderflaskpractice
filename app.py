from flask import Flask
import yfinance as yf
from flask import Response, request, jsonify
from markupsafe import escape
from datetime import date, datetime, timedelta
from utils import (
    bb,
    get_ibov_tickers,
    position_relative_to_bands,
    rsi,
    strategy_points,
    strategy_test,
    backtest_algorithm,
    stochastic
)

app = Flask(__name__)


@app.route("/")
def hello_world():
    return "Hello, World!"


@app.route("/price/<ticker>")
def me_api(ticker):
    yf_ticker = escape(ticker) + ".SA"
    start = request.args.get("start")
    end = request.args.get("end")
    df = yf.download(yf_ticker, start=start, end=end).copy()[["Open", "High", "Close"]]
    return Response(df.to_json(orient="table"), mimetype="application/json")


@app.route("/ifr2/<ticker>")
def ifr2(ticker):
    yf_ticker = escape(ticker) + ".SA"
    start = (datetime.today() - timedelta(days=50)).strftime("%Y-%m-%d")
    end = (date.today() + timedelta(days=1)).strftime("%Y-%m-%d")
    df = yf.download(yf_ticker, start=start, end=end).copy()[
        ["Open", "High", "Adj Close"]
    ]
    ifr2_df = rsi(df, "Adj Close", 2)
    return {"ifr2": int(round(ifr2_df[-1]))}


@app.route("/backtest/ifr2/<ticker>")
def backtest_ifr2(ticker):
    yf_ticker = escape(ticker) + ".SA"
    start = (datetime.today() - timedelta(days=500)).strftime("%Y-%m-%d")
    end = (date.today() + timedelta(days=1)).strftime("%Y-%m-%d")
    df = yf.download(yf_ticker, start=start, end=end).copy()[
        ["Open", "High", "Close", "Adj Close"]
    ]
    df["IFR2"] = rsi(df, column="Adj Close")
    entry = (
        None if request.args.get("entry") is None else int(request.args.get("entry"))
    )
    df = strategy_points(data=df, rsi_parameter=entry)
    all_profits, total_capital = backtest_algorithm(df)
    statistics = strategy_test(all_profits, total_capital)

    return jsonify(statistics)


@app.route("/ifr2")
def api():
    tickers = get_ibov_tickers()

    start = (datetime.today() - timedelta(days=100)).strftime("%Y-%m-%d")
    end = (date.today() + timedelta(days=1)).strftime("%Y-%m-%d")
    df = yf.download(tickers, start=start, end=end).copy()[
        ["Open", "High", "Adj Close"]
    ]

    # print(start)

    df.columns = [" ".join(col).strip() for col in df.columns.values]

    all_rsi = {}
    for ticker in tickers:
        new_df = df[["Open " + ticker, "High " + ticker, "Adj Close " + ticker]].rename(
            columns={
                "Open " + ticker: "Open",
                "High " + ticker: "High",
                "Adj Close " + ticker: "Adj Close",
            }
        )
        new_df.dropna(inplace=True)

        rsi_value = int(round(rsi(new_df, "Adj Close", 2)[-1]))
        max_today = new_df["High"][-1]
        max_1_day_ago = new_df["High"][-2]

        # Target is the max value of today and yesterday. This is because the operation
        # starts at the end of the current day, and all possible sells are in the next day
        # Therefore, tomorrow the last two days will be today and yesterday
        target = max(max_today, max_1_day_ago)
        price = new_df["Adj Close"][-1]
        upside = ((target - price) / price) * 100

        # Variation of the last 100 days
        initial_price = new_df["Adj Close"][0]
        variation = ((price - initial_price) / initial_price) * 100

        # Figure out if MM50 is up
        mm50 = new_df["Adj Close"].rolling(50).mean()
        mm50_today = mm50[-1]
        mm50_prev = mm50[-2]
        mm50_is_up = 1 if mm50_today > mm50_prev else 0

        all_rsi[ticker.replace(".SA", "")] = {
            "rsi": rsi_value,
            "target": target.round(2),
            "price": price.round(2),
            "upside": upside.round(2),
            "mm50_is_up": mm50_is_up,
            "variation": variation.round(2),
        }

    return jsonify(all_rsi)


@app.route("/bb/<ticker>")
def bollinger_bands(ticker):
    yf_ticker = escape(ticker) + ".SA"
    start = (datetime.today() - timedelta(days=50)).strftime("%Y-%m-%d")
    end = (date.today() + timedelta(days=1)).strftime("%Y-%m-%d")
    df = yf.download(yf_ticker, start=start, end=end).copy()[["Adj Close"]]

    k = 2 if request.args.get("k") is None else float(request.args.get("k"))
    n = 20 if request.args.get("n") is None else int(request.args.get("n"))

    bb_df = bb(df, k, n)
    return jsonify(
        {
            "middle_band": bb_df["Middle Band"][-1].round(2),
            "upper_band": bb_df["Upper Band"][-1].round(2),
            "lower_band": bb_df["Lower Band"][-1].round(2),
            "current_price": bb_df["Adj Close"][-1].round(2),
            "text": position_relative_to_bands(ticker, bb_df["Adj Close"], k, n),
        }
    )

@app.route("/stochastic/<ticker>")
def stochastic_calculation(ticker):
    yf_ticker = escape(ticker) + ".SA"
    start = (datetime.today() - timedelta(days=50)).strftime("%Y-%m-%d")
    end = (date.today() + timedelta(days=1)).strftime("%Y-%m-%d")
    df = yf.download(yf_ticker, start=start, end=end).copy()[
        ["High", "Low", "Adj Close"]
    ]
    df = stochastic(df)
    return {
        "fast_k": int(round(df["%K"][-1])), 
        "fast_d": int(round(df["%D"][-1])),
        "k": int(round(df["Slow %K"][-1])),
        "d": int(round(df["Slow %D"][-1]))
        }
    
@app.route("/stochastic")
def all_stochastic():

    tickers = get_ibov_tickers()

    start = (datetime.today() - timedelta(days=120)).strftime("%Y-%m-%d")
    end = (date.today() + timedelta(days=1)).strftime("%Y-%m-%d")
    df = yf.download(tickers, start=start, end=end).copy()[
        ["High", "Low", "Adj Close"]
    ]

    df.columns = [" ".join(col).strip() for col in df.columns.values]

    all_stochastic = {}
    for ticker in tickers:
        new_df = df[["High " + ticker, "Low " + ticker, "Adj Close " + ticker]].rename(
            columns={
                "High " + ticker: "High",
                "Low " + ticker: "Low",
                "Adj Close " + ticker: "Adj Close",
            }
        )
        
        new_df.dropna(inplace=True)
        
        new_df = stochastic(new_df)

        # current price 
        price = new_df["Adj Close"][-1]
        
        # Variation of the last 120 days
        initial_price = new_df["Adj Close"][0]
        variation = ((price - initial_price) / initial_price) * 100
    
        # Figure out if slow K is up
        k_today = new_df["Slow %K"][-1]
        k_prev = new_df["Slow %K"][-2]
        k_is_up = 1 if k_today > k_prev else 0
        
        # Figure out if slow K crossed above or under D
        d_today = new_df["Slow %D"][-1]
        d_prev = new_df["Slow %D"][-2]
        k_crossed_above = 1 if (k_prev < d_prev) & (k_today > d_today) else 0
        k_crossed_below = 1 if (k_prev > d_prev) & (k_today < d_today) else 0
        
        
        # Figure out if MME80 is up
        mme80 = new_df["Adj Close"].ewm(span=80).mean()
        mme80_today = mme80[-1]
        mme80_prev = mme80[-2]
        mme80_is_up = 1 if mme80_today > mme80_prev else 0
         
        all_stochastic[ticker.replace(".SA", "")] = {
            "k": int(round(k_today)),
            "d": int(round(d_today)),
            "price": price.round(2),
            "variation": variation.round(2),
            "k_is_up": k_is_up,
            "k_crossed_above": k_crossed_above,
            "k_crossed_below": k_crossed_below,
            "mme80_is_up": mme80_is_up
        }
    return jsonify(all_stochastic)
