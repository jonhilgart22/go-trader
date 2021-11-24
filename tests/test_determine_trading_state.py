import math
import os

from app.mlcode.determine_trading_state import DetermineTradingState  # type: ignore
from app.mlcode.predict_price_movements import BollingerBandsPredictor  # type: ignore

os.environ["ON_LOCAL"] = "True"


def test_no_btc_action(
    example_btc_df,
    example_eth_df,
    constants,
    ml_config,
    btc_trading_state_config,
    btc_won_and_lost_constants,
    btc_actions_to_take_constants,
):
    """verify everyting works as intended"""
    # for faster tests, uncomment
    # price_prediction = 900
    coin_to_predict = "btc"
    btc_predictor = BollingerBandsPredictor(
        coin_to_predict, constants, ml_config, example_btc_df, additional_dfs=[example_eth_df]
    )
    btc_predictor._build_technical_indicators()
    price_prediction = btc_predictor.predict()
    print(f"Price prediction = {price_prediction}")
    assert math.isnan(price_prediction) != True
    # btc_predictor.df has the bollinger bands
    trading_state_class = DetermineTradingState(
        "btc",
        price_prediction,
        constants,
        btc_trading_state_config,
        btc_predictor.df,
        btc_won_and_lost_constants,
        btc_actions_to_take_constants,
        False,
    )
    trading_state_class.calculate_positions()
    trading_state_class.update_state()

    assert btc_trading_state_config == trading_state_class.trading_state_constants


def test_no_sol_action(
    example_sol_df,
    example_eth_df,
    constants,
    ml_config,
    sol_trading_state_config,
    sol_won_and_lost_constants,
    sol_actions_to_take_constants,
):
    """verify everyting works as intended"""
    # for faster tests, uncomment
    # price_prediction = 900
    coin_to_predict = "sol"
    btc_predictor = BollingerBandsPredictor(
        coin_to_predict, constants, ml_config, example_sol_df, additional_dfs=[example_eth_df]
    )
    btc_predictor._build_technical_indicators()
    price_prediction = btc_predictor.predict()
    print(f"Price prediction = {price_prediction}")
    assert math.isnan(price_prediction) != True
    # btc_predictor.df has the bollinger bands
    trading_state_class = DetermineTradingState(
        coin_to_predict,
        price_prediction,
        constants,
        sol_trading_state_config,
        btc_predictor.df,
        sol_won_and_lost_constants,
        sol_actions_to_take_constants,
        False,
    )
    trading_state_class.calculate_positions()
    trading_state_class.update_state()

    assert sol_trading_state_config == trading_state_class.trading_state_constants


def test_no_eth_action(
    example_btc_df,
    example_eth_df,
    constants,
    ml_config,
    eth_trading_state_config,
    eth_won_and_lost_constants,
    eth_actions_to_take_constants,
):
    """verify everyting works as intended"""

    coin_to_predict = "eth"
    btc_predictor = BollingerBandsPredictor(
        coin_to_predict, constants, ml_config, example_btc_df, additional_dfs=[example_eth_df]
    )
    btc_predictor._build_technical_indicators()
    price_prediction = btc_predictor.predict()
    print(f"Price prediction = {price_prediction}")
    assert math.isnan(price_prediction) != True
    price_prediction = 900
    # btc_predictor.df has the bollinger bands
    trading_state_class = DetermineTradingState(
        coin_to_predict,
        price_prediction,
        constants,
        eth_trading_state_config,
        btc_predictor.df,
        eth_won_and_lost_constants,
        eth_actions_to_take_constants,
        False,
    )
    trading_state_class.calculate_positions()
    trading_state_class.update_state()

    assert eth_trading_state_config == trading_state_class.trading_state_constants


