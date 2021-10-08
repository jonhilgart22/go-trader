FROM golang:1.17-stretch

# make directories / folders
RUN mkdir home home/app home/data home/app/csvutils home/app/ftx home/app/mlcode home/app/s3utils home/app/src home/app/structs

# pyenv
ENV HOME="/home"
WORKDIR ${HOME}


## PYTHON
ENV PYTHONUNBUFFERED=1
RUN  apt-get -y update && \
    apt-get -y install sudo && \
    sudo apt-get -y install gcc && \
    sudo apt-get -y clean && \
    sudo apt-get -y install apt-utils && \
    sudo apt-get -y install build-essential && \
    sudo apt-get -y install libssl-dev && \
    sudo apt-get -y install libpcap-dev && \
    sudo apt-get -y  install libpq-dev && \
    sudo apt-get -y install zlib1g-dev && \
    sudo apt-get -y install zlibc && \
    sudo apt-get -y install  ibssl1.0 && \
    sudo apt-get -y install libffi-dev && \
    sudo apt-get -y install git && \
    sudo apt-get -y install libsqlite3-dev && \
    sudo apt-get -y install libbz2-dev  && \
    sudo apt-get -y install liblzma-dev


RUN git clone --depth=1 https://github.com/pyenv/pyenv.git .pyenv
ENV PYENV_ROOT="${HOME}/.pyenv"
ENV PATH="${PYENV_ROOT}/shims:${PYENV_ROOT}/bin:/go/.pyenv/versions/3.7.8/bin:${PATH}"
ENV PYTHON_VERSION=3.7.8
RUN pyenv install ${PYTHON_VERSION}
RUN pyenv global ${PYTHON_VERSION}

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
COPY go.mod go.sum ./
ENV GO111MODULE=on

# Copy files over
ADD app app

RUN  go mod download 

RUN cd app/src && go build -o go-trader .

CMD  go run ./app/src/main.go