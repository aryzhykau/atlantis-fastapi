# 🚀 РОАДМАП РЕФАКТОРИНГА АРХИТЕКТУРЫ

> **Поэтапный план рефакторинга бэкенда Atlantis**  
> *Создано: Декабрь 2024*

---

## 📋 **ОБЩИЙ ПЛАН**

### **Цель:** Реорганизация архитектуры для улучшения читаемости, тестируемости и поддерживаемости кода

### **Принципы:**
- ✅ **CRUD** - только простые операции с одной таблицей
- ✅ **Сервисы** - сложная бизнес-логика с использованием CRUD
- ✅ **Валидаторы** - общие проверки и валидация
- ✅ **Единообразие** - одинаковые паттерны везде

---

## 🎯 **ЭТАП 1: СОЗДАНИЕ НОВОЙ СТРУКТУРЫ CRUD**

### **1.1 Создание crud/training.py** ✅
- [x] Создать файл `crud/training.py`
- [x] Перенести простые CRUD операции из `real_training.py`
- [x] Убрать сложную бизнес-логику
- [x] Добавить типизацию и документацию
- [ ] Написать базовые тесты

**Функции для переноса:**
- [x] `get_training()`
- [x] `create_training()`
- [x] `update_training()`
- [x] `delete_training()`
- [x] `get_training_students()`
- [x] `add_student_to_training()`
- [x] `update_student_attendance()`
- [x] `remove_student_from_training()`

### **1.2 Создание crud/invoice.py** ✅
- [x] Создать файл `crud/invoice.py`
- [x] Вынести простые операции из `services/invoice.py`
- [x] Добавить базовые CRUD операции
- [ ] Написать тесты

**Функции для создания:**
- [x] `create_invoice()`
- [x] `get_invoice()`
- [x] `update_invoice()`
- [x] `cancel_invoice()`
- [x] `get_student_invoices()`
- [x] `get_training_invoice()` (вместо get_by_training_and_student)

### **1.3 Расширение crud/subscription.py** ✅
- [x] Расширить существующий `crud/subscription.py`
- [x] Добавить операции с занятиями
- [x] Добавить операции с автопродлением
- [ ] Написать тесты

**Новые функции:**
- [x] `deduct_session()`
- [x] `add_session()`
- [x] `get_active_subscription()`
- [x] `check_subscription_availability()`
- [x] `freeze_subscription()`
- [x] `unfreeze_subscription()`
- [x] `get_expiring_subscriptions()`
- [x] `get_frozen_subscriptions()`

### **1.4 Упрощение crud/payment.py** ✅
- [x] Упростить существующий `crud/payment.py`
- [x] Убрать сложную бизнес-логику
- [x] Оставить только простые CRUD операции
- [ ] Обновить тесты

---

## 🎯 **ЭТАП 2: СОЗДАНИЕ ВАЛИДАТОРОВ**

### **2.1 Создание папки validators/** ✅
- [x] Создать папку `app/validators/`
- [x] Создать `__init__.py`

### **2.2 Создание validators/training_validators.py** ✅
- [x] Создать файл `validators/training_validators.py`
- [x] Добавить валидацию тренировок
- [x] Добавить валидацию студентов на тренировках
- [x] Добавить валидацию времени отмены
- [ ] Написать тесты

**Функции валидации:**
- [x] `validate_training_exists()`
- [x] `validate_student_in_training()`
- [x] `validate_cancellation_time()`
- [x] `validate_training_not_cancelled()`
- [x] `validate_training_capacity()`
- [x] `validate_attendance_status()`
- [x] `validate_training_for_student_registration()`
- [x] `validate_training_for_student_cancellation()`

### **2.3 Создание validators/financial_validators.py** ✅
- [x] Создать файл `validators/financial_validators.py`
- [x] Добавить валидацию инвойсов
- [x] Добавить валидацию платежей
- [x] Добавить валидацию абонементов
- [ ] Написать тесты

**Функции валидации:**
- [x] `validate_invoice_exists()`
- [x] `validate_invoice_not_cancelled()`
- [x] `validate_invoice_can_be_paid()`
- [x] `validate_payment_amount()`
- [x] `validate_client_balance_sufficient()`
- [x] `validate_invoice_for_payment()`
- [x] `validate_payment_for_cancellation()`

### **2.4 Создание validators/subscription_validators.py** ✅
- [x] Создать файл `validators/subscription_validators.py`
- [x] Добавить валидацию абонементов
- [x] Добавить валидацию занятий
- [ ] Написать тесты

**Функции валидации:**
- [x] `validate_subscription_exists()`
- [x] `validate_subscription_active()`
- [x] `validate_sessions_available()`
- [x] `validate_subscription_not_frozen()`
- [x] `validate_subscription_for_training()`
- [x] `validate_subscription_for_freeze()`
- [x] `validate_subscription_for_unfreeze()`

---

## 🎯 **ЭТАП 3: РЕФАКТОРИНГ СЕРВИСОВ**

### **3.1 Создание services/training.py** ✅
- [x] Создать файл `services/training.py`
- [x] Создать класс `TrainingService`
- [x] Перенести сложную логику из `services/real_training.py`
- [x] Использовать CRUD и валидаторы
- [ ] Написать тесты

