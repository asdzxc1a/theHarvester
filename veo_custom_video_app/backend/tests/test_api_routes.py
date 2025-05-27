from fastapi.testclient import TestClient
import pytest

# --- Helper Data ---
# These can be used as base data for creating entities in tests.
AGENCY_DATA_1 = {"name": "Test Agency One", "email": "agency1@example.com"}
AGENCY_DATA_2 = {"name": "Test Agency Two", "email": "agency2@example.com"}
VISION_DATA_BASE = {"name": "Base Vision", "description": "Base vision", "veo_parameters": {"prompt": "base_prompt", "style": "base_style"}}
VIDEO_CREATE_DATA = {} # Currently empty as per VideoCreate schema, not used for DB video creation fields

# --- Authentication Tests ---
# These tests should remain largely the same as they test auth layer, not DB.

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

def test_create_duplicate_agency_email(client: TestClient):
    # Create first agency
    client.post("/api/v1/agencies/", json=AGENCY_DATA_1)
    # Attempt to create another agency with the same email
    response = client.post("/api/v1/agencies/", json={"name": "Another Name", "email": AGENCY_DATA_1["email"]})
    assert response.status_code == 400 # Expecting a conflict due to unique constraint
    assert "Agency with this email already exists" in response.json()["detail"]

def test_create_duplicate_agency_name(client: TestClient):
    # Create first agency
    client.post("/api/v1/agencies/", json=AGENCY_DATA_1)
    # Attempt to create another agency with the same name
    response = client.post("/api/v1/agencies/", json={"name": AGENCY_DATA_1["name"], "email": "unique_email@example.com"})
    assert response.status_code == 400 # Expecting a conflict
    assert "Agency with this name already exists" in response.json()["detail"]


def test_list_agencies(client: TestClient):
    # Create a couple of agencies
    response1 = client.post("/api/v1/agencies/", json=AGENCY_DATA_1)
    assert response1.status_code == 201
    response2 = client.post("/api/v1/agencies/", json=AGENCY_DATA_2)
    assert response2.status_code == 201
    
    response_list = client.get("/api/v1/agencies/")
    assert response_list.status_code == 200
    data = response_list.json()
    assert isinstance(data, list)
    assert len(data) >= 2 # Should be exactly 2 if DB is clean per test, or more if tests run in sequence without full isolation
    
    names_in_response = [item["name"] for item in data]
    assert AGENCY_DATA_1["name"] in names_in_response
    assert AGENCY_DATA_2["name"] in names_in_response

def test_get_specific_agency(client: TestClient):
    # Create an agency
    response_create = client.post("/api/v1/agencies/", json=AGENCY_DATA_1)
    assert response_create.status_code == 201
    agency_id = response_create.json()["id"]
    
    response_get = client.get(f"/api/v1/agencies/{agency_id}")
    assert response_get.status_code == 200
    data = response_get.json()
    assert data["id"] == agency_id
    assert data["name"] == AGENCY_DATA_1["name"]

def test_get_non_existent_agency(client: TestClient):
    response = client.get("/api/v1/agencies/99999") # Assuming 99999 does not exist
    assert response.status_code == 404

def test_update_agency(client: TestClient):
    # Create an agency
    response_create = client.post("/api/v1/agencies/", json=AGENCY_DATA_1)
    assert response_create.status_code == 201
    agency_id = response_create.json()["id"]
    
    update_data = {"name": "Updated Test Agency One", "email": "updated_agency1@example.com"}
    response_update = client.put(f"/api/v1/agencies/{agency_id}", json=update_data)
    assert response_update.status_code == 200
    data = response_update.json()
    assert data["name"] == update_data["name"]
    assert data["email"] == update_data["email"]
    assert data["id"] == agency_id

def test_update_agency_duplicate_email(client: TestClient):
    # Create two agencies
    agency1_res = client.post("/api/v1/agencies/", json=AGENCY_DATA_1)
    assert agency1_res.status_code == 201
    
    agency2_res = client.post("/api/v1/agencies/", json=AGENCY_DATA_2)
    assert agency2_res.status_code == 201
    agency2_id = agency2_res.json()["id"]

    # Try to update agency2's email to agency1's email
    update_data = {"email": AGENCY_DATA_1["email"]}
    response = client.put(f"/api/v1/agencies/{agency2_id}", json=update_data)
    assert response.status_code == 400
    assert "Another agency with this email already exists" in response.json()["detail"]


