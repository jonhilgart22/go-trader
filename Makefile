PHONY: clean setup upload_model upload_data
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

upload_model:
 	aws s3 cp "./models/nbeats_btc_30_days.pth.tar" s3://go-trader/models/nbeats_btc_30_days.pth.tar --sse aws:kms

upload_data:
	aws s3 cp "./data/historic_crypto_prices - bitcoin_jan_2017_sept_4_2021 copy.csv" "s3://go-trader/data/historic_crypto_prices - bitcoin_jan_2017_sept_4_2021 copy.csv" --sse aws:kms
	aws s3 cp "./data/historic_crypto_prices - etherum_jan_2017_sept_4_2021.csv" "s3://go-trader/data/historic_crypto_prices - etherum_jan_2017_sept_4_2021 copy.csv" --sse aws:kms