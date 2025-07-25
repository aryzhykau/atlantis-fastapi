# Сценарий: Запись на тренировку

## Участники
- Клиент
- Система
- Администратор (опционально)

## Предусловия
1. Клиент авторизован в системе
2. У клиента есть активная подписка
3. Тренировка доступна для записи

## Основной сценарий

### 1. Выбор тренировки
**Клиент**:
1. Открывает расписание тренировок
2. Фильтрует по нужным параметрам (дата, тип, тренер)
3. Выбирает конкретную тренировку

**Система**:
1. Отображает детали тренировки:
   - Тип тренировки
   - Время и дата
   - Тренер
   - Количество свободных мест

### 2. Проверка возможности записи
**Система проверяет**:
1. Наличие свободных мест
2. Активность подписки клиента
3. Отсутствие пересечений в расписании клиента
4. Отсутствие записи на эту тренировку
5. Соответствие уровня клиента

### 3. Подтверждение записи
**Клиент**:
1. Подтверждает запись на тренировку

**Система**:
1. Создает запись в базе данных
2. Обновляет количество свободных мест
3. Добавляет тренировку в расписание клиента
4. Отправляет подтверждение

## Альтернативные сценарии

### А. Нет свободных мест
1. Система информирует о отсутствии мест
2. Предлагает:
   - Записаться в лист ожидания
   - Выбрать другую тренировку

### Б. Неактивная подписка
1. Система информирует о необходимости продления
2. Предлагает:
   - Продлить подписку
   - Купить разовое занятие

### В. Конфликт в расписании
1. Система показывает конфликтующую тренировку
2. Предлагает:
   - Отменить существующую запись
   - Выбрать другое время

## Постусловия
1. Клиент записан на тренировку
2. Место в группе зарезервировано
3. Тренировка появилась в расписании клиента

## Исключения
1. Технический сбой при записи
2. Отмена тренировки до её начала
3. Изменение расписания тренером

## Реализация

### API Endpoints
```python
# Запись на тренировку
POST /real-trainings/{training_id}/students
{
    "student_id": int,
    "template_student_id": int (optional)
}

# Проверка возможности записи
GET /real-trainings/{training_id}/availability
{
    "student_id": int
}
```

### Бизнес-логика
Основная логика реализована в:
- [`app/crud/real_training.py`](../../../app/crud/real_training.py)
- [`app/endpoints/real_trainings.py`](../../../app/endpoints/real_trainings.py)

## Связанные сценарии
- [Отмена записи на тренировку](./canceling-booking.md)
- [Изменение расписания](./schedule-change.md)
- [Управление листом ожидания](./waitlist-management.md) 