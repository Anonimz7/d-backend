from app.apps.claisrox.schemas.base import CamelModel


class LoginRequest(CamelModel):
    username: str
    password: str


class TokenResponse(CamelModel):
    access_token: str
    token_type: str = "bearer"


class SessionResponse(CamelModel):
    username: str
    name: str
    tier: int
    tier_name: str = ""
    menus: list[str]
