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
from sklearn.ensemble import RandomForestRegressor

try:  # need modules for pytest to work
    from app.mlcode.base_predictions import BasePredictor
    from app.mlcode.utils import running_on_aws, setup_logging
except ModuleNotFoundError:  # Go is unable to run python modules -m
    from base_predictions import BasePredictor
    from utils import running_on_aws, setup_logging


__all__ = ["CoinPricePredictor"]

logger = setup_logging()


class CoinPricePredictor(BasePredictor):
    def __init__(
        self,
        coin_to_predict: str,
        constants: Dict[str, Any],
        ml_constants: Dict[str, Any],
        input_df: pd.DataFrame,
        all_predictions_filename: str,
        additional_dfs: List[pd.DataFrame] = [],
        period: str = "24H",
        verbose: bool = True,
        n_years_filter: int = 3,
        stacking_model_name: str = "RF",
    ):
        super().__init__()
        self.n_years_filer = n_years_filter

        self.coin_to_predict = coin_to_predict
        self.constants: Dict[str, Any] = constants
        self.ml_constants: Dict[str, Any] = ml_constants
        self.window = self.ml_constants["prediction_params"]["bollinger_window"]
        self.no_of_std = self.ml_constants["prediction_params"]["no_of_std"]
        self.df = input_df
        self.all_predictions_filename = all_predictions_filename
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
        self.date_col = self.constants["date_col"]

        if type(self.ml_constants["prediction_params"]["lookback_window"]) != list:
            raise ValueError("Need to enter a list for loockback_window")

        self.models: List[Any] = []  # store models here

        self.tcn_model = TCNModel
        self.nbeats_model = NBEATSModel
        self.stacking_model_name = stacking_model_name
        self.random_state = 432

    def _create_models(self, load_model: bool = False) -> None:
        # TODO: we should really convert self.additional_dfs into a dict so we can lookup the names of the addtional DFs we are using to predict against. Using the length is ok as long as we don't remove DFs. 🤷‍♂️

        nbeats_model_name: str = ""

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
        elif self.coin_to_predict.lower() == "matic":
            tcn_model_name = self.constants["tcn_modelname_matic"]
            tcn_filename = self.constants["tcn_filename_matic"]
            nbeats_model_name = self.constants["nbeats_modelname_matic"]
            nbeats_filename = self.constants["nbeats_filename_matic"]
        elif self.coin_to_predict.lower() == "link":
            tcn_model_name = self.constants["tcn_modelname_link"]
            tcn_filename = self.constants["tcn_filename_link"]
            nbeats_model_name = self.constants["nbeats_modelname_link"]
            nbeats_filename = self.constants["nbeats_filename_link"]

        else:
            raise ValueError(f"You haven't added the correct class vars for the coin {self.coin_to_predict}")
        logger.info("------")
        logger.info(f"Creating models for coin {self.coin_to_predict}")

        for lookback_window in self.ml_constants["prediction_params"]["lookback_window"]:
            MODEL_NAME_CONSTANT = f"_lookback_{lookback_window}_window_{self.window}_std_{self.no_of_std}_num_add_dfs_{len(self.additional_dfs)}"
            logger.info(f"len(self.additional_dfs) = {len(self.additional_dfs)}")
            logger.info(f"Creating model name = {MODEL_NAME_CONSTANT}")
            if "ON_LOCAL" in os.environ:
                work_dir = "./"
            else:
                work_dir = self.ml_constants["prediction_params"]["work_dir"]

            nbeats_model = NBEATSModel(
                input_chunk_length=lookback_window,
                output_chunk_length=self.ml_constants["prediction_params"]["prediction_n_days"],
                random_state=self.random_state,
                model_name=nbeats_model_name + MODEL_NAME_CONSTANT,
                num_blocks=self.ml_constants["hyperparameters_nbeats"]["num_blocks"],
                layer_widths=self.ml_constants["hyperparameters_nbeats"]["layer_widths"],
                force_reset=True,
                log_tensorboard=False,
                work_dir=work_dir,
                save_checkpoints=False,
            )
            if load_model:

                self.nbeats_model.load_from_checkpoint(
                    model_name=nbeats_model_name,
                    file_name=nbeats_filename,
                    work_dir=self.constants["ml_models_dir"],
                    best=False,
                )

                logger.info(f"Loading model {tcn_model_name}, {tcn_filename}")

            logger.info(f"Creating model {tcn_model_name},{tcn_filename}")

            tcn_model = TCNModel(
                dropout=self.ml_constants["hyperparameters_tcn"]["dropout"],
                random_state=self.random_state,
                dilation_base=self.ml_constants["hyperparameters_tcn"]["dilation_base"],
                weight_norm=self.ml_constants["hyperparameters_tcn"]["weight_norm"],
                kernel_size=self.ml_constants["hyperparameters_tcn"]["kernel_size"],
                num_filters=self.ml_constants["hyperparameters_tcn"]["num_filters"],
                num_layers=self.ml_constants["hyperparameters_tcn"]["num_layers"],
                input_chunk_length=lookback_window,
                output_chunk_length=self.ml_constants["prediction_params"]["prediction_n_days"],
                model_name=tcn_model_name + MODEL_NAME_CONSTANT,
                force_reset=True,
                log_tensorboard=False,
                work_dir=work_dir,
                save_checkpoints=False,
            )
            # This works
            if load_model:
                self.tcn_model.load_from_checkpoint(
                    model_name=tcn_model_name,
                    work_dir=self.constants["ml_models_dir"],
                    file_name=tcn_filename,
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

    def _slice_df(self) -> None:
        # some dataframes don't have enough data a full lookback window
        additional_dfs_min_date = np.max([df.index.min() for df in self.additional_dfs])
        slice_date = np.max([self.df.index.min(), additional_dfs_min_date])
        # Filter for years class var filter
        years_filter_slice_date = self.df.index.max() - pd.DateOffset(years=self.n_years_filer)

        final_slice_date = np.max([slice_date, years_filter_slice_date])

        logger.info(f"Slice date , earliest day of data for main df or years filter = {final_slice_date}")

        self.df = self.df.loc[final_slice_date:, :].copy()

        logger.info(f"self.df.shape = {self.df.shape}")
        logger.info(f"self.df.index.min() = {self.df.index.min()}")

        sliced_additional_dfs = []
        if len(self.additional_dfs) > 0:
            for add_df in self.additional_dfs:
                sliced_df = add_df.loc[final_slice_date:, :].copy()
                logger.info(f"sliced_df.shape = {sliced_df.shape}")
                logger.info(f"sliced_df.index.min() {sliced_df.index.min()}")
                logger.info(f"sliced_df.index.max() {sliced_df.index.max()}")
                sliced_additional_dfs.append(sliced_df)
        self.additional_dfs = sliced_additional_dfs

    def _build_technical_indicators(self) -> None:

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

                new_additional_dfs.append(df)
                logger.info(df.tail())
        self.additional_dfs = new_additional_dfs

    def _scale_time_series_df_and_time_cols(
        self, input_df: pd.DataFrame, time_cols: List[str] = ["year", "month", "day"]
    ) -> Tuple[Dict[str, Scaler], TimeSeries, TimeSeries]:
        ts_transformers: Dict[str, Scaler] = {}
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

    def _scale_time_series_df(
        self, input_df: pd.DataFrame, use_pred_col: bool = False
    ) -> Tuple[Dict[Any, Scaler], Any]:
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

    def _add_additional_training_dfs(
        self, ts_stacked_series: TimeSeries, verbose: bool = False
    ) -> Tuple[Dict[Dict[str, Any], Scaler], TimeSeries]:
        """
        Scale any additional DFs provided (such as ETHER)

        ts_stacked_series: the current scaled lists from the df_original provided
        """
        all_ts_transfomers = []
        for idx, df in enumerate(self.additional_dfs):
            (additional_ts_transformers, additional_ts_stacked_series) = self._scale_time_series_df(
                df, use_pred_col=True
            )
            if idx == 0:  # type :ignore
                if verbose:
                    logger.info(
                        f"last date for training additional df data {additional_ts_stacked_series.time_index[-1]}"
                    )
                all_ts_stacked_series = additional_ts_stacked_series.stack(ts_stacked_series)
                if verbose:
                    logger.info(f"all_ts_stacked_series FIRST {all_ts_stacked_series.components}")
                all_ts_transfomers.append(additional_ts_transformers)
            else:
                all_ts_stacked_series = all_ts_stacked_series.stack(additional_ts_stacked_series)
                if verbose:
                    logger.info(f"all_ts_stacked_series SECOND {all_ts_stacked_series.components} ")
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
            additional_ts_transformers, ts_stacked_series = self._add_additional_training_dfs(ts_stacked_series)
            ts_transformers = {**additional_ts_transformers, **ts_transformers}  # type: ignore
        self.ts_transformers = ts_transformers
        self.ts_stacked_series = ts_stacked_series
        self.train_close_series = train_close_series

        if self.verbose:
            logger.info(f"all series now stacked = {ts_stacked_series.components}")

        return train_close_series, ts_stacked_series

    def _train_model_with_thread(
        self, model: Any, train_close_series: TimeSeries, ts_stacked_series: TimeSeries, epochs: int
    ) -> None:
        # Target function for training within threads
        model.fit(series=train_close_series, past_covariates=[ts_stacked_series], verbose=self.verbose, epochs=epochs)

    def _train_models(self, train_close_series: TimeSeries, ts_stacked_series: TimeSeries) -> None:
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
                    raise ValueError(f"We have an incorrect model name of {model.model_name} we need tcn or nbeats")
        # block until all models are trained
        for k, v in dict_of_threads.items():
            logger.info(f"Have thread = {k}")
            v.join()

    def _make_stacking_prediction_and_save(self) -> float:
        # train a RF model on the input predictions from each model.
        # we need to date align the previous predictions on the date_prediction_for
        # from the  _all_predictions file
        # test on the current days predictions
        # save the predictions to the tmp folder including the stacking prediction
        DATE_PART_AND_STACKING_COLS_TO_EXCLUDE = [
            self.constants["date_col"],
            "date_pred",
            "date_true",
            self.constants["date_prediction_for_col"],
            self.constants["stacking_prediction_col"],
        ]
        NUMERIC_COLS_TO_EXCLUDE = [
            self.constants["bollinger_low_col"],
            self.constants["bollinger_high_col"],
            self.constants["close_col"],
        ] + self.ml_train_cols
        ALL_COLS_TO_EXCLUDE_RF_TRAINING = DATE_PART_AND_STACKING_COLS_TO_EXCLUDE + NUMERIC_COLS_TO_EXCLUDE

        if self.stacking_model_name.lower() == "rf":
            # self.df # this has the actual close prices
            # self.final_all_predictions_df # this has all predictions
            self.final_all_predictions_df.date_prediction_for = pd.to_datetime(
                self.final_all_predictions_df.date_prediction_for
            )
            self.final_all_predictions_df.index = pd.to_datetime(self.final_all_predictions_df.date)

            # merge on the future date for this prediction to compare to the close price
            merged_df = pd.merge(
                self.final_all_predictions_df,
                self.df,
                left_on="date_prediction_for",
                right_index=True,
                suffixes=["_pred", "_true"],
            )
            merged_df.index = merged_df.date_prediction_for
            todays_date = self.df.index.max()

            # for training, we need to use the aligned date of the prediction FOR which is in merged_df
            # TODO: we need to ensure the order of the columns is the same across both DFs. Use the training DF col orders
            training_df = merged_df[merged_df.index < todays_date]
            testing_df = self.final_all_predictions_df[self.final_all_predictions_df.index == todays_date]

            def _create_date_part_cols(input_df: pd.DataFrame) -> pd.DataFrame:
                # for  DFs used for RF, create day part cols
                input_df["day"] = [t.day for t in pd.to_datetime(input_df.date)]
                input_df["month"] = [t.month for t in pd.to_datetime(input_df.date)]
                input_df["quarter"] = [t.quarter for t in pd.to_datetime(input_df.date)]
                input_df["day_of_year"] = [t.strftime("%j") for t in pd.to_datetime(input_df.date)]
                input_df["year"] = [t.year for t in pd.to_datetime(input_df.date)]
                return input_df

            testing_df = _create_date_part_cols(testing_df)
            training_df = _create_date_part_cols(training_df)
            # Exclude the date related cols

            testing_df = testing_df.iloc[:, ~testing_df.columns.isin(DATE_PART_AND_STACKING_COLS_TO_EXCLUDE)]

            stacked_x_data_train = training_df.iloc[
                :, ~training_df.columns.isin(ALL_COLS_TO_EXCLUDE_RF_TRAINING)
            ]  # don't include the current row
            stacked_y_data_train = training_df[self.pred_col]  # don't include the current row
            testing_df = testing_df.reindex(stacked_x_data_train.columns, axis=1)
            # assert column order is the same
            assert list(stacked_x_data_train.columns) == list(testing_df.columns)

            if self.verbose:
                logger.info(f"{training_df.head} training_df head")
                logger.info(f"training_df tail ={training_df.tail()}")
                logger.info(f"training_df cols {training_df.columns}")
                logger.info(f"{stacked_x_data_train.shape} 'stacked_x_data_train shape'")
                logger.info(f"{stacked_x_data_train.index.min()} 'stacked_x_data_train index min'")
                logger.info(f"{stacked_x_data_train.index.max()} 'stacked_x_data_train index max'")
                logger.info(f"{stacked_y_data_train.shape} 'stacked_y_data_train.shape'")
                logger.info(f"{testing_df.shape} 'testing_df.shape'")
                logger.info(f"{merged_df}, merged_df")
                logger.info(f"{merged_df.index}, merged_df index")
                logger.info(f"{todays_date}, todays_date")
                logger.info(f"self.final_all_predictions_df = {self.final_all_predictions_df}")
                logger.info(f"self.final_all_predictions_df cols = {self.final_all_predictions_df.columns}")
                logger.info(
                    f"self.final_all_predictions_df date prediction for = {self.final_all_predictions_df.date_prediction_for}"
                )
                logger.info(f"self.df.index = {self.df.index}")
                logger.info("cols difference")
                logger.info(set(stacked_x_data_train.columns) - set(testing_df.columns))
                logger.info(set(testing_df.columns) - set(stacked_x_data_train.columns))
            estimator = RandomForestRegressor(
                n_estimators=self.ml_constants["hyperparameters_random_forest"]["n_estimators"],
                n_jobs=-1,
                random_state=self.random_state,
            )

            # convert both to numpy arrays
            stacked_x_data_train = stacked_x_data_train.to_numpy()

            estimator.fit(stacked_x_data_train, stacked_y_data_train)
            # if we have multiple rows for todays_date, run this multiple times, take the first
            if len(testing_df) > 1:
                testing_df = testing_df.iloc[0, :].to_numpy().reshape(1, -1)  # numpy array of 1 row, all cols
            prediction = estimator.predict(testing_df)[0]  # predict returns a numpy array, so we need to index it

        # save prediction as part of all predictions. Update the last stacking prediction to this new prediction
        # cast as float
        self.final_all_predictions_df[self.constants["stacking_prediction_col"]] = self.final_all_predictions_df[
            self.constants["stacking_prediction_col"]
        ].astype(float)
        logger.info(f"dtypes of self.final_all_predictions_df {self.final_all_predictions_df.dtypes}")
        current_stacking_predictions = list(self.final_all_predictions_df[self.constants["stacking_prediction_col"]])
        current_stacking_predictions[-1] = prediction
        self.final_all_predictions_df[self.constants["stacking_prediction_col"]] = current_stacking_predictions

        if running_on_aws():
            all_predictions_filename = "/" + self.all_predictions_filename
        else:
            all_predictions_filename = self.all_predictions_filename
        self.final_all_predictions_df.to_csv(all_predictions_filename, index=False)
        return prediction

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
        # base predictions from child class
        predictions_dict = self._make_base_predictions_dict(train_close_series, ts_stacked_series)
        logger.info(f"predictions_dict = {predictions_dict}")
        self._generate_base_predictions_df(predictions_dict)

        logger.info(f" stacking the predictions with {self.stacking_model_name}")
        prediction = self._make_stacking_prediction_and_save()
        logger.info(f"Prediction = {prediction}")
        sys.stdout.flush()
        # for now, still return the mean
        return prediction
