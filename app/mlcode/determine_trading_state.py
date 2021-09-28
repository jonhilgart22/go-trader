from predict_price_movements import BollingerBandsPredictor
import pandas as pd
from utils import read_in_constants, read_in_data, update_yaml_config
from typing import Dict
import time
import logging
import yaml
from datetime import date
from datetime import timedelta
import numpy as np

logger = logging.getLogger(__name__)


class DetermineTradingState:
    def __init__(
        self,
        price_prediction: float,
        trading_state_constants: Dict[str, str],
        prediction_df: pd.DataFrame,
    ):
        """Determine the current state we should be in for trading. Buy Short, entering, or exiting positions.

        Args:
            price_prediction ([type]): price prediction for the future price of the given coin
            trading_state_constants (Dict[str, str]): the current state we are in for trading (buy short no_position)
            prediction_df (pd.DataFrame):  the DF with Bolligner bands to predict against
        """
        self.price_prediction = price_prediction
        self.trading_state_constants = trading_state_constants
        self.prediction_df = prediction_df

        # trading state args
        for k, v in trading_state_constants.items():
            setattr(self, k, v)
            logger.info(f"Setting the class var self.{k} = {v}")

        # self.mode = self.trading_state_constants["mode"]
        # self.position_entry_date = self.trading_state_constants["position_entry_date"]
        # self.buy_entry_price = self.trading_state_constants["buy_entry_price"]
        # self.short_entry_price = self.trading_state_constants["short_entry_price"]
        # self.stop_loss_price = self.trading_state_constants["stop_loss_price"]
        # self.buy_has_crossed_mean = self.trading_state_constants["buy_has_crossed_mean"]
        # self.short_has_crossed_mean = self.trading_state_constants["short_has_crossed_mean"]

    def calculate_positions(self):
        # self.prediction_df["Position"] = None
        # self.prediction_df["Mode"] = None
        # self.prediction_df["ML_Future_Prediction"] = None
        # grab the last row, and verify the date is equal to yesterday's date
        row = self.prediction_df.iloc[-1:]
        logger.info(row)
        logger.info("row")
        prev_row = self.prediction_df.iloc[-2:-1]
        logger.info(prev_row)
        logger.info("prev_row")
        # assert date is yesterday date

        yesterday = pd.to_datetime(date.today() - timedelta(days=1))
        two_days_ago = pd.to_datetime(date.today() - timedelta(days=2))
        try:
            assert row.index == yesterday
            assert prev_row.index == two_days_ago
        except ValueError:
            raise (
                f"Incorrect dates passed. Yesterday = {yesterday} Two days ago = {two_days_ago}"
            )

        # update stop loss
        if (
            self.mode == "buy"
            and (1 - self.stop_loss_pct) * row["close"][0] > self.stop_loss_price
        ):
            self.stop_loss_price = (1 - self.stop_loss_pct) * row["close"]
            self._print_log_statements(
                f"Updating stop loss to {self.stop_loss_price}", row
            )

        if (
            self.mode == "short"
            and (1 + self.stop_loss_pct) * row["close"][0] < self.stop_loss_price
        ):
            self.stop_loss_price = (1 + self.stop_loss_pct) * row["close"][0]
            self._print_log_statements(
                f"Updating stop loss to {self.stop_loss_price}", row
            )

        # check if we've previously crossed the mean trailing price
        if self.mode == "buy" and row["close"] > row["Rolling Mean"]:
            self.buy_has_crossed_mean = True

        if self.mode == "short" and row["close"] < row["Rolling Mean"]:
            self.short_has_crossed_mean = True

        # stop loss, get out of buy position
        if self.mode == "buy" and self.stop_loss_price > row["close"]:
            self._print_log_statements(
                f"stop loss activated for getting out of our buy", row
            )

            self._determine_win_or_loss_amount(row)
            # record keeping

            self.mode = "no_position"
            self.buy_has_crossed_mean = False

        # stop loss, get out of short position
        elif self.mode == "short" and self.stop_loss_price < row["close"]:
            self._print_log_statements(
                f"stop loss activated for getting out of our short", row
            )

            self._determine_win_or_loss_amount(row)
            # record keeping
            self.mode = "no_position"
            self.short_has_crossed_mean = False

        # buy -> no_position? no position is below running mean
        # or, if we are above the top band (mean reversion)
        elif self.mode == "buy" and (
            (
                row["close"][0] < row["Rolling Mean"][0]
                and self.trading_state_constants["buy_has_crossed_mean"][0]
            )
            or (row["close"][0] > row["Bollinger High"][0])
            or (row["close"][0] < row["Bollinger Low"][0])
            or (row["Rolling Mean"][0] < self.buy_entry_price)
        ):
            self._check_buy_to_no_position(row)

        # short -> no_position? no position if above running mean
        # or, if we are below the bottom band (mean reversion)
        elif self.mode == "short" and (
            (
                row["close"] > row["Rolling Mean"]
                and self.trading_state_constants["short_has_crossed_mean"]
            )
            or (row["close"] < row["Bollinger Low"])
            or (row["close"] > row["Bollinger High"])
            or row["Rolling Mean"] > self.short_entry_price
        ):
            self._check_short_to_no_position(row)

        # buy check with ML model
        elif (
            self.mode == "no_position"
            and row["close"][0] < row["Bollinger Low"][0]
            and prev_row["close"][0] > prev_row["Bollinger Low"][0]
        ):
            self._check_if_we_should_buy(row)

        # short?
        elif (
            self.mode == "no_position"
            and row["close"][0] > row["Bollinger High"][0]
            and prev_row["close"][0] < prev_row["Bollinger High"][0]
        ):
            self._check_if_we_should_short(row)

        else:
            self._print_log_statements("Taking no action today", row)

    def _determine_win_or_loss_amount(self, row):
        """
        For position we've exited, did we win? if so, by how much
        """
        # short s

        # stop loss for short
        if self.mode == "short" and self.short_entry_price < row["close"]:
            lost_amount = row["close"] - self.short_entry_price
            logger.info(f"Lost {lost_amount} on this trade")

            self.win_and_lose_amount_dict["n_short_lost"] += 1
            self.win_and_lose_amount_dict["$_short_lost"] += lost_amount

        # made money
        elif self.mode == "short" and self.short_entry_price > row["close"]:

            win_amount = self.short_entry_price - row["close"]
            logger.info(f"Won {win_amount} on this trade")
            self.win_and_lose_amount_dict["n_short_won"] += 1
            self.win_and_lose_amount_dict["$_short_won"] += win_amount
        # end short
        # buys

        # lost money
        elif self.mode == "buy" and self.buy_entry_price > row["close"]:

            lost_amount = self.buy_entry_price - row["close"]
            logger.info(f"Lost {lost_amount} on this trade")
            self.win_and_lose_amount_dict["n_buy_lost"] += 1
            self.win_and_lose_amount_dict["$_buy_lost"] += lost_amount

        # made money
        elif self.mode == "buy" and self.buy_entry_price < row["close"]:

            won_amount = row["close"] - self.buy_entry_price
            logger.info(f"Won {won_amount} on this trade")
            self.win_and_lose_amount_dict["n_buy_won"] += 1
            self.win_and_lose_amount_dict["$_buy_won"] += won_amount

        days_in_trade = row.name - self.position_entry_date
        logger.info(days_in_trade.days, "days in trade")
        self.n_total_days_in_trades += days_in_trade.days

        # info logging

        logger.info(
            f"Average days in trades = {self.n_total_days_in_trades/(self.win_and_lose_amount_dict['n_buy_won']  + self.win_and_lose_amount_dict['n_buy_lost'] + self.win_and_lose_amount_dict['n_short_won']  + self.win_and_lose_amount_dict['n_short_lost'] )}"
        )
        if (
            self.win_and_lose_amount_dict["n_buy_won"] > 0
            or self.win_and_lose_amount_dict["n_buy_lost"] > 0
        ):
            logger.info(
                f"Bat rate buy so far = {self.win_and_lose_amount_dict['n_buy_won'] / (self.win_and_lose_amount_dict['n_buy_won'] + self.win_and_lose_amount_dict['n_buy_lost'])}"
            )
        if (
            self.win_and_lose_amount_dict["n_short_won"] > 0
            or self.win_and_lose_amount_dict["n_short_lost"] > 0
        ):
            logger.info(
                f"Bat rate short so far = {self.win_and_lose_amount_dict['n_short_won'] / (self.win_and_lose_amount_dict['n_short_won'] + self.win_and_lose_amount_dict['n_short_lost'])}"
            )

        if (
            self.win_and_lose_amount_dict["$_buy_won"] > 0
            or self.win_and_lose_amount_dict["$_buy_lost"] > 0
        ):
            logger.info(
                f"Win rate buy so far = {self.win_and_lose_amount_dict['$_buy_won'] / (self.win_and_lose_amount_dict['$_buy_won'] + self.win_and_lose_amount_dict['$_buy_lost'])}"
            )
        if (
            self.win_and_lose_amount_dict["$_short_won"] > 0
            or self.win_and_lose_amount_dict["$_short_lost"] > 0
        ):
            logger.info(
                f"Win rate short so far = {self.win_and_lose_amount_dict['$_short_won'] / (self.win_and_lose_amount_dict['$_short_won'] + self.win_and_lose_amount_dict['$_short_lost'])}"
            )
        logger.info(f"WIn / lost dict {self.win_and_lose_amount_dict}")

        logger.info(f"Total days in trades = {self.n_total_days_in_trades }")

        # reset for sanity
        self.position_entry_date = None

    def _check_short_to_no_position(self, index, row):
        """
        While in a short position, check if we should exit
        """
        self._print_log_statements(
            "checking if we should get out of our short position", row
        )

        # check ML predicted trend as well

        if (
            (self.price_prediction > row["Rolling Mean"][0])
            or (self.price_prediction > self.short_entry_price)
            or (row["Rolling Mean"][0] > self.short_entry_price)
        ):
            logger.info("short_to_no_position")

            self._determine_win_or_loss_amount(row)

            self.mode = "no_position"
            self.short_has_crossed_mean = False
        else:
            logger.info("not exiting out short position")

    def _check_buy_to_no_position(self, index, row):
        """
        While in a buy/long position, check if we should exit
        """
        self._print_log_statements(
            "checking if we should exit our buy position", row)

        # check ML predicted trend as well

        if (
            (self.price_prediction < row["Rolling Mean"][0])
            or (self.price_prediction < self.buy_entry_price)
            or (row["Rolling Mean"][0] < self.buy_entry_price)
        ):
            logger.info("buy_to_no_position")

            self._determine_win_or_loss_amount(row)
            # record keeping

            self.mode = "no_position"
            self.buy_has_crossed_mean = False
        else:
            logger.info("Not exiting buy position")

    def _check_if_we_should_buy(self, row):
        """
        Determine if we should enter a buy position
        """
        self._print_log_statements(
            "Checking if we should enter a buy position", row)
        start_time = time.time()
        # check ML predicted trend as well

        if self.price_prediction > row["Rolling Mean"]:
            logger.info(f"ml pred higher than mean taking position")

            self.mode = "buy"
            self.buy_entry_price = row["close"]
            self.stop_loss_price = row["close"] * (1 - self.stop_loss_pct)
            self.position_entry_date = row.name
        else:
            logger.info(
                "self.price_prediction is not higher than the Rolling Mean. Not going to buy"
            )

        end_time = time.time()
        logger.info(f"Eval buy took {(end_time - start_time)/60} minutes")

    def _check_if_we_should_short(self, row):
        """
        Check if we should enter a short position
        """
        self._print_log_statements(
            "Checking if we should enter a short position", row)

        start_time = time.time()

        if self.price_prediction < row["Rolling Mean"]:
            logger.info("pred  lower than mean taking position")

            self.mode = "short"
            self.short_entry_price = row["close"]
            self.stop_loss_price = row["close"] * (1 + self.stop_loss_pct)
            self.position_entry_date = row.name
        else:
            logger.info("not taking a position to short")

        end_time = time.time()
        logger.info(f"Eval short took {(end_time - start_time)/60} minutes")

    def _print_log_statements(self, message: str, row: pd.Series):
        logger.info("------------")
        logger.info(message)

        logger.info(f"current date = {row.index}")
        logger.info(f"close = {row['close']}")

        logger.info(f"mean = {row['Rolling Mean']}")
        logger.info(f"self.buy_entry_price = {self.buy_entry_price}")
        logger.info(f"self.short_entry_price = {self.short_entry_price}")
        logger.info(f"ml price_prediction  = {self.price_prediction}")

        logger.info("------------")


