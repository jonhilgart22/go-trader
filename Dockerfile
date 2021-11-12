FROM lambci/lambda:build-python3.8

# make directories / folders
RUN mkdir app app/utils app/ftx app/mlcode app/awsUtils app/src app/structs

## PYTHON
# COPY poetry env over
COPY poetry.lock pyproject.toml ./

# Poetry install
RUN  pip install poetry
RUN set -x \
    && pip install --no-cache-dir --upgrade pip \
    && pip install wheel  \
    && poetry export --without-hashes -f requirements.txt -o requirements.txt \
    && pip install --no-cache-dir -r requirements.txt \
    && rm requirements.txt

## GOLANG
RUN yum -y install go
RUN echo $(ls)
ENV PATH="/usr/local/go/bin:${PATH}"

COPY go.mod go.sum ./
ENV GO111MODULE=on

RUN  go mod download

# Copy files over
ADD app app
# except the configs
RUN rm app/actions_to_take.yml
RUN rm app/ml_config.yml
RUN rm app/constants.yml
RUN rm app/trading_state_config.yml
RUN rm app/won_and_lost_amount_config.yml


RUN cd app/src && go build -o go-trader .

ENTRYPOINT  ["app/src/go-trader"]
