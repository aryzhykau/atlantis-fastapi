from datetime import date, datetime, timedelta
from typing import Optional
from sqlalchemy.orm import Session

from app.models import RealTraining, RealTrainingStudent, AttendanceStatus
from app.crud import training as training_crud


# =============================================================================
# ВАЛИДАЦИЯ ТРЕНИРОВОК
# =============================================================================

def validate_training_exists(db: Session, training_id: int) -> Optional[RealTraining]:
    """
    Проверка существования тренировки
    
    Returns:
        RealTraining если существует, None если нет
    """
    return training_crud.get_training(db, training_id)


def validate_training_not_cancelled(training: RealTraining) -> bool:
    """
    Проверка, что тренировка не отменена
    
    Returns:
        True если тренировка не отменена, False если отменена
    """
    return training.cancelled_at is None


def validate_training_date_not_passed(training: RealTraining) -> bool:
    """
    Проверка, что дата тренировки ещё не прошла
    
    Returns:
        True если тренировка ещё не прошла, False если прошла
    """
    today = date.today()
    return training.training_date >= today


def validate_training_time_not_passed(training: RealTraining) -> bool:
    """
    Проверка, что время тренировки ещё не прошло
    
    Returns:
        True если тренировка ещё не прошла, False если прошла
    """
    now = datetime.now()
    training_datetime = datetime.combine(training.training_date, training.start_time)
    return training_datetime > now


def validate_training_capacity(training: RealTraining, max_participants: Optional[int] = None) -> bool:
    """
    Проверка, что на тренировке есть свободные места
    
    Args:
        training: Тренировка для проверки
        max_participants: Максимальное количество участников (если None, берётся из типа тренировки)
    
    Returns:
        True если есть свободные места, False если нет
    """
    if max_participants is None and training.training_type:
        max_participants = training.training_type.max_participants
    
    if max_participants is None:
        return True  # Нет ограничений
    
    current_participants = len(training.students)
    return current_participants < max_participants


# =============================================================================
# ВАЛИДАЦИЯ СТУДЕНТОВ НА ТРЕНИРОВКАХ
# =============================================================================

def validate_student_in_training(
    db: Session, 
    training_id: int, 
    student_id: int
) -> Optional[RealTrainingStudent]:
    """
    Проверка, что студент записан на тренировку
    
    Returns:
        RealTrainingStudent если записан, None если нет
    """
    return training_crud.get_training_student(db, training_id, student_id)


def validate_student_not_in_training(
    db: Session, 
    training_id: int, 
    student_id: int
) -> bool:
    """
    Проверка, что студент НЕ записан на тренировку
    
    Returns:
        True если студент не записан, False если записан
    """
    return training_crud.get_training_student(db, training_id, student_id) is None


def validate_attendance_status(status: str) -> bool:
    """
    Проверка корректности статуса посещаемости
    
    Returns:
        True если статус корректный, False если нет
    """
    return status in [status.value for status in AttendanceStatus]


def validate_attendance_can_be_updated(
    student_training: RealTrainingStudent,
    new_status: str
) -> bool:
    """
    Проверка, можно ли обновить статус посещаемости
    
    Args:
        student_training: Запись студента на тренировку
        new_status: Новый статус посещаемости
    
    Returns:
        True если можно обновить, False если нет
    """
    # Нельзя изменить статус для отменённых тренировок
    if student_training.real_training.cancelled_at:
        return False
    
    # Проверяем, что новый статус корректный
    if not validate_attendance_status(new_status):
        return False
    
    return True


# =============================================================================
# ВАЛИДАЦИЯ ВРЕМЕНИ ОТМЕНЫ
# =============================================================================

def validate_cancellation_time(
    training: RealTraining,
    cancellation_deadline_hours: int = 24
) -> bool:
    """
    Проверка, можно ли отменить тренировку по времени
    
    Args:
        training: Тренировка для проверки
        cancellation_deadline_hours: За сколько часов до тренировки можно отменить
    
    Returns:
        True если можно отменить, False если поздно
    """
    now = datetime.now()
    training_datetime = datetime.combine(training.training_date, training.start_time)
    deadline = training_datetime - timedelta(hours=cancellation_deadline_hours)
    
    return now < deadline


