class UserError(Exception):
    """Базовый класс для всех ошибок, связанных с пользователями."""

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class UserNotFoundError(Exception):
    def __init__(self):
        super().__init__("Пользователь не найден")


class ClientUserNotFoundError(Exception):
    def __init__(self):
        super().__init__("Пользователь не найден")


class UserEmailAlreadyExistError(Exception):
    def __init__(self):
        super().__init__("Пользователь c таким email уже существует")


class UserPhoneAlreadyExistError(Exception):
    def __init__(self):
        super().__init__("Пользователь c таким телефоном уже существует")