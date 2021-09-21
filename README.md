
# Go Trader
- Golang build Bollinger bands that trigger buy signals alongside a Python ML model

1. `wget http://api.bitcoincharts.com/v1/csv/localbtcUSD.csv.gz`
- This data is used in `notebooks/testing_bollinger_bands_and_ts_models.ipynb`
2. Manually scrape datat from [https://coinmarketcap.com/](https://coinmarketcap.com/)
- This data is more recent, up to 09-04-2021, and is used in `notebooks/bollinger_bands_and_coinbase_data.ipynb`

## Architecture

1. The go app handles connecting to the FTX exchange, pulling down data from/pushing up data to  S3, adding the new data, launching the python program, and executing orders
2. The Python program trains the ML models, builds the Bollinger Bands, predict whether to enter/exit trades and returns current trade information to the golang app.

## Performance

- View the different model performance results [here](https://docs.google.com/spreadsheets/d/1xEaxfYBcXNcGN71LAj_Yw-EDEifm_MficTvFqpLUR3s/edit?usp=sharing)