#!/usr/local/bin/python
import logging
import yaml
import pandas as pd
import time
import time
from datetime import datetime
from tqdm.keras import TqdmCallback
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from typing import Dict, Any, List
import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np

from darts import TimeSeries
from darts.dataprocessing.transformers import Scaler
from darts.models import TCNModel, NBEATSModel
from darts.utils.missing_values import fill_missing_values

from darts.metrics import mape, mse
from darts.utils.timeseries_generation import datetime_attribute_timeseries

from math import sqrt
from time import time

from datetime import timedelta

import warnings

warnings.filterwarnings("ignore")
logging.disable(logging.CRITICAL)


def read_in_constants(input_file: str):
    print(f"Reading in {input_file}")
    with open(input_file, "r") as stream:
        try:
            constants = yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            print(exc)
            return

    for k, v in constants.items():
        print(f"Key = {k} Value = {v}")
    return constants


def read_in_data(input_file: str) -> pd.DataFrame:
    print(f"Input file {input_file}")
    df = pd.read_csv(input_file, index_col=0, parse_dates=True)
    print(df.head())
    print(df.tail())
    print("---")
    return df


class BollingerBandsPredictor:
    def __init__(
        self,
        df_original,
        from_date,
        period,
        window,
        no_of_std,
        ml_lookback_windows,
        ml_prediction_n_days,
        model_name="TCN",
        additional_dfs=[],
        stop_loss_pct=0.10,
        figsize=None,
    ):
        """
        df_original: The input dataframe containing candles we want to build bollinger bands from and predict.
            Assumes thes date is the index
        from_date: The start date to slice the df_original by
        period: time frequency to build candles if needed and transform timeseries dataset
        window: lookback window for bollinger bands + roling mean
        no_of_std: number of std for bollinger bands
        ml_lookback_windows: one lookback window per ML model
        ml_prediction_n_days: n days in the future to predcit
        additional_dfs: Additional DFs. Assumed to be the same dates are the df_original and have a 'close' col
        stop_loss_pct: the percent under/over our short/buy to keep a stop at
        """
        self.df = df_original
        self.from_date = from_date
        self.period = period
        self.window = window
        self.no_of_std = no_of_std
        self.figsize = figsize
        self.ml_lookback_windows = ml_lookback_windows
        self.max_looback = max(ml_lookback_windows)
        # vars for taking / exiting positions
        self.ml_models_dict = {}
        self.have_trained_ml_models = False
        self.buy_entry_price = None
        self.short_entry_price = None
        # the number of days in the future to predict
        self.ml_prediction_n_days = ml_prediction_n_days
        self.additional_dfs = additional_dfs
        self.ml_train_cols = ["open", "high", "low", "Rolling Mean", "volume"]
        self.model_name = model_name  # what type of ML model to train
        self.pred_col = "close"
        self.stop_loss_price = 0  # Price at which we get out of our position
        self.stop_loss_pct = 0.10  # percent to trail our buy/short until we get out
        self.first_run = True  # if first run, train the models longer
        self.number_of_trades = 0
        self.buy_has_crossed_mean = False
        self.short_has_crossed_mean = False
        self.ml_prediction_date_and_price = {}
        self.mode = "no_position"  # the curent position we have

        self.start_time = time.time()
        # trade analytics
        self.position_entry_date = None
        self.n_total_days_in_trades = 0
        self.win_and_lose_amount_dict = {
            "n_short_lost": 0,
            "n_buy_lost": 0,
            "n_short_won": 0,
            "n_buy_won": 0,
            "$_short_lost": 0,
            "$_buy_lost": 0,
            "$_short_won": 0,
            "$_buy_won": 0,
        }

    def _scale_time_series_df_and_time_cols(
        self, input_df, time_cols=["year", "month", "day"]
    ):
        ts_transformers = {}
        ts_stacked_series = None
        ts_transformers, ts_stacked_series = self._scale_time_series_df(input_df)

        # build year and month and day series:
        for col in time_cols:
            transformer = Scaler()
            transformed_series = transformer.fit_transform(
                datetime_attribute_timeseries(ts_stacked_series, attribute=col)
            )
            ts_transformers[col] = transformer

            ts_stacked_series = ts_stacked_series.stack(transformed_series)

        return (
            ts_transformers,
            ts_stacked_series,
            TimeSeries.from_series(input_df[self.pred_col], freq=self.period),
        )

    def _scale_time_series_df(self, input_df, use_pred_col=False):
        """
        Scale an input time series col from 0 to 1

        input_df: the DF that contains the col
        use_pred_col: if we are transforming additional DFs, we can use the pred col 'close' for them
        """
        ts_transformers = {}
        ts_stacked_series = None
        cols_to_transform = self.ml_train_cols.copy()
        # if we have additional DFs, we can include their close price
        if use_pred_col:
            cols_to_transform.append(self.pred_col)
        for col in cols_to_transform:
            transformer = Scaler()

            transformed_series = transformer.fit_transform(
                fill_missing_values(
                    TimeSeries.from_series(input_df[col], freq=self.period)
                )
            )
            ts_transformers[col] = transformer

            if ts_stacked_series:
                ts_stacked_series = ts_stacked_series.stack(transformed_series)

            else:
                ts_stacked_series = transformed_series
        return ts_transformers, ts_stacked_series

    def _add_additional_training_dfs(
        self, ts_stacked_series, additional_dfs, verbose=False
    ):
        """
        Scale any additional DFs provided (such as ETHER)

        ts_stacked_series: the current scaled lists from the df_original provided
        additional_dfs: additional dataframes that have been sliced for the correct date
        """
        all_ts_stacked_series = None
        for df in additional_dfs:
            (
                additional_ts_transformers,
                additional_ts_stacked_series,
            ) = self._scale_time_series_df(df, use_pred_col=True)
            if all_ts_stacked_series is None:
                if verbose:
                    print(
                        "last date for training additional df data",
                        additional_ts_stacked_series.time_index[-1],
                    )
                all_ts_stacked_series = additional_ts_stacked_series
            else:
                return "Error. More than one time series for _add_additional_training_dfs not implemented"
        return (
            additional_ts_transformers,
            all_ts_stacked_series.stack(ts_stacked_series),
        )

    def _check_ml_prediction(
        self,
        end_time,
        tcn_first_epochs=200,
        tcn_sub_epochs=100,
        nbeats_first_epochs=10,
        nbeats_sub_epochs=2,
        verbose=False,
    ) -> float:
        """train ML model to predict price movement over the last self.ml_lookback_windows days
            predicting over the next self.ml_prediction_n_days days in teh future
        end_time: the current date to predict up to
        output_chunk_length: number of predicts to make
        tcn_first_epochs: n of training epochs for the first training run
        tcn_sub_epochs: n of training epochs for subsequents training runs
        nbeats_first_epochs: first epochs
        nbeats_sub_epochs: epochs for NBEATS model
        """
        if not self.have_trained_ml_models:  # create models once, retrain incrementally

            for model_n in self.model_name:
                for lookback_window in self.ml_lookback_windows:
                    if model_n == "NBEATS":
                        self.ml_models_dict[
                            str(lookback_window) + "_NBEATS"
                        ] = NBEATSModel(
                            input_chunk_length=lookback_window,
                            output_chunk_length=self.ml_prediction_n_days,
                            random_state=0,
                            model_name=str(lookback_window) + "_nbeats",
                            num_blocks=4,
                            layer_widths=256,
                            force_reset=True,
                            log_tensorboard=True,
                        )
                    elif model_n == "TCN":
                        self.ml_models_dict[str(lookback_window) + "_TCN"] = TCNModel(
                            dropout=0.1,
                            random_state=0,
                            dilation_base=2,
                            weight_norm=True,
                            kernel_size=3,
                            num_filters=6,
                            num_layers=6,
                            input_chunk_length=lookback_window,
                            output_chunk_length=self.ml_prediction_n_days,
                            model_name=str(lookback_window) + "_tcn",
                            force_reset=True,
                            log_tensorboard=True,
                        )
                    else:
                        raise ValueError
                        print(f"Error. Incorrect input model of {self.model_name}")

        training_df = self.df[self.df.index <= pd.to_datetime(end_time)]
        # add in any additional DFs, like ETHER
        additional_dfs_sliced = []
        if len(self.additional_dfs) > 0:
            for additional_df in self.additional_dfs:
                additional_dfs_sliced.append(
                    additional_df[additional_df.index <= pd.to_datetime(end_time)]
                )

        # combine TS from both DFs
        (
            ts_transformers,
            ts_stacked_series,
            train_close_series,
        ) = self._scale_time_series_df_and_time_cols(training_df)
        if verbose:
            print("original DF training series", ts_stacked_series.components)
            print("last date for training data", ts_stacked_series.time_index[-1])

        if len(self.additional_dfs) > 0:
            # overwrite the ts_stacked_series var if we have additional DFS
            (
                additional_ts_transformers,
                ts_stacked_series,
            ) = self._add_additional_training_dfs(
                ts_stacked_series, additional_dfs_sliced
            )
            # TODO: in the future, combine the ts_tra
            ts_transformers = {
                **additional_ts_transformers,
                **ts_transformers,
            }  # merge dicts

        if verbose:
            print("all series now stacked", ts_stacked_series.components)

        # train the model & make predictions
        all_predictions = []
        for lookback_name, model in self.ml_models_dict.items():
            if verbose:
                print(f"Lookback name = {lookback_name}, model = {model}")
                print(str(lookback_window) + "_TCN")
                print(self.first_run, "first run")
            if self.first_run and "TCN" in lookback_name:
                model.fit(
                    series=train_close_series,
                    past_covariates=[ts_stacked_series],
                    verbose=verbose,
                    epochs=tcn_first_epochs,
                )
            elif self.first_run and "_NBEATS" in lookback_name:
                model.fit(
                    series=train_close_series,
                    past_covariates=[ts_stacked_series],
                    verbose=verbose,
                    epochs=nbeats_first_epochs,
                )
            elif "_NBEATS" in lookback_name:
                model.fit(
                    series=train_close_series,
                    past_covariates=[ts_stacked_series],
                    verbose=verbose,
                    epochs=nbeats_sub_epochs,
                )
            elif "_TCN" in lookback_name:
                model.fit(
                    series=train_close_series,
                    past_covariates=[ts_stacked_series],
                    verbose=verbose,
                    epochs=tcn_sub_epochs,
                )

            ml_prediction = model.predict(
                n=self.ml_prediction_n_days,
                series=train_close_series,
                past_covariates=[ts_stacked_series],
            ).last_value()  # grab the last value
            print(f" Lookback = {lookback_name} Prediction = {ml_prediction}")
            all_predictions.append(ml_prediction)
        self.first_run = False

        return np.mean(all_predictions)  # average the predictions

    def _calculate_positions(self):
        self.df["Position"] = None
        self.df["Mode"] = None
        self.df["ML_Future_Prediction"] = None

        for index in range(len(self.df)):

            row = self.df.iloc[index]
            prev_row = self.df.iloc[index - 1]

            # lookback windows needed for ML model
            if pd.to_datetime(row.name) < self.prediction_start:
                self.df.iloc[index, self.df.columns.get_loc("Mode")] = self.mode
                continue

            if index == 0:
                self.df.iloc[index, self.df.columns.get_loc("Mode")] = self.mode
                continue

            # update stop loss
            if (
                self.mode == "buy"
                and (1 - self.stop_loss_pct) * row["close"] > self.stop_loss_price
            ):
                self.stop_loss_price = (1 - self.stop_loss_pct) * row["close"]
                print(f"Updating stop loss to {self.stop_loss_price}")
                print(row["close"], "row close")

            if (
                self.mode == "short"
                and (1 + self.stop_loss_pct) * row["close"] < self.stop_loss_price
            ):
                self.stop_loss_price = (1 + self.stop_loss_pct) * row["close"]
                print(f"Updating stop loss to {self.stop_loss_price}")
                print(row["close"], "row close")

            # check if we've previously crossed the mean trailing price
            if self.mode == "buy" and row["close"] > row["Rolling Mean"]:
                self.buy_has_crossed_mean = True

            if self.mode == "short" and row["close"] < row["Rolling Mean"]:
                self.short_has_crossed_mean = True

            # stop loss, get out of buy position
            if self.mode == "buy" and self.stop_loss_price > row["close"]:
                print("----")
                print("stop loss activated for getting out of our buy")
                print(row.name, "current date")
                print(row["close"], "row close")
                print(self.stop_loss_price, "self.stop_loss_price")
                print(self.buy_entry_price, "self.buy_entry_price")

                self.df.iloc[index, self.df.columns.get_loc("Position")] = 1
                if index + 1 == len(self.df):
                    self.df.iloc[index, self.df.columns.get_loc("Position")] = 0
                else:
                    # for pct change it does a ffilll. ffill with zeros
                    self.df.iloc[index + 1, self.df.columns.get_loc("Position")] = 0
                self._determine_win_or_loss_amount(row)
                # record keeping
                self.df.iloc[
                    index, self.df.columns.get_loc("Mode")
                ] = "buy_to_no_position"
                self.mode = "no_position"
                buy_has_crossed_mean = False

            # stop loss, get out of short position
            elif self.mode == "short" and self.stop_loss_price < row["close"]:
                print("----")
                print("stop loss activated for getting out of our short")
                print(row.name, "current date")
                print(row["close"], "row close")
                print(self.stop_loss_price, "self.stop_loss_price")
                print(self.short_entry_price, "self.short_entry_price")

                self.df.iloc[index, self.df.columns.get_loc("Position")] = -1
                if index + 1 == len(self.df):
                    self.df.iloc[index, self.df.columns.get_loc("Position")] = 0
                else:
                    # for pct change it does a ffilll. ffill with zeros
                    self.df.iloc[index + 1, self.df.columns.get_loc("Position")] = 0
                self._determine_win_or_loss_amount(row)
                # record keeping
                self.df.iloc[
                    index, self.df.columns.get_loc("Mode")
                ] = "short_to_no_position"
                self.mode = "no_position"
                short_has_crossed_mean = False

            # buy -> no_position? no position is below running mean
            # or, if we are above the top band (mean reversion)
            elif self.mode == "buy" and (
                (row["close"] < row["Rolling Mean"] and self.buy_has_crossed_mean)
                or (row["close"] > row["Bollinger High"])
                or (row["close"] < row["Bollinger Low"])
                or (row["Rolling Mean"] < self.buy_entry_price)
            ):
                self._check_buy_to_no_position(index, row)

            # short -> no_position? no position if above running mean
            # or, if we are below the bottom band (mean reversion)
            elif self.mode == "short" and (
                (row["close"] > row["Rolling Mean"] and self.short_has_crossed_mean)
                or (row["close"] < row["Bollinger Low"])
                or (row["close"] > row["Bollinger High"])
                or row["Rolling Mean"] > self.short_entry_price
            ):
                self._check_short_to_no_position(index, row)

            # buy check with ML model
            elif (
                self.mode == "no_position"
                and row["close"] < row["Bollinger Low"]
                and prev_row["close"] > prev_row["Bollinger Low"]
            ):
                self._check_if_we_should_buy(index, row)

            # short?
            elif (
                self.mode == "no_position"
                and row["close"] > row["Bollinger High"]
                and prev_row["close"] < prev_row["Bollinger High"]
            ):
                self._check_if_we_should_short(index, row)

            else:
                self.df.iloc[index, self.df.columns.get_loc("Mode")] = self.mode

    def _determine_win_or_loss_amount(self, row):
        """
        For position we've exited, did we win? if so, by how much
        """
        # short s

        # stop loss for short
        if self.mode == "short" and self.short_entry_price < row["close"]:
            lost_amount = row["close"] - self.short_entry_price
            print(f"Lost {lost_amount} on this trade")

            self.win_and_lose_amount_dict["n_short_lost"] += 1
            self.win_and_lose_amount_dict["$_short_lost"] += lost_amount

        # made money
        elif self.mode == "short" and self.short_entry_price > row["close"]:

            win_amount = self.short_entry_price - row["close"]
            print(f"Won {win_amount} on this trade")
            self.win_and_lose_amount_dict["n_short_won"] += 1
            self.win_and_lose_amount_dict["$_short_won"] += win_amount
        # end short
        # buys

        # lost money
        elif self.mode == "buy" and self.buy_entry_price > row["close"]:

            lost_amount = self.buy_entry_price - row["close"]
            print(f"Lost {lost_amount} on this trade")
            self.win_and_lose_amount_dict["n_buy_lost"] += 1
            self.win_and_lose_amount_dict["$_buy_lost"] += lost_amount

        # made money
        elif self.mode == "buy" and self.buy_entry_price < row["close"]:

            won_amount = row["close"] - self.buy_entry_price
            print(f"Won {won_amount} on this trade")
            self.win_and_lose_amount_dict["n_buy_won"] += 1
            self.win_and_lose_amount_dict["$_buy_won"] += won_amount

        days_in_trade = row.name - self.position_entry_date
        print(days_in_trade.days, "days in trade")
        self.n_total_days_in_trades += days_in_trade.days

        # info logging

        print(
            f"Average days in trades = {self.n_total_days_in_trades/(self.win_and_lose_amount_dict['n_buy_won']  + self.win_and_lose_amount_dict['n_buy_lost'] + self.win_and_lose_amount_dict['n_short_won']  + self.win_and_lose_amount_dict['n_short_lost'] )}"
        )
        if (
            self.win_and_lose_amount_dict["n_buy_won"] > 0
            or self.win_and_lose_amount_dict["n_buy_lost"] > 0
        ):
            print(
                f"Bat rate buy so far = {self.win_and_lose_amount_dict['n_buy_won'] / (self.win_and_lose_amount_dict['n_buy_won'] + self.win_and_lose_amount_dict['n_buy_lost'])}"
            )
        if (
            self.win_and_lose_amount_dict["n_short_won"] > 0
            or self.win_and_lose_amount_dict["n_short_lost"] > 0
        ):
            print(
                f"Bat rate short so far = {self.win_and_lose_amount_dict['n_short_won'] / (self.win_and_lose_amount_dict['n_short_won'] + self.win_and_lose_amount_dict['n_short_lost'])}"
            )

        if (
            self.win_and_lose_amount_dict["$_buy_won"] > 0
            or self.win_and_lose_amount_dict["$_buy_lost"] > 0
        ):
            print(
                f"Win rate buy so far = {self.win_and_lose_amount_dict['$_buy_won'] / (self.win_and_lose_amount_dict['$_buy_won'] + self.win_and_lose_amount_dict['$_buy_lost'])}"
            )
        if (
            self.win_and_lose_amount_dict["$_short_won"] > 0
            or self.win_and_lose_amount_dict["$_short_lost"] > 0
        ):
            print(
                f"Win rate short so far = {self.win_and_lose_amount_dict['$_short_won'] / (self.win_and_lose_amount_dict['$_short_won'] + self.win_and_lose_amount_dict['$_short_lost'])}"
            )
        print(f"WIn / lost dict {self.win_and_lose_amount_dict}")

        print(f"Total days in trades = {self.n_total_days_in_trades }")

        # reset for sanity
        self.position_entry_date = None

    def _check_short_to_no_position(self, index, row):
        """
        While in a short position, check if we should exit
        """

        print("---------")
        print("checking if we should get out of our short position")
        print(row.name, "current date")
        print(row["Rolling Mean"], "mean")
        print(self.short_entry_price, "self.short_entry_price")
        print(row["close"], "current close")

        # check ML predicted trend as well
        try:
            ml_pred = self._check_ml_prediction(row.name)
        except ValueError:  # don't have enough data for ML prediction
            print("Ran into not enough data ValueError for short_to_no_position")
            return
        print(ml_pred, "ml_pred")
        if (
            (ml_pred > row["Rolling Mean"])
            or (ml_pred > self.short_entry_price)
            or (row["Rolling Mean"] > self.short_entry_price)
        ):
            print("short_to_no_position")
            self.df["ML_Future_Prediction"] = ml_pred

            self.df.iloc[index, self.df.columns.get_loc("Position")] = -1
            if index + 1 == len(self.df):
                self.df.iloc[index, self.df.columns.get_loc("Position")] = 0
            else:
                # for pct change it does a ffilll. ffill with zeros
                self.df.iloc[index + 1, self.df.columns.get_loc("Position")] = 0

            self._determine_win_or_loss_amount(row)
            # record keeping
            self.df.iloc[
                index, self.df.columns.get_loc("Mode")
            ] = "short_to_no_position"
            self.mode = "no_position"
            short_has_crossed_mean = False
        else:
            self.df.iloc[index, self.df.columns.get_loc("Mode")] = self.mode

    def _check_buy_to_no_position(self, index, row):
        """
        While in a buy/long position, check if we should exit
        """
        print("---------")
        print("checking if we should get out of our buy position")
        print(row.name, "current date")
        print(row["Rolling Mean"], "mean")
        print(self.buy_entry_price, "self.buy_entry_price")
        print(row["close"], "current close")

        # check ML predicted trend as well
        try:
            ml_pred = self._check_ml_prediction(row.name)
        except ValueError:  # don't have enough data for ML prediction
            print("Ran into not enough data ValueError for buy_to_no_position")
            return
        print(ml_pred, "ml_pred")

        if (
            (ml_pred < row["Rolling Mean"])
            or (ml_pred < self.buy_entry_price)
            or (row["Rolling Mean"] < self.buy_entry_price)
        ):
            print("buy_to_no_position")
            self.df["ML_Future_Prediction"] = ml_pred

            self.df.iloc[index, self.df.columns.get_loc("Position")] = 1

            if index + 1 == len(self.df):
                self.df.iloc[index, self.df.columns.get_loc("Position")] = 0
            else:
                # for pct change it does a ffilll. ffill with zeros
                self.df.iloc[index + 1, self.df.columns.get_loc("Position")] = 0

            self._determine_win_or_loss_amount(row)
            # record keeping
            self.df.iloc[index, self.df.columns.get_loc("Mode")] = "buy_to_no_position"
            self.mode = "no_position"
            self.buy_has_crossed_mean = False
        else:
            self.df.iloc[index, self.df.columns.get_loc("Mode")] = self.mode

    def _check_if_we_should_buy(self, index, row):
        """
        Determine if we should enter a buy position
        """
        start_time = time.time()
        print("----------")
        print("buy")
        print(row.name, "current date")
        print(row["close"], "close")
        # check ML predicted trend as well
        try:
            ml_pred = self._check_ml_prediction(row.name)
        except ValueError:  # don't have enough data for ML prediction
            print("Ran into not enough data ValueError for buy")
            self.df.iloc[index, self.df.columns.get_loc("Mode")] = self.mode
            return 9999999

        print(ml_pred, "ml prediction day")
        print(row["Rolling Mean"], "mean")

        if ml_pred > row["Rolling Mean"]:
            print(f"ml pred higher than mean taking position")
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
                self.df.iloc[index + 1, self.df.columns.get_loc("Position")] = 1
            self.df.iloc[index, self.df.columns.get_loc("Mode")] = "buy"
            self.number_of_trades += 1
            self.mode = "buy"
            self.buy_entry_price = row["close"]
            self.stop_loss_price = row["close"] * (1 - self.stop_loss_pct)
            self.position_entry_date = row.name
        else:
            self.df.iloc[index, self.df.columns.get_loc("Mode")] = self.mode

        end_time = time.time()
        print(f"Eval buy took {(end_time - start_time)/60} minutes")

    def _check_if_we_should_short(self, index, row):
        """
        Check if we should enter a short position
        """
        start_time = time.time()
        print("----------")
        print("short")
        print(row.name, "current date")
        print(row["close"], "close")
        # check ML predicted trend as well
        try:
            ml_pred = self._check_ml_prediction(row.name)
        except Exception as e:  # don't have enough data for ML prediction
            print("Ran into not enough data ValueError for short")
            print(e)
            self.df.iloc[index, self.df.columns.get_loc("Mode")] = self.mode
            return 0

        print(ml_pred, "ml pred day")
        print(row["Rolling Mean"], "mean")

        if ml_pred < row["Rolling Mean"]:
            print("pred 7 day lower than mean taking position")
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
                self.df.iloc[index + 1, self.df.columns.get_loc("Position")] = -1
            self.df.iloc[index, self.df.columns.get_loc("Mode")] = "short"
            self.number_of_trades += 1
            self.mode = "short"
            self.short_entry_price = row["close"]
            self.stop_loss_price = row["close"] * (1 + self.stop_loss_pct)
            self.position_entry_date = row.name
        else:
            self.df.iloc[index, self.df.columns.get_loc("Mode")] = self.mode

        end_time = time.time()
        print(f"Eval short took {(end_time - start_time)/60} minutes")

    def _build_bollinger_bands(self):
        rolling_mean = self.df["close"].rolling(self.window).mean()
        rolling_std = self.df["close"].rolling(self.window).std()

        self.df["Rolling Mean"] = rolling_mean
        self.df["Bollinger High"] = rolling_mean + (rolling_std * self.no_of_std)
        self.df["Bollinger Low"] = rolling_mean - (rolling_std * self.no_of_std)

        new_additional_dfs = []
        if len(self.additional_dfs) > 0:
            for df in self.additional_dfs:
                rolling_mean = df["close"].rolling(self.window).mean()
                rolling_std = df["close"].rolling(self.window).std()

                df["Rolling Mean"] = rolling_mean
                df["Bollinger High"] = rolling_mean + (rolling_std * self.no_of_std)
                df["Bollinger Low"] = rolling_mean - (rolling_std * self.no_of_std)

                new_additional_dfs.append(df)
        self.additional_dfs = new_additional_dfs

    def _load_model(model_name: str, ml_constants: Dict[Dict[str, Any]]):

        if "nbeats" in model_name.lower():
            NBEATSModel(
                input_chunk_length=ml_constants["prediction_params"]["lookback_window"],
                output_chunk_length=ml_constants["prediction_params"][
                    "lookback_window"
                ],
                random_state=0,
                model_name=ml_constants["hyperparamters_nbeats"]["model_name"],
                num_blocks=ml_constants["hyperparamters_nbeats"]["num_blocks"],
                layer_widths=ml_constants["hyperparamters_nbeats"]["layer_widths"],
                force_reset=True,
                log_tensorboard=True,
            )
        elif "tcn" in model_name.lower():
            TCNModel(
                dropout=0.1,
                random_state=0,
                dilation_base=2,
                weight_norm=True,
                kernel_size=3,
                num_filters=6,
                num_layers=6,
                input_chunk_length=lookback_window,
                output_chunk_length=self.ml_prediction_n_days,
                model_name=str(lookback_window) + "_tcn",
                force_reset=True,
                log_tensorboard=True,
            )

        return

    def simulate(self):
        self._build_bollinger_bands()
        self._load_model()

        self._calculate_positions()
        self.end_time = time.time()

        print(f" Minutes taken = {(self.end_time - self.start_time)/60}")

        return (
            self.period,
            self.window,
            self.no_of_std,
            self.df["Strategy Return"].sum(),
            self.number_of_trades,
        )


def main():
    constants = read_in_constants("app/constants.yml")
    bitcoin_df = read_in_data(constants["bitcoin_filename"])
    etherum_df = read_in_data(constants["etherum_filename"])

    ml_constants = read_in_constants("app/ml_config.yml")

    # BollingerBandsPredictor(

    # )

    # simulator = BollingerBandsSimulator(
    #     etherum_df,
    #     from_date="2019-1-01",
    #     period="24H",
    #     window=14,
    #     no_of_std=1.25,
    #     ml_lookback_windows=[31],
    #     ml_prediction_n_days=30,
    #     additional_dfs = [bitcoin_df],
    #     stop_loss_pct=.10,
    #     model_name=["TCN", "NBEATS"]
    # )
    # simulator.simulate()

    return


if __name__ == "__main__":
    main()
