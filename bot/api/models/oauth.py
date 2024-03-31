from typing import Optional

from pydantic import BaseModel, Field


class OAuthResponse(BaseModel):
  session_id: str = Field(description='The session ID for the user.')
  jwt: str = Field(description='The JSON Web Token for the user.')


class DiscordUser(BaseModel):
  id: int = Field(description='The user ID.')
  username: str = Field(description='The username.')
  discriminator: str = Field(description='The discriminator.')
  avatar: Optional[str] = Field(
    default=None, description='The avatar hash, if the user has one.'
  )
