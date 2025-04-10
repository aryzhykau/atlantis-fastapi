FROM python:3.10
WORKDIR /api
COPY ./pyproject.toml /api/pyproject.toml
COPY ./poetry.lock /api/poetry.lock
# RUN apt-get update && apt-get upgrade -y
# RUN  curl -sSL https://raw.githubusercontent.com/python-poetry/poetry/master/
#get-poetry.py | python -
#RUN bash -c "source $HOME/.poetry/env"
RUN pip install poetry
RUN poetry install --no-root
COPY . .
COPY ./entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]

