
# Go Trader

- Golang lambda app that trigger buy signals alongside a Python ML model

![bollinger](media/bollinger.png)

1. `wget http://api.bitcoincharts.com/v1/csv/localbtcUSD.csv.gz`
- This data is used in `notebooks/testing_bollinger_bands_and_ts_models.ipynb`
2. Manually scrape data from [https://coinmarketcap.com/](https://coinmarketcap.com/)
- This data is more recent, up to 09-04-2021, and is used in `notebooks/bollinger_bands_and_coinbase_data.ipynb`
3. Download SPY data from [here](https://www.nasdaq.com/market-activity/funds-and-etfs/spy/historical)
   

## Architecture

1. The go app handles connecting to the FTX exchange, pulling down data from/pushing up data to  S3, adding the new data, launching the python program, and executing orders
2. The Python program trains the ML models, builds the Bollinger Bands, predict whether to enter/exit trades and returns current trade information to the golang app.

## Data

- All data is store in S3 in `s3://go-trader/data`

## Models

- Stored in S3 in `s3://go-trader/models`

## Deployment

### Infrastructure

- All contained in the `terraform/` directory. This project uses   `tfswitch` to change between Terraform versions.
1. `bash terraform plan`
2. `bash terraform apply`
Helpful Terraform article for VPC lambdas [here](https://www.maxivanov.io/deploy-aws-lambda-to-vpc-with-terraform/)

S3 bucket: `go-trader`


### CI/CD

- Use act to test locally
- `bash brew install act`
- run act `bash act`

### Deploy

1. Make any config changes and then `make upload_configs`
2. Build and push the docker image `./build.sh`
3. If you need to update any env vars, use the `scripts/set_ssm.sh` script with the name and value
4. Update the Docker Image for the lambda if you've build a new one
- `aws lambda update-function-code --function-name go-trader-function --image-uri $(aws lambda get-function --function-name go-trader-function | jq -r '.Code.ImageUri')`
5. Wait for the next Lambda run! 

## Testing

1. New Python code
- `make run_python`
2. New Golang code (need to build the go binary and run it as if it were a lambda)
- `docker run --rm -v "$PWD":/go/src/handler lambci/lambda:build-go1.x sh -c 'go build app/src/main.go'`
- ` docker run --rm -v "$HOME"/.aws:/home/sbx_user1051/.aws:ro -v "$PWD":/var/task lambci/lambda:go1.x   main '{"Records": []}'`
   
## Performance

- View the different model performance results [here](https://docs.google.com/spreadsheets/d/1xEaxfYBcXNcGN71LAj_Yw-EDEifm_MficTvFqpLUR3s/edit?usp=sharing)
- 