def test_buy_btc_action(
    example_btc_df_bollinger_exit_position,
    constants,
    btc_trading_state_config,
    btc_won_and_lost_constants,
    btc_actions_to_take_constants,
    ml_config,
    example_btc_df,
    example_eth_df,
):

    coin_to_predict = "btc"
    btc_predictor = BollingerBandsPredictor(
        coin_to_predict, constants, ml_config, example_btc_df, additional_dfs=[example_eth_df]
    )

    price_prediction = btc_predictor.predict()
    print(f"Price prediction = {price_prediction}")
    assert math.isnan(price_prediction) != True
    # ensure the rest of the tests pass
    price_prediction = 9000

    # btc_predictor.df has the bollinger bands
    coin_to_predict = "btc"
    trading_state_class = DetermineTradingState(
        coin_to_predict,
        price_prediction,
        constants,
        btc_trading_state_config,
        example_btc_df_bollinger_exit_position,
        btc_won_and_lost_constants,
        btc_actions_to_take_constants,
        False,
    )

    trading_state_class.calculate_positions()
    trading_state_class.update_state()

    assert trading_state_class.trading_state_constants["mode"] == "buy"
    assert trading_state_class.trading_state_constants["short_entry_price"] == 0
    assert trading_state_class.trading_state_constants["buy_entry_price"] == 982
    assert trading_state_class.trading_state_constants["stop_loss_price"] == 883.8000000000001
    assert trading_state_class.actions_to_take_constants["action_to_take"] == "none_to_buy"


# def test_short_btc_action(
#     example_btc_df_bollinger_short,
#     constants,
#     trading_state_config,
#     won_and_lost_constants,
#     actions_to_take_constants,
# ):
#     price_prediction = 90

#     # btc_predictor.df has the bollinger bands
#     coin_to_predict = "btc"
#     trading_state_class = DetermineTradingState(
#         coin_to_predict,
#         price_prediction,
#         constants,
#         trading_state_config,
#         example_btc_df_bollinger_short,
#         won_and_lost_constants,
#         actions_to_take_constants,
#     )
#     trading_state_class.calculate_positions()
#     trading_state_class.update_state()
#     assert (
#         trading_state_class.actions_to_take_constants[coin_to_predict]["action_to_take"]
#         == "none_to_short"
#     )
#     assert (
#         trading_state_class.trading_state_constants[coin_to_predict]["mode"] == "short"
#     )
#     assert (
#         trading_state_class.trading_state_constants[coin_to_predict][
#             "short_entry_price"
#         ]
#         == 1500
#     )
#     assert (
#         trading_state_class.trading_state_constants[coin_to_predict]["buy_entry_price"]
#         == 0
#     )
#     assert (
#         trading_state_class.trading_state_constants[coin_to_predict]["stop_loss_price"]
#         == 1575
#     )


def test_buy_to_none_via_prediction_btc(
    example_btc_df_bollinger_exit_position,
    constants,
    btc_trading_state_config_buy,
    btc_won_and_lost_constants,
    btc_actions_to_take_constants,
    ml_config,
    example_eth_df,
):

    coin_to_predict = "btc"
    btc_predictor = BollingerBandsPredictor(
        coin_to_predict, constants, ml_config, example_btc_df_bollinger_exit_position, additional_dfs=[example_eth_df]
    )

    price_prediction = btc_predictor.predict()
    print(f"Price prediction = {price_prediction}")
    assert math.isnan(price_prediction) != True

    # ensure the rest of the tests pass
    price_prediction = 9

    # btc_predictor.df has the bollinger bands
    coin_to_predict = "btc"
    trading_state_class = DetermineTradingState(
        coin_to_predict,
        price_prediction,
        constants,
        btc_trading_state_config_buy,
        example_btc_df_bollinger_exit_position,
        btc_won_and_lost_constants,
        btc_actions_to_take_constants,
        False,
    )

    trading_state_class.calculate_positions()
    trading_state_class.update_state()
    assert trading_state_class.actions_to_take_constants["action_to_take"] == "buy_to_none"
    # assert trading state is correct
    assert trading_state_class.trading_state_constants["mode"] == "no_position"
    assert trading_state_class.trading_state_constants["short_entry_price"] == 0
    assert trading_state_class.trading_state_constants["buy_has_crossed_mean"] == False
    assert trading_state_class.trading_state_constants["short_has_crossed_mean"] == False
    assert trading_state_class.trading_state_constants["buy_entry_price"] == 0
    assert trading_state_class.trading_state_constants["stop_loss_price"] == 0
    assert trading_state_class.trading_state_constants["position_entry_date"] == None
    ## assert win/lose is correct
    assert trading_state_class.won_and_lose_amount_dict["n_buy_lost"] == 1
    assert trading_state_class.won_and_lose_amount_dict["dollar_amount_buy_lost"] == 18


