#!/usr/bin/env python
import yaml
import pandas as pd
import logging
from logging import config

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


def update_yaml_config(file_name: str, data):
    with open(file_name, "w") as yaml_file:
        yaml_file.write(yaml.dump(data, default_flow_style=False))


def read_in_yaml(input_file: str):
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


def read_in_data(input_file: str) -> pd.DataFrame:
    logger.info(f"Input file {input_file}")
    df = pd.read_csv(input_file, index_col=0, parse_dates=True)
    logger.info(df.head())
    logger.info(df.tail())
    logger.info("---")
    return df
