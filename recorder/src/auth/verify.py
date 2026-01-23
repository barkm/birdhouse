from src.auth import firebase, google
from src.auth.types import DecodedToken

from typing import Callable


def verify_token(token: str) -> DecodedToken:
    verifiers: list[Callable[[str], DecodedToken | ValueError]] = [
        _verify_or_error(firebase.decode),
        _verify_or_error(google.decode),
    ]
    decoded_tokens_or_errors = [verify(token) for verify in verifiers]
    decoded_tokens = (
        dt for dt in decoded_tokens_or_errors if isinstance(dt, DecodedToken)
    )
    first_decoded_token = next(decoded_tokens, None)
    if not first_decoded_token:
        errors = (
            err for err in decoded_tokens_or_errors if isinstance(err, ValueError)
        )
        raise next(errors)
    return first_decoded_token


def _verify_or_error(
    verify: Callable[[str], DecodedToken],
) -> Callable[[str], ValueError | DecodedToken]:
    def _verify(token: str) -> DecodedToken | ValueError:
        try:
            return verify(token)
        except ValueError as e:
            return e

    return _verify
