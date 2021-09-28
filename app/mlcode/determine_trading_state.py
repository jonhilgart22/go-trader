from predict_price_movements import BollingerBandsPredictor
import pandas as pd
from utils import read_in_constants, read_in_data
from typing import Dict
import time
import logging

logger = logging.getLogger(__name__)


class DetermineTradingState:
    def __init__(
        self, price_prediction: float, trading_state_constants: Dict[str, str], prediction_df: pd.DataFrame
    ):
        """[summary]

        Args:
            price_prediction ([type]): price prediction for the future price of the given coin
            trading_state_constants (Dict[str, str]): the current state we are in for trading (buy short no_position)
            prediction_df (pd.DataFrame):  the DF with Bolligner bands to predict against
        """
        self.price_prediction = price_prediction
        self.trading_state_constants = trading_state_constants
        self.prediction_df = prediction_df
        self.stop_loss_price = self.trading_state_constants['stop_loss_price']

    def calculate_positions(self):
        # self.prediction_df["Position"] = None
        # self.prediction_df["Mode"] = None
        # self.prediction_df["ML_Future_Prediction"] = None
        # grab the last row, and verify the date is equal to yesterday's date
        row = self.prediction_df.iloc[-1:]
        logger.info(row)
        logger.info('row')
        prev_row = self.prediction_df.iloc[-2:-1]
        logger.info(prev_row)
        logger.info('prev_row')
        # TODO: assert date is yesterday date

        # update stop loss
        if (
            self.trading_state_constants["mode"] == "buy"
            and (1 - self.trading_state_constants["stop_loss_pct"]) * row["close"]
            > self.stop_loss_price
        ):
            self.stop_loss_price = (
                1 - self.trading_state_constants["stop_loss_pct"]
            ) * row["close"]
            logger.info(f"Updating stop loss to {self.stop_loss_price}")
            logger.info(row["close"])
            logger.info("row close")

        if (
            self.trading_state_constants["mode"] == "short"
            and (1 + self.trading_state_constants["stop_loss_pct"]) * row["close"]
            < self.stop_loss_price
        ):
            self.stop_loss_price = (
                1 + self.trading_state_constants["stop_loss_pct"]
            ) * row["close"]
            logger.info(f"Updating stop loss to {self.stop_loss_price}")
            logger.info(row["close"], "row close")

        # check if we've previously crossed the mean trailing price
        if self.trading_state_constants["mode"] == "buy" and row["close"] > row["Rolling Mean"]:
            self.buy_has_crossed_mean = True

        if self.trading_state_constants["mode"] == "short" and row["close"] < row["Rolling Mean"]:
            self.short_has_crossed_mean = True

        # stop loss, get out of buy position
        if self.trading_state_constants["mode"] == "buy" and self.stop_loss_price > row["close"]:
            logger.info("----")
            logger.info("stop loss activated for getting out of our buy")
            logger.info(row.name, "current date")
            logger.info(row["close"], "row close")
            logger.info(self.stop_loss_price, "self.stop_loss_price")
            logger.info(self.buy_entry_price, "self.buy_entry_price")

            self.df.iloc[index, self.df.columns.get_loc("Position")] = 1
            if index + 1 == len(self.df):
                self.df.iloc[index, self.df.columns.get_loc("Position")] = 0
            else:
                # for pct change it does a ffilll. ffill with zeros
                self.df.iloc[index + 1,
                             self.df.columns.get_loc("Position")] = 0
            self._determine_win_or_loss_amount(row)
            # record keeping
            self.df.iloc[index, self.df.columns.get_loc(
                "Mode")] = "buy_to_no_position"
            self.trading_state_constants["mode"] = "no_position"
            buy_has_crossed_mean = False

        # stop loss, get out of short position
        elif self.trading_state_constants["mode"] == "short" and self.stop_loss_price < row["close"]:
            logger.info("----")
            logger.info("stop loss activated for getting out of our short")
            logger.info(row.name, "current date")
            logger.info(row["close"], "row close")
            logger.info(self.stop_loss_price, "self.stop_loss_price")
            logger.info(self.short_entry_price, "self.short_entry_price")

            self.df.iloc[index, self.df.columns.get_loc("Position")] = -1
            if index + 1 == len(self.df):
                self.df.iloc[index, self.df.columns.get_loc("Position")] = 0
            else:
                # for pct change it does a ffilll. ffill with zeros
                self.df.iloc[index + 1,
                             self.df.columns.get_loc("Position")] = 0
            self._determine_win_or_loss_amount(row)
            # record keeping
            self.df.iloc[
                index, self.df.columns.get_loc("Mode")
            ] = "short_to_no_position"
            self.trading_state_constants["mode"] = "no_position"
            short_has_crossed_mean = False

        # buy -> no_position? no position is below running mean
        # or, if we are above the top band (mean reversion)
        elif self.trading_state_constants["mode"] == "buy" and (
            (row["close"] < row["Rolling Mean"] and self.buy_has_crossed_mean)
            or (row["close"] > row["Bollinger High"])
            or (row["close"] < row["Bollinger Low"])
            or (row["Rolling Mean"] < self.buy_entry_price)
        ):
            self._check_buy_to_no_position(index, row)

        # short -> no_position? no position if above running mean
        # or, if we are below the bottom band (mean reversion)
        elif self.trading_state_constants["mode"] == "short" and (
            (row["close"] > row["Rolling Mean"]
             and self.short_has_crossed_mean)
            or (row["close"] < row["Bollinger Low"])
            or (row["close"] > row["Bollinger High"])
            or row["Rolling Mean"] > self.short_entry_price
        ):
            self._check_short_to_no_position(index, row)

        # buy check with ML model
        elif (
            self.trading_state_constants["mode"] == "no_position"
            and row["close"] < row["Bollinger Low"]
            and prev_row["close"] > prev_row["Bollinger Low"]
        ):
            self._check_if_we_should_buy(index, row)

        # short?
        elif (
            self.trading_state_constants["mode"] == "no_position"
            and row["close"] > row["Bollinger High"]
            and prev_row["close"] < prev_row["Bollinger High"]
        ):
            self._check_if_we_should_short(index, row)

        else:
            self.df.iloc[index, self.df.columns.get_loc(
                "Mode")] = self.trading_state_constants["mode"]

    def _determine_win_or_loss_amount(self, row):
        """
        For position we've exited, did we win? if so, by how much
        """
        # short s

        # stop loss for short
        if self.trading_state_constants["mode"] == "short" and self.short_entry_price < row["close"]:
            lost_amount = row["close"] - self.short_entry_price
            logger.info(f"Lost {lost_amount} on this trade")

            self.win_and_lose_amount_dict["n_short_lost"] += 1
            self.win_and_lose_amount_dict["$_short_lost"] += lost_amount

        # made money
        elif self.trading_state_constants["mode"] == "short" and self.short_entry_price > row["close"]:

            win_amount = self.short_entry_price - row["close"]
            logger.info(f"Won {win_amount} on this trade")
            self.win_and_lose_amount_dict["n_short_won"] += 1
            self.win_and_lose_amount_dict["$_short_won"] += win_amount
        # end short
        # buys

        # lost money
        elif self.trading_state_constants["mode"] == "buy" and self.buy_entry_price > row["close"]:

            lost_amount = self.buy_entry_price - row["close"]
            logger.info(f"Lost {lost_amount} on this trade")
            self.win_and_lose_amount_dict["n_buy_lost"] += 1
            self.win_and_lose_amount_dict["$_buy_lost"] += lost_amount

        # made money
        elif self.trading_state_constants["mode"] == "buy" and self.buy_entry_price < row["close"]:

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

        logger.info("---------")
        logger.info("checking if we should get out of our short position")
        logger.info(row.name, "current date")
        logger.info(row["Rolling Mean"], "mean")
        logger.info(self.short_entry_price, "self.short_entry_price")
        logger.info(row["close"], "current close")

        # check ML predicted trend as well
        try:
            ml_pred = self._check_ml_prediction(row.name)
        except ValueError:  # don't have enough data for ML prediction
            logger.info(
                "Ran into not enough data ValueError for short_to_no_position")
            return
        logger.info(ml_pred, "ml_pred")
        if (
            (ml_pred > row["Rolling Mean"])
            or (ml_pred > self.short_entry_price)
            or (row["Rolling Mean"] > self.short_entry_price)
        ):
            logger.info("short_to_no_position")
            self.df["ML_Future_Prediction"] = ml_pred

            self.df.iloc[index, self.df.columns.get_loc("Position")] = -1
            if index + 1 == len(self.df):
                self.df.iloc[index, self.df.columns.get_loc("Position")] = 0
            else:
                # for pct change it does a ffilll. ffill with zeros
                self.df.iloc[index + 1,
                             self.df.columns.get_loc("Position")] = 0

            self._determine_win_or_loss_amount(row)
            # record keeping
            self.df.iloc[
                index, self.df.columns.get_loc("Mode")
            ] = "short_to_no_position"
            self.trading_state_constants["mode"] = "no_position"
            short_has_crossed_mean = False
        else:
            self.df.iloc[index, self.df.columns.get_loc(
                "Mode")] = self.trading_state_constants["mode"]

    def _check_buy_to_no_position(self, index, row):
        """
        While in a buy/long position, check if we should exit
        """
        logger.info("---------")
        logger.info("checking if we should get out of our buy position")
        logger.info(row.name, "current date")
        logger.info(row["Rolling Mean"], "mean")
        logger.info(self.buy_entry_price, "self.buy_entry_price")
        logger.info(row["close"], "current close")

        # check ML predicted trend as well
        try:
            ml_pred = self._check_ml_prediction(row.name)
        except ValueError:  # don't have enough data for ML prediction
            logger.info(
                "Ran into not enough data ValueError for buy_to_no_position")
            return
        logger.info(ml_pred, "ml_pred")

        if (
            (ml_pred < row["Rolling Mean"])
            or (ml_pred < self.buy_entry_price)
            or (row["Rolling Mean"] < self.buy_entry_price)
        ):
            logger.info("buy_to_no_position")
            self.df["ML_Future_Prediction"] = ml_pred

            self.df.iloc[index, self.df.columns.get_loc("Position")] = 1

            if index + 1 == len(self.df):
                self.df.iloc[index, self.df.columns.get_loc("Position")] = 0
            else:
                # for pct change it does a ffilll. ffill with zeros
                self.df.iloc[index + 1,
                             self.df.columns.get_loc("Position")] = 0

            self._determine_win_or_loss_amount(row)
            # record keeping
            self.df.iloc[index, self.df.columns.get_loc(
                "Mode")] = "buy_to_no_position"
            self.trading_state_constants["mode"] = "no_position"
            self.buy_has_crossed_mean = False
        else:
            self.df.iloc[index, self.df.columns.get_loc(
                "Mode")] = self.trading_state_constants["mode"]

    def _check_if_we_should_buy(self, index, row):
        """
        Determine if we should enter a buy position
        """
        start_time = time.time()
        logger.info("----------")
        logger.info("buy")
        logger.info(row.name, "current date")
        logger.info(row["close"], "close")
        # check ML predicted trend as well
        try:
            ml_pred = self._check_ml_prediction(row.name)
        except ValueError:  # don't have enough data for ML prediction
            logger.info("Ran into not enough data ValueError for buy")
            self.df.iloc[index, self.df.columns.get_loc(
                "Mode")] = self.trading_state_constants["mode"]
            return 9999999

        logger.info(ml_pred, "ml prediction day")
        logger.info(row["Rolling Mean"], "mean")

        if ml_pred > row["Rolling Mean"]:
            logger.info(f"ml pred higher than mean taking position")
            self.df["ML_Future_Prediction"] = ml_pred
            self.ml_prediction_date_and_price[
                row.name + timedelta(days=self.ml_prediction_n_days)
            ] = ml_pred

            # buy. add one to index so that pct_change works
            self.df.iloc[index, self.df.columns.get_loc("Position")] = 0

            if index + 1 == len(self.df):
                self.df.iloc[index, self.df.columns.get_loc("Position")] = 1
            else:
                # buy. add one to index so that pct_change works
                self.df.iloc[index + 1,
                             self.df.columns.get_loc("Position")] = 1
            self.df.iloc[index, self.df.columns.get_loc("Mode")] = "buy"
            self.number_of_trades += 1
            self.trading_state_constants["mode"] = "buy"
            self.buy_entry_price = row["close"]
            self.stop_loss_price = row["close"] * (
                1 - self.trading_state_constants["stop_loss_pct"]
            )
            self.position_entry_date = row.name
        else:
            self.df.iloc[index, self.df.columns.get_loc(
                "Mode")] = self.trading_state_constants["mode"]

        end_time = time.time()
        logger.info(f"Eval buy took {(end_time - start_time)/60} minutes")

    def _check_if_we_should_short(self, index, row):
        """
        Check if we should enter a short position
        """
        start_time = time.time()
        logger.info("----------")
        logger.info("short")
        logger.info(row.name, "current date")
        logger.info(row["close"], "close")
        # check ML predicted trend as well
        try:
            ml_pred = self._check_ml_prediction(row.name)
        except Exception as e:  # don't have enough data for ML prediction
            logger.info("Ran into not enough data ValueError for short")
            logger.info(e)
            self.df.iloc[index, self.df.columns.get_loc(
                "Mode")] = self.trading_state_constants["mode"]
            return 0

        logger.info(ml_pred, "ml pred day")
        logger.info(row["Rolling Mean"], "mean")

        if ml_pred < row["Rolling Mean"]:
            logger.info("pred 7 day lower than mean taking position")
            self.df["ML_Future_Prediction"] = ml_pred
            self.ml_prediction_date_and_price[
                row.name + timedelta(days=self.ml_prediction_n_days)
            ] = ml_pred

            # short starts at the end of the day. Calculate pct_change starting tomorrow
            self.df.iloc[index, self.df.columns.get_loc("Position")] = 0
            # short starts at the end of the day. Calculate pct_change starting tomorrow
            self.df.iloc[index + 1, self.df.columns.get_loc("Position")] = -1
            if index + 1 == len(self.df):
                self.df.iloc[index, self.df.columns.get_loc("Position")] = -1
            else:
                # buy. add one to index so that pct_change works
                self.df.iloc[index + 1,
                             self.df.columns.get_loc("Position")] = -1
            self.df.iloc[index, self.df.columns.get_loc("Mode")] = "short"
            self.number_of_trades += 1
            self.trading_state_constants["mode"] = "short"
            self.short_entry_price = row["close"]
            self.stop_loss_price = row["close"] * (
                1 + self.trading_state_constants["stop_loss_pct"]
            )
            self.position_entry_date = row.name
        else:
            self.df.iloc[index, self.df.columns.get_loc(
                "Mode")] = self.trading_state_constants["mode"]

        end_time = time.time()
        logger.info(f"Eval short took {(end_time - start_time)/60} minutes")


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
    logger.info("Determine trading state")

    # btc_predictor.df has the bollinger bands
    trading_state_class = DetermineTradingState(
        price_prediction, trading_constants, btc_predictor.df)
    trading_state_class.calculate_positions()
    logger.info("---- Finished determinig trading strategy --- ")

    # update self.stop_loss_price  in the trading_state_config file


if __name__ == "__main__":
    main()
