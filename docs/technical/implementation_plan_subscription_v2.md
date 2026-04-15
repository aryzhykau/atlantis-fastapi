# План имплементации — Абонементы v2

> Дата: 6 апреля 2026  
> Статус: в работе

---

## Бэкенд

### 1. Alembic миграция

Новые поля:

```sql
-- StudentSubscription: когда расписание было подтверждено (NULL = PENDING_SCHEDULE)
ALTER TABLE student_subscriptions ADD COLUMN schedule_confirmed_at TIMESTAMPTZ;

-- Student: информация о пробном занятии
ALTER TABLE students ADD COLUMN trial_used_at TIMESTAMPTZ;
ALTER TABLE students ADD COLUMN trial_real_training_student_id INT REFERENCES real_training_students(id);
```

Команда генерации:
```bash
alembic revision --autogenerate -m "add_schedule_confirmed_and_trial_fields"
```

---

### 2. Модели (`app/models/`)

#### `subscription.py` → `StudentSubscription`
- Добавить `schedule_confirmed_at = Column(DateTime(timezone=True), nullable=True)`
- Обновить `status` hybrid_property:
  ```python
  # Новый статус: если schedule_confirmed_at IS NULL → "pending_schedule"
  # Иначе — существующая логика (pending/frozen/expired/active)
  ```

#### `student.py` → `Student`
- Добавить `trial_used_at = Column(DateTime(timezone=True), nullable=True)`
- Добавить `trial_real_training_student_id = Column(Integer, ForeignKey("real_training_students.id"), nullable=True)`

---

### 3. CRUD (`app/crud/subscription_v2.py`)

#### `get_active_or_pending_subscription`
- Добавить исключение `PENDING_SCHEDULE` из результатов — студент с pending_schedule абонементом не должен быть допущен на тренировки.

#### `count_subscription_only_visits`
- Убрать фильтр по `training_type_id` — считаем ВСЕ subscription_only посещения студента за неделю.

#### Новая функция: `count_student_active_templates`
```python
def count_student_active_templates(db, student_id) -> int:
    """Считает количество активных TrainingStudentTemplate для студента."""
```

---

### 4. Сервис (`app/services/subscription_v2.py`)

#### `add_subscription_to_student_v2` — ключевые изменения:

**ДО:**
```
Создать StudentSubscription → рассчитать цену → создать Invoice → ACTIVE
```

**ПОСЛЕ:**
```
Если покупка 1-го числа:
  → StudentSubscription(schedule_confirmed_at=now)  # сразу активен
  → Invoice(PENDING, full_price, due_date=7-е)
  
Если покупка в середине месяца:
  → StudentSubscription(schedule_confirmed_at=NULL)  # PENDING_SCHEDULE
  → Инвойс НЕ создаётся
```

**Добавить:**
- Проверку на дублирующий активный абонемент (`SubscriptionAlreadyActive`)

#### Новая функция: `confirm_schedule_and_create_invoice`
```python
def confirm_schedule_and_create_invoice(db, student_subscription_id, template_ids) -> Invoice:
    """
    Вызывается когда count(templates) == sessions_per_week.
    
    1. Считает remaining_sessions и total_sessions по переданным template_ids
    2. calculated_price = full_price * remaining / total
    3. Если remaining == 0: start_date = 1-е следующего месяца, цена = full_price
    4. Создаёт Invoice(PENDING, calculated_price, due_date=7-е следующего месяца)
    5. Устанавливает schedule_confirmed_at = now
    6. Пробует автооплату из баланса
    """
```

---

### 5. CRUD training_template (`app/crud/training_template.py`)

#### `create_training_student_template` — добавить триггер:

```python
# После успешного создания TrainingStudentTemplate:

# Проверяем: есть ли у студента PENDING_SCHEDULE абонемент?
pending_sub = get_pending_schedule_subscription(db, student_id)
if pending_sub:
    sessions_per_week = pending_sub.subscription.sessions_per_week
    template_count = count_student_active_templates(db, student_id)
    
    if template_count >= sessions_per_week:
        # Собираем все template_ids студента
        template_ids = get_student_template_ids(db, student_id)
        # Триггер: выставить инвойс и активировать абонемент
        confirm_schedule_and_create_invoice(db, pending_sub.id, template_ids)
```

**Важно:** триггер срабатывает ТОЛЬКО если статус `PENDING_SCHEDULE` (`schedule_confirmed_at IS NULL`).

---

### 6. Валидатор (`app/validators/subscription_validators_v2.py`)

#### `validate_subscription_for_training_v2`
- `get_active_or_pending_subscription` теперь возвращает только `ACTIVE` (не `pending_schedule`) — логика уже корректна после изменения CRUD
- Убрать мёртвый параметр `training_is_subscription_only` — early exit из шага 3 убрать, теперь лимит проверяем всегда для subscription_only

