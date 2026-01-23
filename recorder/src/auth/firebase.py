import logging

from firebase_admin import credentials, initialize_app
from firebase_admin import auth

from src.auth.types import DecodedToken

logger = logging.getLogger(__name__)


def initialize(cert_path: str | None = None):
    initialize_app(credentials.Certificate(cert_path) if cert_path else None)


class FirebaseDecoder:
    def decode(self, token: str) -> DecodedToken:
        return _decode(token)


def _decode(token: str) -> DecodedToken:
    try:
        claims = auth.verify_id_token(token, check_revoked=True)
    except auth.ExpiredIdTokenError:
        raise ValueError("Token expired")
    except auth.RevokedIdTokenError:
        raise ValueError("Token revoked")
    except auth.InvalidIdTokenError:
        raise ValueError("Invalid token")
    except Exception as e:
        logger.exception(f"Token verification failed: {e}")
        raise ValueError("Token verification failed")
    return DecodedToken(uid=claims["uid"], email=claims["email"])
