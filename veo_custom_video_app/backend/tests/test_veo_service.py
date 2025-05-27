import pytest
import sys
from httpx import ConnectError, TimeoutException
from pytest_httpx import HTTPXMock

from veo_custom_video_app.backend.services.veo_service import (
    VeoService,
    ConfigurationError,
    VeoAPIError,
    VeoOperationNotFound # Updated Exception Name
)

# Define default test values for Google Cloud Veo API
TEST_GCP_ACCESS_TOKEN = "test_gcp_access_token_123"
TEST_BASE_ENDPOINT = "https://us-central1-aiplatform.googleapis.com" # Example base
TEST_PROJECT_ID = "test-gcp-project"
TEST_REGION = "us-central1" # Should match the region in TEST_BASE_ENDPOINT for consistency
TEST_MODEL_ID = "veo-3.0-test-model"


@pytest.fixture
def mock_env_vars_gcp(monkeypatch):
    """Fixture to mock environment variables for VeoService (GCP version)."""
    monkeypatch.setenv("VEO_API_KEY", TEST_GCP_ACCESS_TOKEN)
    monkeypatch.setenv("VEO_API_ENDPOINT", TEST_BASE_ENDPOINT)
    monkeypatch.setenv("VEO_PROJECT_ID", TEST_PROJECT_ID)
    monkeypatch.setenv("VEO_REGION", TEST_REGION)
    monkeypatch.setenv("VEO_MODEL_ID", TEST_MODEL_ID)
    # Ensure settings module is not found by default, forcing env var usage
    monkeypatch.setitem(sys.modules, "veo_custom_video_app.config.settings", None)

@pytest.fixture
def mock_settings_module_gcp(monkeypatch):
    """Fixture to mock the settings module for VeoService (GCP version)."""
    class MockSettingsGCP:
        VEO_API_KEY = "settings_gcp_token_456"
        VEO_API_ENDPOINT = "https://europe-west1-aiplatform.googleapis.com"
        VEO_PROJECT_ID = "settings-gcp-project"
        VEO_REGION = "europe-west1"
        VEO_MODEL_ID = "veo-3.0-settings-model"

    monkeypatch.setitem(sys.modules, "veo_custom_video_app.config.settings", MockSettingsGCP())
    return MockSettingsGCP


def test_veo_service_init_success_from_env_gcp(mock_env_vars_gcp):
    service = VeoService()
    assert service.gcp_access_token == TEST_GCP_ACCESS_TOKEN
    assert service.base_endpoint == TEST_BASE_ENDPOINT
    assert service.project_id == TEST_PROJECT_ID
    assert service.region == TEST_REGION
    assert service.model_id == TEST_MODEL_ID
    assert isinstance(service.client, httpx.AsyncClient)

def test_veo_service_init_success_from_settings_module_gcp(mock_settings_module_gcp, monkeypatch):
    # Set some env vars to ensure settings module takes precedence
    monkeypatch.setenv("VEO_PROJECT_ID", "env_project_should_be_overridden")
    
    service = VeoService()
    assert service.gcp_access_token == mock_settings_module_gcp.VEO_API_KEY
    assert service.base_endpoint == mock_settings_module_gcp.VEO_API_ENDPOINT
    assert service.project_id == mock_settings_module_gcp.VEO_PROJECT_ID
    assert service.region == mock_settings_module_gcp.VEO_REGION
    assert service.model_id == mock_settings_module_gcp.VEO_MODEL_ID

def test_veo_service_init_derive_region_from_endpoint(monkeypatch):
    monkeypatch.setenv("VEO_API_KEY", TEST_GCP_ACCESS_TOKEN)
    monkeypatch.setenv("VEO_API_ENDPOINT", "https://australia-southeast1-aiplatform.googleapis.com")
    monkeypatch.setenv("VEO_PROJECT_ID", TEST_PROJECT_ID)
    monkeypatch.setenv("VEO_MODEL_ID", TEST_MODEL_ID)
    monkeypatch.delenv("VEO_REGION", raising=False) # Ensure VEO_REGION is not set
    monkeypatch.setitem(sys.modules, "veo_custom_video_app.config.settings", None)
    
    service = VeoService()
    assert service.region == "australia-southeast1"

