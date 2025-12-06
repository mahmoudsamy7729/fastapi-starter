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
    stripe_customer_id: Mapped[str] = mapped_column(String(), nullable=True)
    provider: Mapped[Provider] = mapped_column(SAENUM(Provider), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),
                                    default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),
                default=lambda: datetime.now(timezone.utc),onupdate=lambda: datetime.now(timezone.utc))
    
    subscriptions = relationship("Subscription", back_populates="user")


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


    