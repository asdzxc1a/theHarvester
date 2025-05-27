from fastapi.testclient import TestClient
import pytest
from unittest.mock import AsyncMock, patch

# --- Helper Data ---
# These can be used as base data for creating entities in tests.
AGENCY_DATA_1 = {"name": "Test Agency One", "email": "agency1@example.com"}
AGENCY_DATA_2 = {"name": "Test Agency Two", "email": "agency2@example.com"}

VISION_DATA_BASE = {
    "prompt": "A default cinematic prompt for testing.",
    "name": "Base Vision Name",
    "description": "Base vision description",
    "veo_parameters": { # Corresponds to VeoApiParameters model
        "duration": 6.5,
        "aspectRatio": "16:9",
        "seed": 1000,
        "storageUri": "gs://test-bucket/outputs/base_vision/" 
    }
}
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
    agency_id = create_test_agency(client, {"name": "VisionAgencyCRUD", "email": "va_crud@example.com"})
    
    # Use VISION_DATA_BASE and override specific fields for this test if needed
    vision_payload = {
        **VISION_DATA_BASE, 
        "name": "My Test Vision",
        "prompt": "A beautiful sunset over a mountain range, detailed, 8k.",
        "veo_parameters": { # Ensure this is a complete and valid VeoApiParameters structure
            "duration": 5.5, 
            "aspectRatio": "16:9", 
            "seed": 12345,
            "storageUri": "gs://my-test-bucket/outputs/my_test_vision/"
        }
    }
    
    response = client.post(f"/api/v1/agencies/{agency_id}/visions/", json=vision_payload)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == vision_payload["name"]
    assert data["prompt"] == vision_payload["prompt"]
    assert data["agency_id"] == agency_id
    assert data["veo_parameters"]["duration"] == vision_payload["veo_parameters"]["duration"]
    assert data["veo_parameters"]["aspectRatio"] == vision_payload["veo_parameters"]["aspectRatio"]
    assert data["veo_parameters"]["seed"] == vision_payload["veo_parameters"]["seed"]
    assert data["veo_parameters"]["storageUri"] == vision_payload["veo_parameters"]["storageUri"]
    assert "id" in data

def test_list_visions_for_agency(client: TestClient):
    agency_id = create_test_agency(client, {"name": "ListVisionAgencyCRUD", "email": "lva_crud@example.com"})
    
    vision_payload_1 = {
        **VISION_DATA_BASE, 
        "name": "Vision One for List Test",
        "prompt": "Prompt for vision 1"
    }
    vision_payload_2 = {
        **VISION_DATA_BASE, 
        "name": "Vision Two for List Test", 
        "prompt": "Prompt for vision 2",
        "veo_parameters": {"duration": 8.0, "aspectRatio": "9:16"} # Example of different params
    }
    
    client.post(f"/api/v1/agencies/{agency_id}/visions/", json=vision_payload_1)
    client.post(f"/api/v1/agencies/{agency_id}/visions/", json=vision_payload_2)
    
    response = client.get(f"/api/v1/agencies/{agency_id}/visions/")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 2
    names_in_response = [item["name"] for item in data]
    assert vision_payload_1["name"] in names_in_response
    assert vision_payload_2["name"] in names_in_response
    prompts_in_response = [item["prompt"] for item in data]
    assert vision_payload_1["prompt"] in prompts_in_response
    assert vision_payload_2["prompt"] in prompts_in_response

def test_get_specific_vision(client: TestClient):
    agency_id = create_test_agency(client, {"name": "GetVisionAgencyCRUD", "email": "gva_crud@example.com"})
    vision_payload = {
        **VISION_DATA_BASE, 
        "name": "Specific Vision to Get Test",
        "prompt": "Detailed prompt for specific vision."
    }
    response_create = client.post(f"/api/v1/agencies/{agency_id}/visions/", json=vision_payload)
    assert response_create.status_code == 201
    vision_id = response_create.json()["id"]
    
    response_get = client.get(f"/api/v1/visions/{vision_id}")
    assert response_get.status_code == 200
    data = response_get.json()
    assert data["id"] == vision_id
    assert data["name"] == vision_payload["name"]
    assert data["prompt"] == vision_payload["prompt"]
    assert data["veo_parameters"] == vision_payload["veo_parameters"] # Assuming VISION_DATA_BASE has full params

