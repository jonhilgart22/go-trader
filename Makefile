PHONY: clean setup upload_models upload_data install run_go run_python test_python upload_configs update_lambda download_configs compile_go

PYTHON_VERSION=3.7.8

install:
	hash pyenv || brew install pyenv
	pyenv install ${PYTHON_VERSION} -s
	pyenv local ${PYTHON_VERSION}
	hash poetry || curl -sSL https://raw.githubusercontent.com/python-poetry/poetry/master/get-poetry.py | python
	poetry run pip install --upgrade pip
	poetry install --no-root
	pre-commit install
	hash go || brew install go
	hash golangci-lint || brew install golangci-lint
	hash tfswitch || brew install tfswtich

lint: install
	poetry run isort .
	poetry run black .
	poetry run flake8
	poetry run mypy .
	golangci-lint run

clean:
	rm -rf notebooks/.darts

run_go:
	go run app/src/main.go

test_python:
	poetry run  python -m pytest -vs

run_python:
	python -m app.mlcode.main --coin_to_predict btc

# update_lambda:
# 	aws lambda update-function-code --function-name go-trader-function  	--image-uri $(aws lambda get-function --function-name go-trader-function | jq -r '.Code.ImageUri')

upload_configs:
	aws s3 cp app/actions_to_take.yml s3://go-trader/app/actions_to_take.yml --sse aws:kms 
	aws s3 cp app/constants.yml s3://go-trader/app/constants.yml --sse aws:kms 
	aws s3 cp app/ml_config.yml s3://go-trader/app/ml_config.yml --sse aws:kms 
	aws s3 cp app/trading_state_config.yml s3://go-trader/app/trading_state_config.yml --sse aws:kms 
	aws s3 cp env_vars.sh s3://go-trader/env_vars.sh --sse aws:kms 

download_configs:
	aws s3 cp s3://go-trader/app/actions_to_take.yml  app/actions_to_take.yml --sse aws:kms 
	aws s3 cp app/constants.yml s3://go-trader/app/constants.yml  cp app/constants.yml  --sse aws:kms 
	aws s3 cp s3://go-trader/app/ml_config.yml app/ml_config.yml  --sse aws:kms 
	aws s3 cp s3://go-trader/app/trading_state_config.yml   app/trading_state_config.yml --sse aws:kms 

update_image:
	aws --profile lambda-model \
  lambda \
  update-function-code \
  --function-name go-trader-function \
  --image-uri 950264656373.dkr.ecr.us-east-1.amazonaws.com/go-trader:latest

# upload_models:
#  	aws s3 cp ./models/checkpoints/31_tcn_eth/checkpoint_5649.pth.tar s3://go-trader/models/checkpoints/31_tcn_eth/checkpoint_5649.pth.tar --sse aws:kms 
# 	aws s3 cp ./models/checkpoints/31_tcn_btc/checkpoint_4499.pth.tar s3://go-trader/models/checkpoints/31_tcn_btc/checkpoint_4499.pth.tar --sse aws:kms
# 	aws s3 cp ./models/checkpoints/31_nbeats_btc/checkpoint_257.pth.tar s3://go-trader/models/checkpoints/31_nbeats_btc/checkpoint_257.pth.tar --sse aws:kms
# 	aws s3 cp ./models/checkpoints/31_nbeats_eth/checkpoint_257.pth.tar s3://go-trader/models/checkpoints/31_nbeats_eth/checkpoint_257.pth.tar --sse aws:kms

# upload_data:
# 	aws s3 cp "./data/historic_crypto_prices - bitcoin_jan_2017_sep_4_2021 copy.csv" "s3://go-trader/data/historic_crypto_prices - bitcoin_jan_2017_sep_4_2021 copy.csv" --sse aws:kms
# 	aws s3 cp "./data/historic_crypto_prices - etherum_jan_2017_sept_4_2021.csv" "s3://go-trader/data/historic_crypto_prices - etherum_jan_2017_sept_4_2021 copy.csv" --sse aws:kms
# aws s3 cp "data/historic_crypto_prices - SPY_historical.csv" "s3://go-trader/data/historic_crypto_prices - SPY_historical.csv" --sse aws:kms

# download_data:
# aws s3 cp "s3://go-trader/data/historic_crypto_prices - bitcoin_jan_2017_sep_4_2021 copy.csv" "./data/historic_crypto_prices - bitcoin_jan_2017_sep_4_2021 copy.csv"  --sse aws:kms
# aws s3 cp  "s3://go-trader/data/historic_crypto_prices - etherum_jan_2017_sept_4_2021 copy.csv" "./data/historic_crypto_prices - etherum_jan_2017_sept_4_2021 copy.csv" --sse aws:kms

# compile_golang
# compile_go:
# 	docker run --rm -v "$PWD":/go/src/handler lambci/lambda:build-go1.x sh -c 'go build app/src/main.go'

## run_golang_btc
# docker run --rm -e  ON_LOCAL=true -v "$HOME"/.aws:/home/sbx_user1051/.aws:ro -v "$PWD":/var/task lambci/lambda:go1.x  main '{"coinToPredict": "btc"}'

## run_golang_eth
# docker run --rm -e  ON_LOCAL=true -v "$HOME"/.aws:/home/sbx_user1051/.aws:ro -v "$PWD":/var/task lambci/lambda:go1.x   main '{"coinToPredict": "eth"}'
