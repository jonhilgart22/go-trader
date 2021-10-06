FROM ubuntu:18.04

# make directories / folders
RUN mkdir app
RUN mkdir data
RUN mkdir app/csvutils
RUN mkdir app/ftx
RUN mkdir app/mlcode
RUN mkdir app/s3utils
RUN mkdir app/src
RUN mkdir app/structs

# COPY files over
ADD app app
COPY poetry.lock pyproject.toml ./
COPY go.mod go.sum ./

## PYTHON
# Install python/pip. Python3.7 is what is used in .toml
ENV PYTHONUNBUFFERED=1
RUN  apt-get -y update && \
    apt-get -y install sudo && \
    sudo apt-get -y install gcc && \
    sudo apt-get -y clean

# Python package management and basic dependencies
RUN apt-get install -y curl python3.7 python3.7-dev python3.7-distutils

# Register the version in alternatives
RUN update-alternatives --install /usr/bin/python python /usr/bin/python3.7 1

# Set python 3 as the default python
RUN update-alternatives --set python /usr/bin/python3.7

# Upgrade pip to latest version
RUN curl -s https://bootstrap.pypa.io/get-pip.py -o get-pip.py && \
    python get-pip.py --force-reinstall && \
    rm get-pip.py

RUN pip install --no-cache --upgrade pip setuptools
# System deps:
RUN pip install poetry

RUN set -x \
    && pip install --no-cache-dir --upgrade pip \
    && poetry export --without-hashes -f requirements.txt -o requirements.txt \
    && pip install --no-cache-dir -r requirements.txt \
    && rm requirements.txt

## GOLANG
# install build tools
RUN apt-get add go git
RUN go env -w GOPROXY=direct
# cache dependencies
RUN go mod download 

RUN go build -o /app/src/main

ENTRYPOINT [ "/app/src/main" ] 