# TODO: uncomment once FTX.US supports short tokens
# def test_short_to_none_via_prediction_btc(
#     example_btc_df_bollinger_exit_position,
#     constants,
#     trading_state_config_short,
#     won_and_lost_constants,
#     actions_to_take_constants,
# ):
#     price_prediction = 99999

#     # btc_predictor.df has the bollinger bands
#     coin_to_predict = "btc"
#     trading_state_class = DetermineTradingState(
#         coin_to_predict,
#         price_prediction,
#         constants,
#         trading_state_config_short,
#         example_btc_df_bollinger_exit_position,
#         won_and_lost_constants,
#         actions_to_take_constants,
#     )

#     trading_state_class.calculate_positions()
#     trading_state_class.update_state()
#     assert (
#         trading_state_class.actions_to_take_constants[coin_to_predict]["action_to_take"]
#         == "short_to_none"
#     )
#     # assert trading state is correct
#     assert (
#         trading_state_class.trading_state_constants[coin_to_predict]["mode"]
#         == "no_position"
#     )
#     assert (
#         trading_state_class.trading_state_constants[coin_to_predict][
#             "short_entry_price"
#         ]
#         == 0
#     )
#     assert (
#         trading_state_class.trading_state_constants[coin_to_predict][
#             "buy_has_crossed_mean"
#         ]
#         == False
#     )
#     assert (
#         trading_state_class.trading_state_constants[coin_to_predict][
#             "short_has_crossed_mean"
#         ]
#         == False
#     )
#     assert (
#         trading_state_class.trading_state_constants[coin_to_predict]["buy_entry_price"]
#         == 0
#     )
#     assert (
#         trading_state_class.trading_state_constants[coin_to_predict]["stop_loss_price"]
#         == 0
#     )
#     assert (
#         trading_state_class.trading_state_constants[coin_to_predict][
#             "position_entry_date"
#         ]
#         == None
#     )
#     # assert win/lose is correct
#     assert (
#         trading_state_class.won_and_lose_amount_dict[coin_to_predict]["n_short_won"]
#         == 1
#     )
#     assert (
#         trading_state_class.won_and_lose_amount_dict[coin_to_predict][
#             "dollar_amount_short_won"
#         ]
#         == 18
#     )


# def test_short_to_stop_loss(
#     example_btc_df_bollinger_exit_position,
#     constants,
#     trading_state_config_short_stop_loss,
#     won_and_lost_constants,
#     actions_to_take_constants,
# ):
#     price_prediction = 99999

#     # btc_predictor.df has the bollinger bands
#     coin_to_predict = "btc"
#     trading_state_class = DetermineTradingState(
#         coin_to_predict,
#         price_prediction,
#         constants,
#         trading_state_config_short_stop_loss,
#         example_btc_df_bollinger_exit_position,
#         won_and_lost_constants,
#         actions_to_take_constants,
#     )

#     trading_state_class.calculate_positions()
#     trading_state_class.update_state()

#     assert (
#         trading_state_class.actions_to_take_constants[coin_to_predict]["action_to_take"]
#         == "short_to_none"
#     )
#     # assert trading state is correct
#     assert (
#         trading_state_class.trading_state_constants[coin_to_predict]["mode"]
#         == "no_position"
#     )
#     assert (
#         trading_state_class.trading_state_constants[coin_to_predict][
#             "short_entry_price"
#         ]
#         == 0
#     )
#     assert (
#         trading_state_class.trading_state_constants[coin_to_predict][
#             "buy_has_crossed_mean"
#         ]
#         == False
#     )
#     assert (
#         trading_state_class.trading_state_constants[coin_to_predict][
#             "short_has_crossed_mean"
#         ]
#         == False
#     )
#     assert (
#         trading_state_class.trading_state_constants[coin_to_predict]["buy_entry_price"]
#         == 0
#     )
#     assert (
#         trading_state_class.trading_state_constants[coin_to_predict]["stop_loss_price"]
#         == 0
#     )
#     assert (
#         trading_state_class.trading_state_constants[coin_to_predict][
#             "position_entry_date"
#         ]
#         == None
#     )
#     # assert win/lose is correct
#     assert (
#         trading_state_class.won_and_lose_amount_dict[coin_to_predict]["n_short_lost"]
#         == 1
#     )
#     assert (
#         trading_state_class.won_and_lose_amount_dict[coin_to_predict][
#             "dollar_amount_short_lost"
#         ]
#         == 977
#     )
# can't test total # of days in trade because it's based off of today
