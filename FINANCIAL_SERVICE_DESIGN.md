# 💰 ДИЗАЙН FINANCIAL SERVICE

> **Детальное описание единого финансового сервиса для Atlantis**  
> *Создано: Декабрь 2024*

---

## 🎯 **НАЗНАЧЕНИЕ FINANCIAL SERVICE**

`FinancialService` будет централизованно управлять всеми финансовыми операциями в системе:

### **Основные области ответственности:**
1. **Создание инвойсов** - за тренировки, абонементы, автопродления
2. **Обработка платежей** - погашение инвойсов, управление балансом
3. **Возвраты и отмены** - при отмене тренировок, возврат денег
4. **Списание занятий** - с абонементов при посещении тренировок
5. **Автопродления** - создание новых абонементов и инвойсов

---

## 🔧 **ОПЕРАЦИИ FINANCIAL SERVICE**

### **1. Создание инвойсов**

```python
class FinancialService:
    def create_training_invoice(
        self,
        training_id: int,
        student_id: int,
        amount: float,
        description: str
    ) -> Invoice:
        """Создание инвойса за тренировку"""
        
    def create_subscription_invoice(
        self,
        subscription_id: int,
        student_id: int,
        amount: float,
        description: str,
        is_auto_renewal: bool = False
    ) -> Invoice:
        """Создание инвойса за абонемент"""
        
    def create_auto_renewal_invoice(
        self,
        student_subscription: StudentSubscription
    ) -> Invoice:
        """Создание инвойса для автопродления"""
```

### **2. Обработка платежей**

```python
class FinancialService:
    def process_payment(
        self,
        payment: Payment,
        student_id: int
    ) -> List[Invoice]:
        """Обработка платежа и погашение инвойсов"""
        
    def auto_pay_invoices(
        self,
        client_id: int,
        available_amount: float
    ) -> List[Invoice]:
        """Автоматическое погашение инвойсов с баланса"""
        
    def revert_payment(
        self,
        invoice_id: int,
        cancelled_by_id: int
    ) -> Invoice:
        """Отмена платежа и возврат средств"""
```

### **3. Управление абонементами**

```python
class FinancialService:
    def deduct_session_from_subscription(
        self,
        student_id: int,
        training_date: date
    ) -> StudentSubscription:
        """Списание занятия с абонемента"""
        
    def return_session_to_subscription(
        self,
        student_id: int,
        training_date: date
    ) -> StudentSubscription:
        """Возврат занятия в абонемент"""
        
    def check_subscription_availability(
        self,
        student_id: int,
        training_date: date
    ) -> Optional[StudentSubscription]:
        """Проверка доступности абонемента"""
```

### **4. Обработка отмен**

```python
class FinancialService:
    def handle_safe_cancellation(
        self,
        training_id: int,
        student_id: int
    ) -> Dict[str, Any]:
        """Обработка безопасной отмены (полный возврат)"""
        
    def handle_unsafe_cancellation(
        self,
        training_id: int,
        student_id: int
    ) -> Dict[str, Any]:
        """Обработка небезопасной отмены (штраф)"""
        
    def cancel_invoice(
        self,
        invoice_id: int,
        cancelled_by_id: int
    ) -> Invoice:
        """Отмена инвойса"""
```

### **5. Массовые операции**

```python
class FinancialService:
    def process_training_finances(
        self,
        training_id: int
    ) -> Dict[str, Any]:
        """Обработка финансов для одной тренировки"""
        
    def process_daily_finances(
        self,
        processing_date: date
    ) -> Dict[str, Any]:
        """Обработка финансов за день"""
        
    def process_auto_renewals(
        self
    ) -> Dict[str, Any]:
        """Обработка автопродлений"""
```

---

## 🔄 **ЛОГИКА РАБОТЫ С ДРУГИМИ ПРОЦЕССАМИ**

### **Сценарий 1: Генерация тренировок + Создание инвойсов**

```python
# В generate_next_week_trainings()
def generate_next_week_trainings(db: Session) -> Tuple[int, List[RealTraining]]:
    # ... существующая логика создания тренировок ...
    
    # После создания тренировки
    financial_service = FinancialService(db)
    
    for training in created_trainings:
        for student_training in training.students:
            # Проверяем, нужен ли инвойс
            if not financial_service.check_subscription_availability(
                student_training.student_id, 
                training.training_date
            ):
                # Создаём инвойс сразу при генерации
                financial_service.create_training_invoice(
                    training_id=training.id,
                    student_id=student_training.student_id,
                    amount=training.training_type.price,
                    description=f"Тренировка: {training.training_type.name}"
                )
```

### **Сценарий 2: Ежедневная обработка**

```python
# В DailyOperationsService
class DailyOperationsService:
    def __init__(self, db: Session):
        self.db = db
        self.financial_service = FinancialService(db)
        self.attendance_service = AttendanceService(db)
    
    def process_daily_operations(self):
        today = date.today()
        
        # 1. Обработка посещаемости
        self.attendance_service.process_today_attendance(today)
        
        # 2. Финансовая обработка
        self.financial_service.process_daily_finances(today)
```

### **Сценарий 3: Отмена тренировки**