@pytest.mark.parametrize("missing_var", ["VEO_API_KEY", "VEO_API_ENDPOINT", "VEO_PROJECT_ID"])
def test_veo_service_init_missing_required_config(monkeypatch, missing_var):
    monkeypatch.setenv("VEO_API_KEY", TEST_GCP_ACCESS_TOKEN)
    monkeypatch.setenv("VEO_API_ENDPOINT", TEST_BASE_ENDPOINT)
    monkeypatch.setenv("VEO_PROJECT_ID", TEST_PROJECT_ID)
    monkeypatch.setenv("VEO_REGION", TEST_REGION)
    monkeypatch.setenv("VEO_MODEL_ID", TEST_MODEL_ID)
    
    monkeypatch.delenv(missing_var, raising=False)
    monkeypatch.setitem(sys.modules, "veo_custom_video_app.config.settings", None)
    
    with pytest.raises(ConfigurationError, match=f"{missing_var.split('_', 1)[1]}.* not configured"): # Adjusted match
        VeoService()

@pytest.mark.asyncio
async def test_submit_video_request_success_gcp(httpx_mock: HTTPXMock, mock_env_vars_gcp):
    service = VeoService()
    expected_operation_name = f"projects/{TEST_PROJECT_ID}/locations/{TEST_REGION}/operations/fakeop123"
    
    httpx_mock.add_response(
        method="POST",
        url=f"{TEST_BASE_ENDPOINT}/v1/projects/{TEST_PROJECT_ID}/locations/{TEST_REGION}/publishers/google/models/{TEST_MODEL_ID}:predictLongRunning",
        json={"name": expected_operation_name},
        status_code=200 # Vertex AI LRO submission is 200 OK
    )
    
    prompt = "A futuristic cityscape"
    parameters = {"duration": 5, "storageUri": "gs://my-bucket/output/"}
    result_op_name = await service.submit_video_request(prompt, parameters)
    
    assert result_op_name == expected_operation_name
    
    request = httpx_mock.get_request()
    assert request is not None
    assert request.method == "POST"
    assert request.headers["Authorization"] == f"Bearer {TEST_GCP_ACCESS_TOKEN}"
    assert request.headers["Content-Type"] == "application/json"
    expected_payload = {
        "instances": [{"prompt": prompt}],
        "parameters": parameters
    }
    assert await request.read() == pytest.approx(expected_payload, abs=1e-9) # Using approx for dict comparison

@pytest.mark.asyncio
async def test_submit_video_request_api_error_gcp(httpx_mock: HTTPXMock, mock_env_vars_gcp):
    service = VeoService()
    error_response_json = {"error": {"code": 400, "message": "Invalid argument"}}
    
    httpx_mock.add_response(
        method="POST",
        url=f"{TEST_BASE_ENDPOINT}/v1/projects/{TEST_PROJECT_ID}/locations/{TEST_REGION}/publishers/google/models/{TEST_MODEL_ID}:predictLongRunning",
        json=error_response_json,
        status_code=400
    )
    
    with pytest.raises(VeoAPIError) as exc_info:
        await service.submit_video_request("Test prompt", {})
    
    assert exc_info.value.status_code == 400
    assert exc_info.value.error_info == error_response_json

@pytest.mark.asyncio
async def test_submit_video_request_network_error_gcp(httpx_mock: HTTPXMock, mock_env_vars_gcp):
    service = VeoService()
    httpx_mock.add_exception(ConnectError("Simulated GCP connection failure"))
    
    with pytest.raises(VeoAPIError) as exc_info:
        await service.submit_video_request("Test prompt", {})
    assert exc_info.value.status_code == 503
    assert "Request to Google Cloud Veo API failed: Simulated GCP connection failure" in str(exc_info.value)


@pytest.mark.asyncio
async def test_get_video_status_success_processing_gcp(httpx_mock: HTTPXMock, mock_env_vars_gcp):
    service = VeoService()
    operation_name = f"projects/{TEST_PROJECT_ID}/locations/{TEST_REGION}/operations/op_processing_123"
    mock_api_response = {"name": operation_name, "done": False}
    
    httpx_mock.add_response(
        method="GET",
        url=f"{TEST_BASE_ENDPOINT}/v1/{operation_name}",
        json=mock_api_response,
        status_code=200
    )
    
    expected_result = {
        "operation_name": operation_name,
        "done": False,
        "status": "processing",
        "video_uris": [],
        "error": None
    }
    result = await service.get_video_status(operation_name)
    assert result == expected_result
    
    request = httpx_mock.get_request()
    assert request is not None
    assert request.method == "GET"
    assert request.url == f"{TEST_BASE_ENDPOINT}/v1/{operation_name}"
    assert request.headers["Authorization"] == f"Bearer {TEST_GCP_ACCESS_TOKEN}"

