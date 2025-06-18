"""
User entity model.
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import Boolean, Column, DateTime, String, Text
from sqlalchemy.dialects.postgresql import TIMESTAMP, UUID
from sqlalchemy.orm import relationship

from src.database.core import Base


class User(Base):
    """User entity with schema compatible for NextAuth.js integration."""

    __tablename__ = "users"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=True)
    email = Column(String(255), unique=True, index=True, nullable=True)
    emailVerified = Column(TIMESTAMP(timezone=True), nullable=True)
    image = Column(Text, nullable=True)

    # Additional fields for our application
    password_hash = Column(String(255), nullable=True)  # For local auth
    company_name = Column(String(255), nullable=True)
    role = Column(String(50), default="user", nullable=False)  # user, admin
    is_active = Column(Boolean, default=True, nullable=False)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(UTC))
    updated_at = Column(DateTime, nullable=True, onupdate=lambda: datetime.now(UTC))

    # Relationships
    accounts = relationship("Account", back_populates="user", cascade="all, delete-orphan")
    sessions = relationship("Session", back_populates="user", cascade="all, delete-orphan")
    files = relationship("FileUpload", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<User(email='{self.email}', id='{self.id}')>"
