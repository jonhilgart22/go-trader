from datetime import datetime, timedelta
from typing import Any, Dict

import pandas as pd
import pytest
from freezegun import freeze_time

from app.mlcode.utils import read_in_yaml

# csv for predictions


@pytest.fixture
def btc_updated_predictions_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "date": ["2022-01-01", "2022-01-02", "2022-01-03"],
            "test_model_lookback_1": [1, 2, 3],
            "date_prediction_for": ["2022-01-05", "2022-01-06", "2022-01-07"],
            "nbeats_btc_lookback_2_window_2_std_1.5_num_add_dfs_1": [0, 0, 0],
            "tcn_btc_lookback_2_window_2_std_1.5_num_add_dfs_1": [0, 0, 0],
        }
    )


@pytest.fixture
def btc_all_predictions_csv() -> str:
    btc_filename = "tests/configs/btc_all_predictions_updated.csv"
    return btc_filename


@pytest.fixture
def sol_updated_predictions_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "date": ["2022-01-01", "2022-01-02", "2022-01-03"],
            "test_model_lookback_1": [1, 2, 3],
            "date_prediction_for": ["2022-01-05", "2022-01-06", "2022-01-07"],
            "nbeats_sol_lookback_2_window_2_std_1.5_num_add_dfs_1": [0, 0, 0],
            "tcn_sol_lookback_2_window_2_std_1.5_num_add_dfs_1": [0, 0, 0],
        }
    )


@pytest.fixture
def sol_all_predictions_csv() -> str:
    sol_filename = "tests/configs/sol_all_predictions_updated.csv"
    return sol_filename


@pytest.fixture
def eth_updated_predictions_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "date": ["2022-01-01", "2022-01-02", "2022-01-03"],
            "test_model_lookback_1": [1, 2, 3],
            "date_prediction_for": ["2022-01-05", "2022-01-06", "2022-01-07"],
            "nbeats_eth_lookback_2_window_2_std_1.5_num_add_dfs_1": [0, 0, 0],
            "tcn_eth_lookback_2_window_2_std_1.5_num_add_dfs_1": [0, 0, 0],
        }
    )


@pytest.fixture
def eth_all_predictions_csv() -> str:
    eth_filename = "tests/configs/eth_all_predictions_updated.csv"
    return eth_filename


# configs


@pytest.fixture
def eth_won_and_lost_constants() -> Dict[str, Any]:
    return read_in_yaml("tests/configs/eth_won_and_lost_config.yml", False)


@pytest.fixture
def btc_won_and_lost_constants() -> Dict[str, Any]:
    return read_in_yaml("tests/configs/btc_won_and_lost_config.yml", False)


@pytest.fixture
def sol_won_and_lost_constants() -> Dict[str, Any]:
    return read_in_yaml("tests/configs/sol_won_and_lost_config.yml", False)


@pytest.fixture
def constants() -> Dict[str, Any]:
    return read_in_yaml("tests/configs/constants.yml", False)


@pytest.fixture
def ml_config() -> Dict[str, Any]:
    return read_in_yaml("tests/configs/ml_config.yml", False)


@pytest.fixture
def eth_trading_state_config() -> Dict[str, Any]:
    return read_in_yaml("tests/configs/eth_trading_state_config.yml", False)


@pytest.fixture
def btc_trading_state_config() -> Dict[str, Any]:
    return read_in_yaml("tests/configs/btc_trading_state_config.yml", False)


@pytest.fixture
def sol_trading_state_config() -> Dict[str, Any]:
    return read_in_yaml("tests/configs/sol_trading_state_config.yml", False)


@pytest.fixture
def eth_trading_state_config_buy() -> Dict[str, Any]:
    return read_in_yaml("tests/configs/eth_trading_state_config_buy.yml", False)


@pytest.fixture
def btc_trading_state_config_short() -> Dict[str, Any]:
    return read_in_yaml("tests/configs/btc_trading_state_config_short.yml", False)


@pytest.fixture
def btc_trading_state_config_buy() -> Dict[str, Any]:
    return read_in_yaml("tests/configs/btc_trading_state_config_buy.yml", False)


@pytest.fixture
def btc_trading_state_config_short_stop_loss() -> Dict[str, Any]:
    return read_in_yaml("tests/configs/btc_trading_state_config_short_stop_loss.yml", False)


@pytest.fixture
def btc_actions_to_take_constants() -> Dict[str, Any]:
    return read_in_yaml("tests/configs/btc_actions_to_take.yml", False)


@pytest.fixture
def eth_actions_to_take_constants() -> Dict[str, Any]:
    return read_in_yaml("tests/configs/eth_actions_to_take.yml", False)


