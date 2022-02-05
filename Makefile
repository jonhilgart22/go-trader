PHONY: clean setup upload_models upload_data install run_go run_python test_python upload_configs_and_data update_lambda download_configs_and_data compile_go update_lambda run_golang_btc run_golang_eth coverage_go coverage_python test_go

PYTHON_VERSION=3.8.2

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
	go vet ./...
	go fmt ./...

clean:
	rm -rf notebooks/.darts

run_go:
	go run app/src/main.go

test_python:
	poetry run  python -m pytest -vs

test_go:
	go test -v ./...

run_python:
	python -m app.mlcode.main --coin_to_predict btc

# we make sure to download first. However, if you've already downloaded, you can copy the upload command
upload_configs_and_data: download_configs_and_data
	aws s3 cp tmp/   s3://go-trader/tmp/  --sse aws:kms --recursive

download_configs_and_data:
	aws s3 cp s3://go-trader/tmp/  tmp/ --sse aws:kms --recursive


# Constants never changes, no need to download it
#aws s3 cp s3://go-trader/tmp/constants.yml   tmp/constants.yml  --sse aws:kms

update_lambda:
	aws lambda update-function-code --function-name go-trader-function --image-uri $(aws lambda get-function --function-name go-trader-function | jq -r '.Code.ImageUri')

# upload_models:
#  	aws s3 cp ./models/checkpoints/31_tcn_eth/checkpoint_5649.pth.tar s3://go-trader/models/checkpoints/31_tcn_eth/checkpoint_5649.pth.tar --sse aws:kms
# 	aws s3 cp ./models/checkpoints/31_tcn_btc/checkpoint_4499.pth.tar s3://go-trader/models/checkpoints/31_tcn_btc/checkpoint_4499.pth.tar --sse aws:kms
# 	aws s3 cp ./models/checkpoints/31_nbeats_btc/checkpoint_257.pth.tar s3://go-trader/models/checkpoints/31_nbeats_btc/checkpoint_257.pth.tar --sse aws:kms
# 	aws s3 cp ./models/checkpoints/31_nbeats_eth/checkpoint_257.pth.tar s3://go-trader/models/checkpoints/31_nbeats_eth/checkpoint_257.pth.tar --sse aws:kms

upload_data:
	aws s3 cp data/ s3://go-trader/data --sse aws:kms --recursive
# aws s3 cp   "./data/historic_crypto_prices - sol_jan_2017_oct_18_2021.csv"  "s3://go-trader/data/historic_crypto_prices - sol_jan_2017_oct_18_2021.csv" --sse aws:kms

download_data:
	aws s3 cp s3://go-trader/data data/  --sse aws:kms --recursive
# aws s3 cp "s3://go-trader/data/historic_crypto_prices - bitcoin_jan_2017_sep_4_2021 copy.csv" "./data/historic_crypto_prices - bitcoin_jan_2017_sep_4_2021 copy.csv"  --sse aws:kms
# aws s3 cp  "s3://go-trader/data/historic_crypto_prices - etherum_jan_2017_sept_4_2021 copy.csv" "./data/historic_crypto_prices - etherum_jan_2017_sept_4_2021 copy.csv" --sse aws:kms
# aws s3 cp  "s3://go-trader/data/historic_crypto_prices - sol_jan_2017_oct_18_2021.csv" "./data/historic_crypto_prices - sol_jan_2017_oct_18_2021.csv" --sse aws:kms

# compile_golang
compile_go:
	docker run --rm -v "$PWD":/go/src/handler lambci/lambda:build-go1.x sh -c 'go build app/src/main.go'

## mount the tmp folders
run_golang_btc:
	docker run --rm -e  ON_LOCAL=true -v "$HOME"/.aws:/home/sbx_user1051/.aws:ro -v "$(pwd)"/tmp:/tmp -v "$PWD":/var/task lambci/lambda:go1.x  main '{"coinToPredict": "btc"}'

run_golang_eth:
	docker run --rm -e  ON_LOCAL=true -v "$HOME"/.aws:/home/sbx_user1051/.aws:ro -v "$(pwd)"/tmp:/tmp  -v "$PWD":/var/task lambci/lambda:go1.x   main '{"coinToPredict": "eth"}'

run_golang_sol:
	docker run --rm -e  ON_LOCAL=true -v "$HOME"/.aws:/home/sbx_user1051/.aws:ro -v "$(pwd)"/tmp:/tmp  -v "$PWD":/var/task lambci/lambda:go1.x   main '{"coinToPredict": "sol"}'

clean_up_efs:
	terraform destroy -target=aws_efs_file_system.efs_for_lambda
	terraform apply -target=aws_efs_file_system.efs_for_lambda

coverage_go:
	go test ./... -coverprofile cover.out

coverage_python:
	poetry run coverage run -m pytest  && poetry run coverage report -m
