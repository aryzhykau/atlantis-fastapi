class TrainingError(Exception):
    """Базовый класс для всех ошибок, связанных с тренировками."""

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class TrainerBusyError(TrainingError):
    """Ошибка, возникающая, если тренер занят в указанное время."""

    def __init__(self):
        super().__init__("У данного тренера уже есть тренировка на выбранное время.")


class TrainingTypeNotFoundError(TrainingError):
    """Ошибка, возникающая, если тип тренировки не найден."""

    def __init__(self, training_type_id: int):
        super().__init__(f"Тип тренировки с ID {training_type_id} не существует.")


class ClientAlreadyInTrainingError(TrainingError):
    """Ошибка, возникающая, если клиент уже добавлен в тренировку."""

    def __init__(self, client_id: int):
        super().__init__(f"Клиент {client_id} уже добавлен в эту тренировку.")


class ClientTimeConflictError(TrainingError):
    """Ошибка, возникающая, если у клиента есть пересечение по времени с другой тренировкой."""

    def __init__(self, client_id: int):
        super().__init__(f"Пересечение времени тренировки для клиента с ID {client_id} обнаружено.")


class ClientSubscriptionError(TrainingError):
    """Ошибка, возникающая, если у клиента нет активной подписки, а она требуется."""

    def __init__(self, client_id: int):
        super().__init__(f"Клиент {client_id} не имеет активной подписки или пробного занятия.")

class ClientSubscriptionSessionsError(TrainingError):
    """Ошибка, возникающая, если у клиента нет активной подписки, а она требуется."""

    def __init__(self, client_id: int):
        super().__init__(f"У клиента {client_id} не осталось доступных по абонементу тренировок")


class TrainingWithoutClientsError(TrainingError):
    def __init__(self):
        super().__init__(f"Тренировка должна иметь хотя бы одного клиента")


class TrainingWithoutTrainingTypeError(TrainingError):
    def __init__(self):
        super().__init__(f"Тип тренировки отсутствует")


class TrainingClientIdMissingError(TrainingError):
    def __init__(self):
        super().__init__("Отсутствует поле ID у клиента")