def test_update_vision(client: TestClient):
    agency_id = create_test_agency(client, {"name": "UpdateVisionAgencyCRUD", "email": "uva_crud@example.com"})
    initial_vision_payload = {
        **VISION_DATA_BASE, 
        "name": "Vision to Update Original",
        "prompt": "Original prompt.",
        "veo_parameters": {"duration": 5.0, "aspectRatio": "16:9", "seed": 500}
    }
    response_create = client.post(f"/api/v1/agencies/{agency_id}/visions/", json=initial_vision_payload)
    assert response_create.status_code == 201
    vision_id = response_create.json()["id"]
    
    update_payload = {
        "name": "Updated Vision Name by Test", 
        "description": "Updated description by test.",
        "prompt": "An updated exciting prompt for the vision!",
        "veo_parameters": { # This will replace the entire veo_parameters object
            "duration": 7.0, 
            "seed": 2000,
            "aspectRatio": "9:16" # Note: other original params like storageUri will be gone if not included here
        }
    }
    response_update = client.put(f"/api/v1/visions/{vision_id}", json=update_payload)
    assert response_update.status_code == 200
    data = response_update.json()
    assert data["name"] == update_payload["name"]
    assert data["description"] == update_payload["description"]
    assert data["prompt"] == update_payload["prompt"]
    assert data["id"] == vision_id
    
    # Check that veo_parameters was fully replaced
    assert data["veo_parameters"]["duration"] == update_payload["veo_parameters"]["duration"]
    assert data["veo_parameters"]["seed"] == update_payload["veo_parameters"]["seed"]
    assert data["veo_parameters"]["aspectRatio"] == update_payload["veo_parameters"]["aspectRatio"]
    assert "storageUri" not in data["veo_parameters"] # Assuming it was in VISION_DATA_BASE but not in update_payload

def test_delete_vision(client: TestClient):
    agency_id = create_test_agency(client, {"name": "DeleteVisionAgencyCRUD", "email": "dva_crud@example.com"})
    vision_to_delete_data = {
        **VISION_DATA_BASE, 
        "name": "Vision To Be Deleted Test",
        "prompt": "Prompt for vision to be deleted."
    }
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

@patch('veo_custom_video_app.backend.main.veo_service_instance.submit_video_request', new_callable=AsyncMock)
async def test_create_video_for_vision(mock_submit_request: AsyncMock, client: TestClient):
    # Arrange Data
    test_prompt = "A unique test prompt for video creation"
    test_veo_params = {"duration": 5.0, "aspectRatio": "16:9", "storageUri": "gs://test-bucket/outputs/unique/"}
    
    vision_id = create_test_vision(client, 
                                   {"name": "VideoCreateAgency", "email": "vca@example.com"},
                                   {"prompt": test_prompt, "name": "Vision For Video Create Test", "veo_parameters": test_veo_params})
    
    # Configure the mock for VeoService.submit_video_request
    expected_operation_name = f"projects/{TEST_PROJECT_ID}/locations/{TEST_REGION}/operations/fakeop_create123" # Using constants from test_veo_service
    mock_submit_request.return_value = expected_operation_name

    # Act
    response = client.post(f"/api/v1/visions/{vision_id}/videos/", json={}) # VIDEO_CREATE_DATA is empty, so {} is fine
    
    # Assert - API Response
    assert response.status_code == 201
    data = response.json()
    assert data["vision_id"] == vision_id
    assert "id" in data # Internal DB ID for the Video record
    assert data["veo_video_id"] == expected_operation_name # This now stores the operation name
    assert data["status"] == "processing" # Initial status set by the route after successful submission

    # Assert - Service Call
    mock_submit_request.assert_called_once()
    
    # Correct way to get call_args for an async mock might still be .call_args
    # If it's a regular mock wrapped by AsyncMock, args might be in mock_submit_request.mock.call_args
    # For AsyncMock itself, it should be call_args
    called_args, called_kwargs = mock_submit_request.call_args
    
    # Assuming submit_video_request is called with positional args: prompt, parameters
    assert called_args[0] == test_prompt
    assert called_args[1] == test_veo_params
    # Or if called with keyword args:
    # assert called_kwargs['prompt'] == test_prompt
    # assert called_kwargs['parameters'] == test_veo_params


