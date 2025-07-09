FROM python:3.10-slim

WORKDIR /api

# Установка uv
RUN pip install uv

# Копирование файлов зависимостей
COPY pyproject.toml uv.lock ./

# Установка зависимостей через uv
RUN uv sync --frozen

# Копирование исходного кода
COPY . .

# Копирование и настройка entrypoint
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
CMD ["startapp"]

