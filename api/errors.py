"""Define package errors."""
from typing import Dict, Type


class AnkerSolixError(Exception):
    """Define a base error."""
    pass

class AuthorizationError(AnkerSolixError):
    """Authorization error."""
    pass

class ConnectError(AnkerSolixError):
    """Connection error."""
    pass

class NetworkError(AnkerSolixError):
    """Network error."""
    pass

class ServerError(AnkerSolixError):
    """Server error."""
    pass

class RequestError(AnkerSolixError):
    """Request error."""
    pass

class VerifyCodeError(AnkerSolixError):
    """Verify code error."""
    pass

class VerifyCodeExpiredError(AnkerSolixError):
    """Verification code has expired."""
    pass

class NeedVerifyCodeError(AnkerSolixError):
    """Need verification code error."""
    pass

class VerifyCodeMaxError(AnkerSolixError):
    """Maximum attempts of verications error."""
    pass

class VerifyCodeNoneMatchError(AnkerSolixError):
    """Verify code none match error."""
    pass

class VerifyCodePasswordError(AnkerSolixError):
    """Verify code password error."""
    pass

class ClientPublicKeyError(AnkerSolixError):
    """Define an error for client public key error."""
    pass

class TokenKickedOutError(AnkerSolixError):
    """Define an error for token does not exist because it was kicked out."""
    pass

class InvalidCredentialsError(AnkerSolixError):
    """Define an error for unauthenticated accounts."""
    pass

class RetryExceeded(AnkerSolixError):
    """Define an error for exceeded retry attempts. Please try again in 24 hours."""
    pass

ERRORS: Dict[int, Type[AnkerSolixError]] = {
    401: AuthorizationError,
    997: ConnectError,
    998: NetworkError,
    999: ServerError,
    10000: RequestError,
    10003: RequestError,
    10007: RequestError,
    26050: VerifyCodeError,
    26051: VerifyCodeExpiredError,
    26052: NeedVerifyCodeError,
    26053: VerifyCodeMaxError,
    26054: VerifyCodeNoneMatchError,
    26055: VerifyCodePasswordError,
    26070: ClientPublicKeyError,
    26084: TokenKickedOutError,
    26108: InvalidCredentialsError,
    100053: RetryExceeded,
}


def raise_error(data: dict) -> None:
    """Raise the appropriate error based upon a response code."""
    code = data.get("code", -1)
    if code in [0]:
        return
    cls = ERRORS.get(code, AnkerSolixError)
    raise cls(f'({code}) {data.get("msg","Error msg not found")}')
