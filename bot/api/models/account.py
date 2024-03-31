from typing import Optional

from pydantic import BaseModel, Field


class AccountResponse(BaseModel):
  username: str = Field(description="The user's username.")
  spotify_logged_in: bool = Field(
    description='Whether the user is logged in to Spotify.'
  )
  spotify_username: Optional[str] = Field(
    default=None, description="The user's Spotify username, if logged in."
  )
  lastfm_logged_in: bool = Field(
    description='Whether the user is logged in to Last.fm.'
  )
  lastfm_username: Optional[str] = Field(
    default=None, description="The user's Last.fm username, if logged in."
  )
