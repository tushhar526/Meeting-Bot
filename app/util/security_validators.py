from pydantic import Field, AfterValidator
from typing import Annotated
import re


def validated_Pass(password):
    pattern = r"^(?=.*[A-Z])(?=.*[a-z])(?=.*\d)(?=.*[!@#$%^&*?])"

    if not re.match(pattern, password):
        raise ValueError(
            "Password must contain 1 uppercase letter, 1 lowercase letter, 1 digit and 1 special character"
        )

    if len(password) < 8:
        raise ValueError("Password must be atleast 8 character long")

    return password


PasswordStr = Annotated[str, AfterValidator(validated_Pass)]
