from pydantic import BaseModel


class Config(BaseModel):
    dg_core_url: str = "http://localhost:8000"
    dg_bot_api_key: str = ""
    dg_game_id: str = ""
    dg_bot_username: str = "小倩Bot"
