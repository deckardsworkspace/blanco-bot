from pydantic import BaseModel


class Session(BaseModel):
  user_id: int
  session_id: str
  expiration_time: int
