import contextvars
import hashlib
from dataclasses import dataclass

import jwt

from .config import settings

TENANT = settings.azure_tenant_id
JWKS = jwt.PyJWKClient(f"https://login.microsoftonline.com/{TENANT}/discovery/v2.0/keys")
ISSUER = f"https://login.microsoftonline.com/{TENANT}/v2.0"
AUDIENCES = [settings.mcp_api_client_id, f"api://{settings.mcp_api_client_id}"]


@dataclass
class User:
    oid: str
    name: str
    group_ids: list[str]

    @property
    def hashed_id(self) -> str:
        return hashlib.sha256(self.oid.encode()).hexdigest()[:16]


_current: contextvars.ContextVar[User] = contextvars.ContextVar("user")


def current_user() -> User:
    return _current.get()


def validate(token: str) -> User:
    key = JWKS.get_signing_key_from_jwt(token).key
    claims = jwt.decode(token, key, algorithms=["RS256"], audience=AUDIENCES, issuer=ISSUER,
                        options={"require": ["exp", "iss", "aud", "oid"]})
    if "Evidence.Read" not in claims.get("scp", "").split():
        raise PermissionError("missing Evidence.Read scope")
    return User(claims["oid"], claims.get("name", ""), claims.get("groups", []))


class EntraAuthMiddleware:
    """Rejects any request without a valid Entra token; remembers the user for the request."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope["path"] == "/healthz" or scope.get("method") == "OPTIONS":
            return await self.app(scope, receive, send)
        auth = dict(scope["headers"]).get(b"authorization", b"").decode()
        try:
            user = validate(auth.removeprefix("Bearer ").strip())
        except Exception:
            await send({"type": "http.response.start", "status": 401,
                        "headers": [(b"www-authenticate", b"Bearer"), (b"content-type", b"text/plain")]})
            await send({"type": "http.response.body", "body": b"unauthorized"})
            return
        token = _current.set(user)
        try:
            await self.app(scope, receive, send)
        finally:
            _current.reset(token)