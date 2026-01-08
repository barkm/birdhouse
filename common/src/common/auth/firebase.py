import enum
import logging

from common.auth.exception import AuthException
from common.auth.token import get_token
from firebase_admin import credentials, initialize_app
from firebase_admin import auth

logger = logging.getLogger(__name__)


def initialize(cert_path: str | None = None):
    initialize_app(credentials.Certificate(cert_path) if cert_path else None)


def verify(headers: dict[str, str]) -> None:
    token = get_token(headers)
    try:
        claims = auth.verify_id_token(token, check_revoked=True)
    except auth.ExpiredIdTokenError:
        raise AuthException("Token expired", status_code=401)
    except auth.RevokedIdTokenError:
        raise AuthException("Token revoked", status_code=401)
    except auth.InvalidIdTokenError:
        raise AuthException("Invalid token", status_code=401)
    except Exception as e:
        logger.exception(f"Token verification failed: {e}")
        raise AuthException("Token verification failed", status_code=401)

    if not get_role(claims):
        raise AuthException("User not authorized", status_code=403)


class Role(str, enum.Enum):
    USER = "user"
    ADMIN = "admin"


def get_role(claims: dict) -> Role | None:
    return claims.get("role", None)


def set_role(uid: str, role: Role | None):
    _set_claim(uid, "role", role.value if role else None)


def _set_claim(uid: str, key: str, value):
    user = auth.get_user(uid)
    claims = user.custom_claims or {}
    claims[key] = value
    auth.set_custom_user_claims(uid, claims)
