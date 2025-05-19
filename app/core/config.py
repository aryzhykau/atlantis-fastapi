import os

# API ключ для cron-задач
CRON_API_KEY: str = os.getenv("CRON_API_KEY", "your-secure-api-key-here")  # В продакшене установить через переменную окружения 