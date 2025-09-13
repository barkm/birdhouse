import logging

from fastapi.responses import JSONResponse
from firebase_admin import credentials, initialize_app
from firebase_admin import auth

logger = logging.getLogger(__name__)


def initialize_firebase(cert_path: str | None = None):
    initialize_app(credentials.Certificate(cert_path) if cert_path else None)


def verify(
    token: str,
    allowed_emails: list[str] | None = None,
) -> JSONResponse | None:
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

    return None
