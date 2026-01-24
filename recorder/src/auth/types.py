from dataclasses import dataclass
from typing import NewType, Protocol

UID = NewType("UID", str)
Email = NewType("Email", str)


@dataclass
class DecodedToken:
    uid: UID
    email: Email
    provider: str


class TokenDecoder(Protocol):
    def decode(self, token: str) -> DecodedToken: ...
