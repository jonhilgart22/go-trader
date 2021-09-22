#!/usr/local/bin/python
import yaml
import pandas as pd


def read_in_constants(input_file: str):
    with open(input_file, "r") as stream:
        try:
            constants = yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            print(exc)

    for k, v in constants.items():
        print(f"Key = {k} Value = {v}")
    return constants


def read_in_data(input_file: str) -> pd.DataFrame:
    df = pd.read_csv(input_file, index_col=0, parse_dates=True)
    print(df.head())
    print(df.tail())

    return


def main():
    constants = read_in_constants("app/constants.yml")
    bitcoin_df = read_in_data(constants["bitcoin_filename"])

    return


if __name__ == "__main__":
    main()
