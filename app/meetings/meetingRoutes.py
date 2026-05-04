from app.core.database import get_db
from app.util.response_util.response import SuccessResponse
from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends
from .meetingController import create_bot, get_bot_status
from .meetingSchema import CreateBotRequest
from app.core.middlewares.jwt_authenticator import get_current_user_id

meetingsrouter = APIRouter(prefix="/bot", tags=["Bot"])


@meetingsrouter.post("/create")
def create_bot_route(
    data: CreateBotRequest,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    meeting = create_bot(db, user_id, data)

    return SuccessResponse(
        message="The Bot would join the Meeting", data={"meeting_id": meeting.id}
    )


@meetingsrouter.get("/status/{meeting_id}")
def get_bot_status_route(
    meeting_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    result = get_bot_status(db, meeting_id, user_id)
    return SuccessResponse(message="The bot Status data is retrieved", data=result)
