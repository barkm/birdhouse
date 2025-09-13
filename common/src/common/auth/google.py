from fastapi.responses import JSONResponse
from google.oauth2 import id_token
from google.auth.transport import requests


def verify(
    token: str,
    allowed_emails: list[str] | None = None,
    audience: str | None = None,
) -> JSONResponse | None:
    try:
        decoded = id_token.verify_oauth2_token(
            token, requests.Request(), audience=audience
        )
    except ValueError as e:
        return JSONResponse(
            {"detail": f"Token verification failed: {e}"}, status_code=401
        )

    if decoded.get("iss") not in {"https://accounts.google.com", "accounts.google.com"}:
        return JSONResponse({"detail": "Wrong issuer"}, status_code=401)

    if decoded.get("email") not in allowed_emails:
        return JSONResponse({"detail": "Unauthorized"}, status_code=403)

    return None
