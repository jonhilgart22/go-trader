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
import os

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
    print("----------")
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
        constants: Dict[str, Dict[str, any]],
        ml_constants: Dict[str, Dict[str, any]],
        input_df: pd.DataFrame,
        additional_dfs: List[pd.DataFrame] = None,
    ):
        self.constants: Dict[str, Dict[str, Any]] = constants
        self.ml_constants: Dict[str, Dict[str, Any]] = ml_constants
        self.window = self.ml_constants["prediction_params"]["bollinger_window"]
        self.no_of_std = self.ml_constants["prediction_params"]["no_of_std"]
        self.df = input_df
        self.additional_dfs = additional_dfs

    def _load_models(self):
        # print(
        #     f"Loading model {self.ml_constants['hyperparameters_nbeats']['model_name_etherum']}")
        # self.nbeats_model_eth = NBEATSModel(
        #     input_chunk_length=self.ml_constants["prediction_params"]["lookback_window"],
        #     output_chunk_length=self.ml_constants["prediction_params"]["prediction_n_days"],
        #     random_state=0,
        #     model_name=self.ml_constants["hyperparameters_nbeats"]["model_name_etherum"],
        #     num_blocks=self.ml_constants["hyperparameters_nbeats"]["num_blocks"],
        #     layer_widths=self.ml_constants["hyperparameters_nbeats"]["layer_widths"],
        #     force_reset=True,
        #     log_tensorboard=True,
        # )
        # self.nbeats_model_eth.load_from_checkpoint(
        #     model_name=self.ml_constants["hyperparameters_nbeats"]["model_name_etherum"],
        #     work_dir=self.ml_constants["prediction_params"]["ml_models_dir"],
        #     best=False)
        # # filename=os.path.join(
        # #     "models", self.ml_constants["hyperparameters_nbeats"]["model_name_etherum"]), best=False)
        # ##
        # print(
        #     f"Loading model {self.ml_constants['hyperparameters_nbeats']['model_name_bitcoin']}")
        # self.nbeats_model_btc = NBEATSModel(
        #     input_chunk_length=self.ml_constants["prediction_params"]["lookback_window"],
        #     output_chunk_length=self.ml_constants["prediction_params"]["prediction_n_days"],
        #     random_state=0,
        #     model_name=self.ml_constants["hyperparameters_nbeats"]["model_name_bitcoin"],
        #     num_blocks=self.ml_constants["hyperparameters_nbeats"]["num_blocks"],
        #     layer_widths=self.ml_constants["hyperparameters_nbeats"]["layer_widths"],
        #     force_reset=True,
        #     log_tensorboard=True,
        # )
        print(
            f"Loading model {self.constants['tcn_modelname_eth']}")

        self.tcn_model_eth = TCNModel(
            dropout=self.ml_constants["hyperparameters_tcn"]["dropout"],
            random_state=0,
            dilation_base=self.ml_constants["hyperparameters_tcn"]["dilation_base"],
            weight_norm=self.ml_constants["hyperparameters_tcn"]["weight_norm"],
            kernel_size=self.ml_constants["hyperparameters_tcn"]["kernel_size"],
            num_filters=self.ml_constants["hyperparameters_tcn"]["num_filters"],
            num_layers=self.ml_constants["hyperparameters_tcn"]["num_layers"],
            input_chunk_length=self.ml_constants["prediction_params"]["lookback_window"],
            output_chunk_length=self.ml_constants["prediction_params"]["prediction_n_days"],
            model_name=self.constants["tcn_modelname_eth"],
            force_reset=True,
            log_tensorboard=True,
        )
        # This works
        self.tcn_model_eth.load_from_checkpoint(
            model_name=self.constants[
                "tcn_modelname_eth"],
            work_dir=self.constants["ml_models_dir"],
            filename=self.constants[
                "tcn_filename_eth"],
            best=False)

        print(
            f"Loading model {self.constants['hyperparameters_tcn']['model_name_bitcoin']}")

        self.tcn_model_btc = TCNModel(
            dropout=self.ml_constants["hyperparameters_tcn"]["dropout"],
            random_state=0,
            dilation_base=self.ml_constants["hyperparameters_tcn"]["dilation_base"],
            weight_norm=self.ml_constants["hyperparameters_tcn"]["weight_norm"],
            kernel_size=self.ml_constants["hyperparameters_tcn"]["kernel_size"],
            num_filters=self.ml_constants["hyperparameters_tcn"]["num_filters"],
            num_layers=self.ml_constants["hyperparameters_tcn"]["num_layers"],
            input_chunk_length=self.ml_constants["prediction_params"]["lookback_window"],
            output_chunk_length=self.ml_constants["prediction_params"]["prediction_n_days"],
            model_name=self.ml_constants["hyperparameters_tcn"]["model_name_bitcoin"],
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
        print("---- Adding Bollinger Bands ----")
        print(self.df.tail())

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
                print(df.tail())
        self.additional_dfs = new_additional_dfs

    def predict(self):
        self._build_bollinger_bands()
        self._load_models()
        # todo
        # self._train_model()
        # self._make_predictions()
        # self._update_state()


def main():
    constants = read_in_constants("app/constants.yml")
    # data should already be downloaded from the golang app
    bitcoin_df = read_in_data(constants["bitcoin_csv_filename"])
    etherum_df = read_in_data(constants["etherum_csv_filename"])
    ml_constants = read_in_constants("app/ml_config.yml")
    btc_predictor = BollingerBandsPredictor(
        constants,  ml_constants, bitcoin_df, additional_dfs=[etherum_df]
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
