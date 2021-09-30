import pytest
import pandas as pd
from datetime import date, timedelta

from app.mlcode.utils import read_in_constants


@pytest.fixture
def won_and_lost_amount_constants():
    return read_in_constants("tests/configs/won_and_lost_amount_config.yml")


@pytest.fixture
def constants():
    return read_in_constants("tests/configs/constants.yml")


@pytest.fixture
def ml_config():
    return read_in_constants("tests/configs/ml_config.yml")


@pytest.fixture
def trading_state_config():
    return read_in_constants("tests/configs/trading_state_config.yml")


@pytest.fixture
def trading_state_config_buy():
    return read_in_constants("tests/configs/trading_state_config_buy.yml")


@pytest.fixture
def trading_state_config_short():
    return read_in_constants("tests/configs/trading_state_config_short.yml")


@pytest.fixture
def trading_state_config_short_stop_loss():
    return read_in_constants("tests/configs/trading_state_config_short_stop_loss.yml")


@pytest.fixture
def example_btc_df():
    df = pd.DataFrame(
        {
            "date": [
                pd.to_datetime(date.today() - timedelta(days=3)),
                pd.to_datetime(date.today() - timedelta(days=2)),
                pd.to_datetime(date.today() - timedelta(days=1)),
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
def example_btc_df_bollinger_exit_position():
    df = pd.DataFrame(
        {
            "date": [
                pd.to_datetime(date.today() - timedelta(days=3)),
                pd.to_datetime(date.today() - timedelta(days=2)),
                pd.to_datetime(date.today() - timedelta(days=1)),
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
def example_btc_df_bollinger_buy_to_no_position():
    df = pd.DataFrame(
        {
            "date": [
                pd.to_datetime(date.today() - timedelta(days=3)),
                pd.to_datetime(date.today() - timedelta(days=2)),
                pd.to_datetime(date.today() - timedelta(days=1)),
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
def example_btc_df_bollinger_short():
    df = pd.DataFrame(
        {
            "date": [
                pd.to_datetime(date.today() - timedelta(days=3)),
                pd.to_datetime(date.today() - timedelta(days=2)),
                pd.to_datetime(date.today() - timedelta(days=1)),
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
def example_eth_df():
    df = pd.DataFrame(
        {
            "date": [
                pd.to_datetime(date.today() - timedelta(days=3)),
                pd.to_datetime(date.today() - timedelta(days=2)),
                pd.to_datetime(date.today() - timedelta(days=1)),
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
