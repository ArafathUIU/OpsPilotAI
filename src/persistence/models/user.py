"""User ORM model for RBAC authorization."""

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from src.persistence.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class UserModel(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """User account model with RBAC role."""

    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(
        String(50), default="VIEWER", nullable=False
    )  # VIEWER, OPERATOR, ADMIN
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