# --- Video Endpoint Error Handling Tests ---

VEO_SERVICE_PATH = 'veo_custom_video_app.backend.main.veo_service_instance'
# Using constants from test_veo_service for test data consistency if needed, or define here.
TEST_PROJECT_ID = "test-gcp-project" 
TEST_REGION = "us-central1"

@patch(f'{VEO_SERVICE_PATH}.submit_video_request', new_callable=AsyncMock)
async def test_create_video_handles_configuration_error(mock_submit_request: AsyncMock, client: TestClient):
    test_prompt = "Config error test prompt"
    vision_id = create_test_vision(client, 
                                   {"name": "ConfigErrorAgency", "email": "cea@example.com"},
                                   {"prompt": test_prompt, "name": "Vision For ConfigError Test"})
    
    mock_submit_request.side_effect = ConfigurationError("Mocked VEO_API_KEY missing")
    
    response = client.post(f"/api/v1/visions/{vision_id}/videos/", json={})
    
    assert response.status_code == 500
    assert "Server configuration error related to video service." in response.json()["detail"]
    mock_submit_request.assert_called_once()

@patch(f'{VEO_SERVICE_PATH}.submit_video_request', new_callable=AsyncMock)
async def test_create_video_handles_veo_api_error(mock_submit_request: AsyncMock, client: TestClient):
    test_prompt = "API error test prompt"
    vision_id = create_test_vision(client, 
                                   {"name": "ApiErrorAgency", "email": "aea@example.com"},
                                   {"prompt": test_prompt, "name": "Vision For ApiError Test"})
    
    mock_submit_request.side_effect = VeoAPIError(status_code=503, error_info="Veo service temporarily unavailable")
    
    response = client.post(f"/api/v1/visions/{vision_id}/videos/", json={})
    
    assert response.status_code == 502 # Bad Gateway as per current route handling
    assert "Video API error: 503 - Veo service temporarily unavailable" in response.json()["detail"]
    mock_submit_request.assert_called_once()


# --- Video Status Retrieval Tests ---

# Helper to create a video for status tests.
# Note: This helper itself doesn't need to be async if client.post is sync.
# The test functions calling it will be async due to patching async service methods.
def create_video_for_status_test_sync(client: TestClient, 
                                 mock_submit_video_request_func: AsyncMock, # Mock for the initial video creation
                                 vision_prompt: str, 
                                 vision_veo_params: dict,
                                 agency_email_suffix: str) -> tuple[int, str]:
    # Create agency and vision
    # Using unique agency email to avoid conflicts if tests run in parallel or state leaks (though db_session should prevent this)
    vision_id = create_test_vision(client,
                                   {"name": f"StatusTestAgency-{agency_email_suffix}", "email": f"sta-{agency_email_suffix}@example.com"},
                                   {"prompt": vision_prompt, "name": f"Vision {vision_prompt[:10]}", "veo_parameters": vision_veo_params})
    
    # Mock the submission call that happens *inside* this helper's client.post call
    # This mock is for the `submit_video_request` call made by the POST /videos/ endpoint.
    # The `mock_submit_video_request_func` passed in is the one patched at the test function level.
    expected_op_name = f"projects/fakeproject/op/{vision_prompt[:10]}_op123"
    mock_submit_video_request_func.return_value = expected_op_name
    
    response_create_video = client.post(f"/api/v1/visions/{vision_id}/videos/", json={})
    assert response_create_video.status_code == 201
    video_id = response_create_video.json()["id"] 
    assert response_create_video.json()["veo_video_id"] == expected_op_name
    return video_id, expected_op_name


@patch(f'{VEO_SERVICE_PATH}.submit_video_request', new_callable=AsyncMock) # This mock is for create_video_for_status_test_sync
@patch(f'{VEO_SERVICE_PATH}.get_video_status', new_callable=AsyncMock)
async def test_get_video_status_processing(mock_get_status: AsyncMock, mock_submit_video_for_helper: AsyncMock, client: TestClient):
    video_id, operation_name = create_video_for_status_test_sync(client, mock_submit_video_for_helper,
                                                                 "processing_prompt", {})
    
    mock_get_status.return_value = {
        "operation_name": operation_name, "done": False, "status": "processing", 
        "video_uris": [], "error": None
    }
    
    response = client.get(f"/api/v1/videos/{video_id}")
    
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == video_id
    assert data["veo_video_id"] == operation_name
    assert data["status"] == "processing"
    assert data["download_url"] is None
    
    mock_get_status.assert_called_once_with(operation_name=operation_name)