#### Обновить `count_subscription_only_visits`
- Считать все subscription_only тренировки студента за неделю (без фильтра по типу)

---

### 7. Схемы (`app/schemas/subscription_v2.py`)

#### `StudentSubscriptionResponseV2` — добавить:
```python
schedule_confirmed_at: Optional[datetime] = None
trial_used_at: Optional[datetime] = None  # из student (для карточки)
```

#### Новый ответ при добавлении в шаблон:
```python
class TemplateAddStudentResponse(BaseModel):
    student_template: TrainingStudentTemplateResponse
    subscription_activated: bool
    invoice: Optional[InvoiceResponse] = None
    # Если True — фронт показывает toast "Абонемент активирован"
```

---

### 8. Эндпоинты (`app/endpoints/subscriptions_v2.py`)

Без новых эндпоинтов.  
Результат триггера возвращается через ответ `POST /training_student_templates/`.

---

### 9. Баги которые фиксим попутно

| Файл | Проблема | Фикс |
|---|---|---|
| `services/daily_operations_v2.py` | `processing_date = date.today()` | `date.today() - timedelta(days=1)` |
| `services/subscription_v2.py` | Нет проверки на дублирующий абонемент | Добавить guard перед созданием |
| `services/subscription_v2.py` | `process_overdue_invoices_v2` нет per-item try/except | Обернуть каждый инвойс |

---

## Фронтенд

### 1. RTK Query API

#### `calendarApi-v2.ts`
- Обновить тип ответа `createTrainingStudentTemplate` → `TemplateAddStudentResponse`
- При `subscription_activated: true` → инвалидировать тег `Student` (обновить карточку)

#### `studentsApi.ts` (или аналог)
- `StudentSubscription` тип — добавить `schedule_confirmed_at`

---

### 2. `TrainingTemplateModal.tsx`

После добавления студента (`handleAddStudent`):
- Проверить ответ на `subscription_activated: true` → показать toast
- Если у добавляемого студента есть `pending_schedule` абонемент → показать подсказку в форме:
  ```
  🟡 Ожидает расписания: N из M дней добавлено
  После добавления этого слота счёт выставится автоматически.
  ```

**Как получить статус абонемента студента в модалке:**
- При открытии формы добавления → запросить `GET /v2/subscriptions/student/{student_id}`
- Найти абонемент с `schedule_confirmed_at == null`

---

### 3. `AddSubscriptionForm.tsx` (карточка студента)

**Убрать:**
- Логику предпросмотра цены с пропорцией по дням

**Добавить:**
- Информационный блок: _"Счёт будет выставлен автоматически после настройки расписания в календаре"_
- Исключение: если сегодня 1-е → показать сумму сразу

---

### 4. `StudentActiveSubscriptionCard.tsx`

**Новый статус `pending_schedule`:**
```
🟡 Ожидает расписания
   Добавлено: N из M дней
   [ Открыть календарь → ]
```

Прогресс `N` получаем из `GET /v2/subscriptions/student/{id}` или через отдельный счётчик шаблонов.

---

### 5. `RealTrainingModal.tsx` — секция добавления студента

**Новая логика при выборе студента:**

```
GET /v2/subscriptions/student/{student_id} → есть активный абонемент?

ДА + недельный лимит не превышен:
  → обычная кнопка [Добавить]

НЕТ + trial не использован (trial_used_at = null):
  → 💡 "Записать как пробное занятие (бесплатно, 1 раз)"
  → radio: ○ Обычная ● Пробное
  → [Добавить]

НЕТ + trial использован:
  → ⚠️ "Пробное использовано. Необходим абонемент."
  → кнопка [Добавить] заблокирована

ACTIVE абонемент + лимит исчерпан:
  → ⚠️ "Недельный лимит исчерпан (N из N)"
  → кнопка заблокирована (или разблокирована если есть makeup)
```

**Для проверки trial:** данные `trial_used_at` получаем из ответа `GET /v2/subscriptions/student/{student_id}` (добавить в ответ).

---

## Порядок выполнения

```
[x] Бизнес-логика задокументирована
[ ] 1. Alembic миграция
[ ] 2. Модели
[ ] 3. CRUD subscription_v2
[ ] 4. Сервис subscription_v2
[ ] 5. CRUD training_template (триггер)
[ ] 6. Валидатор
[ ] 7. Схемы
[ ] 8. Баги (daily_ops, duplicate guard, overdue per-item)
--- проверка: alembic upgrade head + запуск тестов ---
[ ] 9. Фронтенд: RTK Query типы
[ ] 10. Фронтенд: TrainingTemplateModal
[ ] 11. Фронтенд: AddSubscriptionForm
[ ] 12. Фронтенд: StudentActiveSubscriptionCard
[ ] 13. Фронтенд: RealTrainingModal
```
