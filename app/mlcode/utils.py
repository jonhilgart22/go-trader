#!/usr/bin/env python
import logging
import os
from datetime import datetime
from typing import Any, Dict, Union

import pandas as pd
import yaml

__all__ = ["setup_logging", "update_yaml_config", "read_in_data", "running_on_aws", "read_in_yaml"]


def setup_logging() -> logging.Logger:

    root = logging.getLogger()
    if root.handlers:
        for handler in root.handlers:
            root.removeHandler(handler)

    logging.basicConfig(format="%(asctime)s: : %(funcName)s  %(message)s", level=logging.INFO)

    return logging.getLogger(__name__)


logger = setup_logging()


def update_yaml_config(file_name: str, data: Dict[str, Any], running_on_aws: bool) -> None:
    if running_on_aws:
        s = file_name.split("/")
        file_name = "/tmp/" + s[-1]
    with open(file_name, "w") as yaml_file:
        logger.info(f"Updating {file_name} with {data}")
        yaml_file.write(yaml.dump(data, default_flow_style=False))


def read_in_yaml(input_file: str, running_on_aws: bool) -> Union[Dict[str, Any], ValueError]:
    if running_on_aws:
        s = input_file.split("/")
        input_file = "/tmp/" + s[-1]

    logger.info(f"Reading in {input_file}")
    with open(input_file, "r") as stream:
        try:
            constants = yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            logger.error(exc)
            raise ValueError(f" Incorrect YAML file {input_file}")

    for k, v in constants.items():
        logger.info(f"Key = {k} Value = {v}")
    logger.info("----------")
    return constants


def running_on_aws() -> bool:
    return os.environ.get("AWS_EXECUTION_ENV") is not None


def read_in_data(
    input_file: str,
    running_on_aws: bool,
    date_col: str,
    missing_dates: bool = False,
) -> pd.DataFrame:
    if running_on_aws:
        input_file
        s = input_file.split("/")
        input_file = "/tmp/" + s[-1]
    logger.info(f"Input file {input_file}")
    df = pd.read_csv(input_file, index_col=0, parse_dates=True)  # dates are index
    df = df.sort_index()  # ensure monotonic
    if missing_dates:  # for SPY
        idx = pd.date_range(df.index.min(), datetime.utcnow().date())
        df.index = pd.DatetimeIndex(df.index)
        df = df.reindex(idx, method="ffill")
        df.index = df.index.rename(date_col)
    logger.info(df.head())
    logger.info(df.tail())
    logger.info("---")
    return df
