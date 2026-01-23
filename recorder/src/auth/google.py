from google.oauth2 import id_token
from google.auth.transport import requests


def verify(
    token: str,
    audience: str | None = None,
) -> tuple[str, str]:
    try:
        decoded = id_token.verify_oauth2_token(
            token, requests.Request(), audience=audience
        )
    except ValueError:
        raise ValueError("Invalid token")

    if decoded.get("iss") not in {"https://accounts.google.com", "accounts.google.com"}:
        raise ValueError("Wrong issuer")

    return decoded["sub"], decoded["email"]
