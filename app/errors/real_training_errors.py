# app/errors/real_training_errors.py

class RealTrainingError(Exception):
    """Base exception for real training-related errors."""
    pass

class TrainingNotFound(RealTrainingError):
    """Raised when a real training is not found."""
    pass

class StudentNotOnTraining(RealTrainingError):
    """Raised when a student is not found on a specific training."""
    pass

class StudentAlreadyRegistered(RealTrainingError):
    """Raised when a student is already registered for a training."""
    pass

class StudentInactive(RealTrainingError):
    """Raised when an operation is attempted with an inactive student."""
    pass

class SubscriptionRequired(RealTrainingError):
    """Raised when a training requires an active subscription but none is found."""
    pass

class InsufficientSessions(RealTrainingError):
    """Raised when a student's subscription has insufficient sessions."""
    pass
