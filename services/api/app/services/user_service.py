from __future__ import annotations

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import AppError
from app.core.security import hash_password
from app.db.models.user import User


class UserService:
    def __init__(self, db: Session):
        self.db = db

    def get_by_username(self, username: str) -> User | None:
        return (
            self.db.query(User).filter(User.username == username).one_or_none()
        )

    def get_by_id(self, user_id: int) -> User | None:
        return self.db.query(User).filter(User.id == user_id).one_or_none()

    def create_user(self, username: str, password: str, role: str = "user") -> User:
        if self.get_by_username(username) is not None:
            raise AppError.conflict("username already exists")

        user = User(username=username, password_hash=hash_password(password), role=role)
        self.db.add(user)
        try:
            self.db.commit()
        except IntegrityError:
            self.db.rollback()
            raise AppError.conflict("username already exists")
        self.db.refresh(user)
        return user

    def ensure_bootstrap_admin(self) -> None:
        user = self.get_by_username(settings.admin_username)
        if user is not None:
            return
        admin = User(
            username=settings.admin_username,
            password_hash=hash_password(settings.admin_password),
            role=settings.admin_role,
        )
        self.db.add(admin)
