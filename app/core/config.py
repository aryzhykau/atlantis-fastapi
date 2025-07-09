import os

# API ключ для cron-задач
CRON_API_KEY: str = os.getenv("CRON_API_KEY", "test-cron-api-key-12345")  # В продакшене установить через переменную окружения 