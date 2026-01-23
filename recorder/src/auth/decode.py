from src.auth import firebase, google
from src.auth.types import DecodedToken

from typing import Callable


def decode_token(token: str) -> DecodedToken:
    decoders: list[Callable[[str], DecodedToken | ValueError]] = [
        _decode_token_or_error(firebase.decode),
        _decode_token_or_error(google.decode),
    ]
    decoded_tokens_or_errors = [decode(token) for decode in decoders]
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


def _decode_token_or_error(
    decode: Callable[[str], DecodedToken],
) -> Callable[[str], ValueError | DecodedToken]:
    def _decode(token: str) -> DecodedToken | ValueError:
        try:
            return decode(token)
        except ValueError as e:
            return e

    return _decode
