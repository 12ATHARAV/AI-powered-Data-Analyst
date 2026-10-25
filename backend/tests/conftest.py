import pytest
from backend.app.config import settings


@pytest.fixture(scope="session", autouse=True)
def isolated_database(tmp_path_factory):
    """
    Run the whole suite against an throwaway copy of the database so tests
    never pollute the developer's live analyst.db (which is what the UI reads).

    The samples are ingested by the first test into this temp DB, and later
    tests reuse the same session-scoped path.
    """
    original = settings.DATABASE_PATH
    settings.DATABASE_PATH = str(tmp_path_factory.mktemp("test-db") / "analyst.db")
    yield
    settings.DATABASE_PATH = original
