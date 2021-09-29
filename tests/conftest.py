import pytest
import pandas as pd
from datetime import date, timedelta

from app.mlcode.utils import read_in_constants


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
def example_btc_df_no_action():
    df = pd.DataFrame(
        {
            "date": [
                pd.to_datetime(date.today() - timedelta(days=3)),
                pd.to_datetime(date.today() - timedelta(days=2)),
                pd.to_datetime(date.today() - timedelta(days=1)),
            ],
            "open": [963.66, 993.66, 988],
            "high": [1103, 1031, 11024],
            "low": [958, 996, 9978],
            "close": [958, 996, 9982],
            "volume": [147775008, 222184992, 177875208],
        }
    )
    return df.set_index('date')


@pytest.fixture
def example_eth_df_no_action():
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
        }
    )
    return df.set_index('date')


@pytest.fixture
def example_btc_df_short():
    return None


@pytest.fixture
def example_btc_df_buy():
    return None


@pytest.fixture
def example_btc_df_buy_to_no_position():
    return None


@pytest.fixture
def example_btc_df_short_to_no_position():
    return None
