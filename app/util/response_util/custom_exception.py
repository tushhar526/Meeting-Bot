from http import HTTPStatus


class AppException(Exception):
    """
    Base exception for the entire project.
    All custom exceptions MUST inherit from this.
    """

    default_message = "An application error occurred"
    status_code = HTTPStatus.BAD_REQUEST
    error_code = "app_error"

    def __init__(self, message: str = None):
        self.message = message or self.default_message
        super().__init__(self.message)


class AuthenticationError(AppException):
    default_message = "Authentication failed"
    status_code = HTTPStatus.UNAUTHORIZED
    error_code = "authentication_error"


class AccessTokenExpired(AppException):
    default_message = "Access token expired"
    status_code = HTTPStatus.REQUEST_TIMEOUT
    error_code = "acces_token_expired"


class PermissionDeniedError(AppException):
    default_message = "Permission denied"
    status_code = HTTPStatus.FORBIDDEN
    error_code = "permission_denied"


class NotFoundError(AppException):
    default_message = "Resource not found"
    status_code = HTTPStatus.NOT_FOUND
    error_code = "not_found"


class AlredyExistError(AppException):
    default_message = "Workspace error"
    status_code = HTTPStatus.CONFLICT
    error_code = "workspace_error"