**Методы сервиса:**
- [x] `add_student_to_training()`
- [x] `remove_student_from_training()`
- [x] `update_student_attendance()`
- [x] `cancel_training()`
- [x] `get_training_with_students()`
- [x] `get_training_attendance_summary()`
- [x] `auto_mark_attendance()`
- [x] `get_student_training_history()`

### **3.2 Создание services/financial.py**
- [ ] Создать файл `services/financial.py`
- [ ] Создать класс `FinancialService`
- [ ] Объединить логику из `services/invoice.py` и `services/payment.py`
- [ ] Добавить обработку отмен
- [ ] Написать тесты

**Методы сервиса:**
- [ ] `handle_safe_cancellation()`
- [ ] `handle_unsafe_cancellation()`
- [ ] `process_training_finances()`
- [ ] `create_training_invoice()`
- [ ] `process_payment()`
- [ ] `cancel_invoice()`

### **3.3 Создание services/generation.py**
- [ ] Создать файл `services/generation.py`
- [ ] Создать класс `TrainingGenerationService`
- [ ] Перенести `generate_next_week_trainings()` из CRUD
- [ ] Добавить создание инвойсов при генерации
- [ ] Написать тесты

**Методы сервиса:**
- [ ] `generate_next_week_trainings()`
- [ ] `create_training_from_template()`
- [ ] `add_students_to_training()`
- [ ] `create_invoices_for_training()`

### **3.4 Обновление services/daily_operations.py**
- [ ] Обновить `services/daily_operations.py`
- [ ] Использовать новые сервисы
- [ ] Упростить координацию
- [ ] Обновить тесты

---

## 🎯 **ЭТАП 4: ОБНОВЛЕНИЕ ЭНДПОИНТОВ**

### **4.1 Обновление endpoints/real_trainings.py**
- [ ] Обновить импорты
- [ ] Заменить прямые вызовы CRUD на сервисы
- [ ] Добавить валидацию через валидаторы
- [ ] Обновить тесты

### **4.2 Обновление endpoints/invoice.py**
- [ ] Обновить импорты
- [ ] Использовать `FinancialService`
- [ ] Добавить валидацию
- [ ] Обновить тесты

### **4.3 Обновление endpoints/payment.py**
- [ ] Обновить импорты
- [ ] Использовать `FinancialService`
- [ ] Добавить валидацию
- [ ] Обновить тесты

### **4.4 Обновление endpoints/cron.py**
- [ ] Обновить импорты
- [ ] Использовать новые сервисы
- [ ] Обновить тесты

---

## 🎯 **ЭТАП 5: ТЕСТИРОВАНИЕ И ОЧИСТКА**

### **5.1 Написание тестов**
- [ ] Тесты для новых CRUD операций
- [ ] Тесты для валидаторов
- [ ] Тесты для новых сервисов
- [ ] Интеграционные тесты

### **5.2 Удаление старых файлов**
- [ ] Удалить старые CRUD файлы
- [ ] Удалить старые сервисы
- [ ] Обновить импорты
- [ ] Проверить, что ничего не сломалось

### **5.3 Обновление документации**
- [ ] Обновить README
- [ ] Обновить API документацию
- [ ] Создать документацию по новой архитектуре
- [ ] Обновить примеры использования

---

## 📊 **ПРОГРЕСС ВЫПОЛНЕНИЯ**

### **Этап 1: CRUD** 
- [ ] 1.1 Создание crud/training.py
- [ ] 1.2 Создание crud/invoice.py  
- [ ] 1.3 Расширение crud/subscription.py
- [ ] 1.4 Упрощение crud/payment.py

### **Этап 2: Валидаторы**
- [ ] 2.1 Создание папки validators/
- [ ] 2.2 Создание validators/training_validators.py
- [ ] 2.3 Создание validators/financial_validators.py
- [ ] 2.4 Создание validators/subscription_validators.py

### **Этап 3: Сервисы**
- [ ] 3.1 Создание services/training.py
- [ ] 3.2 Создание services/financial.py
- [ ] 3.3 Создание services/generation.py
- [ ] 3.4 Обновление services/daily_operations.py

### **Этап 4: Эндпоинты**
- [ ] 4.1 Обновление endpoints/real_trainings.py
- [ ] 4.2 Обновление endpoints/invoice.py
- [ ] 4.3 Обновление endpoints/payment.py
- [ ] 4.4 Обновление endpoints/cron.py

### **Этап 5: Тестирование и очистка**
- [ ] 5.1 Написание тестов
- [ ] 5.2 Удаление старых файлов
- [ ] 5.3 Обновление документации

---

## 🎯 **ОЖИДАЕМЫЕ РЕЗУЛЬТАТЫ**

### **После завершения рефакторинга:**
- ✅ **Упрощённая архитектура** - чёткое разделение ответственности
- ✅ **Переиспользуемый код** - CRUD функции в разных сервисах
- ✅ **Улучшенная тестируемость** - каждый слой тестируется отдельно
- ✅ **Лучшая читаемость** - простые функции в CRUD, сложная логика в сервисах
- ✅ **Единообразие** - одинаковые паттерны везде

---

*Этот роадмап будет обновляться по мере выполнения задач.* 