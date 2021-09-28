#!/usr/bin/env python
import logging
import os
import sys
import time
import warnings
from datetime import datetime, timedelta
from math import sqrt
from time import time
from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.optim as optim
import yaml
from darts import TimeSeries
from darts.dataprocessing.transformers import Scaler
from darts.metrics import mape, mse
from darts.models import NBEATSModel, TCNModel
from darts.utils.missing_values import fill_missing_values
from darts.utils.timeseries_generation import datetime_attribute_timeseries

from utils import read_in_constants, read_in_data

warnings.filterwarnings("ignore")

__all__ = ["generate_predictions"]

logger = logging.getLogger(__name__)


class BollingerBandsPredictor:
    def __init__(
        self,
        coin_to_predict: str,
        constants: Dict[str, Dict[str, any]],
        ml_constants: Dict[str, Dict[str, any]],
        input_df: pd.DataFrame,
        additional_dfs: List[pd.DataFrame] = None,
        period="24H",
        verbose=True,
    ):
        self.coin_to_predict = coin_to_predict
        self.constants: Dict[str, Dict[str, Any]] = constants
        self.ml_constants: Dict[str, Dict[str, Any]] = ml_constants
        self.window = self.ml_constants["prediction_params"]["bollinger_window"]
        self.no_of_std = self.ml_constants["prediction_params"]["no_of_std"]
        self.df = input_df
        self.additional_dfs = additional_dfs
        self.period = period
        self.verbose = verbose

        self.ml_train_cols = ["open", "high", "low", "Rolling Mean", "volume"]
        self.pred_col = "close"

    def _create_models(self, load_model: bool = False):

        if self.coin_to_predict.lower() == "bitcoin":
            tcn_model_name = self.constants["tcn_modelname_btc"]
            tcn_filename = self.constants["tcn_filename_btc"]
            nbeats_model_name = self.constants["nbeats_modelname_btc"]
            nbeats_filename = self.constants["nbeats_filename_btc"]
        elif self.coin_to_predict.lower() == "etherum":
            tcn_model_name = self.constants["tcn_modelname_eth"]
            tcn_filename = self.constants["tcn_filename_eth"]
            nbeats_model_name = self.constants["nbeats_modelname_eth"]
            nbeats_filename = self.constants["nbeats_filename_eth"]
        else:
            raise ValueError(
                f"Incorrect model token to predict given {self. coin_to_predict}"
            )
        logger.info("------")
        logger.info(f"Creating models for coin {self.coin_to_predict}")

        logger.info(f"Creating model {nbeats_model_name},{nbeats_filename}")

        self.nbeats_model = NBEATSModel(
            input_chunk_length=self.ml_constants["prediction_params"][
                "lookback_window"
            ],
            output_chunk_length=self.ml_constants["prediction_params"][
                "prediction_n_days"
            ],
            random_state=0,
            model_name=nbeats_model_name,
            num_blocks=self.ml_constants["hyperparameters_nbeats"]["num_blocks"],
            layer_widths=self.ml_constants["hyperparameters_nbeats"]["layer_widths"],
            force_reset=True,
            log_tensorboard=True,
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

        self.tcn_model = TCNModel(
            dropout=self.ml_constants["hyperparameters_tcn"]["dropout"],
            random_state=0,
            dilation_base=self.ml_constants["hyperparameters_tcn"]["dilation_base"],
            weight_norm=self.ml_constants["hyperparameters_tcn"]["weight_norm"],
            kernel_size=self.ml_constants["hyperparameters_tcn"]["kernel_size"],
            num_filters=self.ml_constants["hyperparameters_tcn"]["num_filters"],
            num_layers=self.ml_constants["hyperparameters_tcn"]["num_layers"],
            input_chunk_length=self.ml_constants["prediction_params"][
                "lookback_window"
            ],
            output_chunk_length=self.ml_constants["prediction_params"][
                "prediction_n_days"
            ],
            model_name=tcn_model_name,
            force_reset=True,
            log_tensorboard=True,
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

    def _build_bollinger_bands(self):

        rolling_mean = self.df["close"].rolling(self.window).mean()
        rolling_std = self.df["close"].rolling(self.window).std()

        self.df["Rolling Mean"] = rolling_mean
        self.df["Bollinger High"] = rolling_mean + \
            (rolling_std * self.no_of_std)
        self.df["Bollinger Low"] = rolling_mean - \
            (rolling_std * self.no_of_std)
        logger.info("---- Adding Bollinger Bands ----")
        logger.info(self.df.tail())

        new_additional_dfs = []
        if len(self.additional_dfs) > 0:
            for df in self.additional_dfs:
                rolling_mean = df["close"].rolling(self.window).mean()
                rolling_std = df["close"].rolling(self.window).std()

                df["Rolling Mean"] = rolling_mean
                df["Bollinger High"] = rolling_mean + \
                    (rolling_std * self.no_of_std)
                df["Bollinger Low"] = rolling_mean - \
                    (rolling_std * self.no_of_std)

                new_additional_dfs.append(df)
                logger.info(df.tail())
        self.additional_dfs = new_additional_dfs

    def _scale_time_series_df_and_time_cols(
        self, input_df, time_cols=["year", "month", "day"]
    ):
        ts_transformers = {}
        ts_stacked_series = None
        ts_transformers, ts_stacked_series = self._scale_time_series_df(
            input_df)

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

    def _add_additional_training_dfs(self, ts_stacked_series):
        """
        Scale any additional DFs provided (such as ETHER)

        ts_stacked_series: the current scaled lists from the df_original provided

        """
        all_ts_stacked_series = None
        for df in self.additional_dfs:
            additional_ts_transformers, additional_ts_stacked_series = self._scale_time_series_df(
                df, use_pred_col=True
            )
            if all_ts_stacked_series is None:
                if self.verbose:
                    logger.info(
                        "last date for training additional df data")
                    logger.info((additional_ts_stacked_series.time_index[-1]),
                                )
                all_ts_stacked_series = additional_ts_stacked_series
            else:
                return "Error. More than one time series for _add_additional_training_dfs not implemented"
        return (
            additional_ts_transformers,
            all_ts_stacked_series.stack(ts_stacked_series),
        )

    def _convert_data_to_timeseries(self) -> Tuple[TimeSeries, TimeSeries]:
        # combine TS from both DFs
        ts_transformers, ts_stacked_series, train_close_series = self._scale_time_series_df_and_time_cols(
            self.df
        )
        if self.verbose:
            logger.info("original DF training series")
            logger.info(ts_stacked_series.components)
            logger.info("last date for training data")
            logger.info(ts_stacked_series.time_index[-1])

        if len(self.additional_dfs) > 0:
            # overwrite the ts_stacked_series var if we have additional DFS
            additional_ts_transformers, ts_stacked_series = self._add_additional_training_dfs(
                ts_stacked_series
            )
            ts_transformers = {
                **additional_ts_transformers,
                **ts_transformers,
            }  # merge dicts
        self.ts_transformers = ts_transformers

        if self.verbose:
            logger.info("all series now stacked")
            logger.info(ts_stacked_series.components)

        return train_close_series, ts_stacked_series

    def _train_models(self, train_close_series, ts_stacked_series):

        self.nbeats_model.fit(
            series=train_close_series,
            past_covariates=[ts_stacked_series],
            verbose=self.verbose,
            epochs=self.ml_constants["hyperparameters_nbeats"]["epochs"],
        )
        self.tcn_model.fit(
            series=train_close_series,
            past_covariates=[ts_stacked_series],
            verbose=self.verbose,
            epochs=self.ml_constants["hyperparameters_tcn"]["epochs"],
        )

    def _make_prediction(self, train_close_series, ts_stacked_series):
        nbeats_prediction = self.nbeats_model.predict(
            n=self.ml_constants["prediction_params"]["prediction_n_days"],
            series=train_close_series,
            past_covariates=[ts_stacked_series],
        ).last_value()  # grab the last value
        logger.info(
            f" Model = { self.nbeats_model.model_name} Lookback = {self.ml_constants['prediction_params']['prediction_n_days']} Prediction = {nbeats_prediction}"
        )
        tcn_prediction = self.tcn_model.predict(
            n=self.ml_constants["prediction_params"]["prediction_n_days"],
            series=train_close_series,
            past_covariates=[ts_stacked_series],
        ).last_value()  # grab the last value
        logger.info(
            f" Model = { self.tcn_model.model_name} Lookback = {self.ml_constants['prediction_params']['prediction_n_days']} Prediction = {tcn_prediction}"
        )

        return np.mean([tcn_prediction, nbeats_prediction])

    def predict(self):
        logger.info("Building Bollinger Bands")
        sys.stdout.flush()
        self._build_bollinger_bands()
        logger.info("Creating Models")
        sys.stdout.flush()
        # turns out, it's better to create new models than retrain old ones
        self._create_models()
        # TODO
        logger.info("Converting data to timeseries")
        sys.stdout.flush()
        train_close_series, ts_stacked_series = self._convert_data_to_timeseries()
        logger.info("Training models")
        sys.stdout.flush()
        self._train_models(train_close_series, ts_stacked_series)
        logger.info("making predictions")
        sys.stdout.flush()
        prediction = self._make_prediction(
            train_close_series, ts_stacked_series)
        logger.info("prediction")
        logger.info(prediction)
        sys.stdout.flush()
        # self._update_state()


# if __name__ == "__main__":
    # constants = read_in_constants("app/constants.yml")
    # # data should already be downloaded from the golang app
    # bitcoin_df = read_in_data(constants["bitcoin_csv_filename"])
    # etherum_df = read_in_data(constants["etherum_csv_filename"])
    # ml_constants = read_in_constants("app/ml_config.yml")
    # btc_predictor = BollingerBandsPredictor(
    #     "bitcoin", constants, ml_constants, bitcoin_df, additional_dfs=[etherum_df]
    # )

    # logger.info(btc_predictor.predict(), 'price prediction')
