from app.mlcode.determine_trading_state import DetermineTradingState
from app.mlcode.predict_price_movements import BollingerBandsPredictor
import logging
import unittest
import pytest


def test_no_btc_action(example_btc_df_no_action, example_eth_df_no_action, constants, ml_config, trading_state_config):
    price_prediction = 900
    btc_predictor = BollingerBandsPredictor(
        "bitcoin", constants, ml_config, example_btc_df_no_action, additional_dfs=[example_eth_df_no_action]
    )
    btc_predictor._build_bollinger_bands()
    # btc_predictor.df has the bollinger bands
    trading_state_class = DetermineTradingState(
        price_prediction, constants, trading_state_config, btc_predictor.df
    )
    trading_state_class.calculate_positions()


# class LoggerTestCase(unittest.TestCase):
#     @pytest.fixture(autouse=True)
#     def test_no_btc_action(self, example_btc_df_no_action, example_eth_df_no_action, constants, ml_config, trading_state_config):

#         logger = logging.getLogger(__name__)
#         with self.assertLogs(logger, level='INFO') as logs:
#             price_prediction = 900
#             btc_predictor = BollingerBandsPredictor(
#                 "bitcoin", constants, ml_config, example_btc_df_no_action, additional_dfs=[example_eth_df_no_action]
#             )
#             btc_predictor._build_bollinger_bands()
#             # btc_predictor.df has the bollinger bands
#             trading_state_class = DetermineTradingState(
#                 price_prediction, constants, trading_state_config, btc_predictor.df
#             )
#             trading_state_class.calculate_positions()
#             logging.getLogger().info('Taking no action today')
#             self.assertEqual(logs.output, [
#                 "[09-29-2021 11:45:59] : INFO : determine_trading_state : _print_log_statements : 345  Taking no action today"])
