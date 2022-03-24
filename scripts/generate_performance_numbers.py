import glob
import logging

import click
import yaml

logging.basicConfig(format="%(asctime)s %(message)s", datefmt="%m/%d/%Y %I:%M:%S %p", level=logging.INFO)


@click.command()
@click.option("--directory", default="tmp", help="The directory where the won_and_lost configs are")
@click.option("--file_name_glob", default="won_and_lost_config", help="the name in the files to parse")
def main(directory: str, file_name_glob: str):
    if not validate_downloaded_configs():
        return "Need to download the configs. make download_configs_and_data"

    logging.info(f"Directory: {directory}")
    logging.info(f"File name glob: {file_name_glob}")

    total_dollars_won = 0
    total_n_won = 0
    total_dollars_lost = 0
    total_n_lost = 0

    for file in glob.glob(f"{directory}/*"):
        if file_name_glob in file:
            logging.info(f"File = {file}")
            coin = file.split("_")[0]
            logging.info("______________")
            logging.info(f"Coin = {coin}")
            logging.info(f"Parsing results for coin {coin}")
            with open(file, "r") as stream:
                try:
                    loaded_yaml = yaml.safe_load(stream)
                    dollars_won_for_this_coin = loaded_yaml["dollar_amount_buy_won"]
                    dollars_lost_for_this_coin = loaded_yaml["dollar_amount_buy_lost"]
                    n_won_for_this_coin = loaded_yaml["n_buy_won"]
                    n_lost_for_this_coin = loaded_yaml["n_buy_lost"]

                    pct_return = ((dollars_won_for_this_coin / max(dollars_lost_for_this_coin, 1)) - 1) * 100
                    total_dollars_won += dollars_won_for_this_coin
                    total_dollars_lost += dollars_lost_for_this_coin
                    total_n_won += n_won_for_this_coin
                    total_n_lost += n_lost_for_this_coin

                    logging.info(f"Total n won  for this coin= { n_won_for_this_coin:.2f}")
                    logging.info(f"Total n lost for this coin = { n_lost_for_this_coin:.2f}")
                    logging.info(f"total_dollars_won for this coin = {dollars_won_for_this_coin:.2f}")
                    logging.info(f"total_dollars_lost for this coin = { dollars_lost_for_this_coin:.2f}")
                    logging.info(f"Percent return = {pct_return}%")

                except yaml.YAMLError as exc:
                    print(exc)
    logging.info("-----------")
    logging.info(f"Total won = {total_dollars_won}")
    logging.info(f"Total lost = {total_dollars_lost}")
    logging.info(f"Total return = { ((total_dollars_won /  (total_dollars_lost) ) -1)  * 100}%")
    logging.info(f"Total n trades = {total_n_won + total_n_lost:.2f}")
    logging.info(f"Bat rate = {total_n_won / (total_n_won + total_n_lost)*100:.2f}%")
    logging.info(
        f"Won or lost per trade = {(total_dollars_won -  total_dollars_lost)/( total_n_won + total_n_lost) : .2f}"
    )


def validate_downloaded_configs():
    """
    Validates that you downloaded  configs.
    """
    val = input("Did you download the configs (y,yes,n,no) ")
    if val.lower() in ["yes", "y"]:
        return True
    else:
        return False


# def read_in_yaml_files():
#     """
#     Reads in the yaml files and returns a dataframe.
#     """
#     df = pd.read_csv('configs.csv')
#     return df

#     with open("example.yaml", "r") as stream:
#         try:
#             print(yaml.safe_load(stream))
#         except yaml.YAMLError as exc:
#             print(exc)

if __name__ == "__main__":
    main()
