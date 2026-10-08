from __future__ import annotations

import secrets
from datetime import datetime, timedelta

import bcrypt
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..db import crud, schemas
from ..db.base import get_db

router = APIRouter()

def _password_bytes(password: str) -> bytes:
    encoded = password.encode("utf-8")
    if len(encoded) > 72:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password too long (max 72 UTF-8 bytes).",
        )
    return encoded


def _hash_password(password: str) -> str:
    return bcrypt.hashpw(_password_bytes(password), bcrypt.gensalt()).decode("ascii")


def _verify_password(password: str, hashed: str) -> bool:
    encoded = _password_bytes(password)
    try:
        return bcrypt.checkpw(encoded, hashed.encode("ascii"))
    except (ValueError, UnicodeEncodeError):
        return False


def _issue_token() -> dict:
    # Lightweight token stub; replace with JWT/session in production.
    return {
        "access_token": secrets.token_urlsafe(32),
        "token_type": "bearer",
        "expires_at": (datetime.utcnow() + timedelta(hours=8)).isoformat() + "Z",
    }


@router.post("/register", response_model=schemas.UserRead)
def register_user(payload: schemas.UserCreate, db: Session = Depends(get_db)):
    _password_bytes(payload.password)
    existing = crud.get_user_by_email(db, payload.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Email already registered."
        )
    user = crud.create_user(db, payload, hashed_password=_hash_password(payload.password))
    return user


@router.post("/login")
def login_user(payload: schemas.UserCreate, db: Session = Depends(get_db)):
    _password_bytes(payload.password)
    user = crud.get_user_by_email(db, payload.email)
    if not user or not _verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials.",
        )
    return {
        "token": _issue_token(),
        "user": schemas.UserRead.model_validate(user),
    }
