from typing import Generic, TypeVar, Optional, Any
from pydantic import BaseModel

T = TypeVar("T")


# Schema for meta data
class MetaData(BaseModel):
    total: Optional[int] = None
    page: Optional[int] = None
    page_size: Optional[int] = None

    model_config = {"extra": "allow"}


# Schema for Success Response
class SuccessResponse(BaseModel, Generic[T]):
    success: bool = True
    message: str
    data: Optional[T] = None
    meta: Optional[MetaData] = None


# Schema For Error Response
class ErrorDetail(BaseModel):
    error_code: str
    error_type: str


class ErrorResponse(BaseModel):
    success: bool = False
    message: str
    error: ErrorDetail
