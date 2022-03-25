import glob
import logging
import os
from collections import defaultdict

import ccxt
import click

logging.basicConfig(format="%(asctime)s %(message)s", datefmt="%m/%d/%Y %I:%M:%S %p", level=logging.INFO)


# first, iterate through tmp and pull out the unique coins


@click.command()
@click.option("--directory", default="tmp", help="The directory where the won_and_lost configs are")
@click.option("--file_name_glob", default="won_and_lost_config", help="the name in the files to parse")
def main(directory: str, file_name_glob: str):

    response = input("Have you exported the env vars from .env_vars.sh ? (y/n)")

    if response.lower() != "y":
        return "Export env vars! copy and paste them"

    not_coins = ["ml", "historic", "logs.txt", "README.md", "actions", "constants.yml"]

    list_of_coins = []

    for file in glob.glob(f"{directory}/*"):
        logging.info(file)
        coin = file.split("/")[1].split("_")[0]
        if coin not in list_of_coins and coin not in not_coins:
            list_of_coins.append(coin)

    unique_coins = list(set(list_of_coins))

    performance_per_coin = defaultdict(int)
    # run through coins and pull performance data

    for coin in unique_coins:
        logging.info(f"Coin = {coin}")
        ftx_key = os.getenv(coin.upper() + "_FTX_KEY")
        ftx_secret = os.getenv(coin.upper() + "_FTX_SECRET")
        logging.info(f"Subaccount name env var = {coin.upper() + '_SUBACCOUNT_NAME'}")
        subaccount_name = os.getenv(coin.upper() + "_SUBACCOUNT_NAME")

        logging.info(f"Subaccount name = {subaccount_name}")

        # make sure your version is 1.51+
        logging.info(f"CCXT Version: {ccxt.__version__}")

        exchange = ccxt.ftxus({"apiKey": ftx_key, "secret": ftx_secret, "FTXUS-SUBACCOUNT": subaccount_name})

        # markets = exchange.load_markets()

        # exchange.verbose = True  # uncomment for debugging

        all_trades = {}
        symbol = coin + "/USD"
        since = None
        limit = 200
        end_time = exchange.milliseconds()

        while True:
            logging.info("------------------------------------------------------------------")
            params = {"end_time": int(end_time / 1000), "FTXUS-SUBACCOUNT": subaccount_name}
            trades = exchange.fetch_my_trades(symbol, since, limit, params)
            if len(trades):
                first_trade = trades[0]
                end_time = first_trade["timestamp"] + 1000

                fetched_new_trades = False
                for trade in trades:
                    trade_id = trade["id"]
                    if trade_id not in all_trades:
                        fetched_new_trades = True
                        all_trades[trade_id] = trade
                if not fetched_new_trades:
                    logging.info("Done")
                    break
            else:
                logging.info("Done")
                break

        all_trades = list(all_trades.values())
        total_bought = 0
        total_won = 0
        total_sold = 0
        total_lost = 0
        current_buy_price = None

        logging.info(f"Fetched {len(all_trades)} trades")
        for i in range(0, len(all_trades)):
            trade = all_trades[i]

            dollars_traded = trade["price"] * trade["amount"]

            if trade["side"] == "buy":
                total_bought += dollars_traded
                current_buy_price = trade["price"]
            if trade["side"] == "sell":
                total_sold += dollars_traded
                if current_buy_price is None:
                    continue
                elif current_buy_price < trade["price"]:  # buy low sell high
                    total_won += 1
                else:
                    total_lost += 1

                current_buy_price = None

        logging.info(f"Total won = { total_sold - total_bought }")
        # profit for long trades, total money at risk, # of trades, winning trades
        performance_per_coin[coin] = (total_sold - total_bought, total_bought, total_won + total_lost, total_won)
    logging.info(f"performance_per_coin = {performance_per_coin}")
    # aggregate metrics

    total_dollars_won_or_lost = 0
    total_dollars_at_risk = 0
    total_trades_won = 0
    total_trades = 0
    for key, value in performance_per_coin.items():
        total_dollars_won_or_lost += value[0]
        total_dollars_at_risk += value[1]
        total_trades_won += value[3]
        total_trades += value[2]

    logging.info(f"total_dollars_won_or_lost = ${total_dollars_won_or_lost}")
    logging.info(f"total_dollars_at_risk = ${total_dollars_at_risk}")
    logging.info(f"total_trades = {total_trades}")
    logging.info(f"total_trades_won = {total_trades_won}")
    logging.info(f"Bat rate = {total_trades_won/total_trades * 100:.2f}%")
    logging.info(f"Percent Return = {(total_dollars_won_or_lost/total_dollars_at_risk)*100:.2f}%")
    logging.info(f"Amount won or lost per trade = ${total_dollars_won_or_lost/total_trades:.2f}")


if __name__ == "__main__":
    main()