@patch(f'{VEO_SERVICE_PATH}.submit_video_request', new_callable=AsyncMock)
@patch(f'{VEO_SERVICE_PATH}.get_video_status', new_callable=AsyncMock)
async def test_get_video_status_completed(mock_get_status: AsyncMock, mock_submit_video_for_helper: AsyncMock, client: TestClient):
    video_id, operation_name = create_video_for_status_test_sync(client, mock_submit_video_for_helper,
                                                                 "completed_prompt", {})
    gcs_uri = "gs://bucket/video_completed.mp4"
    mock_get_status.return_value = {
        "operation_name": operation_name, "done": True, "status": "completed", 
        "video_uris": [gcs_uri], "error": None
    }
    
    response = client.get(f"/api/v1/videos/{video_id}")
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"
    assert data["download_url"] == gcs_uri
    mock_get_status.assert_called_once_with(operation_name=operation_name)

@patch(f'{VEO_SERVICE_PATH}.submit_video_request', new_callable=AsyncMock)
@patch(f'{VEO_SERVICE_PATH}.get_video_status', new_callable=AsyncMock)
async def test_get_video_status_failed(mock_get_status: AsyncMock, mock_submit_video_for_helper: AsyncMock, client: TestClient):
    video_id, operation_name = create_video_for_status_test_sync(client, mock_submit_video_for_helper,
                                                                 "failed_prompt", {})
    error_details = {"code": 3, "message": "Render job failed"}
    mock_get_status.return_value = {
        "operation_name": operation_name, "done": True, "status": "failed", 
        "video_uris": [], "error": error_details
    }
    
    response = client.get(f"/api/v1/videos/{video_id}")
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "failed"
    mock_get_status.assert_called_once_with(operation_name=operation_name)

from veo_custom_video_app.backend.services.veo_service import VeoOperationNotFound, VeoAPIError

@patch(f'{VEO_SERVICE_PATH}.submit_video_request', new_callable=AsyncMock)
@patch(f'{VEO_SERVICE_PATH}.get_video_status', new_callable=AsyncMock)
async def test_get_video_status_operation_not_found(mock_get_status: AsyncMock, mock_submit_video_for_helper: AsyncMock, client: TestClient):
    video_id, operation_name = create_video_for_status_test_sync(client, mock_submit_video_for_helper,
                                                                 "op_not_found_prompt", {})
    mock_get_status.side_effect = VeoOperationNotFound(operation_name=operation_name, 
                                                       error_info="Mocked: Op not found on Veo")
    
    response = client.get(f"/api/v1/videos/{video_id}")
    
    # Route logic for VeoOperationNotFound: updates DB status to "error_fetching_status", returns 200 with this status.
    assert response.status_code == 200 
    data = response.json()
    assert data["id"] == video_id
    assert data["status"] == "error_fetching_status"
    mock_get_status.assert_called_once_with(operation_name=operation_name)

@patch(f'{VEO_SERVICE_PATH}.submit_video_request', new_callable=AsyncMock)
@patch(f'{VEO_SERVICE_PATH}.get_video_status', new_callable=AsyncMock)
async def test_get_video_status_handles_configuration_error(mock_get_status: AsyncMock, mock_submit_video_for_helper: AsyncMock, client: TestClient):
    video_id, operation_name = create_video_for_status_test_sync(client, mock_submit_video_for_helper,
                                                                 "config_error_get_prompt", {})
    mock_get_status.side_effect = ConfigurationError("Mocked VEO_PROJECT_ID missing for get_status")
    
    response = client.get(f"/api/v1/videos/{video_id}")
    
    assert response.status_code == 200 # Route currently designed to return last known status
    data = response.json()
    assert data["id"] == video_id
    assert data["status"] == "processing" # Initial status
    mock_get_status.assert_called_once_with(operation_name=operation_name)
    # Add a print or log in route to confirm this was logged server-side.