def test_delete_agency(client: TestClient):
    # Create an agency
    agency_to_delete_data = {"name": "Agency To Delete", "email": "delete_me@example.com"}
    response_create = client.post("/api/v1/agencies/", json=agency_to_delete_data)
    assert response_create.status_code == 201
    agency_to_delete_id = response_create.json()["id"]

    # Delete it
    response_delete = client.delete(f"/api/v1/agencies/{agency_to_delete_id}")
    assert response_delete.status_code == 200
    assert "deleted successfully" in response_delete.json()["message"]

    # Verify it's gone
    response_get = client.get(f"/api/v1/agencies/{agency_to_delete_id}")
    assert response_get.status_code == 404

# --- Helper function to create an agency and return its ID ---
def create_test_agency(client: TestClient, agency_data: dict) -> int:
    response = client.post("/api/v1/agencies/", json=agency_data)
    assert response.status_code == 201
    return response.json()["id"]

# --- Vision Endpoint Tests ---
# Removed module-scoped fixtures. Tests will create their own prerequisite data.

def test_create_vision(client: TestClient):
    agency_id = create_test_agency(client, {"name": "VisionAgency", "email": "va@example.com"})
    vision_data = {**VISION_DATA_BASE, "name": "My New Vision"}
    
    response = client.post(f"/api/v1/agencies/{agency_id}/visions/", json=vision_data)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == vision_data["name"]
    assert data["agency_id"] == agency_id
    assert data["veo_parameters"] == vision_data["veo_parameters"]
    assert "id" in data

def test_list_visions_for_agency(client: TestClient):
    agency_id = create_test_agency(client, {"name": "ListVisionAgency", "email": "lva@example.com"})
    vision_data_1 = {**VISION_DATA_BASE, "name": "Vision One for List"}
    vision_data_2 = {**VISION_DATA_BASE, "name": "Vision Two for List", "veo_parameters": {"prompt":"p2"}}
    
    client.post(f"/api/v1/agencies/{agency_id}/visions/", json=vision_data_1)
    client.post(f"/api/v1/agencies/{agency_id}/visions/", json=vision_data_2)
    
    response = client.get(f"/api/v1/agencies/{agency_id}/visions/")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 2
    names_in_response = [item["name"] for item in data]
    assert vision_data_1["name"] in names_in_response
    assert vision_data_2["name"] in names_in_response

def test_get_specific_vision(client: TestClient):
    agency_id = create_test_agency(client, {"name": "GetVisionAgency", "email": "gva@example.com"})
    vision_data = {**VISION_DATA_BASE, "name": "Specific Vision to Get"}
    response_create = client.post(f"/api/v1/agencies/{agency_id}/visions/", json=vision_data)
    assert response_create.status_code == 201
    vision_id = response_create.json()["id"]
    
    response_get = client.get(f"/api/v1/visions/{vision_id}")
    assert response_get.status_code == 200
    data = response_get.json()
    assert data["id"] == vision_id
    assert data["name"] == vision_data["name"]

def test_update_vision(client: TestClient):
    agency_id = create_test_agency(client, {"name": "UpdateVisionAgency", "email": "uva@example.com"})
    vision_data = {**VISION_DATA_BASE, "name": "Vision to Update"}
    response_create = client.post(f"/api/v1/agencies/{agency_id}/visions/", json=vision_data)
    assert response_create.status_code == 201
    vision_id = response_create.json()["id"]
    
    update_payload = {"name": "Updated Vision Name", "description": "Updated description"}
    response_update = client.put(f"/api/v1/visions/{vision_id}", json=update_payload)
    assert response_update.status_code == 200
    data = response_update.json()
    assert data["name"] == update_payload["name"]
    assert data["description"] == update_payload["description"]
    assert data["id"] == vision_id

def test_delete_vision(client: TestClient):
    agency_id = create_test_agency(client, {"name": "DeleteVisionAgency", "email": "dva@example.com"})
    vision_to_delete_data = {**VISION_DATA_BASE, "name": "Vision To Delete"}
    response_create = client.post(f"/api/v1/agencies/{agency_id}/visions/", json=vision_to_delete_data)
    assert response_create.status_code == 201
    vision_to_delete_id = response_create.json()["id"]

    response_delete = client.delete(f"/api/v1/visions/{vision_to_delete_id}")
    assert response_delete.status_code == 200
    assert "deleted successfully" in response_delete.json()["message"]

    response_get = client.get(f"/api/v1/visions/{vision_to_delete_id}")
    assert response_get.status_code == 404

