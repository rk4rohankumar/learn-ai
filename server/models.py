import uuid

from sqlalchemy import (
    Column,
    DateTime,
    Enum as SQLEnum,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
from enum import Enum
from db import Base


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    created_at: Mapped[datetime] = mapped_column(
    DateTime(timezone=True),
    server_default=func.now(),
)

    messages = relationship(
        "Message",
        back_populates="conversation",
        cascade="all, delete-orphan",
    )


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id"),
    )

    role: Mapped[str] = mapped_column(
        String(20)
    )

    content: Mapped[str] = mapped_column(
        Text
    )

    created_at: Mapped[datetime] = mapped_column(
    DateTime(timezone=True),
    server_default=func.now(),
    )

    conversation = relationship(
        "Conversation",
        back_populates="messages",
    )
    # generated_from = relationship(
    # "Generation",
    # foreign_keys="Generation.assistant_message_id",
    # uselist=False,
    # )

    # generation = relationship(
    #     "Generation",
    #     foreign_keys="Generation.user_message_id",
    #     uselist=False,
    # )
    
#generation status
class GenerationStatus(str, Enum):
    CREATED = "created"
    STREAMING = "streaming"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

#Generation table
class Generation(Base):
    __tablename__ = "generations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    user_message_id = Column(
        UUID(as_uuid=True),
        ForeignKey("messages.id"),
        nullable=False,
    )

    assistant_message_id = Column(
        UUID(as_uuid=True),
        ForeignKey("messages.id"),
        nullable=True,
    )

    status = Column(
        SQLEnum(GenerationStatus),
        nullable=False,
        default=GenerationStatus.CREATED,
    )

    provider = Column(String, nullable=False)
    model = Column(String, nullable=False)

    started_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    first_token_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    stop_reason = Column(String, nullable=True)
    error = Column(String, nullable=True)

    input_tokens = Column(Integer, nullable=True)
    output_tokens = Column(Integer, nullable=True)
    