@patch(f'{VEO_SERVICE_PATH}.submit_video_request', new_callable=AsyncMock) 
@patch(f'{VEO_SERVICE_PATH}.get_video_status', new_callable=AsyncMock)
async def test_get_video_status_veo_api_error(mock_get_status: AsyncMock, mock_submit_video_for_helper: AsyncMock, client: TestClient):
    video_id, operation_name = create_video_for_status_test_sync(client, mock_submit_video_for_helper,
                                                                 "api_error_prompt", {})
    mock_get_status.side_effect = VeoAPIError(status_code=500, error_info="Veo internal server error")
    
    response = client.get(f"/api/v1/videos/{video_id}")
    
    # Route logic for general VeoAPIError on GET /videos/{id} is to return last known status (200).
    assert response.status_code == 200 
    data = response.json()
    assert data["status"] == "processing" # Initial status before VeoService error, as it's not updated
    mock_get_status.assert_called_once_with(operation_name=operation_name)


@pytest.mark.skip(reason="Superseded by scenario-specific status tests using mocks.")
async def test_get_video_status_and_updates(client: TestClient): 
    # This test will need significant updates to mock `get_video_status` from VeoService
    # and to align with the operation_name based workflow.
    # For now, keeping the structure but acknowledging it needs a similar patching approach.
    vision_id = create_test_vision(client,
                                   {"name": "VideoStatusAgency", "email": "vsa_old@example.com"}, 
                                   {"name": "Vision For Video Status Test Old"})
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
    assert data1["status"] == "processing"  # Updated to reflect initial status after VeoService refactor
    assert data1.get("download_url") is None

    # ... remaining assertions are based on old mock logic ...


def test_get_non_existent_video(client: TestClient):
    response = client.get("/api/v1/videos/99999") # Assuming 99999 does not exist
    assert response.status_code == 404

# --- Login Endpoint Tests ---
from veo_custom_video_app.backend.app.models import User as UserModel
from veo_custom_video_app.backend.auth.auth import get_password_hash, create_access_token # Added create_access_token
from jose import jwt
from veo_custom_video_app.backend.auth.auth import SECRET_KEY, ALGORITHM 
from sqlalchemy.orm import Session # For type hinting db_session
from datetime import timedelta # Added timedelta

