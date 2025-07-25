# Управление тренировками

## Общее описание
Процесс управления тренировками включает в себя создание, редактирование и отмену тренировок администраторами, а также управление посещаемостью тренерами.

## Основные процессы

### 1. Создание тренировки (Администратор)

#### Через шаблон
1. Администратор выбирает шаблон тренировки
2. Система автоматически создает тренировку с параметрами из шаблона
3. Система добавляет участников из шаблона

#### Вручную
1. Администратор указывает:
   - Тип тренировки
   - Дату и время
   - Тренера
2. Система проверяет доступность временного слота
3. Система создает тренировку

### 2. Управление участниками (Администратор)

#### Добавление участника
1. Администратор выбирает тренировку
2. Выбирает участника из списка
3. Система проверяет:
   - Наличие свободных мест
   - Отсутствие пересечений в расписании
4. Система добавляет участника

#### Удаление участника
1. Администратор выбирает участника
2. Система удаляет участника из тренировки
3. Система обновляет список участников

### 3. Отмена тренировки (Администратор)

#### Процесс отмены
1. Администратор инициирует отмену
2. Указывает причину отмены
3. Система отменяет тренировку
4. Система обновляет статус для всех участников

### 4. Управление посещаемостью (Тренер)

#### Отметка посещаемости
1. Тренер открывает список участников
2. Отмечает присутствие/отсутствие
3. Система сохраняет отметки
4. Система обновляет статистику

## Роли и ответственности

### Администратор
- Создание тренировок
- Отмена тренировок
- Управление шаблонами
- Управление списком участников
- Назначение тренеров

### Тренер
- Просмотр назначенных тренировок
- Отметка посещаемости
- Просмотр списка участников
- Просмотр деталей тренировки

## Реализация

### API Endpoints
Основные эндпоинты определены в [`app/endpoints/real_trainings.py`](../../app/endpoints/real_trainings.py):
- POST `/real-trainings/` - создание тренировки (admin)
- PUT `/real-trainings/{id}` - обновление тренировки (admin)
- DELETE `/real-trainings/{id}` - отмена тренировки (admin)
- POST `/real-trainings/{id}/students` - добавление участника (admin)
- PUT `/real-trainings/{id}/attendance` - отметка посещаемости (trainer)

### Бизнес-логика
Основная логика реализована в [`app/crud/real_training.py`](../../app/crud/real_training.py)

## Связанные процессы
- [Управление расписанием](./schedule-management.md)
- [Учет посещаемости](./attendance-tracking.md) 