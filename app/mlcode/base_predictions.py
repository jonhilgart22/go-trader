from typing import Any, Dict, List, Union
import pandas as pd
from darts import TimeSeries

try:  # need modules for pytest to work
    from app.mlcode.utils import read_in_data, running_on_aws, setup_logging
except ModuleNotFoundError:  # Go is unable to run python modules -m
    from utils import read_in_data, running_on_aws, setup_logging

import numpy as np
from collections import defaultdict

__all__ = ["BasePredictor"]

logger = setup_logging()


class BasePredictor:
    def _make_base_predictions_dict(
        self, train_close_series: TimeSeries, ts_stacked_series: TimeSeries
    ) -> Dict[str, float]:
        all_predictions_dict = {}

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
                all_predictions_dict[model.model_name] = prediction
        self.all_predictions_dict = all_predictions_dict

        return all_predictions_dict

    def _add_in_date_cols(
        self, new_predictions_dict: Dict[str, List[Union[int, float]]], predictions_df: pd.DataFrame
    ) -> Dict[str, List[Union[int, float]]]:
        # Add in the dates
        current_pred_dates_list = [index_date.strftime("%Y-%m-%d") for index_date in predictions_df.index]
        logger.info(f"Newest date for all predictions = {self.df.index.max()}")
        current_pred_dates_list.append(self.df.index.max().strftime("%Y-%m-%d"))  # current dates

        new_predictions_dict[self.date_col].extend(current_pred_dates_list)

        # Add in the pred for dates
        # for example, if we have a prediction_n_days of
        # 7, and we predict on 1/1 the date_prediction_for is 1/8

        current_date_pred_for_list = list(predictions_df[self.constants["date_prediction_for_col"]])
        # add in the prediction_n_days window to the current date
        timedelta_days = pd.to_timedelta(self.ml_constants["prediction_params"]["prediction_n_days"], unit="days")
        newest_date_for_pred_str = (self.df.index.max() + timedelta_days).strftime("%Y-%m-%d")
        logger.info(f"newest_date_for_pred_str = {newest_date_for_pred_str}")
        current_date_pred_for_list.append(newest_date_for_pred_str)
        logger.info(f"current_date_pred_for_list = {current_date_pred_for_list}")

        new_predictions_dict[self.constants["date_prediction_for_col"]].extend(current_date_pred_for_list)

        return new_predictions_dict

    @staticmethod
    def _add_in_current_base_predictions(
        new_predictions_dict: Dict[str, List[Union[int, float]]],
        input_predictions: Dict[str, float],
        predictions_df: pd.DataFrame,
        largest_n_predictions: int,
    ) -> Dict[str, List[Union[int, float]]]:
        # for the current base predictions
        all_cols = list(predictions_df.columns)

        for model_name, prediction in input_predictions.items():
            if model_name in all_cols:
                # previous predictions
                current_predictions_list = list(predictions_df[model_name])
                # add in previous
                new_predictions_dict[model_name].extend(current_predictions_list)
                # add in new
                new_predictions_dict[model_name].append(prediction)

            else:  # new model_name
                new_model_predictions_array = list(np.zeros(largest_n_predictions))
                new_model_predictions_array[-1] = input_predictions[model_name]
                new_predictions_dict[model_name].extend(new_model_predictions_array)
        return new_predictions_dict

    def _add_in_missing_cols(
        self,
        new_predictions_dict: Dict[str, List[Union[int, float]]],
        predictions_df: pd.DataFrame,
        input_predictions: Dict[str, float],
        largest_n_predictions: int,
    ) -> Dict[str, List[Union[int, float]]]:
        # From the original predictions_df, what cols do we have that we no longer have?
        # this can happen if we change the predictions params to create new model names
        missing_cols = list(set(predictions_df.columns).difference(list(input_predictions.keys())))
        logger.info(f"missing_cols ={missing_cols}")
        #  make sure to exclude the date cols
        dates_cols = [self.constants["date_prediction_for_col"], self.date_col]

        for col in missing_cols:
            if col not in dates_cols:
                current_preds = predictions_df[col]
                new_array_for_missing_col = list(np.zeros(largest_n_predictions))
                new_array_for_missing_col[: len(current_preds)] = current_preds
                new_predictions_dict[col] = new_array_for_missing_col
        # add in the stacking col predictions. We'll update this below
        current_stacking_preds = []
        if self.constants["stacking_prediction_col"] in predictions_df.columns:
            current_stacking_preds = list(predictions_df[self.constants["stacking_prediction_col"]])

        current_stacking_preds.extend([0 for _ in range(largest_n_predictions - len(current_stacking_preds))])
        new_predictions_dict[self.constants["stacking_prediction_col"]] = current_stacking_preds

        return new_predictions_dict

    def _generate_base_predictions_df(self, input_predictions: Dict[str, float]) -> None:
        # 1)  read in the csv file for this coin
        # 2) Add in the new price predictions, one for each col. If we don't have a col, create a new one
        # 3) save the file back to the tmp folder (depending if running on AWS or not)

        # this sets the date to be the index
        predictions_df = read_in_data(self.all_predictions_filename, running_on_aws(), self.constants["date_col"])
        largest_n_predictions = 1 + np.max(predictions_df.count())
        # store all arrays we will need to add to the df
        new_predictions_dict: Dict[str, Any] = defaultdict(list)

        new_predictions_dict = BasePredictor._add_in_current_base_predictions(
            new_predictions_dict, input_predictions, predictions_df, largest_n_predictions
        )

        new_predictions_dict = self._add_in_date_cols(new_predictions_dict, predictions_df)
        new_predictions_dict = self._add_in_missing_cols(
            new_predictions_dict, predictions_df, input_predictions, largest_n_predictions
        )

        logger.info(f"new_predictions_dict= {new_predictions_dict}")

        # make sure these are all the same length
        try:
            final_all_predictions_df = pd.DataFrame(new_predictions_dict)
        except ValueError as e:
            logger.error(
                f"Found an array without the same length. {e}. This either means we have a new model or a new lookback window. Check that all arrays are the same length"
            )
            logger.error(f"new_predictions_dict  = {new_predictions_dict}")

        # make sure the 'date' is the first col
        first_col = final_all_predictions_df.pop(self.date_col)
        final_all_predictions_df.insert(0, self.date_col, first_col)
        # assign for stacking to use
        self.final_all_predictions_df = final_all_predictions_df