# Helper function to create a user directly in DB for login tests
def create_db_user(db: Session, email: str, plain_password: str, is_active: bool = True, full_name: str = None, is_superuser: bool = False) -> UserModel:
    hashed_password = get_password_hash(plain_password)
    user = UserModel(
        email=email, 
        hashed_password=hashed_password, 
        is_active=is_active,
        full_name=full_name,
        is_superuser=is_superuser
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

def test_login_successful(client: TestClient, db_session: Session):
    test_email = "login_success@example.com"
    test_password = "goodpassword123"
    create_db_user(db_session, test_email, test_password, is_active=True)
    
    login_data = {"username": test_email, "password": test_password}
    response = client.post("/api/v1/auth/login", data=login_data) # Use data for form submission
    
    assert response.status_code == 200
    token_data = response.json()
    assert "access_token" in token_data
    assert isinstance(token_data["access_token"], str)
    assert token_data["token_type"] == "bearer"
    
    # Optional: Decode token to verify 'sub' and 'exp'
    decoded_token = jwt.decode(token_data["access_token"], SECRET_KEY, algorithms=[ALGORITHM])
    assert decoded_token["sub"] == test_email
    assert "exp" in decoded_token

def test_login_incorrect_password(client: TestClient, db_session: Session):
    test_email = "wrong_pass@example.com"
    test_password = "actual_password"
    create_db_user(db_session, test_email, test_password)
    
    login_data = {"username": test_email, "password": "incorrect_password_attempt"}
    response = client.post("/api/v1/auth/login", data=login_data)
    
    assert response.status_code == 401
    assert "Incorrect email or password" in response.json()["detail"]
    assert response.headers.get("WWW-Authenticate") == "Bearer"


def test_login_user_not_found(client: TestClient, db_session: Session): # db_session is here to ensure clean DB
    login_data = {"username": "nonexistent_user@example.com", "password": "anypassword"}
    response = client.post("/api/v1/auth/login", data=login_data)
    
    assert response.status_code == 401 # Same error as incorrect password for security
    assert "Incorrect email or password" in response.json()["detail"]

def test_login_inactive_user(client: TestClient, db_session: Session):
    test_email = "inactive_user@example.com"
    test_password = "password123"
    create_db_user(db_session, test_email, test_password, is_active=False)
    
    login_data = {"username": test_email, "password": test_password}
    response = client.post("/api/v1/auth/login", data=login_data)
    
    assert response.status_code == 400 # As per current route implementation
    assert "Inactive user" in response.json()["detail"]

def test_login_missing_fields(client: TestClient):
    # Test with missing username (email)
    response_no_user = client.post("/api/v1/auth/login", data={"password": "somepassword"})
    assert response_no_user.status_code == 422 # FastAPI validation error for missing form field
    
    # Test with missing password
    response_no_pass = client.post("/api/v1/auth/login", data={"username": "user@example.com"})
    assert response_no_pass.status_code == 422

# --- JWT Protected Endpoint Tests (/api/v1/agencies/) ---

# Helper function to log in a user and get a token
def login_user_and_get_token(client: TestClient, email: str, password: str) -> str:
    response = client.post("/api/v1/auth/login", data={"username": email, "password": password})
    assert response.status_code == 200, f"Login failed: {response.json()}"
    return response.json()["access_token"]

def test_get_agencies_with_valid_token(client: TestClient, db_session: Session):
    # Setup: Create an active user
    user_email = "jwt_test_user@example.com"
    user_password = "securepassword"
    create_db_user(db_session, user_email, user_password, is_active=True)
    
    # Get token
    token = login_user_and_get_token(client, user_email, user_password)
    
    # Act: Access protected endpoint
    headers = {"Authorization": f"Bearer {token}"}
    # Ensure to call the correct endpoint for listing agencies that is JWT protected
    # This is /api/v1/agencies/ as per previous changes for user_router
    response = client.get("/api/v1/agencies/", headers=headers) 
    
    # Assert
    assert response.status_code == 200
    assert isinstance(response.json(), list) 

def test_get_agencies_no_token(client: TestClient):
    response = client.get("/api/v1/agencies/") # No Authorization header
    # This endpoint is on user_router, which doesn't have X-API-KEY dependency by default.
    # FastAPI's default for missing OAuth2 token is 401 if auto_error=True (which it is for oauth2_scheme).
    assert response.status_code == 401 
    assert "Not authenticated" in response.json()["detail"].lower()

def test_get_agencies_invalid_token_malformed(client: TestClient):
    headers = {"Authorization": "Bearer thisisnotavalidjwttoken"}
    response = client.get("/api/v1/agencies/", headers=headers)
    assert response.status_code == 401 
    assert "Could not validate credentials" in response.json()["detail"] # From get_current_user

# test_get_agencies_invalid_token_wrong_secret is skipped as its core failure mode (JWTError)
# is covered by test_get_agencies_invalid_token_malformed.

def test_get_agencies_expired_token(client: TestClient, db_session: Session):
    user_email = "jwt_expired_user@example.com"
    user_password = "securepassword"
    create_db_user(db_session, user_email, user_password, is_active=True)
    
    # Create an expired token by setting expires_delta to a negative value
    expired_token = create_access_token(data={"sub": user_email}, expires_delta=timedelta(minutes=-5))
    
    headers = {"Authorization": f"Bearer {expired_token}"}
    response = client.get("/api/v1/agencies/", headers=headers)
    
    assert response.status_code == 401
    assert "Could not validate credentials" in response.json()["detail"] # Expired token also raises JWTError

def test_get_agencies_valid_token_inactive_user(client: TestClient, db_session: Session):
    user_email = "jwt_inactive_user@example.com"
    user_password = "securepassword"
    # Create user, initially active to get a token
    user = create_db_user(db_session, user_email, user_password, is_active=True)
    token = login_user_and_get_token(client, user_email, user_password)
    
    # Make user inactive AFTER token is issued
    user.is_active = False
    db_session.commit()
    db_session.refresh(user)
    
    headers = {"Authorization": f"Bearer {token}"}
    response = client.get("/api/v1/agencies/", headers=headers)
    
    assert response.status_code == 400 # From get_current_active_user
    assert "Inactive user" in response.json()["detail"]


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
