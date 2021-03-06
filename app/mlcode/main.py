try:  # need modules for pytest to work
    from app.mlcode.determine_trading_state import DetermineTradingState
    from app.mlcode.predict_price_movements import CoinPricePredictor
    from app.mlcode.utils import read_in_data, read_in_yaml, running_on_aws, setup_logging, update_yaml_config
except ModuleNotFoundError:  # Go is unable to run python modules -m
    from predict_price_movements import CoinPricePredictor
    from utils import read_in_yaml, read_in_data, update_yaml_config, running_on_aws, setup_logging
    from determine_trading_state import DetermineTradingState

import sys

import click

logger = setup_logging()


def add_coin_to_filename(coin: str, filename: str) -> str:
    """
    Adds the coin to the filename
    :param coin:
    """
    filename_split = filename.split("/")
    final_filename = filename_split[0] + "/" + coin + "_" + filename_split[1]
    logger.info(f"final_filename = {final_filename}")

    return final_filename


@click.command()
@click.option("--coin_to_predict", help="Coin to predict either btc or eth")
def main(coin_to_predict: str) -> None:
    is_running_on_aws = running_on_aws()
    logger.info("Running determine trading state")

    constants = read_in_yaml("tmp/constants.yml", is_running_on_aws)
    sys.stdout.flush()

    trading_state_filename = add_coin_to_filename(coin_to_predict, constants["trading_state_config_filename"])
    trading_constants = read_in_yaml(trading_state_filename, is_running_on_aws)

    all_predictions_filename = add_coin_to_filename(coin_to_predict, constants["all_predictions_csv_filename"])

    sys.stdout.flush()

    won_lost_amount_filename = add_coin_to_filename(coin_to_predict, constants["won_and_lost_amount_filename"])
    won_and_lost_amount_constants = read_in_yaml(won_lost_amount_filename, is_running_on_aws)

    actions_to_take_filename = add_coin_to_filename(coin_to_predict, constants["actions_to_take_filename"])
    actions_to_take_constants = read_in_yaml(actions_to_take_filename, is_running_on_aws)

    # data should already be downloaded from the golang app
    bitcoin_df = read_in_data(constants["bitcoin_csv_filename"], is_running_on_aws, constants["date_col"])
    etherum_df = read_in_data(constants["etherum_csv_filename"], is_running_on_aws, constants["date_col"])
    sol_df = read_in_data(constants["sol_csv_filename"], is_running_on_aws, constants["date_col"])
    matic_df = read_in_data(constants["matic_csv_filename"], is_running_on_aws, constants["date_col"])
    link_df = read_in_data(constants["link_csv_filename"], is_running_on_aws, constants["date_col"])
    tbt_df = read_in_data(constants["tbt_csv_filename"], is_running_on_aws, constants["date_col"])
    # spy_df = read_in_data(constants["spu_csv_filename"], is_running_on_aws, missing_dates=True)
    ml_constants = read_in_yaml(constants["ml_config_filename"], is_running_on_aws)
    predictor = None

    sys.stdout.flush()
    if coin_to_predict == "btc":
        predictor = CoinPricePredictor(
            coin_to_predict=coin_to_predict,
            constants=constants,
            ml_constants=ml_constants,
            input_df=bitcoin_df,
            all_predictions_filename=all_predictions_filename,
            additional_dfs=[etherum_df, tbt_df],  # spy_df
        )
    elif coin_to_predict == "eth":
        predictor = CoinPricePredictor(
            coin_to_predict=coin_to_predict,
            constants=constants,
            ml_constants=ml_constants,
            input_df=etherum_df,
            all_predictions_filename=all_predictions_filename,
            additional_dfs=[bitcoin_df, tbt_df],  # spy_df
        )
    elif coin_to_predict == "sol":
        predictor = CoinPricePredictor(
            coin_to_predict=coin_to_predict,
            constants=constants,
            ml_constants=ml_constants,
            input_df=sol_df,
            all_predictions_filename=all_predictions_filename,
            additional_dfs=[bitcoin_df, tbt_df],
        )
    elif coin_to_predict == "matic":
        predictor = CoinPricePredictor(
            coin_to_predict=coin_to_predict,
            constants=constants,
            ml_constants=ml_constants,
            input_df=matic_df,
            all_predictions_filename=all_predictions_filename,
            additional_dfs=[bitcoin_df, tbt_df],
        )
    elif coin_to_predict == "link":
        predictor = CoinPricePredictor(
            coin_to_predict=coin_to_predict,
            constants=constants,
            ml_constants=ml_constants,
            input_df=link_df,
            all_predictions_filename=all_predictions_filename,
            additional_dfs=[bitcoin_df, tbt_df],
        )
    else:
        raise ValueError(f"Incorrect coin to predict {coin_to_predict}. Should be btc, eth, sol, matic or link")
    sys.stdout.flush()
    logger.info("Predict Price Movements")
    sys.stdout.flush()
    price_prediction = predictor.predict()
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
        is_running_on_aws,
    )
    sys.stdout.flush()
    trading_state_class.calculate_positions()
    logger.info("---- Finished determining trading strategy --- ")
    trading_state_class.update_state()
    # this works

    update_yaml_config(trading_state_filename, trading_state_class.trading_state_constants, is_running_on_aws)
    logger.info("---- Updated trading state config --- ")
    update_yaml_config(won_lost_amount_filename, trading_state_class.won_and_lose_amount_dict, is_running_on_aws)
    logger.info("---- Updated win/lost state config --- ")
    update_yaml_config(actions_to_take_filename, trading_state_class.actions_to_take_constants, is_running_on_aws)
    logger.info("---- Updated actions to take state config --- ")


if __name__ == "__main__":
    main()
