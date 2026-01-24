from src.auth import firebase, google
from src.auth.types import DecodedToken, TokenDecoder

from typing import Callable


class Decoder(TokenDecoder):
    def __init__(self) -> None:
        self.decoders: list[TokenDecoder] = [
            firebase.FirebaseDecoder(),
            google.GoogleDecoder(),
        ]

    def decode(self, token: str) -> DecodedToken:
        return _decode_token(token, self.decoders)


def _decode_token(token: str, decoders: list[TokenDecoder]) -> DecodedToken:
    decoded_tokens_or_errors = [
        _decode_token_or_error(decoder)(token) for decoder in decoders
    ]
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
    decoder: TokenDecoder,
) -> Callable[[str], ValueError | DecodedToken]:
    def _decode(token: str) -> DecodedToken | ValueError:
        try:
            return decoder.decode(token)
        except ValueError as e:
            return e

    return _decode
