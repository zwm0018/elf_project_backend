from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ...db import User, get_db, get_user_by_username
from ...schemas import LoginRequest, TokenResponse, UserOut
from ...security import DUMMY_PASSWORD_HASH, create_access_token, verify_password
from ..deps import get_current_user

router = APIRouter(prefix="/auth", tags=["认证"])


def _invalid_credentials() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="用户名或密码错误",
        headers={"WWW-Authenticate": "Bearer"},
    )


def _user_out(user: User) -> UserOut:
    return UserOut(
        id=user.id,
        username=user.username,
        display_name=user.display_name,
    )


@router.post("/login", response_model=TokenResponse, summary="用户名密码登录")
def login(body: LoginRequest, session: Session = Depends(get_db)) -> TokenResponse:
    user = get_user_by_username(session, body.username)
    if user is None:
        # 即使用户不存在也执行一次同成本哈希，避免通过响应时间枚举账号。
        verify_password(body.password, DUMMY_PASSWORD_HASH)
        raise _invalid_credentials()
    if not verify_password(body.password, user.password_hash):
        raise _invalid_credentials()

    token, expires_in = create_access_token(user.id, user.username)
    return TokenResponse(
        access_token=token,
        expires_in=expires_in,
        user=_user_out(user),
    )


@router.get("/me", response_model=UserOut, summary="读取当前登录用户")
def me(current_user: User = Depends(get_current_user)) -> UserOut:
    return _user_out(current_user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT, summary="退出登录")
def logout(_current_user: User = Depends(get_current_user)) -> None:
    # JWT 是无状态的：客户端删除 token 即完成退出；如需即时吊销，可在此加黑名单。
    return None
