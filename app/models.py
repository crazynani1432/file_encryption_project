from datetime import datetime, timezone
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, LargeBinary, String
from sqlalchemy.orm import relationship
try:
    from app.database import Base
except (ImportError, ValueError):
    from database import Base



class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    last_login_at = Column(DateTime, nullable=True)

    files = relationship("EncryptedFile", back_populates="sender", cascade="all, delete-orphan")


class EncryptedFile(Base):
    __tablename__ = "encrypted_files"

    id = Column(String, primary_key=True, index=True)  # Store UUID string
    filename = Column(String, nullable=False)
    filepath = Column(String, nullable=False)
    access_policy = Column(String, nullable=False)  # 'PASSWORD', 'QUESTION', 'OTP'
    sender_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    recipient_email = Column(String, nullable=True)
    security_question = Column(String, nullable=True)
    encrypted_file_key = Column(LargeBinary, nullable=True)  # Encrypted with server master key (OTP mode only)
    download_count = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    sender = relationship("User", back_populates="files")
    otps = relationship("ActiveOTP", back_populates="file", cascade="all, delete-orphan")


class ActiveOTP(Base):
    __tablename__ = "active_otps"

    id = Column(Integer, primary_key=True, index=True)
    file_id = Column(String, ForeignKey("encrypted_files.id"), nullable=False)
    email = Column(String, nullable=False)
    otp_code_hash = Column(String, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    verified = Column(Boolean, default=False, nullable=False)
    attempts = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    file = relationship("EncryptedFile", back_populates="otps")