# --- Helper function to create an agency and a vision, returns vision_id ---
def create_test_vision(client: TestClient, agency_data: dict, vision_data: dict) -> int:
    agency_id = create_test_agency(client, agency_data)
    full_vision_data = {**VISION_DATA_BASE, **vision_data}
    response = client.post(f"/api/v1/agencies/{agency_id}/visions/", json=full_vision_data)
    assert response.status_code == 201
    return response.json()["id"]

# --- Video Endpoint Tests ---
# Removed module-scoped fixtures.

def test_create_video_for_vision(client: TestClient):
    vision_id = create_test_vision(client, 
                                   {"name": "VideoVisionAgency", "email": "vva@example.com"},
                                   {"name": "Vision For Video"})
    
    response = client.post(f"/api/v1/visions/{vision_id}/videos/", json=VIDEO_CREATE_DATA)
    assert response.status_code == 201
    data = response.json()
    assert data["vision_id"] == vision_id
    assert "id" in data
    assert "veo_video_id" in data # From VeoService mock
    assert data["veo_video_id"].startswith("veo_mock_")
    assert data["status"] == "submitted" # Initial status from mock VeoService

def test_get_video_status_and_updates(client: TestClient):
    vision_id = create_test_vision(client,
                                   {"name": "VideoStatusAgency", "email": "vsa@example.com"},
                                   {"name": "Vision For Video Status Test"})
    response_create_video = client.post(f"/api/v1/visions/{vision_id}/videos/", json=VIDEO_CREATE_DATA)
    assert response_create_video.status_code == 201
    video_id = response_create_video.json()["id"]
    veo_video_id = response_create_video.json()["veo_video_id"]
    
    # Call to GET /videos/{video_id} - 1st time
    response1 = client.get(f"/api/v1/videos/{video_id}")
    assert response1.status_code == 200
    data1 = response1.json()
    assert data1["id"] == video_id
    assert data1["veo_video_id"] == veo_video_id
    assert data1["status"] == "submitted" 
    assert data1.get("download_url") is None

    # Call to GET /videos/{video_id} - 2nd time
    response2 = client.get(f"/api/v1/videos/{video_id}")
    assert response2.status_code == 200
    data2 = response2.json()
    assert data2["status"] == "processing"
    assert data2.get("download_url") is None

    # Call to GET /videos/{video_id} - 3rd time
    response3 = client.get(f"/api/v1/videos/{video_id}")
    assert response3.status_code == 200
    data3 = response3.json()
    assert data3["status"] == "processing"

    # Call to GET /videos/{video_id} - 4th time
    response4 = client.get(f"/api/v1/videos/{video_id}")
    assert response4.status_code == 200
    data4 = response4.json()
    assert data4["status"] == "completed"
    assert "download_url" in data4
    assert data4["download_url"] is not None
    assert data4["download_url"].endswith(".mp4")

def test_get_non_existent_video(client: TestClient):
    response = client.get("/api/v1/videos/99999") # Assuming 99999 does not exist
    assert response.status_code == 404

def test_delete_agency_cascades(client: TestClient):
    # 1. Create agency
    cas_agency_data = {"name": "Cascade Test Agency", "email": "cascade_test@example.com"}
    res_agency = client.post("/api/v1/agencies/", json=cas_agency_data)
    assert res_agency.status_code == 201
    cas_agency_id = res_agency.json()["id"]

    # 2. Create vision
    cas_vision_data = {**VISION_DATA_BASE, "name": "Cascade Test Vision"}
    res_vision = client.post(f"/api/v1/agencies/{cas_agency_id}/visions/", json=cas_vision_data)
    assert res_vision.status_code == 201
    cas_vision_id = res_vision.json()["id"]

    # 3. Create video
    res_video = client.post(f"/api/v1/visions/{cas_vision_id}/videos/", json={})
    assert res_video.status_code == 201
    cas_video_id = res_video.json()["id"]

    # 4. Delete agency
    res_del_agency = client.delete(f"/api/v1/agencies/{cas_agency_id}")
    assert res_del_agency.status_code == 200

    # 5. Verify vision is deleted (due to cascade from agency)
    res_get_vision = client.get(f"/api/v1/visions/{cas_vision_id}")
    assert res_get_vision.status_code == 404

    # 6. Verify video is deleted (due to cascade from vision)
    res_get_video = client.get(f"/api/v1/videos/{cas_video_id}")
    assert res_get_video.status_code == 404
