import logging

from fastapi.responses import JSONResponse
from firebase_admin import credentials, initialize_app
from fastapi import Request
from firebase_admin import auth

logger = logging.getLogger(__name__)


def initialize_firebase(cert_path: str | None = None):
    initialize_app(credentials.Certificate(cert_path) if cert_path else None)


async def validate(
    request: Request, call_next, allowed_emails: list[str] | None = None
):
    if not request.headers.get("x-external", "false").lower() == "true":
        return await call_next(request)
    auth_header = request.headers.get("authorization", "")
    scheme, _, token = auth_header.partition(" ")
    if scheme != "Bearer" or not token:
        return JSONResponse({"detail": "Missing Bearer token"}, status_code=401)
    try:
        decoded = auth.verify_id_token(token, check_revoked=True)
    except auth.ExpiredIdTokenError:
        return JSONResponse({"detail": "Token expired"}, status_code=401)
    except auth.RevokedIdTokenError:
        return JSONResponse({"detail": "Token revoked"}, status_code=401)
    except auth.InvalidIdTokenError:
        return JSONResponse({"detail": "Invalid token"}, status_code=401)
    except Exception as e:
        logger.exception(f"Token verification failed: {e}")
        return JSONResponse({"detail": "Token verification failed"}, status_code=401)

    if allowed_emails is not None:
        email = decoded.get("email")
        if email not in allowed_emails:
            return JSONResponse({"detail": "Email not authorized"}, status_code=403)

    return await call_next(request)
