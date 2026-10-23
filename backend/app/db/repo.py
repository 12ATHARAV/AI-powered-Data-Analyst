import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Conversation, File, Message, Pin, User


def get_or_create_user(db: Session, clerk_user_id: str, email: str | None = None) -> User:
    """Fetch existing user by clerk_user_id or create a new user."""
    stmt = select(User).where(User.clerk_user_id == clerk_user_id)
    user = db.scalar(stmt)
    if not user:
        user = User(clerk_user_id=clerk_user_id, email=email)
        db.add(user)
        db.commit()
        db.refresh(user)
    elif email and user.email != email:
        user.email = email
        db.commit()
        db.refresh(user)
    return user


def get_user_by_clerk_id(db: Session, clerk_user_id: str) -> User | None:
    """Find user by clerk_user_id."""
    stmt = select(User).where(User.clerk_user_id == clerk_user_id)
    return db.scalar(stmt)


def get_user_by_id(db: Session, user_id: uuid.UUID) -> User | None:
    """Find user by primary key ID."""
    stmt = select(User).where(User.id == user_id)
    return db.scalar(stmt)


# File operations
def create_file(
    db: Session,
    user_id: uuid.UUID,
    original_name: str,
    table_name: str,
    rows: int,
    cols: int,
    size_bytes: int,
    storage_path: str,
    profile_json: dict[str, Any],
    quality_json: dict[str, Any],
    warnings_json: list[str],
) -> File:
    """Create a new file record for the user."""
    file_record = File(
        user_id=user_id,
        original_name=original_name,
        table_name=table_name,
        rows=rows,
        cols=cols,
        size_bytes=size_bytes,
        storage_path=storage_path,
        profile_json=profile_json,
        quality_json=quality_json,
        warnings_json=warnings_json,
    )
    db.add(file_record)
    db.commit()
    db.refresh(file_record)
    return file_record


def get_file(db: Session, user_id: uuid.UUID, file_id: uuid.UUID) -> File | None:
    """Get a file by ID strictly filtered by user_id."""
    stmt = select(File).where(File.id == file_id, File.user_id == user_id)
    return db.scalar(stmt)


def get_file_by_table_name(db: Session, user_id: uuid.UUID, table_name: str) -> File | None:
    """Get a file by table_name strictly filtered by user_id."""
    stmt = select(File).where(File.table_name == table_name, File.user_id == user_id)
    return db.scalar(stmt)


def list_files(db: Session, user_id: uuid.UUID) -> list[File]:
    """List all files for the user ordered by creation time."""
    stmt = select(File).where(File.user_id == user_id).order_by(File.created_at.asc())
    return list(db.scalars(stmt).all())


def delete_file(db: Session, user_id: uuid.UUID, file_id: uuid.UUID) -> bool:
    """Delete a file belonging to user_id. Returns True if found and deleted, else False."""
    file_record = get_file(db, user_id, file_id)
    if not file_record:
        return False
    db.delete(file_record)
    db.commit()
    return True


# Conversation operations
def create_conversation(db: Session, user_id: uuid.UUID, title: str | None = None) -> Conversation:
    """Create a new conversation for user_id."""
    conv = Conversation(user_id=user_id, title=title)
    db.add(conv)
    db.commit()
    db.refresh(conv)
    return conv


def get_conversation(db: Session, user_id: uuid.UUID, conv_id: uuid.UUID) -> Conversation | None:
    """Get a conversation strictly filtered by user_id."""
    stmt = select(Conversation).where(Conversation.id == conv_id, Conversation.user_id == user_id)
    return db.scalar(stmt)


def list_conversations(db: Session, user_id: uuid.UUID) -> list[Conversation]:
    """List all conversations for user_id, newest first."""
    stmt = select(Conversation).where(Conversation.user_id == user_id).order_by(Conversation.created_at.desc())
    return list(db.scalars(stmt).all())


def update_conversation_title(db: Session, user_id: uuid.UUID, conv_id: uuid.UUID, title: str) -> Conversation | None:
    """Update conversation title if owned by user_id."""
    conv = get_conversation(db, user_id, conv_id)
    if not conv:
        return None
    conv.title = title
    db.commit()
    db.refresh(conv)
    return conv


def delete_conversation(db: Session, user_id: uuid.UUID, conv_id: uuid.UUID) -> bool:
    """Delete conversation and cascade messages if owned by user_id."""
    conv = get_conversation(db, user_id, conv_id)
    if not conv:
        return False
    db.delete(conv)
    db.commit()
    return True


# Message operations
def create_message(
    db: Session,
    user_id: uuid.UUID,
    conv_id: uuid.UUID,
    role: str,
    content: str,
    artifacts_json: list[dict[str, Any]] | None = None,
    trace_json: dict[str, Any] | None = None,
    verification_json: dict[str, Any] | None = None,
) -> Message:
    """Create a message in a conversation owned by user_id."""
    conv = get_conversation(db, user_id, conv_id)
    if not conv:
        raise ValueError("Conversation not found or access denied")
    msg = Message(
        conversation_id=conv_id,
        user_id=user_id,
        role=role,
        content=content,
        artifacts_json=artifacts_json or [],
        trace_json=trace_json,
        verification_json=verification_json,
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)
    return msg


def get_messages(
    db: Session,
    user_id: uuid.UUID,
    conv_id: uuid.UUID,
    limit: int | None = None,
) -> list[Message]:
    """Get messages for a conversation owned by user_id, oldest first."""
    conv = get_conversation(db, user_id, conv_id)
    if not conv:
        return []
    stmt = select(Message).where(Message.conversation_id == conv_id, Message.user_id == user_id).order_by(Message.created_at.asc())
    if limit:
        # If limiting, get the last N messages in chronological order
        subquery = (
            select(Message)
            .where(Message.conversation_id == conv_id, Message.user_id == user_id)
            .order_by(Message.created_at.desc())
            .limit(limit)
            .subquery()
        )
        stmt = select(Message).join(subquery, Message.id == subquery.c.id).order_by(Message.created_at.asc())
    return list(db.scalars(stmt).all())


# Pin operations
def create_pin(
    db: Session,
    user_id: uuid.UUID,
    title: str,
    figure_json: dict[str, Any],
    sql_text: str | None = None,
) -> Pin:
    """Create a dashboard pin for user_id."""
    pin = Pin(
        user_id=user_id,
        title=title,
        figure_json=figure_json,
        sql_text=sql_text,
    )
    db.add(pin)
    db.commit()
    db.refresh(pin)
    return pin


def get_pin(db: Session, user_id: uuid.UUID, pin_id: uuid.UUID) -> Pin | None:
    """Get a pin by ID strictly filtered by user_id."""
    stmt = select(Pin).where(Pin.id == pin_id, Pin.user_id == user_id)
    return db.scalar(stmt)


def list_pins(db: Session, user_id: uuid.UUID) -> list[Pin]:
    """List all pins for user_id, newest first."""
    stmt = select(Pin).where(Pin.user_id == user_id).order_by(Pin.created_at.desc())
    return list(db.scalars(stmt).all())


def delete_pin(db: Session, user_id: uuid.UUID, pin_id: uuid.UUID) -> bool:
    """Delete a pin if owned by user_id."""
    pin = get_pin(db, user_id, pin_id)
    if not pin:
        return False
    db.delete(pin)
    db.commit()
    return True
