# flake8: noqa
import glob
import logging
import os
from collections import defaultdict
from typing import Any, Dict

import ccxt
import click

logging.basicConfig(format="%(asctime)s %(message)s", datefmt="%m/%d/%Y %I:%M:%S %p", level=logging.INFO)


# first, iterate through tmp and pull out the unique coins


@click.command()
@click.option("--directory", default="tmp", help="The directory where the won_and_lost configs are")
@click.option("--file_name_glob", default="won_and_lost_config", help="the name in the files to parse")
def main(directory: str, file_name_glob: str) -> None:

    response = input("Have you exported the env vars from .env_vars.sh ? (y/n)")

    if response.lower() != "y":
        print("Export env vars! copy and paste them")

    not_coins = ["ml", "historic", "logs.txt", "README.md", "actions", "constants.yml", "example"]

    list_of_coins = []

    for file in glob.glob(f"{directory}/*"):
        logging.info(f"file = {file}")
        coin = file.split("/")[1].split("_")[0]
        if coin not in list_of_coins and coin not in not_coins:
            list_of_coins.append(coin)

    unique_coins = list(set(list_of_coins))

    performance_per_coin: Dict[str, Any] = defaultdict(int)
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
            logging.info(f" Coin = {symbol}")
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

        all_trades_list = list(all_trades.values())
        total_bought = 0
        n_buy = 0
        total_sold = 0
        n_sell = 0
        total_fees = 0.0

        logging.info(f"Fetched {len(all_trades_list)} trades")
        for i in range(0, len(all_trades_list)):
            trade = all_trades_list[i]
            logging.info(f"{i} of {len(all_trades_list)-1}")
            if (i == len(all_trades_list) - 1) and (
                trade["side"] == "buy"
            ):  # last trade, if BUY, exclude.. we are in an active position
                logging.info(f"Last trade, excluding")
                logging.info(f"{trade['datetime'], trade['side'], trade['price'], trade['amount'],  trade['cost']}")
                continue
            total_fees += float(trade["fee"]["cost"])

            logging.info(f"{trade['datetime'], trade['side'], trade['price'], trade['amount'],  trade['cost']}")

            dollars_traded = trade["cost"]

            if trade["side"] == "buy":
                total_bought += dollars_traded
                n_buy += 1
            if trade["side"] == "sell":
                total_sold += dollars_traded
                n_sell += 1

        total_won_or_lost = total_sold - total_bought
        total_won_or_lost_minus_fees = total_won_or_lost - total_fees
        logging.info("total bought = " + str(total_bought))
        logging.info("total sold = " + str(total_sold))
        logging.info(f"Total won = {total_won_or_lost }")
        logging.info(f"Total fees = {total_fees}")
        logging.info(f"Total won minus fees = {total_won_or_lost_minus_fees}")
        # profit for long trades, total money at risk, # of trades, winning trades
        performance_per_coin[coin] = (
            total_won_or_lost,
            total_bought,
            n_buy + n_sell,
            n_buy,
            total_won_or_lost_minus_fees,
        )
    logging.info(f"performance_per_coin = {performance_per_coin}")
    # aggregate metrics

    total_dollars_won_or_lost = 0
    total_dollars_at_risk = 0
    n_trades_buy = 0
    total_trades = 0
    total_won_or_lost_minus_fees = 0
    total_fees = 0
    for key, value in performance_per_coin.items():
        total_dollars_won_or_lost += value[0]
        total_dollars_at_risk += value[1]
        n_trades_buy += value[3]
        total_trades += value[2]
        total_won_or_lost_minus_fees += value[4]
        total_fees += value[0] - value[4]

    logging.info(f"total_dollars_won_or_lost = ${total_dollars_won_or_lost:.2f}")
    logging.info(f"total_fees = ${total_fees:.2f}")
    logging.info(f"total_won_or_lost_minus_fees = ${total_won_or_lost_minus_fees:.2f}")
    logging.info(f"total_dollars_at_risk = ${total_dollars_at_risk:.2f}")
    logging.info(f"total_trades = {total_trades}")
    logging.info(f"n_trades_buy = {n_trades_buy}")
    logging.info(f"Bat rate = {n_trades_buy/total_trades * 100:.2f}%")
    logging.info(f"Percent return minus feeds = {(total_won_or_lost_minus_fees/total_dollars_at_risk)*100:.2f}%")
    logging.info(f"Amount won or lost per trade minus fees = ${total_won_or_lost_minus_fees/total_trades:.2f}")


if __name__ == "__main__":
    main()
