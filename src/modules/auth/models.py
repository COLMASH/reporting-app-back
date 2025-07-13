"""
Database models for authentication module.
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import BigInteger, Boolean, Column, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import TIMESTAMP, UUID
from sqlalchemy.orm import relationship

from src.core.database.core import Base


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
    files = relationship("File", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<User(email='{self.email}', id='{self.id}')>"


class Account(Base):
    """OAuth account connections (for NextAuth.js compatibility)."""

    __tablename__ = "accounts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    userId = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    type = Column(String(255), nullable=False)
    provider = Column(String(255), nullable=False)
    providerAccountId = Column(String(255), nullable=False)
    refresh_token = Column(Text, nullable=True)
    access_token = Column(Text, nullable=True)
    expires_at = Column(BigInteger, nullable=True)
    id_token = Column(Text, nullable=True)
    scope = Column(Text, nullable=True)
    session_state = Column(Text, nullable=True)
    token_type = Column(Text, nullable=True)

    # Relationships
    user = relationship("User", back_populates="accounts")

    def __repr__(self) -> str:
        return f"<Account(provider='{self.provider}', userId='{self.userId}')>"


class Session(Base):
    """User sessions table (for NextAuth.js compatibility)."""

    __tablename__ = "sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    userId = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    expires = Column(TIMESTAMP(timezone=True), nullable=False)
    sessionToken = Column(String(255), nullable=False, unique=True, index=True)

    # Relationships
    user = relationship("User", back_populates="sessions")

    def __repr__(self) -> str:
        return f"<Session(userId='{self.userId}', expires='{self.expires}')>"


class VerificationToken(Base):
    """Email verification tokens table (for NextAuth.js compatibility)."""

    __tablename__ = "verification_token"

    identifier = Column(Text, primary_key=True)
    token = Column(Text, primary_key=True)
    expires = Column(TIMESTAMP(timezone=True), nullable=False)

    def __repr__(self) -> str:
        return f"<VerificationToken(identifier='{self.identifier}')>"
