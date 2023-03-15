from flask import Flask, jsonify, request
import single_stock_analysis

app = Flask(__name__)

@app.route("/stock-info")
def stock_info():
    ticker = request.args.get("ticker")
    data = single_stock_analysis.buy_or_sell(ticker)
    return jsonify(data)

if __name__ == "__main__":
    app.run(port=3000)