def main():
    logger.info("Running determine trading state")

    constants = read_in_constants("app/constants.yml")
    trading_constants = read_in_constants("app/trading_state_config.yml")
    # data should already be downloaded from the golang app
    bitcoin_df = read_in_data(constants["bitcoin_csv_filename"])
    etherum_df = read_in_data(constants["etherum_csv_filename"])
    ml_constants = read_in_constants("app/ml_config.yml")
    btc_predictor = BollingerBandsPredictor(
        "bitcoin", constants, ml_constants, bitcoin_df, additional_dfs=[etherum_df]
    )

    # TODO: uncomment
    price_prediction = btc_predictor.predict()
    print(price_prediction, 'price_prediction')
    logger.info("Determine trading state")

    # btc_predictor.df has the bollinger bands
    trading_state_class = DetermineTradingState(
        price_prediction, trading_constants, btc_predictor.df
    )
    trading_state_class.calculate_positions()
    logger.info("---- Finished determinig trading strategy --- ")
    # this works
    # update_yaml_config("app/trading_state_config.yml", trading_constants)
    # logger.info("---- Finished updating yaml config--- ")

    # update self.stop_loss_price  in the trading_state_config file
    # update self.trading_state_constants
    # update self. short_has_crossed_mean
    # update position_entry_date


if __name__ == "__main__":
    main()
