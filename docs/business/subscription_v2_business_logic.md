# Бизнес-логика абонементов v2

> Зафиксировано: 6 апреля 2026

---

## Принципы

- Работаем **только с v2** — v1 не рассматривается
- У студента одновременно может быть **только один активный абонемент**
- Абонемент привязан к **типу тренировки** (`training_type`), а не к конкретному шаблону
- Стоимость считается по **фактическим занятиям в расписании студента** за месяц

---

## Шаблон абонемента (`Subscription`)

| Поле | Описание |
|---|---|
| `name` | Название |
| `price` | Полная стоимость за "стандартный" месяц |
| `sessions_per_week` | Количество посещений в неделю — используется для **контроля доступа** и для триггера расчёта цены |

---

## Флоу назначения абонемента студенту

### Шаг 1 — Создание абонемента

```
POST /v2/subscriptions/student

→ StudentSubscription создаётся со статусом PENDING_SCHEDULE
→ Инвойс НЕ выставляется
→ Студент пока НЕ может ходить на тренировки
```

### Шаг 2 — Добавление в расписание

Администратор добавляет студента в шаблоны тренировок (`TrainingStudentTemplate`) по одному.

**Триггер работает только если абонемент в статусе `PENDING_SCHEDULE`.**  
Если абонемент уже `ACTIVE` — добавление/удаление из шаблонов не влияет на цену и инвойс. Расписание меняется свободно.

После каждого добавления (при `PENDING_SCHEDULE`) автоматически проверяется:

```
count(TrainingStudentTemplate WHERE student_id = X)
    == subscription.sessions_per_week ?

→ НЕТ: ждём (расписание ещё не готово)
→ ДА:  расписание готово → триггер расчёта
```

### Шаг 3 — Расчёт цены (триггер)

```
remaining_sessions = COUNT(RealTraining по всем шаблонам студента
                            WHERE training_date >= today
                            AND training_date <= last_day_of_month
                            AND cancelled_at IS NULL)

total_sessions = COUNT(RealTraining по всем шаблонам студента
                        WHERE training_date >= first_day_of_month
                        AND training_date <= last_day_of_month
                        AND cancelled_at IS NULL)

calculated_price = round(full_price × remaining_sessions / total_sessions)
```

### Шаг 4 — Выставление инвойса

```
Invoice(
    type = SUBSCRIPTION,
    status = PENDING,
    amount = calculated_price,
    due_date = 7-е следующего месяца
)

StudentSubscription.status → ACTIVE
Студент может ходить на тренировки
```

---

## Граничный случай: 0 занятий до конца месяца

Если студента добавили в расписание, но до конца месяца не осталось ни одного занятия (например, добавили 30-го):

```
start_date = 1-е следующего месяца
total_sessions = занятия по шаблонам в следующем месяце
calculated_price = full_price (полный месяц, без пропорций)
due_date = 7-е следующего месяца
```

---

## Первое число месяца

Если абонемент оформляется 1-го числа:

```
remaining_sessions == total_sessions
calculated_price = full_price

due_date = 7-е текущего месяца
```

---

## Авторенью (конец месяца)

```
Условие: is_auto_renew = True AND end_date = сегодня

→ Новый StudentSubscription на следующий месяц
→ calculated_price = full_price (полный месяц, без пропорций)
→ Invoice(PENDING, due_date = 7-е следующего месяца)
→ Студент продолжает ходить по тому же расписанию
```

---

## Контроль доступа на тренировку

```
Студент регистрируется на subscription_only тренировку:

1. Есть активный абонемент?
   → НЕТ → проверяем пробное занятие (см. ниже)
   → ДА  → продолжаем

2. Не превышен ли недельный лимит? (неделя: Пн–Вс)
   count(всех subscription_only посещений студента за текущую неделю) < sessions_per_week?
   → ДА  → допускаем, обычная запись
   → НЕТ → переходим к шагу 3

3. Есть ли активная отработка?
   MissedSession WHERE student_id = X
                 AND is_excused = True
                 AND made_up_at IS NULL
                 AND makeup_deadline_date >= today
   → ДА  → допускаем как отработку (made_up_real_training_student_id проставится после занятия)
   → НЕТ → 403: "Недельный лимит исчерпан"
```

---

## Пробные занятия

### Правила

- **1 пробное занятие на студента** — глобально, на всю историю
- Только для тренировок с `is_subscription_only = True`
- Пробное **бесплатно**, в инвойс не включается

### Флоу

```
Студент хочет записаться на subscription_only тренировку, абонемента нет:

→ trial_used_at IS NULL?
   → ДА  → записываем как TRIAL (is_trial=True, requires_payment=False)
   → НЕТ → 403: "Необходим абонемент"
```

### Отмена пробного

| Сценарий | Результат |
|---|---|
| Студент отменил заранее (CANCELLED_SAFE) | Пробное **не засчитано** — может использовать снова |
| Студент не пришёл (ABSENT) | Пробное **засчитано** — прогулял, не возвращаем |
| Студент пришёл (PRESENT) | Пробное **засчитано** |

### После пробного

```
После обработки дня (daily ops):
  RealTrainingStudent.is_trial = True AND status = PRESENT
  → student.trial_used_at = now

Следующий визит на subscription_only → требует абонемент.
Никаких зачётов стоимости при покупке абонемента. Пробное было подарком.
```

---

## Механика пропусков (MissedSession)

Существующая логика остаётся без изменений:

| Статус посещения | Действие |
|---|---|
| `CANCELLED_SAFE` | `MissedSession(is_excused=True, deadline=today+N дней)` — студент может отработать |
| `CANCELLED_PENALTY` | `MissedSession(is_excused=False)` + штраф или инвойс |
| `ABSENT` | `MissedSession(is_excused=False)` — занятие считается использованным |
| Отработка | `MissedSession.made_up_at = now`, студенту открывается дополнительный слот сверх лимита |

---

## Статусы StudentSubscription

| Статус | Условие |
|---|---|
| `PENDING_SCHEDULE` | Абонемент создан, расписание ещё не заполнено |
| `PENDING` | `now < start_date` |
| `ACTIVE` | Расписание готово, инвойс выставлен, идёт месяц |
| `FROZEN` | Заморожен администратором |
| `EXPIRED` | `now > end_date` и не продлён |

---

## Изменения в БД (к реализации)

```sql
-- Экземпляр абонемента: рассчитанная цена и статус расписания
ALTER TABLE student_subscriptions ADD COLUMN calculated_price FLOAT;
ALTER TABLE student_subscriptions ADD COLUMN schedule_confirmed_at TIMESTAMPTZ;

-- Студент: история пробного занятия
ALTER TABLE students ADD COLUMN trial_used_at TIMESTAMPTZ;
ALTER TABLE students ADD COLUMN trial_real_training_student_id INT REFERENCES real_training_students(id);
```
