import time
from unittest.mock import patch

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from starlette.testclient import TestClient

from iea_mcp import auth
from iea_mcp.config import settings

KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)


def make_token(**overrides) -> str:
    claims = {"aud": settings.mcp_api_client_id, "iss": auth.ISSUER, "exp": int(time.time()) + 600,
              "oid": "user-1", "name": "Test User", "scp": "Evidence.Read", "groups": ["g1"]}
    claims.update(overrides)
    return jwt.encode(claims, KEY, algorithm="RS256")


@pytest.fixture(autouse=True)
def fake_signing_key():
    class SigningKey:
        key = KEY.public_key()
    with patch.object(auth.JWKS, "get_signing_key_from_jwt", return_value=SigningKey()):
        yield


def test_valid_token_returns_user_and_groups():
    user = auth.validate(make_token())
    assert user.oid == "user-1" and user.group_ids == ["g1"]


def test_expired_token_rejected():
    with pytest.raises(jwt.ExpiredSignatureError):
        auth.validate(make_token(exp=int(time.time()) - 60))


def test_wrong_audience_rejected():
    with pytest.raises(jwt.InvalidAudienceError):
        auth.validate(make_token(aud="some-other-api"))


def test_wrong_issuer_rejected():
    with pytest.raises(jwt.InvalidIssuerError):
        auth.validate(make_token(iss="https://evil.example.com/v2.0"))


def test_missing_scope_rejected():
    with pytest.raises(PermissionError):
        auth.validate(make_token(scp="User.Read"))


def test_http_endpoints():
    from iea_mcp.server import app
    client = TestClient(app)
    assert client.get("/healthz").status_code == 200
    assert client.post("/mcp").status_code == 401
    assert client.post("/mcp", headers={"Authorization": "Bearer not-a-real-token"}).status_code == 401
    assert client.get("/api/my-drafts").status_code == 401