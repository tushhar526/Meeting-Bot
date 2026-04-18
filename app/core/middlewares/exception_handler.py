from fastapi import Request
from fastapi.responses import JSONResponse
from app.util import AppException
from http import HTTPStatus
from fastapi.exceptions import RequestValidationError


async def global_app_exception_handler(request: Request, exc: AppException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "message": exc.message,
            "error": {
                "error_code": exc.error_code,
                "error_type": exc.__class__.__name__,
            },
        },
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
        content={
            "success": False,
            "message": "Validation failed",
            "error": {
                "error_code": "validation_error",
                "error_type": "ValidationError",
                "details": exc.errors(),
            },
        },
    )