def validate_safe_cancellation_time(
    training: RealTraining,
    safe_cancellation_hours: int = 24
) -> bool:
    """
    Проверка, можно ли безопасно отменить тренировку (без штрафа)
    
    Args:
        training: Тренировка для проверки
        safe_cancellation_hours: За сколько часов до тренировки можно безопасно отменить
    
    Returns:
        True если можно безопасно отменить, False если будет штраф
    """
    return validate_cancellation_time(training, safe_cancellation_hours)


def validate_unsafe_cancellation_time(
    training: RealTraining,
    unsafe_cancellation_hours: int = 2
) -> bool:
    """
    Проверка, можно ли отменить тренировку с штрафом
    
    Args:
        training: Тренировка для проверки
        unsafe_cancellation_hours: За сколько часов до тренировки можно отменить с штрафом
    
    Returns:
        True если можно отменить с штрафом, False если слишком поздно
    """
    return validate_cancellation_time(training, unsafe_cancellation_hours)


# =============================================================================
# КОМПЛЕКСНЫЕ ВАЛИДАЦИИ
# =============================================================================

def validate_training_for_student_registration(
    db: Session,
    training_id: int,
    student_id: int,
    max_participants: Optional[int] = None
) -> tuple[bool, str]:
    """
    Комплексная валидация для записи студента на тренировку
    
    Returns:
        (is_valid, error_message)
    """
    # Проверяем существование тренировки
    training = validate_training_exists(db, training_id)
    if not training:
        return False, "Тренировка не найдена"
    
    # Проверяем, что тренировка не отменена
    if not validate_training_not_cancelled(training):
        return False, "Тренировка отменена"
    
    # Проверяем, что тренировка ещё не прошла
    if not validate_training_date_not_passed(training):
        return False, "Тренировка уже прошла"
    
    # Проверяем, что студент ещё не записан
    if not validate_student_not_in_training(db, training_id, student_id):
        return False, "Студент уже записан на эту тренировку"
    
    # Проверяем вместимость
    if not validate_training_capacity(training, max_participants):
        return False, "Нет свободных мест на тренировке"
    
    return True, ""


def validate_training_for_student_cancellation(
    db: Session,
    training_id: int,
    student_id: int,
    safe_cancellation_hours: int = 24
) -> tuple[bool, str, bool]:
    """
    Комплексная валидация для отмены записи студента на тренировку
    
    Returns:
        (is_valid, error_message, is_safe_cancellation)
    """
    # Проверяем существование тренировки
    training = validate_training_exists(db, training_id)
    if not training:
        return False, "Тренировка не найдена", False
    
    # Проверяем, что тренировка не отменена
    if not validate_training_not_cancelled(training):
        return False, "Тренировка отменена", False
    
    # Проверяем, что студент записан
    student_training = validate_student_in_training(db, training_id, student_id)
    if not student_training:
        return False, "Студент не записан на эту тренировку", False
    
    # Проверяем время отмены
    is_safe = validate_safe_cancellation_time(training, safe_cancellation_hours)
    if not is_safe and not validate_unsafe_cancellation_time(training, 2):
        return False, "Слишком поздно отменять тренировку", False
    
    return True, "", is_safe


def validate_training_for_attendance_update(
    db: Session,
    training_id: int,
    student_id: int,
    new_status: str
) -> tuple[bool, str]:
    """
    Комплексная валидация для обновления посещаемости
    
    Returns:
        (is_valid, error_message)
    """
    # Проверяем существование тренировки
    training = validate_training_exists(db, training_id)
    if not training:
        return False, "Тренировка не найдена"
    
    # Проверяем, что студент записан
    student_training = validate_student_in_training(db, training_id, student_id)
    if not student_training:
        return False, "Студент не записан на эту тренировку"
    
    # Проверяем, можно ли обновить статус
    if not validate_attendance_can_be_updated(student_training, new_status):
        return False, "Нельзя обновить статус посещаемости"
    
    return True, "" 