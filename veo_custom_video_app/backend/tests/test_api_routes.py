from fastapi.testclient import TestClient
import pytest
import time # For simulating delay to check video status changes

# Assuming conftest.py provides 'client' (authenticated) and 'client_unauthenticated'
# from veo_custom_video_app.backend.auth.auth import API_KEY_NAME, SECRET_API_KEY

# --- Helper Data ---
AGENCY_DATA_1 = {"name": "Test Agency One", "email": "agency1@example.com"}
AGENCY_DATA_2 = {"name": "Test Agency Two", "email": "agency2@example.com"}
VISION_DATA_1 = {"name": "Vision Alpha", "description": "First vision", "veo_parameters": {"prompt": "prompt1", "style": "style1"}}
VIDEO_CREATE_DATA = {} # Currently empty as per VideoCreate schema

# --- Authentication Tests ---

def test_unauthenticated_access(client_unauthenticated: TestClient):
    """Test that accessing a protected endpoint without API key fails."""
    response = client_unauthenticated.get("/api/v1/agencies/")
    assert response.status_code == 401 # or 403 if auto_error=False and not handled
    assert "Invalid or missing API Key" in response.json().get("detail", "")


def test_incorrect_api_key(client_unauthenticated: TestClient):
    """Test that accessing a protected endpoint with an incorrect API key fails."""
    response = client_unauthenticated.get("/api/v1/agencies/", headers={"X-API-KEY": "WRONG_KEY"})
    assert response.status_code == 401
    assert "Invalid or missing API Key" in response.json().get("detail", "")

def test_correct_api_key(client: TestClient):
    """Test that accessing a protected endpoint with the correct API key succeeds."""
    response = client.get("/api/v1/agencies/")
    assert response.status_code == 200 # Expect empty list if DB is clear

# --- Agency Endpoint Tests ---

def test_create_agency(client: TestClient):
    response = client.post("/api/v1/agencies/", json=AGENCY_DATA_1)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == AGENCY_DATA_1["name"]
    assert data["email"] == AGENCY_DATA_1["email"]
    assert "id" in data
    assert "created_at" in data
    assert "updated_at" in data
    pytest.agency_id_1 = data["id"] # Store for subsequent tests

def test_create_duplicate_agency_email(client: TestClient):
    # First agency creation is expected to succeed (done in test_create_agency or a fixture)
    # Attempt to create another agency with the same email
    response = client.post("/api/v1/agencies/", json={"name": "Another Name", "email": AGENCY_DATA_1["email"]})
    assert response.status_code == 400
    assert "Agency with this email already exists" in response.json()["detail"]

def test_list_agencies(client: TestClient):
    # Create a second agency to test listing multiple
    client.post("/api/v1/agencies/", json=AGENCY_DATA_2) # Assuming email is unique
    
    response = client.get("/api/v1/agencies/")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 2 # Based on this and previous test
    assert any(item["name"] == AGENCY_DATA_1["name"] for item in data)
    assert any(item["name"] == AGENCY_DATA_2["name"] for item in data)

