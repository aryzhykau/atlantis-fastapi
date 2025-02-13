# from sqlalchemy.orm import Session
# from app.models.payment import Payment, Subscription
# from datetime import date
#
#
# def create_payment(db: Session, client_id: int, amount: float, payment_type: str):
#     db_payment = Payment(client_id=client_id, amount=amount, payment_type=payment_type)
#     db.add(db_payment)
#     db.commit()
#     db.refresh(db_payment)
#     return db_payment
#
#
# def create_subscription(db: Session, client_id: int, subscription_type: str, start_date: date, remaining_sessions: int):
#     # Создаем абонемент
#     subscription = Subscription(
#         client_id=client_id,
#         subscription_type=subscription_type,
#         start_date=start_date,
#         end_date=start_date.replace(year=start_date.year + 1),  # Продление на 1 год
#         remaining_sessions=remaining_sessions
#     )
#     db.add(subscription)
#     db.commit()
#     db.refresh(subscription)
#     return subscription
#
#
# def extend_subscription(db: Session, client_id: int, additional_sessions: int):
#     # Получаем текущий абонемент клиента
#     current_subscription = db.query(Subscription).filter(Subscription.client_id == client_id).order_by(
#         Subscription.end_date.desc()).first()
#
#     # Если абонемент есть, считаем перенос
#     if current_subscription:
#         # Если оставшиеся занятия меньше 3, переносим их
#         carried_over_sessions = min(current_subscription.remaining_sessions, 3)
#
#         # Создаем новый абонемент с учетом переноса
#         current_subscription.extend_subscription(additional_sessions, carried_over_sessions)
#         db.commit()
#         db.refresh(current_subscription)
#         return current_subscription
#     else:
#         # Если нет активного абонемента, возвращаем ошибку или создаем новый
#         return None
