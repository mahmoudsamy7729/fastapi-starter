from uuid import uuid4, UUID as PyUUID
from enum import Enum
from datetime import timezone, datetime
from src.database import Base
from sqlalchemy import String, Boolean, DateTime, ForeignKey, Enum as SAENUM
from sqlalchemy.orm import relationship, mapped_column, Mapped
from sqlalchemy.dialects.postgresql import UUID



class Provider(str, Enum):
    GOOGLE = "google"
    GITHUB = "github"
    LOCAL = "local"


class User(Base):
    __tablename__ = "users"

    id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    username: Mapped[str] = mapped_column(String(255), unique=True, nullable=False) 
    password: Mapped[str] = mapped_column(String(255), nullable=True) #nullable true for social login 
    is_admin: Mapped[bool] = mapped_column(Boolean(), default=False)
    is_active: Mapped[bool] = mapped_column(Boolean(), default=True) 
    is_verified: Mapped[bool] = mapped_column(Boolean(), default=False) 
    provider: Mapped[Provider] = mapped_column(SAENUM(Provider), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),
                                    default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),
                default=lambda: datetime.now(timezone.utc),onupdate=lambda: datetime.now(timezone.utc))
    
    profile = relationship("Profile", back_populates="user", uselist=False)
    subscriptions = relationship("Subscription", back_populates="user")


class Profile(Base):
    __tablename__ = "profiles"

    id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, unique=True)
    first_name: Mapped[str] = mapped_column(String(255), nullable=True)
    last_name: Mapped[str] = mapped_column(String(255), nullable=True)
    profile_img: Mapped[str] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),
                                    default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),
                default=lambda: datetime.now(timezone.utc),onupdate=lambda: datetime.now(timezone.utc))
    

    user = relationship("User", back_populates="profile")


class LoginCode(Base):
    __tablename__ = 'login_codes'

    id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    code_hash: Mapped[str] = mapped_column(String(), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),
                                    default=lambda: datetime.now(timezone.utc))

    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True)
    )


    