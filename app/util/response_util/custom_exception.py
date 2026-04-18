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


class AlreadyExistError(AppException):
    default_message = "Already Exists"
    status_code = HTTPStatus.CONFLICT
    error_code = "entity_already_error"


class OTPExpiredError(AppException):
    default_message = "OTP has expired"
    status_code = HTTPStatus.BAD_REQUEST
    error_code = "otp_expired"


class InvalidOTPError(AppException):
    default_message = "Invalid OTP"
    status_code = HTTPStatus.BAD_REQUEST
    error_code = "invalid_otp"


class MissingVerificationToken(AppException):
    default_message = "Verification Token is missing"
    status_code = HTTPStatus.BAD_REQUEST
    error_code = "missing_verification_token"


class UserNotFoundError(AppException):
    default_message = "Invalid request"
    status_code = HTTPStatus.BAD_REQUEST
    error_code = "user_not_found"


class InvalidVerificationToken(AppException):
    default_message = "Invalid or expired verification token"
    status_code = HTTPStatus.UNAUTHORIZED
    error_code = "invalid_verification_token"


class VerificationEmailMismatch(AppException):
    default_message = "Verification token does not match email"
    status_code = HTTPStatus.UNAUTHORIZED
    error_code = "verification_email_mismatch"