@pytest.fixture
def sol_actions_to_take_constants() -> Dict[str, Any]:
    return read_in_yaml("tests/configs/sol_actions_to_take.yml", False)


# Dataframes


@pytest.fixture
@freeze_time("2022-03-31")
def example_btc_df() -> pd.DataFrame:
    today = datetime.utcnow().date()
    print(today, "TODAY")
    df = pd.DataFrame(
        {
            "date": [
                pd.to_datetime(today - timedelta(days=3)),
                pd.to_datetime(today - timedelta(days=2)),
                pd.to_datetime(today - timedelta(days=1)),
            ],
            "open": [963.66, 993.66, 988],
            "high": [1103, 1031, 11024],
            "low": [958, 996, 978],
            "close": [958, 996, 982],
            "volume": [147775008, 222184992, 177875208],
        }
    )
    return df.set_index("date")


@pytest.fixture
@freeze_time("2022-03-31")
def example_sol_df() -> pd.DataFrame:
    today = datetime.utcnow().date()
    df = pd.DataFrame(
        {
            "date": [
                pd.to_datetime(today - timedelta(days=3)),
                pd.to_datetime(today - timedelta(days=2)),
                pd.to_datetime(today - timedelta(days=1)),
            ],
            "open": [963.66, 993.66, 988],
            "high": [1103, 1031, 11024],
            "low": [958, 996, 978],
            "close": [958, 996, 982],
            "volume": [147775008, 222184992, 177875208],
        }
    )
    return df.set_index("date")


@pytest.fixture
@freeze_time("2022-03-31")
def example_btc_df_bollinger_exit_position() -> pd.DataFrame:
    today = datetime.utcnow().date()
    df = pd.DataFrame(
        {
            "date": [
                pd.to_datetime(today - timedelta(days=3)),
                pd.to_datetime(today - timedelta(days=2)),
                pd.to_datetime(today - timedelta(days=1)),
            ],
            "open": [963.66, 993.66, 988],
            "high": [1103, 1031, 11024],
            "low": [958, 996, 978],
            "close": [958, 996, 982],
            "volume": [147775008, 222184992, 177875208],
            "Rolling Mean": [50, 50, 50],
            "Bollinger High": [1000, 900, 1000],
            "Bollinger Low": [1000, 900, 1000],
        }
    )
    return df.set_index("date")


@pytest.fixture
@freeze_time("2022-03-31")
def example_btc_df_bollinger_buy_to_none() -> pd.DataFrame:
    today = datetime.utcnow().date()
    df = pd.DataFrame(
        {
            "date": [
                pd.to_datetime(today - timedelta(days=3)),
                pd.to_datetime(today - timedelta(days=2)),
                pd.to_datetime(today - timedelta(days=1)),
            ],
            "open": [963.66, 993.66, 988],
            "high": [1103, 1031, 11024],
            "low": [958, 996, 978],
            "close": [958, 996, 400],
            "volume": [147775008, 222184992, 177875208],
            "Rolling Mean": [500, 500, 500],
            "Bollinger High": [1000, 900, 1000],
            "Bollinger Low": [1000, 900, 1000],
        }
    )
    return df.set_index("date")


@pytest.fixture
@freeze_time("2022-03-31")
def example_btc_df_bollinger_short() -> pd.DataFrame:
    today = datetime.utcnow().date()
    df = pd.DataFrame(
        {
            "date": [
                pd.to_datetime(today - timedelta(days=3)),
                pd.to_datetime(today - timedelta(days=2)),
                pd.to_datetime(today - timedelta(days=1)),
            ],
            "open": [963.66, 993.66, 988],
            "high": [1103, 1031, 11024],
            "low": [958, 996, 978],
            "close": [958, 800, 1500],
            "volume": [147775008, 222184992, 177875208],
            "Rolling Mean": [5000, 5000, 5000],
            "Bollinger High": [1000, 900, 1000],
            "Bollinger Low": [1000, 900, 1000],
        }
    )
    return df.set_index("date")


@pytest.fixture
@freeze_time("2022-03-31")
def example_eth_df() -> pd.DataFrame:
    today = datetime.utcnow().date()
    df = pd.DataFrame(
        {
            "date": [
                pd.to_datetime(today - timedelta(days=3)),
                pd.to_datetime(today - timedelta(days=2)),
                pd.to_datetime(today - timedelta(days=1)),
            ],
            "open": [7.98, 8.17, 9.12],
            "high": [8.47, 8.44, 10.12],
            "low": [7.98, 8.05, 5.65],
            "close": [8.17, 8.38, 8.01],
            "volume": [14731700, 14579600, 12579800],
            "Rolling Mean": [10, 10, 10],
            "Bollinger High": [10, 10, 10],
            "Bollinger Low": [10, 10, 10],
        }
    )
    return df.set_index("date")
