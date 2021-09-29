from app.mlcode.determine_trading_state import DetermineTradingState
from app.mlcode.predict_price_movements import BollingerBandsPredictor
from app.mlcode.utils import update_yaml_config
import logging
import unittest
import pytest


def test_no_btc_action(example_btc_df, example_eth_df, constants, ml_config, trading_state_config):
    """verify everyting works as intended
    """
    price_prediction = 900
    btc_predictor = BollingerBandsPredictor(
        "bitcoin", constants, ml_config, example_btc_df, additional_dfs=[example_eth_df]
    )
    btc_predictor._build_bollinger_bands()
    # btc_predictor.df has the bollinger bands
    trading_state_class = DetermineTradingState(
        price_prediction, constants, trading_state_config, btc_predictor.df
    )
    trading_state_class.calculate_positions()
    trading_state_class.update_state()

    assert trading_state_config == trading_state_class.trading_state_constants


def test_buy_btc_action(example_btc_df_bollinger_buy,  constants, ml_config, trading_state_config):
    price_prediction = 9000

    # btc_predictor.df has the bollinger bands
    trading_state_class = DetermineTradingState(
        price_prediction, constants, trading_state_config, example_btc_df_bollinger_buy
    )
    trading_state_class.calculate_positions()
    trading_state_class.update_state()
    assert trading_state_class.trading_state_constants["mode"] == "buy"
    assert trading_state_class.trading_state_constants["short_entry_price"] == 0
    assert trading_state_class.trading_state_constants["buy_entry_price"] == 982
    assert trading_state_class.trading_state_constants["stop_loss_price"] == 932.9


def test_short_btc_action(example_btc_df_bollinger_short,  constants, ml_config, trading_state_config):
    price_prediction = 90

    # btc_predictor.df has the bollinger bands
    trading_state_class = DetermineTradingState(
        price_prediction, constants, trading_state_config, example_btc_df_bollinger_short
    )
    trading_state_class.calculate_positions()
    trading_state_class.update_state()
    assert trading_state_class.trading_state_constants["mode"] == "short"
    assert trading_state_class.trading_state_constants["short_entry_price"] == 1500
    assert trading_state_class.trading_state_constants["buy_entry_price"] == 0
    assert trading_state_class.trading_state_constants["stop_loss_price"] == 1575


def test_buy_to_no_position_via_prediction_btc(example_btc_df_bollinger_buy,  constants, ml_config, trading_state_config_buy):
    price_prediction = 9

    # btc_predictor.df has the bollinger bands
    trading_state_class = DetermineTradingState(
        price_prediction, constants, trading_state_config_buy, example_btc_df_bollinger_buy
    )
    trading_state_class.calculate_positions()
    trading_state_class.update_state()
    assert trading_state_class.trading_state_constants["mode"] == "no_position"
    assert trading_state_class.trading_state_constants["short_entry_price"] == 0
    assert trading_state_class.trading_state_constants["buy_has_crossed_mean"] == False
    assert trading_state_class.trading_state_constants["buy_entry_price"] == 0
    assert trading_state_class.trading_state_constants["stop_loss_price"] == 0

# def test_buy_to_no_position_via_stop_loss_btc(example_btc_df_bollinger_buy,  constants, ml_config, trading_state_config):
#     price_prediction = 9000

#     # btc_predictor.df has the bollinger bands
#     trading_state_class = DetermineTradingState(
#         price_prediction, constants, trading_state_config, example_btc_df_bollinger_buy
#     )
#     trading_state_class.calculate_positions()
#     trading_state_class.update_state()
#     assert trading_state_class.trading_state_constants["mode"] == "buy"
#     assert trading_state_class.trading_state_constants["short_entry_price"] == 0
#     assert trading_state_class.trading_state_constants["buy_entry_price"] == 982
#     assert trading_state_class.trading_state_constants["stop_loss_price"] == 932.9
