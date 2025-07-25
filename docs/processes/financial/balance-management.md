# Управление балансом

## Общее описание
Баланс клиента - это ключевой элемент финансовой системы Atlantis. Он отражает доступные средства клиента для оплаты услуг и автоматического погашения инвойсов.

## Основные операции

### Пополнение баланса
- Происходит автоматически при регистрации платежа
- Доступно админам и тренерам
- Каждое пополнение фиксируется в истории операций
- Требует указания типа платежа и описания

### Списание средств
- Автоматическое списание при погашении инвойса
- Проверка достаточности средств перед списанием
- Запрет на уход в отрицательный баланс
- Фиксация каждой операции списания

### История операций
- Сохранение всех изменений баланса
- Привязка к платежам и инвойсам
- Доступна для просмотра админам
- Содержит информацию о времени и инициаторе операции

## Правила и ограничения

### Доступ к операциям
- Просмотр баланса: только админы
- Пополнение: админы, тренеры
- Списание: автоматическое
- Просмотр истории: только админы

### Валидация операций
- Проверка корректности суммы
- Проверка достаточности средств
- Валидация типа операции
- Проверка прав доступа

## Технические аспекты
- Атомарность операций
- Транзакционность при изменении баланса
- Логирование всех операций
- Система уведомлений об изменениях 