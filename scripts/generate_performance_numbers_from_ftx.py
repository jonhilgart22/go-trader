import os
import glob
import click
import logging
import ccxt
from collections import defaultdict

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
        print(file)
        coin = file.split("/")[1].split("_")[0]
        if coin not in list_of_coins and coin not in not_coins:
            list_of_coins.append(coin)

    unique_coins = list(set(list_of_coins))

    performance_per_coin = defaultdict(int)
    # run through coins and pull performance data

    for coin in unique_coins:
        logging.info(f"Coin = {coin}")
        ftx_key = os.getenv(coin.upper() + "_FTX_KEY")
        print(ftx_key, 'ftx_key')
        ftx_secret = os.getenv(coin.upper() + "_FTX_SECRET")
        print(ftx_secret, 'ftx_secret')
        logging.info(f"Subaccount name env var = {coin.upper() + '_SUBACCOUNT_NAME'}")
        subaccount_name = os.getenv(coin.upper() + "_SUBACCOUNT_NAME")

        logging.info(f"Subaccount name = {subaccount_name}")

        # make sure your version is 1.51+
        print('CCXT Version:', ccxt.__version__)

        exchange = ccxt.ftxus({
            'apiKey': ftx_key,
            'secret': ftx_secret,

            'FTXUS-SUBACCOUNT': subaccount_name

        })

        # markets = exchange.load_markets()

        exchange.verbose = True  # uncomment for debugging

        all_trades = {}
        symbol = coin + "/USD"
        since = None
        limit = 200
        end_time = exchange.milliseconds()

        while True:
            print('------------------------------------------------------------------')
            params = {
                'end_time': int(end_time / 1000),
                'FTXUS-SUBACCOUNT': subaccount_name,
            }
            trades = exchange.fetch_my_trades(symbol, since, limit, params)
            if len(trades):
                first_trade = trades[0]
                last_trade = trades[len(trades) - 1]
                end_time = first_trade['timestamp'] + 1000
                print('Fetched', len(trades), 'trades from', first_trade['datetime'], 'till', last_trade['datetime'])
                fetched_new_trades = False
                for trade in trades:
                    trade_id = trade['id']
                    if trade_id not in all_trades:
                        fetched_new_trades = True
                        all_trades[trade_id] = trade
                if not fetched_new_trades:
                    print('Done')
                    break
            else:
                print('Done')
                break

        all_trades = list(all_trades.values())
        total_bought = 0
        total_sold = 0

        print('Fetched', len(all_trades), 'trades')
        for i in range(0, len(all_trades)):
            trade = all_trades[i]
            print(i, trade['id'], trade['datetime'], trade['amount'], trade['price'], trade['side'])

            dollars_traded = trade['price'] * trade['amount']

            if trade['side'] == 'buy':
                total_bought += dollars_traded
            if trade['side'] == 'sell':
                total_sold += dollars_traded

        logging.info(f"Total won = { total_sold - total_bought }")
        performance_per_coin[coin] += total_sold - total_bought
    logging.info(f"performance_per_coin = {performance_per_coin}")


if __name__ == '__main__':
    main()
