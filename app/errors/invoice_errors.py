# app/errors/invoice_errors.py

class InvoiceError(Exception):
    """Base exception for invoice-related errors."""
    pass

class InvoiceNotFound(InvoiceError):
    """Raised when an invoice is not found."""
    pass

class InvoiceAlreadyPaid(InvoiceError):
    """Raised when trying to pay an already paid invoice."""
    pass