```python
# В RealTrainingService
class RealTrainingService:
    def __init__(self, db: Session):
        self.db = db
        self.financial_service = FinancialService(db)
    
    async def cancel_student(self, training_id: int, student_id: int, ...):
        # ... проверки ...
        
        if is_safe_cancellation:
            # Безопасная отмена - полный возврат
            result = self.financial_service.handle_safe_cancellation(
                training_id, student_id
            )
        else:
            # Небезопасная отмена - штраф
            result = self.financial_service.handle_unsafe_cancellation(
                training_id, student_id
            )
```

---

## 📊 **ДЕТАЛЬНАЯ ЛОГИКА ОПЕРАЦИЙ**

### **1. Создание инвойса за тренировку**

```python
def create_training_invoice(self, training_id: int, student_id: int, ...) -> Invoice:
    # 1. Валидация
    training = self._validate_training(training_id)
    student = self._validate_student(student_id)
    client = self._validate_client(student.client_id)
    
    # 2. Проверка существующего инвойса
    existing_invoice = self._get_existing_invoice(training_id, student_id)
    if existing_invoice:
        raise ValueError("Invoice already exists")
    
    # 3. Создание инвойса
    invoice = Invoice(
        client_id=client.id,
        student_id=student_id,
        training_id=training_id,
        amount=amount,
        description=description,
        status=InvoiceStatus.UNPAID
    )
    
    # 4. Автоматическое погашение с баланса (если возможно)
    if client.balance >= amount:
        self._auto_pay_invoice(invoice, client)
    
    # 5. Сохранение
    self.db.add(invoice)
    self.db.commit()
    
    return invoice
```

### **2. Обработка безопасной отмены**

```python
def handle_safe_cancellation(self, training_id: int, student_id: int) -> Dict[str, Any]:
    result = {
        "invoice_cancelled": False,
        "session_returned": False,
        "refund_amount": 0.0
    }
    
    # 1. Найти и отменить инвойс
    invoice = self._get_training_invoice(training_id, student_id)
    if invoice and invoice.status != InvoiceStatus.CANCELLED:
        if invoice.status == InvoiceStatus.PAID:
            # Возврат денег
            result["refund_amount"] = invoice.amount
            self._refund_payment(invoice)
        
        self.cancel_invoice(invoice.id, cancelled_by_id=None)
        result["invoice_cancelled"] = True
    
    # 2. Вернуть занятие в абонемент
    training = self._get_training(training_id)
    if training.processed_at:  # Тренировка уже была обработана
        subscription = self._get_active_subscription(student_id, training.training_date)
        if subscription:
            subscription.sessions_left += 1
            result["session_returned"] = True
    
    return result
```

### **3. Списание занятия с абонемента**

```python
def deduct_session_from_subscription(self, student_id: int, training_date: date) -> StudentSubscription:
    # 1. Найти активный абонемент
    subscription = self.check_subscription_availability(student_id, training_date)
    if not subscription:
        raise ValueError("No active subscription available")
    
    # 2. Проверить количество занятий
    if subscription.sessions_left <= 0 and not subscription.is_auto_renew:
        raise ValueError("No sessions left in subscription")
    
    # 3. Списать занятие
    subscription.sessions_left -= 1
    
    # 4. Если занятия закончились и включено автопродление
    if subscription.sessions_left == 0 and subscription.is_auto_renew:
        self._trigger_auto_renewal(subscription)
    
    self.db.commit()
    return subscription
```

---

## 🎯 **ПРЕИМУЩЕСТВА ЕДИНОГО FINANCIAL SERVICE**

### **1. Централизация логики**
- Вся финансовая логика в одном месте
- Единообразная обработка ошибок
- Проще тестировать и отлаживать

### **2. Упрощение зависимостей**
```
До: DailyOperationsService → TrainingProcessingService → InvoiceService
После: DailyOperationsService → FinancialService
```

### **3. Консистентность операций**
- Все финансовые операции проходят через один сервис
- Гарантия атомарности операций
- Единая логика валидации

### **4. Упрощение API**
- Один сервис для всех финансовых операций
- Чёткий интерфейс
- Легче документировать

---

## ⚠️ **РИСКИ И МИТИГАЦИЯ**

### **Риски:**
1. **Сложность сервиса** - может стать слишком большим
2. **Тесная связанность** - много зависимостей
3. **Сложность тестирования** - много сценариев

### **Митогация:**
1. **Разделение на подмодули** - по типам операций
2. **Интерфейсы** - для слабой связанности
3. **Модульные тесты** - для каждого метода отдельно

---

## 📋 **ПЛАН РЕАЛИЗАЦИИ**

### **Этап 1: Базовая структура**
- [ ] Создать `FinancialService` с основными методами
- [ ] Перенести методы из `InvoiceService`
- [ ] Написать базовые тесты

### **Этап 2: Интеграция с тренировками**
- [ ] Добавить методы для работы с тренировками
- [ ] Интегрировать с `generate_next_week_trainings`
- [ ] Обновить `DailyOperationsService`

### **Этап 3: Обработка отмен**
- [ ] Добавить логику безопасных/небезопасных отмен
- [ ] Интегрировать с `RealTrainingService`
- [ ] Протестировать все сценарии

### **Этап 4: Оптимизация**
- [ ] Добавить кэширование
- [ ] Оптимизировать запросы к БД
- [ ] Добавить мониторинг

---

*Этот документ будет обновляться по мере реализации FinancialService.* 