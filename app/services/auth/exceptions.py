from app.core.exceptions import ConflictError, UnauthorizedError


class UserEmailAlreadyExistsError(ConflictError):
    def __init__(self):
        super().__init__(
            "User with this email already exists"
        )

class InvalidCredentialsError(UnauthorizedError):
    def __init__(self):
        super().__init__("Invalid email or password")

class InvalidRefreshTokenError(UnauthorizedError):
    def __init__(self):
        super().__init__("Invalid or expired refresh token")