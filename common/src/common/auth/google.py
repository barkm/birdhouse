from common.auth.exception import AuthException
from common.auth.token import get_token
from google.oauth2 import id_token
from google.auth.transport import requests


def verify(
    headers: dict[str, str],
    allowed_emails: list[str] | None = None,
    audience: str | None = None,
) -> None:
    token = get_token(headers)
    try:
        decoded = id_token.verify_oauth2_token(
            token, requests.Request(), audience=audience
        )
    except ValueError:
        raise AuthException("Token verification failed", status_code=401)

    if decoded.get("iss") not in {"https://accounts.google.com", "accounts.google.com"}:
        raise AuthException("Wrong issuer", status_code=401)

    if allowed_emails is not None and decoded.get("email") not in allowed_emails:
        raise AuthException("Unauthorized", status_code=403)
