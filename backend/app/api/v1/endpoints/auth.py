from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from jose import JWTError

from app.core.deps import CurrentUser, DbSession
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
)
from app.models.user import User
from app.schemas.auth import RefreshRequest, Token, TokenWithUser
from app.schemas.user import UserCreate, UserPublic, UserUpdate
from app.services import auth_service
from app.core.security import hash_password

router = APIRouter(prefix="/auth", tags=["auth"])


def _issue_tokens(user: User) -> dict:
    return {
        "access_token": create_access_token(user.id),
        "refresh_token": create_refresh_token(user.id),
        "token_type": "bearer",
    }


@router.post("/register", response_model=TokenWithUser, status_code=status.HTTP_201_CREATED)
async def register(payload: UserCreate, db: DbSession) -> TokenWithUser:
    user = await auth_service.register_user(db, payload)
    return TokenWithUser(**_issue_tokens(user), user=UserPublic.model_validate(user))


@router.post("/login", response_model=TokenWithUser)
async def login(
    form: Annotated[OAuth2PasswordRequestForm, Depends()], db: DbSession
) -> TokenWithUser:
    """OAuth2 password flow. ``username`` is the user's email."""
    user = await auth_service.authenticate_user(db, form.username, form.password)
    return TokenWithUser(**_issue_tokens(user), user=UserPublic.model_validate(user))


@router.post("/refresh", response_model=Token)
async def refresh(payload: RefreshRequest, db: DbSession) -> Token:
    try:
        data = decode_token(payload.refresh_token, expected_type="refresh")
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token."
        )
    user = await db.get(User, uuid.UUID(data["sub"]))
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token."
        )
    return Token(**_issue_tokens(user))


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(_: CurrentUser):
    """Stateless JWT logout — the client discards its tokens."""
    return None


@router.get("/me", response_model=UserPublic)
async def me(current_user: CurrentUser) -> UserPublic:
    return UserPublic.model_validate(current_user)


@router.patch("/me", response_model=UserPublic)
async def update_me(
    payload: UserUpdate, current_user: CurrentUser, db: DbSession
) -> UserPublic:
    if payload.name is not None:
        current_user.name = payload.name
    if payload.password is not None:
        current_user.hashed_password = hash_password(payload.password)
    await db.commit()
    await db.refresh(current_user)
    return UserPublic.model_validate(current_user)
