# app/errors/subscription_errors.py

class SubscriptionError(Exception):
    """Base exception for subscription-related errors."""
    pass

class SubscriptionNotFound(SubscriptionError):
    """Raised when a subscription is not found."""
    pass

class SubscriptionNotActive(SubscriptionError):
    """Raised when an operation is attempted on an inactive subscription."""
    pass


class SubscriptionAlreadyActive(SubscriptionError):
    """Raised when trying to add a subscription while the student already has an active one."""
    pass

class SubscriptionAlreadyFrozen(SubscriptionError):
    """Raised when trying to freeze an already frozen subscription."""
    pass

class SubscriptionNotFrozen(SubscriptionError):
    """Raised when trying to unfreeze a subscription that is not frozen."""
    pass
