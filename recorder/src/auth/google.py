from google.oauth2 import id_token
from google.auth.transport import requests

from src.auth.types import DecodedToken


class GoogleDecoder:
    def __init__(self, audience: str | None = None) -> None:
        self._audience = audience

    def decode(self, token: str) -> DecodedToken:
        return _decode(token, audience=self._audience)


def _decode(
    token: str,
    audience: str | None = None,
) -> DecodedToken:
    try:
        decoded = id_token.verify_oauth2_token(
            token, requests.Request(), audience=audience
        )
    except ValueError:
        raise ValueError("Invalid token")

    if decoded.get("iss") not in {"https://accounts.google.com", "accounts.google.com"}:
        raise ValueError("Wrong issuer")

    return DecodedToken(uid=decoded["sub"], email=decoded["email"])
