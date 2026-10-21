from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from ..db import User, get_db, get_user_by_id
from ..security import decode_access_token

bearer_scheme = HTTPBearer(auto_error=False)


def _unauthorized(detail: str = "未登录或登录已过期") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    session: Session = Depends(get_db),
) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise _unauthorized()
    try:
        payload = decode_access_token(credentials.credentials)
        user_id = int(payload.get("sub", ""))
    except (ValueError, TypeError):
        raise _unauthorized() from None
    user = get_user_by_id(session, user_id)
    if user is None:
        raise _unauthorized()
    return user
