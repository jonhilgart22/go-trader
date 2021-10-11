#!/usr/bin/env python
import logging
from datetime import datetime
from logging import config
import os
import pandas as pd
import yaml
from typing import Dict, Any

log_config = {
    "version": 1,
    "root": {"handlers": ["console"], "level": "INFO"},
    "handlers": {
        "console": {
            "formatter": "std_out",
            "class": "logging.StreamHandler",
            "level": "INFO",
        }
    },
    "formatters": {
        "std_out": {
            "format": "[%(asctime)s] : %(levelname)s : %(module)s : %(funcName)s : %(lineno)d  %(message)s",
            "datefmt": "%m-%d-%Y %I:%M:%S",
        }
    },
}

config.dictConfig(log_config)

logger = logging.getLogger(__name__)


def update_yaml_config(file_name: str, data: Dict[str, Any], running_on_aws: bool):
    if running_on_aws:
        file_name = "tmp/" + file_name
    with open(file_name, "w") as yaml_file:
        yaml_file.write(yaml.dump(data, default_flow_style=False))


def read_in_yaml(input_file: str, running_on_aws: bool):
    if running_on_aws:
        input_file = "tmp/" + input_file

    logger.info(f"Reading in {input_file}")
    with open(input_file, "r") as stream:
        try:
            constants = yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            logger.error(exc)
            return

    for k, v in constants.items():
        logger.info(f"Key = {k} Value = {v}")
    logger.info("----------")
    return constants


def running_on_aws() -> bool:
    return os.environ.get("AWS_EXECUTION_ENV") is not None


def read_in_data(input_file: str, running_on_aws: bool, missing_dates: bool = False) -> pd.DataFrame:
    if running_on_aws:
        input_file = "tmp/" + input_file
    logger.info(f"Input file {input_file}")
    df = pd.read_csv(input_file, index_col=0, parse_dates=True)  # dates are index
    df = df.sort_index()  # ensure monotonic
    if missing_dates:  # for SPY
        idx = pd.date_range(df.index.min(), datetime.utcnow().date())
        df.index = pd.DatetimeIndex(df.index)
        df = df.reindex(idx, method="ffill")
        df.index = df.index.rename("date")
    logger.info(df.head())
    logger.info(df.tail())
    logger.info("---")
    return df
