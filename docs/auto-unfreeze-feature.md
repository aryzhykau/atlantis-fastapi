# Авторазморозка абонементов

## Обзор

Система автоматической разморозки абонементов позволяет сбрасывать поля заморозки (`freeze_start_date` и `freeze_end_date`) для абонементов, у которых период заморозки уже закончился.

## Как это работает

### Ручной запуск через API
- Администраторы могут запустить авторазморозку в любое время через API endpoint
- Система находит все абонементы с `freeze_end_date < текущее_время`
- Поля `freeze_start_date` и `freeze_end_date` сбрасываются в `None`
- Возвращается список размороженных абонементов

### Внешний планировщик
Рекомендуется настроить внешний планировщик (cron, systemd timer, etc.) для регулярного вызова API endpoint.

Пример cron задачи для запуска каждый день в 01:00:
```bash
0 1 * * * curl -X POST "http://localhost:8000/subscriptions/auto-unfreeze" \
  -H "Authorization: Bearer <admin_token>"
```

## API Endpoints

### Авторазморозка всех истёкших абонементов
```http
POST /subscriptions/auto-unfreeze
X-API-Key: <your-secure-api-key-here>
```

**Ответ:**
```json
[
  {
    "id": 1,
    "student_id": 123,
    "subscription_id": 456,
    "freeze_start_date": null,
    "freeze_end_date": null,
    "status": "active",
    "sessions_left": 8,
    "transferred_sessions": 0,
    "auto_renewal_invoice_id": null,
    "start_date": "2025-07-04T22:20:12.771708",
    "end_date": "2025-08-03T22:20:12.771708",
    "is_auto_renew": false
  }
]
```

## Права доступа

Endpoint защищен API ключом:
- Авторазморозка: требует валидный API ключ в заголовке `X-API-Key`
- API ключ настраивается через переменную окружения `CRON_API_KEY`

## Техническая реализация

### Сервис
```python
class SubscriptionService:
    def auto_unfreeze_expired_subscriptions(self, admin_id: int) -> List[StudentSubscription]:
        """
        Автоматически размораживает абонементы, у которых период заморозки уже закончился.
        """
        current_time = datetime.now(timezone.utc)
        
        expired_frozen_subscriptions = (
            self.db.query(StudentSubscription)
            .filter(
                and_(
                    StudentSubscription.freeze_end_date.isnot(None),
                    StudentSubscription.freeze_end_date < current_time
                )
            )
            .all()
        )
        
        unfrozen_subscriptions = []
        for subscription in expired_frozen_subscriptions:
            logger.info(f"Auto-unfreezing subscription {subscription.id} for student {subscription.student_id}")
            
            # Сбрасываем поля заморозки
            subscription.freeze_start_date = None
            subscription.freeze_end_date = None
            
            unfrozen_subscriptions.append(subscription)
        
        if unfrozen_subscriptions:
            self.db.commit()
            for subscription in unfrozen_subscriptions:
                self.db.refresh(subscription)
            
            logger.info(f"Auto-unfroze {len(unfrozen_subscriptions)} subscriptions")
        
        return unfrozen_subscriptions
```

## Логирование

Все операции авторазморозки логируются:
- Выполнение авторазморозки
- Количество размороженных абонементов
- Ошибки при выполнении

## Примеры использования

### 1. Ручной запуск авторазморозки
```bash
curl -X POST "http://localhost:8000/subscriptions/auto-unfreeze" \
  -H "X-API-Key: your-secure-api-key-here"
```

### 2. Настройка cron для автоматического запуска
```bash
# Добавить в crontab (crontab -e)
0 1 * * * curl -X POST "http://localhost:8000/subscriptions/auto-unfreeze" \
  -H "X-API-Key: your-secure-api-key-here" \
  -H "Content-Type: application/json"
```

### 3. Настройка systemd timer
Создать файл `/etc/systemd/system/auto-unfreeze.service`:
```ini
[Unit]
Description=Auto-unfreeze subscriptions
After=network.target

[Service]
Type=oneshot
ExecStart=/usr/bin/curl -X POST "http://localhost:8000/subscriptions/auto-unfreeze" \
  -H "X-API-Key: your-secure-api-key-here"
User=www-data
```

Создать файл `/etc/systemd/system/auto-unfreeze.timer`:
```ini
[Unit]
Description=Run auto-unfreeze daily at 01:00

[Timer]
OnCalendar=*-*-* 01:00:00
Persistent=true

[Install]
WantedBy=timers.target
```

Затем активировать:
```bash
sudo systemctl enable auto-unfreeze.timer
sudo systemctl start auto-unfreeze.timer
```

## Безопасность

- Endpoint защищен API ключом (передается в заголовке X-API-Key)
- API ключ настраивается через переменную окружения CRON_API_KEY
- Все операции логируются для аудита
- Возвращается список изменённых абонементов для контроля
- Система автоматически находит администратора для выполнения операций

## Мониторинг

Рекомендуется мониторить:
- Количество размороженных абонементов
- Ошибки в логах API
- Время выполнения авторазморозки
- Статус внешнего планировщика (cron/systemd)

## Troubleshooting

### Авторазморозка не работает
1. Проверьте API ключ (должен быть валидный CRON_API_KEY)
2. Проверьте, что есть абонементы с истёкшей заморозкой
3. Проверьте логи на наличие ошибок
4. Убедитесь, что API доступен
5. Убедитесь, что в системе есть пользователь с ролью ADMIN

### Внешний планировщик не работает
1. Проверьте, что cron/systemd timer настроен правильно
2. Проверьте логи планировщика
3. Убедитесь, что API endpoint доступен
4. Проверьте, что API ключ действителен и правильно передается

### Нет размороженных абонементов
1. Проверьте, что есть абонементы с `freeze_end_date < текущее_время`
2. Убедитесь, что поля `freeze_end_date` не пустые
3. Проверьте логи на наличие ошибок 