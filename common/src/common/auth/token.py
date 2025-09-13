def get_token(headers: dict[str, str]) -> str | None:
    auth_header = headers.get("authorization", "")
    scheme, _, token = auth_header.partition(" ")
    if scheme != "Bearer" or not token:
        return None
    return token
