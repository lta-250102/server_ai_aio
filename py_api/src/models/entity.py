from typing import Annotated
from pydantic import BaseModel, BeforeValidator, ConfigDict, Field
from .domain import Game
from utils import objectid_to_str


class User(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: Annotated[str, BeforeValidator(objectid_to_str)] = Field(alias="_id", default=None)
    user_name: str
    user_email: str
    games: list[Game]
