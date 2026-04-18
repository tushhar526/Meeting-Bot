from enum import Enum


class EmailType(str, Enum):
    SIGNUP = "signup"
    FORGOT_PASSWORD = "forgot_password"
