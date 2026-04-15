from fastapi import Request
from fastapi.responses import JSONResponse
from ...util.response_util.custom_exception import AppException


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