@pytest.mark.asyncio
async def test_get_video_status_success_completed_gcp(httpx_mock: HTTPXMock, mock_env_vars_gcp):
    service = VeoService()
    operation_name = f"projects/{TEST_PROJECT_ID}/locations/{TEST_REGION}/operations/op_completed_456"
    video_uri = f"gs://{TEST_PROJECT_ID}-bucket/video_completed.mp4"
    mock_api_response = {
        "name": operation_name,
        "done": True,
        "response": {
            "@type": "type.googleapis.com/google.cloud.aiplatform.v1.PredictLongRunningResponse",
            "generatedVideos": [{"video": video_uri}]
        }
    }
    httpx_mock.add_response(method="GET", url=f"{TEST_BASE_ENDPOINT}/v1/{operation_name}", json=mock_api_response, status_code=200)
    
    expected_result = {
        "operation_name": operation_name,
        "done": True,
        "status": "completed",
        "video_uris": [video_uri],
        "error": None
    }
    result = await service.get_video_status(operation_name)
    assert result == expected_result

@pytest.mark.asyncio
async def test_get_video_status_failed_gcp(httpx_mock: HTTPXMock, mock_env_vars_gcp):
    service = VeoService()
    operation_name = f"projects/{TEST_PROJECT_ID}/locations/{TEST_REGION}/operations/op_failed_789"
    error_payload = {"code": 3, "message": "Job failed due to resource exhaustion."}
    mock_api_response = {"name": operation_name, "done": True, "error": error_payload}
    httpx_mock.add_response(method="GET", url=f"{TEST_BASE_ENDPOINT}/v1/{operation_name}", json=mock_api_response, status_code=200)
    
    expected_result = {
        "operation_name": operation_name,
        "done": True,
        "status": "failed",
        "video_uris": [],
        "error": error_payload
    }
    result = await service.get_video_status(operation_name)
    assert result == expected_result

@pytest.mark.asyncio
async def test_get_video_status_not_found_gcp(httpx_mock: HTTPXMock, mock_env_vars_gcp):
    service = VeoService()
    operation_name = f"projects/{TEST_PROJECT_ID}/locations/{TEST_REGION}/operations/op_not_found"
    error_response_json = {"error": "Operation not found"}
    
    httpx_mock.add_response(method="GET", url=f"{TEST_BASE_ENDPOINT}/v1/{operation_name}", json=error_response_json, status_code=404)
    
    with pytest.raises(VeoOperationNotFound) as exc_info: # Updated Exception
        await service.get_video_status(operation_name)
    
    assert exc_info.value.status_code == 404
    assert exc_info.value.error_info == error_response_json
    assert f"Operation with name '{operation_name}' not found" in str(exc_info.value)

@pytest.mark.asyncio
async def test_get_video_status_api_error_gcp(httpx_mock: HTTPXMock, mock_env_vars_gcp):
    service = VeoService()
    operation_name = f"projects/{TEST_PROJECT_ID}/locations/{TEST_REGION}/operations/op_server_error"
    error_response_json = {"error": "Internal server error on GCP side"}
    
    httpx_mock.add_response(method="GET", url=f"{TEST_BASE_ENDPOINT}/v1/{operation_name}", json=error_response_json, status_code=500)
    
    with pytest.raises(VeoAPIError) as exc_info:
        await service.get_video_status(operation_name)
        
    assert exc_info.value.status_code == 500
    assert exc_info.value.error_info == error_response_json

@pytest.mark.asyncio
async def test_get_video_status_network_error_gcp(httpx_mock: HTTPXMock, mock_env_vars_gcp):
    service = VeoService()
    operation_name = f"projects/{TEST_PROJECT_ID}/locations/{TEST_REGION}/operations/op_network_issue"
    httpx_mock.add_exception(TimeoutException("Simulated GCP timeout"))
    
    with pytest.raises(VeoAPIError) as exc_info:
        await service.get_video_status(operation_name)
    assert exc_info.value.status_code == 503
    assert "Request to Google Cloud Veo API failed: Simulated GCP timeout" in str(exc_info.value)
