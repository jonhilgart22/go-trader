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


def _read_in_constants(input_file: str):
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


def _read_in_data(input_file: str) -> pd.DataFrame:
    print(f"Input file {input_file}")
    df = pd.read_csv(input_file, index_col=0, parse_dates=True)
    print(df.head())
    print(df.tail())
    print("---")
    return df


class BollingerBandsPredictor:
    def __init__(
        self,
        constants: Dict[Dict[str, any]],
        input_df: pd.Dataframe,
        additional_dfs: List[pd.DataFrame] = None,
    ):
        self.constants = constants
        self.df = input_df
        self.additional_dfs = additional_dfs

    def _load_model(self, ml_constants: Dict[Dict[str, Any]]):
        self.nbeats_model_eth = NBEATSModel(
            input_chunk_length=ml_constants["prediction_params"]["lookback_window"],
            output_chunk_length=ml_constants["prediction_params"]["lookback_window"],
            random_state=0,
            model_name=ml_constants["hyperparamters_nbeats"]["model_name_etherum"],
            num_blocks=ml_constants["hyperparamters_nbeats"]["num_blocks"],
            layer_widths=ml_constants["hyperparamters_nbeats"]["layer_widths"],
            force_reset=True,
            log_tensorboard=True,
        )
        self.nbeats_model_btc = NBEATSModel(
            input_chunk_length=ml_constants["prediction_params"]["lookback_window"],
            output_chunk_length=ml_constants["prediction_params"]["lookback_window"],
            random_state=0,
            model_name=ml_constants["hyperparamters_nbeats"]["model_name_bitcoin"],
            num_blocks=ml_constants["hyperparamters_nbeats"]["num_blocks"],
            layer_widths=ml_constants["hyperparamters_nbeats"]["layer_widths"],
            force_reset=True,
            log_tensorboard=True,
        )

        self.tcn_model_eth = TCNModel(
            dropout=ml_constants["hyperparamters_tcn"]["dropout"],
            random_state=0,
            dilation_base=ml_constants["hyperparamters_tcn"]["dilation_base"],
            weight_norm=ml_constants["hyperparamters_tcn"]["weight_norm"],
            kernel_size=ml_constants["hyperparamters_tcn"]["kernel_size"],
            num_filters=ml_constants["hyperparamters_tcn"]["num_filters"],
            num_layers=ml_constants["hyperparamters_tcn"]["num_layers"],
            input_chunk_length=ml_constants["prediction_params"]["lookback_window"],
            output_chunk_length=ml_constants["prediction_params"]["lookback_window"],
            model_name=ml_constants["hyperparamters_tcn"]["model_name_etherum"],
            force_reset=True,
            log_tensorboard=True,
        )
        self.tcn_model_btc = TCNModel(
            dropout=ml_constants["hyperparamters_tcn"]["dropout"],
            random_state=0,
            dilation_base=ml_constants["hyperparamters_tcn"]["dilation_base"],
            weight_norm=ml_constants["hyperparamters_tcn"]["weight_norm"],
            kernel_size=ml_constants["hyperparamters_tcn"]["kernel_size"],
            num_filters=ml_constants["hyperparamters_tcn"]["num_filters"],
            num_layers=ml_constants["hyperparamters_tcn"]["num_layers"],
            input_chunk_length=ml_constants["prediction_params"]["lookback_window"],
            output_chunk_length=ml_constants["prediction_params"]["lookback_window"],
            model_name=ml_constants["hyperparamters_tcn"]["model_name_bitcoin"],
            force_reset=True,
            log_tensorboard=True,
        )

        def _build_bollinger_bands(self):

            rolling_mean = self.df["close"].rolling(self.window).mean()
            rolling_std = self.df["close"].rolling(self.window).std()

            self.df["Rolling Mean"] = rolling_mean
            self.df["Bollinger High"] = rolling_mean + \
                (rolling_std * self.no_of_std)
            self.df["Bollinger Low"] = rolling_mean - \
                (rolling_std * self.no_of_std)

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
        self.additional_dfs = new_additional_dfs

    def predict(self):
        self._build_bollinger_bands()
        self._load_model()
        self._train_model()
        self._make_predictions()
        self._update_state()


def main():
    constants = _read_in_constants("app/constants.yml")
    # data should already be downloaded from the golang app
    bitcoin_df = _read_in_data(constants["bitcoin_csv_filename"])
    etherum_df = _read_in_data(constants["etherum_csv_filename"])
    ml_constants = _read_in_constants("app/ml_config.yml")
    btc_predictor = BollingerBandsPredictor(
        constants, bitcoin_df, additional_dfs=[etherum_df]
    )

    btc_predictor.predict()

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
