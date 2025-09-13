from common.auth.exception import AuthException


def get_token(headers: dict[str, str]) -> str:
    auth_header = headers.get("authorization", "")
    scheme, _, token = auth_header.partition(" ")
    if scheme != "Bearer" or not token:
        raise AuthException("Missing bearer token", status_code=401)
    return token
