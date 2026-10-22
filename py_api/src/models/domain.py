from pydantic import BaseModel


class Game(BaseModel):
    app_id: str
    package_name: str
    app_name: str
    platform: str

class UserContext(BaseModel):
    user_id: str
    games: list[Game]
    growx_mcp_personal_key: str
