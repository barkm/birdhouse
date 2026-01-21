from common.auth.exception import AuthException
from google.oauth2 import id_token
from google.auth.transport import requests


def verify(
    token: str,
    allowed_emails: list[str] | None = None,
    audience: str | None = None,
) -> tuple[str, str]:
    try:
        decoded = id_token.verify_oauth2_token(
            token, requests.Request(), audience=audience
        )
    except ValueError:
        raise AuthException("Token verification failed", status_code=401)

    if decoded.get("iss") not in {"https://accounts.google.com", "accounts.google.com"}:
        raise AuthException("Wrong issuer", status_code=401)

    email = decoded["email"]

    if allowed_emails is not None and email not in allowed_emails:
        raise AuthException("Unauthorized", status_code=403)

    return decoded["sub"], email