def test_get_specific_agency(client: TestClient):
    assert hasattr(pytest, "agency_id_1"), "Agency ID from create_agency test not found"
    agency_id = pytest.agency_id_1
    response = client.get(f"/api/v1/agencies/{agency_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == agency_id
    assert data["name"] == AGENCY_DATA_1["name"]

def test_get_non_existent_agency(client: TestClient):
    response = client.get("/api/v1/agencies/99999")
    assert response.status_code == 404

def test_update_agency(client: TestClient):
    assert hasattr(pytest, "agency_id_1"), "Agency ID from create_agency test not found"
    agency_id = pytest.agency_id_1
    update_data = {"name": "Updated Test Agency One", "email": "updated_agency1@example.com"}
    response = client.put(f"/api/v1/agencies/{agency_id}", json=update_data)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == update_data["name"]
    assert data["email"] == update_data["email"]
    assert data["id"] == agency_id

def test_delete_agency(client: TestClient):
    # Create a new agency specifically for this test to avoid conflicts
    agency_to_delete_data = {"name": "Agency To Delete", "email": "delete_me@example.com"}
    response_create = client.post("/api/v1/agencies/", json=agency_to_delete_data)
    assert response_create.status_code == 201
    agency_to_delete_id = response_create.json()["id"]

    response_delete = client.delete(f"/api/v1/agencies/{agency_to_delete_id}")
    assert response_delete.status_code == 200
    assert "deleted successfully" in response_delete.json()["message"]

    # Verify it's gone
    response_get = client.get(f"/api/v1/agencies/{agency_to_delete_id}")
    assert response_get.status_code == 404

# --- Vision Endpoint Tests ---

@pytest.fixture(scope="module", autouse=True)
def setup_agency_for_visions(client: TestClient):
    """Ensure at least one agency exists for vision tests."""
    # Using agency_id_1 if already created, otherwise create a new one
    if not hasattr(pytest, "agency_id_1"):
        response = client.post("/api/v1/agencies/", json={"name": "AgencyForVisions", "email": "afv@example.com"})
        assert response.status_code == 201
        pytest.agency_id_for_visions = response.json()["id"]
    else:
        pytest.agency_id_for_visions = pytest.agency_id_1


def test_create_vision(client: TestClient):
    agency_id = pytest.agency_id_for_visions
    response = client.post(f"/api/v1/agencies/{agency_id}/visions/", json=VISION_DATA_1)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == VISION_DATA_1["name"]
    assert data["agency_id"] == agency_id
    assert data["veo_parameters"] == VISION_DATA_1["veo_parameters"]
    assert "id" in data
    pytest.vision_id_1 = data["id"]

def test_list_visions_for_agency(client: TestClient):
    agency_id = pytest.agency_id_for_visions
    response = client.get(f"/api/v1/agencies/{agency_id}/visions/")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert any(item["name"] == VISION_DATA_1["name"] for item in data)

def test_get_specific_vision(client: TestClient):
    assert hasattr(pytest, "vision_id_1"), "Vision ID from create_vision test not found"
    vision_id = pytest.vision_id_1
    response = client.get(f"/api/v1/visions/{vision_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == vision_id
    assert data["name"] == VISION_DATA_1["name"]

def test_update_vision(client: TestClient):
    assert hasattr(pytest, "vision_id_1"), "Vision ID from create_vision test not found"
    vision_id = pytest.vision_id_1
    update_data = {"name": "Updated Vision Alpha", "description": "Updated description"}
    response = client.put(f"/api/v1/visions/{vision_id}", json=update_data)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == update_data["name"]
    assert data["description"] == update_data["description"]
    assert data["id"] == vision_id

def test_delete_vision(client: TestClient):
    agency_id = pytest.agency_id_for_visions
    vision_to_delete_data = {"name": "Vision To Delete", "veo_parameters": {"prompt": "delete this"}}
    response_create = client.post(f"/api/v1/agencies/{agency_id}/visions/", json=vision_to_delete_data)
    assert response_create.status_code == 201
    vision_to_delete_id = response_create.json()["id"]

    response_delete = client.delete(f"/api/v1/visions/{vision_to_delete_id}")
    assert response_delete.status_code == 200
    assert "deleted successfully" in response_delete.json()["message"]

    response_get = client.get(f"/api/v1/visions/{vision_to_delete_id}")
    assert response_get.status_code == 404

# --- Video Endpoint Tests ---

@pytest.fixture(scope="module", autouse=True)
def setup_vision_for_videos(client: TestClient):
    """Ensure at least one vision exists for video tests."""
    if not hasattr(pytest, "vision_id_1"):
        agency_id = pytest.agency_id_for_visions
        response = client.post(f"/api/v1/agencies/{agency_id}/visions/", json=VISION_DATA_1)
        assert response.status_code == 201
        pytest.vision_id_for_videos = response.json()["id"]
    else:
        pytest.vision_id_for_videos = pytest.vision_id_1


def test_create_video_for_vision(client: TestClient):
    vision_id = pytest.vision_id_for_videos
    response = client.post(f"/api/v1/visions/{vision_id}/videos/", json=VIDEO_CREATE_DATA)
    assert response.status_code == 201
    data = response.json()
    assert data["vision_id"] == vision_id
    assert "id" in data
    assert "veo_video_id" in data # From VeoService mock
    assert data["veo_video_id"].startswith("veo_mock_")
    assert data["status"] == "submitted" # Initial status from mock VeoService
    pytest.video_id_1 = data["id"]
    pytest.veo_video_id_1 = data["veo_video_id"]

def test_get_video_status_and_updates(client: TestClient):
    assert hasattr(pytest, "video_id_1"), "Video ID from create_video test not found"
    video_id = pytest.video_id_1
    veo_video_id = pytest.veo_video_id_1

    # Call 1: Should reflect the initial 'submitted' status or 'processing'
    # The Video endpoint calls VeoService.get_video_status if status is non-terminal
    # VeoService mock status progression: submitted -> processing -> completed
    
    # Initial state from create_video_for_vision already reflects one call to submit_video_request
    # and the video creation endpoint itself doesn't call get_video_status.
    # The first get_video will call VeoService.get_video_status on the 'submitted' video.
    
    # Call to GET /videos/{video_id} - 1st time (mock VeoService.get_video_status call #1)
    response1 = client.get(f"/api/v1/videos/{video_id}")
    assert response1.status_code == 200
    data1 = response1.json()
    assert data1["id"] == video_id
    assert data1["veo_video_id"] == veo_video_id
    # VeoService mock: first get_video_status call after submit keeps status "submitted"
    assert data1["status"] == "submitted" 
    assert data1.get("download_url") is None

    # Call to GET /videos/{video_id} - 2nd time (mock VeoService.get_video_status call #2)
    # time.sleep(0.1) # Small delay not strictly needed for mock, but good practice for real services
    response2 = client.get(f"/api/v1/videos/{video_id}")
    assert response2.status_code == 200
    data2 = response2.json()
    assert data2["status"] == "processing" # VeoService mock: 2nd get_video_status call -> processing
    assert data2.get("download_url") is None

    # Call to GET /videos/{video_id} - 3rd time (mock VeoService.get_video_status call #3)
    # time.sleep(0.1)
    response3 = client.get(f"/api/v1/videos/{video_id}")
    assert response3.status_code == 200
    data3 = response3.json()
    assert data3["status"] == "processing" # VeoService mock: 3rd get_video_status call -> still processing

    # Call to GET /videos/{video_id} - 4th time (mock VeoService.get_video_status call #4)
    # time.sleep(0.1)
    response4 = client.get(f"/api/v1/videos/{video_id}")
    assert response4.status_code == 200
    data4 = response4.json()
    assert data4["status"] == "completed" # VeoService mock: 4th get_video_status call -> completed
    assert "download_url" in data4
    assert data4["download_url"] is not None
    assert data4["download_url"].endswith(".mp4")

def test_get_non_existent_video(client: TestClient):
    response = client.get("/api/v1/videos/99999")
    assert response.status_code == 404

# Consider adding tests for cascading deletes if implemented
# e.g., deleting an agency deletes its visions and videos.
# The current Agency delete endpoint seems to implement this.

def test_delete_agency_cascades(client: TestClient):
    # 1. Create a new agency
    cas_agency_data = {"name": "Cascade Agency", "email": "cascade@example.com"}
    res_agency = client.post("/api/v1/agencies/", json=cas_agency_data)
    assert res_agency.status_code == 201
    cas_agency_id = res_agency.json()["id"]

    # 2. Create a vision for this agency
    cas_vision_data = {"name": "Cascade Vision", "veo_parameters": {"prompt": "cascade test"}}
    res_vision = client.post(f"/api/v1/agencies/{cas_agency_id}/visions/", json=cas_vision_data)
    assert res_vision.status_code == 201
    cas_vision_id = res_vision.json()["id"]

    # 3. Create a video for this vision
    res_video = client.post(f"/api/v1/visions/{cas_vision_id}/videos/", json={})
    assert res_video.status_code == 201
    cas_video_id = res_video.json()["id"]

    # 4. Delete the agency
    res_del_agency = client.delete(f"/api/v1/agencies/{cas_agency_id}")
    assert res_del_agency.status_code == 200

    # 5. Verify vision is deleted
    res_get_vision = client.get(f"/api/v1/visions/{cas_vision_id}")
    assert res_get_vision.status_code == 404

    # 6. Verify video is deleted
    res_get_video = client.get(f"/api/v1/videos/{cas_video_id}")
    assert res_get_video.status_code == 404
