import pytest
from fastapi.testclient import TestClient
from veo_custom_video_app.backend.main import app
from veo_custom_video_app.backend.auth.auth import SECRET_API_KEY, API_KEY_NAME

@pytest.fixture(scope="session")
def client() -> TestClient:
    """
    Pytest fixture to create a TestClient instance for the FastAPI application.
    Includes the hardcoded X-API-KEY in its headers for authenticated requests.
    """
    # Reset in-memory databases for a clean slate before tests, if applicable
    # This is a bit of a hack for this example, as we don't have a real DB reset.
    # We'll rely on the order of tests or specific cleanup in tests for now.
    # For a real app, you'd use a test database.
    from veo_custom_video_app.backend.api.routes import db_agencies, db_visions, db_videos
    db_agencies.clear()
    db_visions.clear()
    db_videos.clear()
    
    # Also reset ID counters if they are global in routes.py
    # (Assuming they are global for this example based on previous code)
    # This is important for predictable IDs in tests.
    import veo_custom_video_app.backend.api.routes as api_routes
    api_routes.next_agency_id = 1
    api_routes.next_vision_id = 1
    api_routes.next_video_id = 1

    test_client = TestClient(app)
    test_client.headers[API_KEY_NAME] = SECRET_API_KEY
    return test_client

@pytest.fixture(scope="session")
def client_unauthenticated() -> TestClient:
    """
    Pytest fixture for a TestClient without API key for testing unauthenticated access.
    """
    # Reset in-memory databases for a clean slate before tests
    from veo_custom_video_app.backend.api.routes import db_agencies, db_visions, db_videos
    db_agencies.clear()
    db_visions.clear()
    db_videos.clear()
    
    import veo_custom_video_app.backend.api.routes as api_routes
    api_routes.next_agency_id = 1
    api_routes.next_vision_id = 1
    api_routes.next_video_id = 1
    
    return TestClient(app)
