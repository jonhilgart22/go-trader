#!/usr/bin/env python
import os
import sys
from threading import Thread
from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd
from darts import TimeSeries
from darts.dataprocessing.transformers import Scaler
from darts.models import NBEATSModel, TCNModel
from darts.utils.missing_values import fill_missing_values
from darts.utils.timeseries_generation import datetime_attribute_timeseries
from finta import TA
try:  # need modules for pytest to work
    from app.mlcode.utils import setup_logging
except ModuleNotFoundError:  # Go is unable to run python modules -m
    from utils import setup_logging


__all__ = ["BollingerBandsPredictor"]

logger = setup_logging()


class BollingerBandsPredictor:
    def __init__(
        self,
        coin_to_predict: str,
        constants: Dict[str, Dict[str, any]],
        ml_constants: Dict[str, Dict[str, any]],
        input_df: pd.DataFrame,
        additional_dfs: List[pd.DataFrame] = [],
        period: str = "24H",
        verbose: bool = True,
    ):
        self.n_years_filter = "3Y"  # use last 3 years of data

        self.coin_to_predict = coin_to_predict
        self.constants: Dict[str, Dict[str, Any]] = constants
        self.ml_constants: Dict[str, Dict[str, Any]] = ml_constants
        self.window = self.ml_constants["prediction_params"]["bollinger_window"]
        self.no_of_std = self.ml_constants["prediction_params"]["no_of_std"]
        self.df = input_df
        self.additional_dfs = additional_dfs
        self.period = period
        self.verbose = verbose
        # TODO: remember to add new columns here
        self.ml_train_cols = [
            self.constants["open_col"],
            self.constants["high_col"],
            self.constants["low_col"],
            self.constants["rolling_mean_col"],
            self.constants["volume_col"],
            self.constants["macd_col"],
            self.constants["macd_signal_col"],
            self.constants["stc_col"],
            self.constants["stoch_col"],
            self.constants["rsi_col"],
        ]
        self.pred_col = self.constants["close_col"]

        if type(self.ml_constants["prediction_params"]["lookback_window"]) != list:
            raise ValueError("Need to enter a list for loockback_window")

        self.models = []  # store models here

    def _create_models(self, load_model: bool = False):

        if self.coin_to_predict.lower() == "btc":
            tcn_model_name = self.constants["tcn_modelname_btc"]
            tcn_filename = self.constants["tcn_filename_btc"]
            nbeats_model_name = self.constants["nbeats_modelname_btc"]
            nbeats_filename = self.constants["nbeats_filename_btc"]
        elif self.coin_to_predict.lower() == "eth":
            tcn_model_name = self.constants["tcn_modelname_eth"]
            tcn_filename = self.constants["tcn_filename_eth"]
            nbeats_model_name = self.constants["nbeats_modelname_eth"]
            nbeats_filename = self.constants["nbeats_filename_eth"]
        elif self.coin_to_predict.lower() == "sol":
            tcn_model_name = self.constants["tcn_modelname_sol"]
            tcn_filename = self.constants["tcn_filename_sol"]
            nbeats_model_name = self.constants["nbeats_modelname_sol"]
            nbeats_filename = self.constants["nbeats_filename_sol"]

        else:
            raise ValueError(f"Incorrect model token to predict given {self. coin_to_predict}")
        logger.info("------")
        logger.info(f"Creating models for coin {self.coin_to_predict}")

        for lookback_window in self.ml_constants["prediction_params"]["lookback_window"]:

            logger.info(f"Creating model lookback = {lookback_window}_{nbeats_model_name},{nbeats_filename}")
            if "ON_LOCAL" in os.environ:
                work_dir = "./"
            else:
                work_dir = self.ml_constants["prediction_params"]["work_dir"]

            nbeats_model = NBEATSModel(
                input_chunk_length=lookback_window,
                output_chunk_length=self.ml_constants["prediction_params"]["prediction_n_days"],
                random_state=0,
                model_name=nbeats_model_name + f"_lookback_{lookback_window}",
                num_blocks=self.ml_constants["hyperparameters_nbeats"]["num_blocks"],
                layer_widths=self.ml_constants["hyperparameters_nbeats"]["layer_widths"],
                force_reset=True,
                log_tensorboard=False,
                work_dir=work_dir,
            )
            if load_model:
                self.nbeats_model.load_from_checkpoint(
                    model_name=nbeats_model_name,
                    filename=nbeats_filename,
                    work_dir=self.constants["ml_models_dir"],
                    best=False,
                )

                logger.info(f"Loading model {tcn_model_name}, {tcn_filename}")

            logger.info(f"Creating model {tcn_model_name},{tcn_filename}")

            tcn_model = TCNModel(
                dropout=self.ml_constants["hyperparameters_tcn"]["dropout"],
                random_state=0,
                dilation_base=self.ml_constants["hyperparameters_tcn"]["dilation_base"],
                weight_norm=self.ml_constants["hyperparameters_tcn"]["weight_norm"],
                kernel_size=self.ml_constants["hyperparameters_tcn"]["kernel_size"],
                num_filters=self.ml_constants["hyperparameters_tcn"]["num_filters"],
                num_layers=self.ml_constants["hyperparameters_tcn"]["num_layers"],
                input_chunk_length=lookback_window,
                output_chunk_length=self.ml_constants["prediction_params"]["prediction_n_days"],
                model_name=tcn_model_name + f"_lookback_{lookback_window}",
                force_reset=True,
                log_tensorboard=False,
                work_dir=work_dir,
            )
            # This works
            if load_model:
                self.tcn_model.load_from_checkpoint(
                    model_name=tcn_model_name,
                    work_dir=self.constants["ml_models_dir"],
                    filename=tcn_filename,
                    best=False,
                )
            logger.info("---- Finished creating models ----")
            self.models.append([nbeats_model, tcn_model])

    def _add_indicators(self, input_df: pd.DataFrame) -> pd.DataFrame:

        input_df[self.constants["stc_col"]] = TA.STC(input_df)
        input_df[self.constants["stoch_col"]] = TA.STOCH(input_df)
        input_df[self.constants["rsi_col"]] = TA.RSI(input_df, period=self.window)
        macd_df = TA.MACD(input_df)
        input_df[self.constants["macd_col"]] = macd_df["MACD"]
        input_df[self.constants["macd_signal_col"]] = macd_df["SIGNAL"]

        return input_df.fillna(0)

    def _slice_df(self):
        # some dataframes don't have enough data a full lookback window
        slice_date = self.df.index.min()
        logger.info(f"Slice date , earliest day of data for main df, = {slice_date}")

        self.df = self.df.loc[slice_date:, :].copy()

        sliced_additional_dfs = []
        if len(self.additional_dfs) > 0:
            for add_df in self.additional_dfs:
                sliced_df = add_df.loc[slice_date:, :].copy()
                sliced_additional_dfs.append(sliced_df)

        self.additional_dfs = sliced_additional_dfs

    def _build_technical_indicators(self):

        rolling_mean = self.df[self.pred_col].rolling(self.window).mean()
        rolling_std = self.df[self.pred_col].rolling(self.window).std()

        self.df[self.constants["rolling_mean_col"]] = rolling_mean
        self.df[self.constants["bollinger_high_col"]] = rolling_mean + (rolling_std * self.no_of_std)
        self.df[self.constants["bollinger_low_col"]] = rolling_mean - (rolling_std * self.no_of_std)
        logger.info("---- Adding Bollinger Bands ----")
        logger.info(self.df.tail())

        # add rsi
        self.df = self._add_indicators(self.df)

        new_additional_dfs = []
        if len(self.additional_dfs) > 0:
            for df in self.additional_dfs:
                rolling_mean = df[self.pred_col].rolling(self.window).mean()
                rolling_std = df[self.pred_col].rolling(self.window).std()

                df[self.constants["rolling_mean_col"]] = rolling_mean
                df[self.constants["bollinger_high_col"]] = rolling_mean + (rolling_std * self.no_of_std)
                df[self.constants["bollinger_low_col"]] = rolling_mean - (rolling_std * self.no_of_std)
                # add rsi
                df = self._add_indicators(df)

                df = df.last(self.n_years_filter)
                new_additional_dfs.append(df)
                logger.info(df.tail())
        self.additional_dfs = new_additional_dfs
        # slice to only include last X years
        self.df = self.df.last(self.n_years_filter)

    def _scale_time_series_df_and_time_cols(
        self, input_df: pd.DataFrame, time_cols: List[str] = ["year", "month", "day"]
    ):
        ts_transformers = {}
        ts_stacked_series = None
        ts_transformers, ts_stacked_series = self._scale_time_series_df(input_df)

        # build year and month and day series:
        for col in time_cols:
            transformer = Scaler()
            transformed_series = transformer.fit_transform(
                fill_missing_values(datetime_attribute_timeseries(ts_stacked_series, attribute=col))
            )
            ts_transformers[col] = transformer

            ts_stacked_series = ts_stacked_series.stack(transformed_series)

        return (ts_transformers, ts_stacked_series, TimeSeries.from_series(input_df[self.pred_col], freq=self.period))

    def _scale_time_series_df(self, input_df: pd.DataFrame, use_pred_col: bool = False):
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
                fill_missing_values(TimeSeries.from_series(input_df[col], freq=self.period))
            )
            ts_transformers[col] = transformer

            if ts_stacked_series:
                ts_stacked_series = ts_stacked_series.stack(transformed_series)

            else:
                ts_stacked_series = transformed_series
        return ts_transformers, ts_stacked_series

    def _add_additional_training_dfs(self, ts_stacked_series: TimeSeries, verbose=False):
        """
        Scale any additional DFs provided (such as ETHER)

        ts_stacked_series: the current scaled lists from the df_original provided
        """
        all_ts_stacked_series = None
        all_ts_transfomers = []
        for df in self.additional_dfs:
            (additional_ts_transformers, additional_ts_stacked_series) = self._scale_time_series_df(
                df, use_pred_col=True
            )
            if all_ts_stacked_series is None:
                if verbose:
                    print("last date for training additional df data", additional_ts_stacked_series.time_index[-1])
                all_ts_stacked_series = additional_ts_stacked_series.stack(ts_stacked_series)
                if verbose:
                    print("all_ts_stacked_series FIRST", all_ts_stacked_series.components)
                all_ts_transfomers.append(additional_ts_transformers)
            else:
                all_ts_stacked_series = all_ts_stacked_series.stack(additional_ts_stacked_series)
                if verbose:
                    print("all_ts_stacked_series SECOND", all_ts_stacked_series.components)
                all_ts_transfomers.append(additional_ts_transformers)
                # return "Error. More than one time series for _add_additional_training_dfs not implemented"
        return additional_ts_transformers, all_ts_stacked_series

    def _convert_data_to_timeseries(self) -> Tuple[TimeSeries, TimeSeries]:
        # combine TS from both DFs
        (ts_transformers, ts_stacked_series, train_close_series) = self._scale_time_series_df_and_time_cols(self.df)
        if self.verbose:
            logger.info(f"original DF training series = {ts_stacked_series.components}")
            logger.info(f"last date for training data = {ts_stacked_series.time_index[-1]}")

        if len(self.additional_dfs) > 0:
            # overwrite the ts_stacked_series var if we have additional DFS
            (additional_ts_transformers, ts_stacked_series) = self._add_additional_training_dfs(ts_stacked_series)
            ts_transformers = {**additional_ts_transformers, **ts_transformers}  # merge dicts
        self.ts_transformers = ts_transformers
        self.ts_stacked_series = ts_stacked_series
        self.train_close_series = train_close_series

        if self.verbose:
            logger.info(f"all series now stacked = {ts_stacked_series.components}")

        return train_close_series, ts_stacked_series

    def _train_model_with_thread(self, model, train_close_series, ts_stacked_series, epochs):
        # Target function for training within threads
        model.fit(series=train_close_series, past_covariates=[ts_stacked_series], verbose=self.verbose, epochs=epochs)

    def _train_models(self, train_close_series, ts_stacked_series):
        dict_of_threads = {}

        for lookback_window_models in self.models:  # lookback windows
            for model in lookback_window_models:
                if "nbeats" in model.model_name:
                    dict_of_threads[str(lookback_window_models) + "_nbeats"] = Thread(
                        target=self._train_model_with_thread,
                        args=(
                            model,
                            train_close_series,
                            ts_stacked_series,
                            self.ml_constants["hyperparameters_nbeats"]["epochs"],
                        ),
                    )

                    logger.info("Training nbeats")
                    sys.stdout.flush()

                    dict_of_threads[str(lookback_window_models) + "_nbeats"].start()

                elif "tcn" in model.model_name:
                    logger.info("Training TCN")
                    sys.stdout.flush()
                    dict_of_threads[str(lookback_window_models) + "_tcn"] = Thread(
                        target=self._train_model_with_thread,
                        args=(
                            model,
                            train_close_series,
                            ts_stacked_series,
                            self.ml_constants["hyperparameters_nbeats"]["epochs"],
                        ),
                    )

                    logger.info("Training nbeats")
                    sys.stdout.flush()

                    dict_of_threads[str(lookback_window_models) + "_tcn"].start()

                else:
                    raise ValueError(f"We hdave an incorrect model name of {model.model_name} we need tcn or nbeats")
        # block until all models are trained
        for k, v in dict_of_threads.items():
            logger.info(f"Have thread = {k}")
            v.join()

    def _make_prediction(self, train_close_series, ts_stacked_series):
        all_predictions = []

        for lookback_window_models in self.models:  # lookback windows
            for model in lookback_window_models:
                prediction = model.predict(
                    n=self.ml_constants["prediction_params"]["prediction_n_days"],
                    series=train_close_series,
                    past_covariates=[ts_stacked_series],
                ).last_value()  # grab the last value
                logger.info(
                    f" Model = { model.model_name} Lookback = {self.ml_constants['prediction_params']['prediction_n_days']} Prediction = {prediction}"
                )
                all_predictions.append(prediction)
        self.all_predictions = all_predictions

        return np.mean(all_predictions)

    def predict(self) -> float:
        logger.info("Slicing dataframes")
        self._slice_df()
        logger.info("Building Bollinger Bands")
        sys.stdout.flush()
        self._build_technical_indicators()
        logger.info("Creating Models")
        sys.stdout.flush()
        # turns out, it's better to create new models than retrain old ones
        self._create_models()

        logger.info("Converting data to timeseries")
        sys.stdout.flush()
        train_close_series, ts_stacked_series = self._convert_data_to_timeseries()
        logger.info("Training models")
        sys.stdout.flush()
        self._train_models(train_close_series, ts_stacked_series)
        logger.info("making predictions")
        sys.stdout.flush()
        prediction = self._make_prediction(train_close_series, ts_stacked_series)
        logger.info(f"prediction = {prediction}")
        sys.stdout.flush()
        return prediction
