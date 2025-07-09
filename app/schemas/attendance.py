from enum import Enum

class AttendanceStatus(str, Enum):
    # Базовые статусы посещения
    PRESENT = "PRESENT"              # Присутствовал
    ABSENT = "ABSENT"                # Отсутствовал (не пришел)
    
    # Статусы отмены
    CANCELLED_SAFE = "CANCELLED_SAFE"         # Отменен своевременно (>12ч, без штрафа)
    CANCELLED_PENALTY = "CANCELLED_PENALTY"   # Отменен поздно (<12ч, со штрафом)
    
    # Дополнительные статусы
    REGISTERED = "REGISTERED"        # Зарегистрирован, ждет тренировки
    WAITLIST = "WAITLIST"           # В листе ожидания (если есть ограничения) 