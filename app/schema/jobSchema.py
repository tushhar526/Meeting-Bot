from pydantic import BaseModel, Field
from typing import Optional


class JobCreate(BaseModel):
    job_url: str = Field()
