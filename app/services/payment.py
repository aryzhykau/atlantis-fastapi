import logging
from datetime import datetime
from typing import List, Optional
from fastapi import HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.crud import payment as crud
from app.models import (
    Payment,
    User,
    UserRole,
    PaymentHistory,
    Invoice,
    InvoiceStatus
)
from app.models.payment_history import OperationType
from app.services.invoice import InvoiceService


logger = logging.getLogger(__name__)

class PaymentService:
    def __init__(self, db: Session):
        self.db = db
        self.invoice_service = InvoiceService(db)

    def validate_admin_or_trainer(self, user_id: int) -> None:
        """Проверка, что пользователь является админом или тренером"""
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user or user.role not in [UserRole.ADMIN, UserRole.TRAINER]:
            raise HTTPException(
                status_code=403,
                detail="Only admins and trainers can manage payments"
            )

    def get_payment(self, payment_id: int) -> Optional[Payment]:
        """Получение платежа по ID"""
        payment = crud.get_payment(self.db, payment_id)
        if not payment:
            raise HTTPException(status_code=404, detail="Payment not found")
        return payment

    def get_client_payments(
        self,
        client_id: int,
        cancelled_status: str = "all",
        skip: int = 0,
        limit: int = 100
    ) -> List[Payment]:
        """
        Получение списка платежей клиента
        
        Args:
            client_id: ID клиента
            cancelled_status: Статус отмены платежей ("all", "cancelled", "not_cancelled")
            skip: Смещение для пагинации
            limit: Лимит записей для пагинации
            
        Returns:
            Список платежей, соответствующих критериям
        """
        # Проверяем допустимость статуса
        if cancelled_status not in ["all", "cancelled", "not_cancelled"]:
            raise HTTPException(
                status_code=400,
                detail="Invalid cancelled_status. Must be 'all', 'cancelled' or 'not_cancelled'"
            )
            
        return crud.get_client_payments(
            self.db, 
            client_id, 
            cancelled_status=cancelled_status,
            skip=skip, 
            limit=limit
        )

    def register_payment(
        self,
        client_id: int,
        amount: float,
        registered_by_id: int,
        description: Optional[str] = None
    ) -> Payment:
        """
        Регистрация нового платежа
        1. Проверяем права доступа
        2. Валидируем сумму платежа
        3. Создаем платеж
        4. Обновляем баланс клиента ПОЛНОСТЬЮ
        5. Создаем запись в истории
        6. Пытаемся погасить инвойсы из баланса
        """
        # Проверяем права доступа
        self.validate_admin_or_trainer(registered_by_id)

        # Валидация описания
        if description is not None and len(description) > 500:
            raise HTTPException(
                status_code=400,
                detail="Payment description is too long (max 500 characters)"
            )

        # Валидация суммы платежа
        if amount <= 0:
            raise HTTPException(
                status_code=400,
                detail="Payment amount must be greater than zero"
            )

        try:
            # Получаем клиента и его текущий баланс
            client = self.db.query(User).filter(User.id == client_id).first()
            if not client:
                raise ValueError("Client not found")
            
            current_balance = client.balance or 0.0

            # Создаем платеж
            payment = crud.create_payment(
                self.db,
                client_id=client_id,
                amount=amount,
                description=description,
                registered_by_id=registered_by_id
            )
            logger.debug(f"Payment created for user: {client_id}")
            logger.debug(f"Payment amount: {amount}")
            
            # Сначала обновляем баланс клиента на ПОЛНУЮ сумму платежа
            new_balance = current_balance + amount
            client.balance = new_balance
            self.db.add(client)
            
            # Создаем запись в истории платежа
            history = PaymentHistory(
                client_id=client_id,
                payment_id=payment.id,
                operation_type=OperationType.PAYMENT,
                amount=amount,
                balance_before=current_balance,
                balance_after=new_balance,
                created_by_id=registered_by_id,
                description=description
            )
            self.db.add(history)
            
            # Теперь пытаемся оплатить инвойсы из обновленного баланса
            logger.debug(f"Trying to pay invoices for user: {client_id} with balance: {new_balance}")
            # Получаем неоплаченные инвойсы, отсортированные по дате создания
            unpaid_invoices = self.db.query(Invoice).filter(
                Invoice.client_id == client_id,
                Invoice.status == InvoiceStatus.UNPAID
            ).order_by(Invoice.created_at.asc()).all()
            logger.debug(f"Unpaid invoices: {unpaid_invoices}")

            # Пытаемся погасить инвойсы из баланса клиента
            available_balance = new_balance
            for invoice in unpaid_invoices:
                logger.debug(f"Processing Invoice: {invoice}")
                if available_balance >= invoice.amount:
                    invoice.status = InvoiceStatus.PAID
                    invoice.paid_at = datetime.utcnow()
                    # Убираем привязку к конкретному платежу
                    # invoice.payment_id = payment.id
                    available_balance -= invoice.amount
                    self.db.add(invoice)
                    
                    # Обновляем баланс клиента после оплаты каждого инвойса
                    client.balance = available_balance
                    self.db.add(client)
                    
                    # Создаем запись в истории об оплате инвойса
                    invoice_payment_history = PaymentHistory(
                        client_id=client_id,
                        payment_id=None,  # Не привязываем к конкретному платежу
                        invoice_id=invoice.id,  # Привязываем к инвойсу
                        operation_type=OperationType.INVOICE_PAYMENT,
                        amount=-invoice.amount,  # Отрицательная сумма, т.к. это расход
                        balance_before=available_balance + invoice.amount,
                        balance_after=available_balance,
                        created_by_id=registered_by_id,
                        description=f"Оплата инвойса #{invoice.id}"
                    )
                    self.db.add(invoice_payment_history)
                else:
                    # Если баланса не хватает, прекращаем обработку инвойсов
                    break

            self.db.commit()
            return payment
            
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    def cancel_payment(
        self,
        payment_id: int,
        cancelled_by_id: int,
        cancellation_reason: str = None
    ) -> Payment:
        """
        Отмена платежа
        1. Проверяем права доступа (только админ)
        2. Получаем информацию о платеже
        3. Получаем текущий баланс клиента
        4. Сравниваем баланс с суммой платежа:
           - Если баланс >= сумма платежа: просто уменьшаем баланс
           - Если баланс < сумма платежа: зануляем баланс и начинаем отменять инвойсы
        5. Отмена инвойсов идет от новых к старым
        6. Если остаточная сумма меньше суммы инвойса, записываем остаток в баланс
        """
        # Проверяем, что отменяет админ
        user = self.db.query(User).filter(User.id == cancelled_by_id).first()
        if not user or user.role != UserRole.ADMIN:
            raise HTTPException(
                status_code=403,
                detail="Only admins can cancel payments"
            )

        # Получаем информацию о платеже
        payment = self.get_payment(payment_id)
        if payment.cancelled_at:
            raise HTTPException(
                status_code=400,
                detail="Payment already cancelled"
            )

        # Получаем текущий баланс клиента
        client = self.db.query(User).filter(User.id == payment.client_id).first()
        current_balance = client.balance or 0.0
        
        # Сравниваем баланс с суммой платежа
        if current_balance >= payment.amount:
            # Если баланс достаточный, просто уменьшаем его на сумму платежа
            new_balance = current_balance - payment.amount
            client.balance = new_balance
            self.db.add(client)
            
            # Создаем запись в истории
            history = PaymentHistory(
                payment_id=payment.id,
                client_id=payment.client_id,
                operation_type=OperationType.CANCELLATION,
                amount=-payment.amount,
                balance_before=current_balance,
                balance_after=new_balance,
                created_by_id=cancelled_by_id,
                description=cancellation_reason
            )
            self.db.add(history)
        else:
            # Если баланса недостаточно, зануляем баланс и начинаем отменять инвойсы
            remaining_amount = payment.amount - current_balance  # Остаток, который нужно покрыть отменой инвойсов
            
            # Зануляем баланс
            new_balance = 0.0
            client.balance = new_balance
            
            # Создаем запись в истории о списании всего баланса
            history = PaymentHistory(
                payment_id=payment.id,
                client_id=payment.client_id,
                operation_type=OperationType.CANCELLATION,
                amount=-current_balance,  # Списываем весь текущий баланс
                balance_before=current_balance,
                balance_after=new_balance,
                created_by_id=cancelled_by_id,
                description=f"Частичная отмена платежа ({cancellation_reason})"
            )
            self.db.add(history)
            
            # Получаем все оплаченные инвойсы, начиная с новых (в обратном порядке)
            # Ищем в истории платежей записи типа INVOICE_PAYMENT
            paid_invoices_history = self.db.query(PaymentHistory).filter(
                PaymentHistory.client_id == payment.client_id,
                PaymentHistory.operation_type == OperationType.INVOICE_PAYMENT
            ).order_by(desc(PaymentHistory.created_at)).all()
            
            # Обрабатываем каждую запись истории платежей
            for history_item in paid_invoices_history:
                if remaining_amount <= 0:
                    break  # Если остаток полностью покрыт, выходим из цикла
                
                # Получаем инвойс
                invoice = self.db.query(Invoice).filter(
                    Invoice.id == history_item.invoice_id
                ).first()
                
                if not invoice or invoice.status != InvoiceStatus.PAID:
                    continue  # Пропускаем, если инвойс не найден или не оплачен
                
                invoice_amount = abs(history_item.amount)  # Абсолютное значение суммы инвойса
                
                if remaining_amount >= invoice_amount:
                    # Если остатка хватает на полную отмену инвойса
                    invoice.status = InvoiceStatus.UNPAID
                    invoice.paid_at = None
                    self.db.add(invoice)
                    
                    # Уменьшаем остаток
                    remaining_amount -= invoice_amount
                    
                    # Создаем запись в истории об отмене оплаты инвойса
                    invoice_cancel_history = PaymentHistory(
                        client_id=payment.client_id,
                        payment_id=payment.id,
                        invoice_id=invoice.id,
                        operation_type=OperationType.CANCELLATION,
                        amount=0,  # Нулевое изменение баланса, т.к. он уже занулен
                        balance_before=0,
                        balance_after=0,
                        created_by_id=cancelled_by_id,
                        description=f"Отмена оплаты инвойса #{invoice.id} при отмене платежа #{payment.id}"
                    )
                    self.db.add(invoice_cancel_history)
                else:
                    # Если остатка не хватает на полную отмену инвойса
                    # Отменяем инвойс и записываем разницу в баланс
                    invoice.status = InvoiceStatus.UNPAID
                    invoice.paid_at = None
                    self.db.add(invoice)
                    
                    # Добавляем остаток разницы на баланс
                    partial_refund = invoice_amount - remaining_amount
                    client.balance = partial_refund
                    self.db.add(client)
                    
                    # Создаем запись в истории
                    invoice_partial_history = PaymentHistory(
                        client_id=payment.client_id,
                        payment_id=payment.id,
                        invoice_id=invoice.id,
                        operation_type=OperationType.CANCELLATION,
                        amount=partial_refund,  # Положительная сумма, т.к. это пополнение
                        balance_before=0,
                        balance_after=partial_refund,
                        created_by_id=cancelled_by_id,
                        description=f"Отмена оплаты инвойса #{invoice.id} с частичным возвратом на баланс"
                    )
                    self.db.add(invoice_partial_history)
                    
                    remaining_amount = 0  # Весь остаток использован
                    break
        
        # Отмечаем платеж как отмененный
        payment.cancelled_at = datetime.utcnow()
        payment.cancelled_by_id = cancelled_by_id
        self.db.add(payment)

        self.db.commit()
        return payment

    def get_client_balance(self, client_id: int) -> float:
        """Получение текущего баланса клиента"""
        client = self.db.query(User).filter(User.id == client_id).first()
        if not client:
            raise HTTPException(status_code=404, detail="Client not found")
        return client.balance or 0.0

    def get_payment_history(
        self,
        user_id: int,
        client_id: int,
        skip: int = 0,
        limit: int = 100
    ) -> List[PaymentHistory]:
        """
        Получение истории платежей клиента
        Доступно только для админов и тренеров
        """
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user or user.role not in [UserRole.ADMIN, UserRole.TRAINER]:
            raise HTTPException(
                status_code=403,
                detail="Only admins and trainers can view payment history"
            )

        return self.db.query(PaymentHistory).filter(
            PaymentHistory.client_id == client_id
        ).order_by(desc(PaymentHistory.created_at)).offset(skip).limit(limit).all()

    def get_payments_with_filters(
        self,
        user_id: int,
        registered_by_me: bool = False,
        period: str = "week"
    ) -> List[Payment]:
        """
        Получение платежей с фильтрацией по регистрировавшему и периоду
        
        Args:
            user_id: ID пользователя (тренера/админа)
            registered_by_me: Если True, возвращает только платежи зарегистрированные этим пользователем
            period: Период для фильтрации (week/month/3months)
        """
        # Валидация периода
        if period not in ["week", "2weeks"]:
            raise HTTPException(
                status_code=400,
                detail="Invalid period. Must be 'week', 'month' or '3months'"
            )
        
        return crud.get_payments_with_filters(
            self.db,
            user_id=user_id,
            registered_by_me=registered_by_me,
            period=period
        )

    def get_payments_with_filters_extended(
        self,
        user_id: int,
        registered_by_me: bool = False,
        period: str = "week"
    ) -> List[dict]:
        """
        Получение платежей с фильтрацией по регистрировавшему и периоду (с расширенными данными)
        
        Args:
            user_id: ID пользователя (тренера/админа)
            registered_by_me: Если True, возвращает только платежи зарегистрированные этим пользователем
            period: Период для фильтрации (week/2weeks)
        """
        # Валидация периода
        if period not in ["week", "2weeks"]:
            raise HTTPException(
                status_code=400,
                detail="Invalid period. Must be 'week' or '2weeks'"
            )
        
        return crud.get_payments_with_filters_extended(
            self.db,
            user_id=user_id,
            registered_by_me=registered_by_me,
            period=period
        )

    def register_training_payment(
        self,
        client_id: int,
        amount: float,
        training_id: int,
        registered_by_id: int
    ) -> Payment:
        """
        Регистрация платежа через отметку присутствия на тренировке
        """
        # Проверяем, что регистрирует тренер
        user = self.db.query(User).filter(User.id == registered_by_id).first()
        if not user or user.role != UserRole.TRAINER:
            raise HTTPException(
                status_code=403,
                detail="Only trainers can register training payments"
            )

        description = f"Payment for training #{training_id}"
        return self.register_payment(
            client_id=client_id,
            amount=amount,
            registered_by_id=registered_by_id,
            description=description
        )

    def get_payment_history_with_filters(
        self,
        user_id: int,
        filters: "PaymentHistoryFilterRequest"
    ) -> dict:
        """
        Получение истории платежей с фильтрами и пагинацией
        Доступно только для админов
        
        Args:
            user_id: ID пользователя (админа)
            filters: Параметры фильтрации
            
        Returns:
            Словарь с данными истории и пагинацией
        """
        # Проверяем права доступа (только админы)
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user or user.role != UserRole.ADMIN:
            raise HTTPException(
                status_code=403,
                detail="Only admins can view payment history"
            )

        # Валидация параметров фильтрации
        if filters.limit > 1000:
            raise HTTPException(
                status_code=400,
                detail="Limit cannot exceed 1000"
            )
        
        if filters.skip < 0:
            raise HTTPException(
                status_code=400,
                detail="Skip cannot be negative"
            )
        
        if filters.amount_min is not None and filters.amount_max is not None:
            if filters.amount_min > filters.amount_max:
                raise HTTPException(
                    status_code=400,
                    detail="Minimum amount cannot be greater than maximum amount"
                )
        
        if filters.date_from and filters.date_to:
            if filters.date_from > filters.date_to:
                raise HTTPException(
                    status_code=400,
                    detail="Start date cannot be later than end date"
                )

        # Получаем данные через CRUD
        from app.crud import payment as crud
        history_items, total_count = crud.get_payment_history_filtered(
            self.db, filters
        )

        # Формируем ответ
        has_more = (filters.skip + filters.limit) < total_count
        
        return {
            "items": history_items,
            "total": total_count,
            "skip": filters.skip,
            "limit": filters.limit,
            "has_more": has_more
        }

    def get_trainer_registered_payments(
        self,
        trainer_id: int,
        period: str = "all",
        client_id: Optional[int] = None,
        amount_min: Optional[float] = None,
        amount_max: Optional[float] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        description_search: Optional[str] = None,
        skip: int = 0,
        limit: int = 50
    ) -> dict:
        """
        Получение платежей, зарегистрированных тренером
        
        Args:
            trainer_id: ID тренера
            period: Период фильтрации (week/month/3months/all)
            client_id: ID клиента для фильтрации
            amount_min: Минимальная сумма
            amount_max: Максимальная сумма
            date_from: Дата начала периода
            date_to: Дата окончания периода
            description_search: Поиск по описанию
            skip: Смещение для пагинации
            limit: Лимит записей
            
        Returns:
            Словарь с данными платежей и пагинацией
        """
        # Валидация параметров
        if limit > 1000:
            raise HTTPException(
                status_code=400,
                detail="Limit cannot exceed 1000"
            )
        
        if skip < 0:
            raise HTTPException(
                status_code=400,
                detail="Skip cannot be negative"
            )
        
        if amount_min is not None and amount_max is not None:
            if amount_min > amount_max:
                raise HTTPException(
                    status_code=400,
                    detail="Minimum amount cannot be greater than maximum amount"
                )
        
        if date_from and date_to:
            if date_from > date_to:
                raise HTTPException(
                    status_code=400,
                    detail="Start date cannot be later than end date"
                )

        # Получаем данные через CRUD
        from app.crud import payment as crud
        payments, total_count = crud.get_trainer_payments_filtered(
            self.db,
            trainer_id=trainer_id,
            period=period,
            client_id=client_id,
            amount_min=amount_min,
            amount_max=amount_max,
            date_from=date_from,
            date_to=date_to,
            description_search=description_search,
            skip=skip,
            limit=limit
        )

        # Формируем ответ
        has_more = (skip + limit) < total_count
        
        return {
            "payments": payments,
            "total": total_count,
            "skip": skip,
            "limit": limit,
            "has_more": has_more
        } 