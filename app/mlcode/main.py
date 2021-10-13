try:  # need modules for pytest to work
    from app.mlcode.determine_trading_state import DetermineTradingState
    from app.mlcode.predict_price_movements import BollingerBandsPredictor
    from app.mlcode.utils import (read_in_data, read_in_yaml, running_on_aws,
                                  update_yaml_config)
except ModuleNotFoundError:  # Go is unable to run python modules -m
    from predict_price_movements import BollingerBandsPredictor
    from utils import read_in_yaml, read_in_data, update_yaml_config, running_on_aws
    from determine_trading_state import DetermineTradingState

import logging
import sys

import click

# TODO: accept either btc or eth as param

logger = logging.getLogger(__name__)


@click.command()
@click.option("--coin_to_predict", help="Coin to predict either btc or eth")
def main(coin_to_predict: str):
    is_running_on_aws = running_on_aws()
    logger.info("Running determine trading state")

    constants = read_in_yaml("app/constants.yml", is_running_on_aws)
    sys.stdout.flush()
    trading_constants = read_in_yaml(
        constants["trading_state_config_filename"], is_running_on_aws
    )
    sys.stdout.flush()
    won_and_lost_amount_constants = read_in_yaml(
        constants["won_and_lost_amount_filename"], is_running_on_aws
    )
    actions_to_take_constants = read_in_yaml(
        constants["actions_to_take_filename"], is_running_on_aws
    )
    # data should already be downloaded from the golang app
    bitcoin_df = read_in_data(constants["bitcoin_csv_filename"], is_running_on_aws)
    etherum_df = read_in_data(constants["etherum_csv_filename"], is_running_on_aws)
    # spy_df = read_in_data(constants["spu_csv_filename"], is_running_on_aws, missing_dates=True)
    ml_constants = read_in_yaml(constants["ml_config_filename"], is_running_on_aws)
    predictor = None

    if coin_to_predict == "btc":
        predictor = BollingerBandsPredictor(
            coin_to_predict,
            constants,
            ml_constants,
            bitcoin_df,
            additional_dfs=[etherum_df],  # spy_df
        )
    elif coin_to_predict == "eth":
        predictor = BollingerBandsPredictor(
            coin_to_predict,
            constants,
            ml_constants,
            etherum_df,
            additional_dfs=[bitcoin_df],  # spy_df
        )
    else:
        raise ValueError(
            f"Incorrect coin to predict {coin_to_predict}. Needs to be eth or btc."
        )
    sys.stdout.flush()

    predictor._build_bollinger_bands()

    price_prediction = predictor.predict()
    # print(price_prediction, "price_prediction")
    logger.info("Determine trading state")

    # predictor.df has the bollinger bands
    trading_state_class = DetermineTradingState(
        coin_to_predict,
        price_prediction,
        constants,
        trading_constants,
        predictor.df,
        won_and_lost_amount_constants,
        actions_to_take_constants,
    )
    sys.stdout.flush()
    trading_state_class.calculate_positions()
    logger.info("---- Finished determinig trading strategy --- ")
    trading_state_class.update_state()
    # this works
    update_yaml_config(
        constants["trading_state_config_filename"],
        trading_state_class.trading_state_constants,
        is_running_on_aws,
    )
    logger.info("---- Updated trading state config --- ")
    update_yaml_config(
        constants["won_and_lost_amount_filename"],
        trading_state_class.won_and_lose_amount_dict,
        is_running_on_aws,
    )
    logger.info("---- Updated win/lost state config --- ")
    update_yaml_config(
        constants["actions_to_take_filename"],
        trading_state_class.actions_to_take_constants,
        is_running_on_aws,
    )
    logger.info("---- Updated actions to take state config --- ")


if __name__ == "__main__":
    main()
