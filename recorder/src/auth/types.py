from dataclasses import dataclass
from typing import NewType

UID = NewType("UID", str)
Email = NewType("Email", str)


@dataclass
class DecodedToken:
    uid: UID
    email: Email
