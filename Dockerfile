FROM python:3.10
WORKDIR /api

RUN pip install poetry


# RUN apt-get update && apt-get upgrade -y
# RUN  curl -sSL https://raw.githubusercontent.com/python-poetry/poetry/master/
#get-poetry.py | python -
#RUN bash -c "source $HOME/.poetry/env"

COPY ./pyproject.toml /api/pyproject.toml

RUN poetry install --no-root

COPY . .

COPY ./entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
CMD ["startapp"]

