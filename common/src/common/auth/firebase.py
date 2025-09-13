import logging

from common.auth.exception import AuthException
from common.auth.token import get_token
from firebase_admin import credentials, initialize_app
from firebase_admin import auth

logger = logging.getLogger(__name__)


def initialize(cert_path: str | None = None):
    initialize_app(credentials.Certificate(cert_path) if cert_path else None)


def verify(
    headers: dict[str, str],
    allowed_emails: list[str] | None = None,
) -> None:
    token = get_token(headers)
    try:
        decoded = auth.verify_id_token(token, check_revoked=True)
    except auth.ExpiredIdTokenError:
        raise AuthException("Token expired", status_code=401)
    except auth.RevokedIdTokenError:
        raise AuthException("Token revoked", status_code=401)
    except auth.InvalidIdTokenError:
        raise AuthException("Invalid token", status_code=401)
    except Exception as e:
        logger.exception(f"Token verification failed: {e}")
        raise AuthException("Token verification failed", status_code=401)

    if allowed_emails is not None:
        email = decoded.get("email")
        if email not in allowed_emails:
            raise AuthException("Email not authorized", status_code=403)
