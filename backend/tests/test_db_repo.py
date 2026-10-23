import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db import repo
from app.db.base import Base


@pytest.fixture
def db_session() -> Session:
    """In-memory SQLite session for testing repository operations."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    session = session_factory()
    try:
        yield session
    finally:
        session.close()


def test_user_creation_and_lookup(db_session: Session) -> None:
    user = repo.get_or_create_user(db_session, clerk_user_id="user_clerk_1", email="test1@example.com")
    assert user.id is not None
    assert user.clerk_user_id == "user_clerk_1"
    assert user.email == "test1@example.com"

    # Reuse on second call
    user2 = repo.get_or_create_user(db_session, clerk_user_id="user_clerk_1", email="test1_updated@example.com")
    assert user2.id == user.id
    assert user2.email == "test1_updated@example.com"

    by_clerk = repo.get_user_by_clerk_id(db_session, "user_clerk_1")
    assert by_clerk is not None
    assert by_clerk.id == user.id

    by_id = repo.get_user_by_id(db_session, user.id)
    assert by_id is not None
    assert by_id.clerk_user_id == "user_clerk_1"


def test_user_file_crud_and_isolation(db_session: Session) -> None:
    user_a = repo.get_or_create_user(db_session, "clerk_a")
    user_b = repo.get_or_create_user(db_session, "clerk_b")

    # Create file for user A
    file_a = repo.create_file(
        db=db_session,
        user_id=user_a.id,
        original_name="sales.csv",
        table_name="sales",
        rows=100,
        cols=5,
        size_bytes=1024,
        storage_path="/tmp/sales.parquet",
        profile_json={"columns": []},
        quality_json={"score": 90},
        warnings_json=["warn1"],
    )
    assert file_a.id is not None
    assert file_a.table_name == "sales"

    # User A can get and list
    assert repo.get_file(db_session, user_a.id, file_a.id) is not None
    assert repo.get_file_by_table_name(db_session, user_a.id, "sales") is not None
    assert len(repo.list_files(db_session, user_a.id)) == 1

    # User B CANNOT get, lookup, list or delete user A's file
    assert repo.get_file(db_session, user_b.id, file_a.id) is None
    assert repo.get_file_by_table_name(db_session, user_b.id, "sales") is None
    assert len(repo.list_files(db_session, user_b.id)) == 0
    assert repo.delete_file(db_session, user_b.id, file_a.id) is False

    # User A deletes file
    assert repo.delete_file(db_session, user_a.id, file_a.id) is True
    assert repo.get_file(db_session, user_a.id, file_a.id) is None


def test_conversation_and_message_crud_with_cascade(db_session: Session) -> None:
    user_a = repo.get_or_create_user(db_session, "clerk_a")
    user_b = repo.get_or_create_user(db_session, "clerk_b")

    conv_a = repo.create_conversation(db_session, user_a.id, title="Test Chat")
    assert conv_a.title == "Test Chat"

    # User B cannot see user A's conversation
    assert repo.get_conversation(db_session, user_b.id, conv_a.id) is None
    assert len(repo.list_conversations(db_session, user_b.id)) == 0

    # User A adds messages
    msg1 = repo.create_message(db_session, user_a.id, conv_a.id, role="user", content="Hello")
    msg2 = repo.create_message(
        db_session,
        user_a.id,
        conv_a.id,
        role="assistant",
        content="World",
        artifacts_json=[{"kind": "table", "rows": []}],
        trace_json={"provider": "fake"},
    )
    assert msg1.id is not None
    assert msg2.id is not None

    messages = repo.get_messages(db_session, user_a.id, conv_a.id)
    assert len(messages) == 2
    assert messages[0].content == "Hello"
    assert messages[1].content == "World"

    # User B cannot read messages of user A's conversation
    assert repo.get_messages(db_session, user_b.id, conv_a.id) == []

    # Updating title
    updated = repo.update_conversation_title(db_session, user_a.id, conv_a.id, "New Title")
    assert updated is not None
    assert updated.title == "New Title"

    # Cascade delete conversation deletes messages
    assert repo.delete_conversation(db_session, user_a.id, conv_a.id) is True
    assert repo.get_conversation(db_session, user_a.id, conv_a.id) is None
    assert repo.get_messages(db_session, user_a.id, conv_a.id) == []


def test_pin_crud_and_isolation(db_session: Session) -> None:
    user_a = repo.get_or_create_user(db_session, "clerk_a")
    user_b = repo.get_or_create_user(db_session, "clerk_b")

    pin = repo.create_pin(
        db=db_session,
        user_id=user_a.id,
        title="Revenue Chart",
        figure_json={"data": []},
        sql_text="SELECT 1",
    )
    assert pin.id is not None

    # Isolation check
    assert repo.get_pin(db_session, user_a.id, pin.id) is not None
    assert repo.get_pin(db_session, user_b.id, pin.id) is None
    assert len(repo.list_pins(db_session, user_a.id)) == 1
    assert len(repo.list_pins(db_session, user_b.id)) == 0

    assert repo.delete_pin(db_session, user_b.id, pin.id) is False
    assert repo.delete_pin(db_session, user_a.id, pin.id) is True
    assert repo.get_pin(db_session, user_a.id, pin.id) is None
