# app/errors/payment_errors.py

class PaymentError(Exception):
    """Base exception for payment-related errors."""
    pass

class PaymentNotFound(PaymentError):
    """Raised when a payment is not found."""
    pass

class InsufficientBalance(PaymentError):
    """Raised when a client has insufficient balance for an operation."""
    pass
