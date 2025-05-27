import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session as SQLAlchemySession # Renamed to avoid clash
from sqlalchemy.pool import StaticPool # For SQLite in-memory

from veo_custom_video_app.backend.main import app
from veo_custom_video_app.backend.database import Base, get_db # Base for schema, get_db for override
from veo_custom_video_app.backend.auth.auth import SECRET_API_KEY, API_KEY_NAME

# --- Test Database Configuration ---
# Using SQLite in-memory for testing.
# For true parity with production, a separate PostgreSQL test database would be preferred,
# but SQLite is simpler for CI/local testing environments without a dedicated PG instance.
TEST_DATABASE_URL = "sqlite:///:memory:"

test_engine = create_engine(
    TEST_DATABASE_URL,
    # connect_args are specific to SQLite for single-threaded access in tests
    connect_args={"check_same_thread": False},
    # StaticPool is recommended for SQLite in-memory to ensure the same connection is used.
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    """
    Session-scoped fixture to create and drop database tables for tests.
    Autouse=True ensures this runs automatically for the test session.
    """
    # Create all tables defined in models that use the imported Base
    Base.metadata.create_all(bind=test_engine)
    yield
    # Drop all tables after the test session finishes
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture()
def db_session(setup_test_db) -> SQLAlchemySession: # Ensure tables are created first
    """
    Function-scoped fixture to provide a transactional database session for each test.
    Rolls back the transaction after each test to ensure test isolation.
    """
    connection = test_engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    
    yield session
    
    session.close() # Close the session
    transaction.rollback() # Rollback any changes made during the test
    connection.close() # Close the connection


@pytest.fixture()
def client(db_session: SQLAlchemySession) -> TestClient: # Depends on db_session
    """
    Pytest fixture to create a TestClient instance for the FastAPI application,
    with the get_db dependency overridden to use the test database session.
    Includes the hardcoded X-API-KEY in its headers for authenticated requests.
    """
    def override_get_db():
        try:
            yield db_session
        finally:
            # The db_session fixture itself handles closing and rollback.
            # No need to close db_session here again.
            pass 
            
    app.dependency_overrides[get_db] = override_get_db
    
    test_client = TestClient(app)
    test_client.headers[API_KEY_NAME] = SECRET_API_KEY
    
    yield test_client # Provide the TestClient to the test function
    
    del app.dependency_overrides[get_db] # Clean up the override


@pytest.fixture()
def client_unauthenticated(db_session: SQLAlchemySession) -> TestClient: # Depends on db_session
    """
    Pytest fixture for a TestClient without API key, using the test database.
    """
    def override_get_db():
        try:
            yield db_session
        finally:
            pass # db_session fixture handles cleanup

    app.dependency_overrides[get_db] = override_get_db
    
    test_client = TestClient(app)
    
    yield test_client
    
    del app.dependency_overrides[get_db]
