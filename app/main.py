from fastapi import FastAPI
from app.core import setting
from dotenv import load_dotenv
from app.util import AppException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from starlette.middleware.sessions import SessionMiddleware
from app.core.middlewares.exception_handler import (
    global_app_exception_handler,
    validation_exception_handler,
)


# 1. Loaded env
load_dotenv()

# 2. Allowed origins for CORS
origin = ["http://localhost:5173"]


# 3. Create app function for defining fastapi app
def create_app():
    app = FastAPI()

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origin,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.add_exception_handler(AppException, global_app_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)

    app.add_middleware(SessionMiddleware, secret_key=setting.SECRET_KEY)

    return app
