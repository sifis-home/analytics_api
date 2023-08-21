FROM python:3.10
ENV PYTHONPATH=${PYTHONPATH}:${PWD}
RUN python -m pip install --upgrade pip
RUN pip install poetry

RUN mkdir /analytics_api
WORKDIR /analytics_api
COPY analytics_api.py /analytics_api
COPY check.py /analytics_api
COPY pyproject.toml /analytics_api

RUN poetry config virtualenvs.create false
RUN poetry install

# Install Docker from Docker Inc. repositories.
# RUN curl -sSL https://get.docker.com/ | sh

USER root
RUN apt-get update && apt-get -y install sudo
RUN apt-get update && apt-get -y  install docker
RUN apt-get update && apt-get -y  install docker.io

CMD ["python", "analytics_api.py"]