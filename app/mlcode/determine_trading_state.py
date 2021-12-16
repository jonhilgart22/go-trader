from datetime import datetime, timedelta
from typing import Dict, Union

try:  # need modules for pytest to work
    from app.mlcode.utils import setup_logging
except ModuleNotFoundError:  # Go is unable to run python modules -m
    from utils import setup_logging
import pandas as pd

logger = setup_logging()


class DetermineTradingState:
    def __init__(
        self,
        coin_to_predict: str,
        price_prediction: float,
        constants: Dict[str, Dict[str, str]],
        trading_state_constants: Dict[str, str],
        prediction_df: pd.DataFrame,
        won_and_lost_amount_constants: Dict[str, Dict[str, Union[int, float]]],
        actions_to_take_constants: Dict[str, Dict[str, Union[int, float]]],
        running_on_aws: bool,
    ):
        """Determine the current state we should be in for trading. Buy Short, entering, or exiting positions.

        Args:
            coin_to_predict: str - the coin we're predicting
            price_prediction ([type]): price prediction for the future price of the given coin
            constants (Dict[str, str]): The constants read in from yaml
            trading_state_constants (Dict[str, str]): the current state we are in for trading (buy short no_position)
            prediction_df (pd.DataFrame):  the DF with Bolligner bands to predict against
            won_and_lost_amount_constants: track win and lost trades and amount
            actions_to_take_constants: determine which actions to take for each coin (buy, short, none ...etc)
            running_on_aws: are on we lambda?
        """
        self.prediction_n_days = 7  # from ml config

        self.coin_to_predict = coin_to_predict
        self.price_prediction = price_prediction
        self.constants = constants.copy()
        self.trading_state_constants = trading_state_constants.copy()
        self.won_and_lose_amount_dict = won_and_lost_amount_constants.copy()
        self.actions_to_take_constants = actions_to_take_constants.copy()
        self.prediction_df = prediction_df
        self.running_on_aws = running_on_aws

        # trading state args
        for k, v in self.trading_state_constants.items():
            setattr(self, k, v)
            logger.info(f"Setting the class var self.{k} = {v}")

        # Record keeping for how this program is doing
        for k, v in self.won_and_lose_amount_dict.items():
            setattr(self, k, v)
            logger.info(f"Setting the class var self.{k} = {v}")

        # actions to take
        for k, v in self.actions_to_take_constants.items():
            setattr(self, k, v)
            logger.info(f"Setting the class var self.{k} = {v}")

    def calculate_positions(self):

        # grab the last row, and verify the date is equal to yesterday's date
        row = self.prediction_df.iloc[-1:]
        logger.info(f"current row = {row}")
        prev_row = self.prediction_df.iloc[-2:-1]
        logger.info(f"prev_row = {prev_row}")
        # assert date is yesterday date
        today = datetime.utcnow().date()
        yesterday = pd.to_datetime(today - timedelta(days=1))
        two_days_ago = pd.to_datetime(today - timedelta(days=2))
        logger.info(f"Yesterday = {yesterday}")
        logger.info(f"two_days_ago = {two_days_ago}")
        try:
            assert row.index == yesterday
            assert prev_row.index == two_days_ago
        except ValueError:
            raise (f"Incorrect dates passed. Yesterday = {yesterday} Two days ago = {two_days_ago}")

        # current stats
        self.todays_close_price = row[self.constants["close_col"]][0]
        self.todays_rolling_mean = row[self.constants["rolling_mean_col"]][0]
        self.todays_bollinger_high = row[self.constants["bollinger_high_col"]][0]
        self.todays_bollinger_low = row[self.constants["bollinger_low_col"]][0]
        self.previous_days_close = prev_row[self.constants["close_col"]][0]
        self.previous_days_bollinger_low = prev_row[self.constants["bollinger_low_col"]][0]

        # update stop loss
        if self.mode == "buy" and (1 - self.stop_loss_pct) * self.todays_close_price > self.stop_loss_price:
            self.stop_loss_price = (1 - self.stop_loss_pct) * self.todays_close_price
            self._write_and_print_log_statements(f"Updating stop loss to {self.stop_loss_price}", row)

        # TODO: uncomment once FTX allows short leveraged tokens
        # if (
        #     self.mode == "short"
        #     and (1 + self.stop_loss_pct) * self.todays_close_price < self.stop_loss_price
        # ):
        #     self.stop_loss_price = (1 + self.stop_loss_pct) * self.todays_close_price
        #     self._write_and_print_log_statements(
        #         f"Updating stop loss to {self.stop_loss_price}", row
        #     )

        # check if we've previously crossed the mean trailing price
        if self.mode == "buy" and self.todays_close_price > self.todays_rolling_mean:
            self.buy_has_crossed_mean = 1

        # TODO: uncomment once FTX allows shorts
        # if (
        #     self.mode == "short"
        #     and self.todays_close_price < self.todays_rolling_mean
        # ):
        #     self.short_has_crossed_mean = 1

        # stop loss, get out of buy position
        logger.info(f"self.stop_loss_price = {self.stop_loss_price}")
        if self.mode == "buy" and (self.stop_loss_price > self.todays_close_price):
            self._write_and_print_log_statements("stop loss activated for getting out of our buy", row)

            self._determine_win_or_loss_amount(row)
            # record keeping

            self.mode = "no_position"
            self.action_to_take = "buy_to_none"
            self.buy_has_crossed_mean = 0
            self.buy_entry_price = 0
            self.stop_loss_price = 0

        # TODO: uncomment once FTX allows shorts
        # # stop loss, get out of short position
        # elif self.mode == "short" and self.stop_loss_price < row[self.constants["close_col"][0]:
        #     self._write_and_print_log_statements(
        #         f"stop loss activated for getting out of our short", row
        #     )

        #     self._determine_win_or_loss_amount(row)
        #     # record keeping
        #     self.mode = "no_position"
        #     self.action_to_take = "short_to_none"
        #     self.short_has_crossed_mean = 0
        #     self.short_entry_price = 0
        #     self.stop_loss_price = 0

        # buy -> no_position? no position is below running mean
        # or, if we are above the top band (mean reversion)
        elif self.mode == "buy" and (
            (
                self.todays_close_price < self.todays_rolling_mean
                and self.trading_state_constants["buy_has_crossed_mean"] == 1
            )
            or (self.todays_close_price > self.todays_bollinger_high)
            or (self.todays_close_price < self.todays_bollinger_low)
            or (self.todays_rolling_mean < self.buy_entry_price)
        ):
            self._check_buy_to_none(row)

        # short -> no_position? no position if above running mean
        # TODO: FTX doesn't support short tokens... yet
        # or, if we are below the bottom band (mean reversion)
        # elif self.mode == "short" and (
        #     (
        #         row[self.constants["close_col"][0] > self.todays_rolling_mean
        #         and self.trading_state_constants[
        #             "short_has_crossed_mean"
        #         ] == 1
        #     )
        #     or (row[self.constants["close_col"][0] < self.todays_bollinger_low)
        #     or (row[self.constants["close_col"][0] > self.todays_bollinger_high)
        #     or self.todays_rolling_mean > self.short_entry_price
        # ):
        #     self._check_short_to_none(row)

        # buy check with ML model
        elif (
            self.mode == "no_position"
            and self.todays_close_price < self.todays_bollinger_low
            and self.previous_days_close > self.previous_days_bollinger_low
        ):
            self._check_if_we_should_buy(row)

        # short?
        # TODO: FTX doesn't support short tokens... yet. Undue when we are ready to short
        # elif (
        #     self.mode == "no_position"
        #     and row[self.constants["close_col"][0] > self.todays_bollinger_high
        #     and prev_row[self.constants["close_col"][0] < prev_row[self.constants["bollinger_low_col"]][0]
        # ):
        #     self._check_if_we_should_short(row)

        elif self.action_to_take == "none_to_buy":  # not in a position, continue holidng
            self.action_to_take = "buy_to_continue_buy"
            self._write_and_print_log_statements(
                "Taking no action today. Updating none_to_buy to buy_to_continue_buy", row
            )

        else:
            if self.action_to_take == "buy_to_none":
                self.action_to_take = "none_to_none"
                self._write_and_print_log_statements("Taking no action today. Hit the else statement and updated buy_to_none to none_to_none", row)
            else:
                self._write_and_print_log_statements("Taking no action today. Hit the else statement", row)

    def _determine_win_or_loss_amount(self, row: pd.Series):
        """
        For position we've exited, did we win? if so, by how much
        """
        # short s

        # stop loss for short
        if self.mode == "short" and self.short_entry_price < self.todays_close_price:
            lost_amount = self.todays_close_price - self.short_entry_price
            logger.info(f"Lost {lost_amount} on this trade")

            self.n_short_lost += 1
            self.dollar_amount_short_lost += lost_amount

        # made money
        elif self.mode == "short" and self.short_entry_price > self.todays_close_price:

            win_amount = self.short_entry_price - self.todays_close_price
            logger.info(f"Won {win_amount} on this trade")
            self.n_short_won += 1
            self.dollar_amount_short_won += win_amount
        # end short
        # buys

        # lost money
        elif self.mode == "buy" and self.buy_entry_price > self.todays_close_price:

            lost_amount = self.buy_entry_price - self.todays_close_price
            logger.info(f"Lost {lost_amount} on this trade")

            self.n_buy_lost += 1
            self.dollar_amount_buy_lost += lost_amount

        # made money
        elif self.mode == "buy" and self.buy_entry_price < self.todays_close_price:

            won_amount = self.todays_close_price - self.buy_entry_price
            logger.info(f"Won {won_amount} on this trade")
            self.n_buy_won += 1
            self.dollar_amount_buy_won += won_amount
        else:
            raise ValueError("Something went wrong calculating win/lose amount")

        days_in_trade = pd.to_datetime(row.index) - pd.to_datetime(self.position_entry_date)
        logger.info(f"days in trades = {days_in_trade.days}")
        self.n_total_days_in_trades += days_in_trade.days[0]

        # info logging

        logger.info(
            f"Average days in trades = {self.n_total_days_in_trades/(self.n_buy_won  + self.n_buy_lost + self.n_short_won  + self.n_short_lost )}"
        )
        if self.n_buy_won > 0 or self.n_buy_lost > 0:
            logger.info(f"Bat rate buy so far = {self.n_buy_won / (self.n_buy_won + self.n_buy_lost)}")
        if self.n_short_won > 0 or self.n_short_lost > 0:
            logger.info(f"Bat rate short so far = {self.n_short_won / (self.n_short_won + self.n_short_lost)}")

        if self.dollar_amount_buy_won > 0 or self.dollar_amount_buy_lost > 0:
            logger.info(
                f"Win rate buy so far = {float(self.dollar_amount_buy_won) / float(float(self.dollar_amount_buy_won) + float(self.dollar_amount_buy_lost))}"
            )
        if self.dollar_amount_short_won > 0 or self.dollar_amount_short_lost > 0:
            logger.info(
                f"Win rate short so far = {self.dollar_amount_short_won / (self.dollar_amount_short_won + self.dollar_amount_short_lost)}"
            )

        logger.info(f"Total days in trades = {self.n_total_days_in_trades }")

        # reset for sanity
        self.position_entry_date = None

    def _check_short_to_none(self, row: pd.Series):
        """
        While in a short position, check if we should exit
        """
        logger.info("checking if we should get out of our short position")

        # check ML predicted trend as well

        if (
            (self.price_prediction > self.todays_rolling_mean)
            or (self.price_prediction > self.short_entry_price)
            or (self.todays_rolling_mean > self.short_entry_price)
        ):
            # note, the order here matters
            self._determine_win_or_loss_amount(row)

            self.mode = "no_position"
            self.action_to_take = "short_to_none"
            self.short_has_crossed_mean = 0
            self.short_entry_price = 0
            self.stop_loss_price = 0

            self._write_and_print_log_statements("short position to none", row)
        else:
            self._write_and_print_log_statements("not exiting short position", row)
            self.action_to_take = "short_to_contine_short"

    def _check_buy_to_none(self, row: pd.Series):
        """
        While in a buy/long position, check if we should exit
        """
        logger.info("checking if we should exit our buy position")

        # check ML predicted trend as well

        if (
            (self.price_prediction < self.todays_rolling_mean)
            or (self.price_prediction < self.buy_entry_price)
            or (self.todays_rolling_mean < self.buy_entry_price)
        ):
            # note the order here matters
            self._determine_win_or_loss_amount(row)
            # record keeping

            self.mode = "no_position"
            self.action_to_take = "buy_to_none"
            self.buy_has_crossed_mean = 0
            self.buy_entry_price = 0
            self.stop_loss_price = 0

            self._write_and_print_log_statements("Exiting buy position . Mode = buy_to_none ", row)
        else:
            self._write_and_print_log_statements("Not exiting buy position", row)
            self.action_to_take = "buy_to_continue_buy"

    def _check_if_we_should_buy(self, row: pd.Series):
        """
        Determine if we should enter a buy position
        """
        logger.info("Checking if we should buy")
        # check ML predicted trend as well

        if self.price_prediction > self.todays_rolling_mean:
            # note the order here matters. Want to write logs reflecting the current state
            self.mode = "buy"
            self.action_to_take = "none_to_buy"
            self.buy_entry_price = self.todays_close_price
            self.stop_loss_price = self.todays_close_price * (1 - self.stop_loss_pct)
            self.position_entry_date = str(row.index[0])

            self._write_and_print_log_statements("ml pred higher than mean taking position", row)
        else:
            self._write_and_print_log_statements(
                "self.price_prediction is not higher than the Rolling Mean. Not going to buy", row
            )

            self.action_to_take = "none_to_none"

    def _check_if_we_should_short(self, row: pd.Series):
        """
        Check if we should enter a short position
        """
        logger.info("Checking if we should enter a short position")

        if self.price_prediction < self.todays_rolling_mean:

            # note the order here matters. Want to write logs reflecting the current state

            self.mode = "short"
            self.action_to_take = "none_to_short"
            self.short_entry_price = self.todays_close_price
            self.stop_loss_price = self.todays_close_price * (1 + self.stop_loss_pct)
            self.position_entry_date = str(row.index[0])

            self._write_and_print_log_statements("pred  lower than mean taking position to short", row)
        else:
            self._write_and_print_log_statements("not taking a position to short", row)
            self.action_to_take = "none_to_none"

    def _write_and_print_log_statements(self, message: str, row: pd.Series):

        logger.info("------------")
        logger.info(f"Logging for coin = {self.coin_to_predict}")
        logger.info(message)

        logger.info(f"current date = {row.index}")
        logger.info(f"close = {row[self.constants['close_col']][0]}")

        logger.info(f"rolling_mean_col= {row[self.constants['rolling_mean_col']][0]}")
        logger.info(f"bollinger high = {row[self.constants['bollinger_high_col']][0]}")
        logger.info(f"bollinger low = {row[self.constants['bollinger_low_col']][0]}")
        logger.info(f"Self.action_to_take = {self.action_to_take}")

        logger.info(f"self.buy_entry_price = {self.buy_entry_price}")
        # logger.info(f"self.short_entry_price = {self.short_entry_price}")
        logger.info(f"ml price_prediction  = {self.price_prediction}")

        if self.running_on_aws:
            filename = "/tmp/" + self.constants["log_filename"]
        else:
            filename = self.constants["log_filename"]
        logger.info(f"Writing logs to file {filename}")
        with open(filename, "w") as text_file:
            text_file.write("------------")
            text_file.write(self.constants["email_separator"])
            text_file.write(f"Logging for coin = {self.coin_to_predict}")

            text_file.write(self.constants["email_separator"])
            text_file.write(message + "")

            text_file.write(self.constants["email_separator"])
            text_file.write(f"current date = {row.index}\n")

            text_file.write(self.constants["email_separator"])
            text_file.write(f"close = {self.todays_close_price}")

            text_file.write(self.constants["email_separator"])
            text_file.write(f"rolling_mean_col= {self.todays_rolling_mean}")

            text_file.write(self.constants["email_separator"])
            text_file.write(f"bollinger high = {self.todays_bollinger_high} ")

            text_file.write(self.constants["email_separator"])
            text_file.write(f"bollinger low = {self.todays_bollinger_low} ")

            text_file.write(self.constants["email_separator"])
            text_file.write(f"self.buy_entry_price = {self.buy_entry_price}")

            text_file.write(self.constants["email_separator"])
            text_file.write(f"ml price_prediction for next {self.prediction_n_days}  days= {self.price_prediction}")

            text_file.write(self.constants["email_separator"])
            text_file.write(f"Self.mode = {self.mode}")

            text_file.write(self.constants["email_separator"])
            text_file.write(f"Self.action_to_take = {self.action_to_take}")

            text_file.write(self.constants["email_separator"])
            text_file.write(f"stop_loss_price = {self.stop_loss_price}")

            text_file.write(self.constants["email_separator"])
            text_file.write(f"position_entry_date = {self.position_entry_date}")
            text_file.write(self.constants["email_separator"])

            if self.mode == "no_position":
                text_file.write("---- BUY CHECKS ----")

                text_file.write(self.constants["email_separator"])
                text_file.write("Verify the self.mode is no_position")

                text_file.write(self.constants["email_separator"])
                text_file.write(f"Check if todays close is lower than todays bolligner low = {self.todays_close_price < self.todays_bollinger_low}")

                text_file.write(self.constants["email_separator"])
                text_file.write(f"Check if the previous days close was greater than the previous days bollinger low = {self.previous_days_close > self.previous_days_bollinger_low}")

                text_file.write(self.constants["email_separator"])
                text_file.write(f"self.previous_days_close = {self.previous_days_close }")

                text_file.write(self.constants["email_separator"])
                text_file.write(f"self.previous_days_bollinger_low = {self.previous_days_bollinger_low }")

        logger.info("------------")

    def update_state(self):
        """Convenience method to update  our state params. Try to convert everything to floats for serializable"""
        for k, v in self.trading_state_constants.items():
            try:
                item = float(getattr(self, k, v))
            except Exception:
                item = getattr(self, k, v)
            self.trading_state_constants[k] = item
        for k, v in self.won_and_lose_amount_dict.items():
            try:
                item = float(getattr(self, k, v))
            except Exception:
                item = getattr(self, k, v)
            self.won_and_lose_amount_dict[k] = item
        for k, v in self.actions_to_take_constants.items():
            try:
                item = float(getattr(self, k, v))
            except Exception:
                item = getattr(self, k, v)
            self.actions_to_take_constants[k] = item
