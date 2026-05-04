from fastapi import Request, Depends, APIRouter, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.middlewares.jwt_authenticator import get_current_user_id
from app.util.response_util.response import SuccessResponse
from .usersController import get_user_analytics, get_meeting_trends


userrouter = APIRouter(prefix="/users", tags=["Users"])


@userrouter.get("/analytics")
def get_user_analytics_route(
    db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)
):
    result = get_user_analytics(db, user_id)
    return SuccessResponse(message="User analytics retrieved successfully", data=result)


@userrouter.get("/analytics/trends")
def get_meeting_trends_route(
    days: int = Query(default=30, ge=1, le=365, description="Number of days to analyze"),
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    result = get_meeting_trends(db, user_id, days)
    return SuccessResponse(message="Meeting trends retrieved successfully", data=result)
