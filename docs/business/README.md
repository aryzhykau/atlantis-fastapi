# Бизнес-логика Atlantis

## Основные бизнес-сущности

### [Пользователи](./entities/users.md)
- Клиенты
- Тренеры
- Администраторы
- Роли и права доступа

### [Тренировки](./entities/trainings.md)
- Типы тренировок
- Шаблоны тренировок
- Реальные тренировки
- Посещаемость

### [Расписание](./entities/schedule.md)
- Временные слоты
- Регулярные тренировки
- Отмены и переносы

### [Платежи](./entities/payments.md)
- Тарифы
- Подписки
- История платежей

## Бизнес-правила

### [Правила тренировок](./rules/training-rules.md)
- Создание и изменение тренировок
- Ограничения по времени
- Правила отмены
- Учет посещаемости

### [Правила доступа](./rules/access-rules.md)
- Права пользователей
- Ограничения доступа
- Управление ролями

### [Правила оплаты](./rules/payment-rules.md)
- Тарификация
- Правила списания
- Возвраты

## Взаимосвязи

### [Диаграммы связей](./relationships/diagrams.md)
- ER-диаграмма
- Диаграмма процессов
- Диаграмма состояний

### [Зависимости](./relationships/dependencies.md)
- Между сущностями
- Между процессами
- Между правилами 