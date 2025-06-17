"""
Authentication-related entities with schema compatible for NextAuth.js integration.
"""

from sqlalchemy import BigInteger, Column, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.orm import relationship

from src.database.core import Base


class Account(Base):
    """OAuth account connections (for NextAuth.js compatibility)."""

    __tablename__ = "accounts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    userId = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
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

    id = Column(Integer, primary_key=True, autoincrement=True)
    userId = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
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
