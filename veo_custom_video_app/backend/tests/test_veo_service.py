import pytest
import sys
from httpx import ConnectError, TimeoutException
from pytest_httpx import HTTPXMock

from veo_custom_video_app.backend.services.veo_service import (
    VeoService,
    ConfigurationError,
    VeoAPIError,
    VeoVideoNotFound
)

# Define default test values for API key and endpoint
TEST_API_KEY = "test_api_key_123"
TEST_API_ENDPOINT = "https://fake-veo-api.com/test_v3"


@pytest.fixture
def mock_env_vars(monkeypatch):
    """Fixture to mock environment variables for VeoService configuration."""
    monkeypatch.setenv("VEO_API_KEY", TEST_API_KEY)
    monkeypatch.setenv("VEO_API_ENDPOINT", TEST_API_ENDPOINT)
    # Ensure settings module is not found by default, forcing env var usage
    monkeypatch.setitem(sys.modules, "veo_custom_video_app.config.settings", None)


@pytest.fixture
def mock_settings_module(monkeypatch):
    """Fixture to mock the settings module for VeoService configuration."""
    class MockSettings:
        VEO_API_KEY = "settings_api_key_456"
        VEO_API_ENDPOINT = "https://fake-veo-api-from-settings.com/test_v3"

    monkeypatch.setitem(sys.modules, "veo_custom_video_app.config.settings", MockSettings())
    return MockSettings


def test_veo_service_init_success_from_env(mock_env_vars):
    """Test VeoService initializes correctly using environment variables."""
    service = VeoService()
    assert service.api_key == TEST_API_KEY
    assert service.api_endpoint == TEST_API_ENDPOINT
    assert isinstance(service.client, httpx.AsyncClient)

def test_veo_service_init_success_from_settings_module(mock_settings_module, monkeypatch):
    """Test VeoService initializes correctly using the settings module, overriding env vars."""
    # Set env vars to ensure settings module takes precedence
    monkeypatch.setenv("VEO_API_KEY", "env_key_should_be_overridden")
    monkeypatch.setenv("VEO_API_ENDPOINT", "env_endpoint_should_be_overridden")
    
    service = VeoService()
    assert service.api_key == mock_settings_module.VEO_API_KEY
    assert service.api_endpoint == mock_settings_module.VEO_API_ENDPOINT

def test_veo_service_init_missing_api_key(monkeypatch):
    """Test ConfigurationError is raised if VEO_API_KEY is missing."""
    monkeypatch.delenv("VEO_API_KEY", raising=False)
    monkeypatch.setenv("VEO_API_ENDPOINT", TEST_API_ENDPOINT)
    monkeypatch.setitem(sys.modules, "veo_custom_video_app.config.settings", None)
    with pytest.raises(ConfigurationError, match="VEO_API_KEY is not configured"):
        VeoService()

def test_veo_service_init_missing_api_endpoint(monkeypatch):
    """Test ConfigurationError is raised if VEO_API_ENDPOINT is missing."""
    monkeypatch.setenv("VEO_API_KEY", TEST_API_KEY)
    monkeypatch.delenv("VEO_API_ENDPOINT", raising=False)
    monkeypatch.setitem(sys.modules, "veo_custom_video_app.config.settings", None)
    with pytest.raises(ConfigurationError, match="VEO_API_ENDPOINT is not configured"):
        VeoService()


@pytest.mark.asyncio
async def test_submit_video_request_success(httpx_mock: HTTPXMock, mock_env_vars):
    service = VeoService()
    expected_response_json = {"veo_video_id": "vid_123_abc", "status": "submitted"}
    
    httpx_mock.add_response(
        method="POST",
        url=f"{TEST_API_ENDPOINT}/videos",
        json=expected_response_json,
        status_code=201
    )
    
    vision_name = "My Test Vision"
    vision_params = {"prompt": "A cool video", "style": "cinematic"}
    result = await service.submit_video_request(vision_name, vision_params)
    
    assert result == expected_response_json
    
    request = httpx_mock.get_request()
    assert request is not None
    assert request.method == "POST"
    assert request.url == f"{TEST_API_ENDPOINT}/videos"
    assert request.headers["Authorization"] == f"Bearer {TEST_API_KEY}"
    assert request.headers["Content-Type"] == "application/json"
    assert await request.read() == b'{"vision_name": "My Test Vision", "custom_parameters": {"prompt": "A cool video", "style": "cinematic"}}'

@pytest.mark.asyncio
async def test_submit_video_request_api_error(httpx_mock: HTTPXMock, mock_env_vars):
    service = VeoService()
    error_response_json = {"error": {"code": "invalid_param", "message": "Invalid parameter provided"}}
    
    httpx_mock.add_response(
        method="POST",
        url=f"{TEST_API_ENDPOINT}/videos",
        json=error_response_json,
        status_code=400
    )
    
    with pytest.raises(VeoAPIError) as exc_info:
        await service.submit_video_request("Test Vision", {"param": "value"})
    
    assert exc_info.value.status_code == 400
    assert exc_info.value.error_info == error_response_json

@pytest.mark.asyncio
async def test_submit_video_request_network_error(httpx_mock: HTTPXMock, mock_env_vars):
    service = VeoService()
    httpx_mock.add_exception(ConnectError("Simulated connection failure"))
    
    with pytest.raises(VeoAPIError) as exc_info: # VeoService wraps httpx.RequestError in VeoAPIError
        await service.submit_video_request("Test Vision", {"param": "value"})
    assert exc_info.value.status_code == 503 # As per VeoService implementation
    assert "Request to Veo API failed: Simulated connection failure" in str(exc_info.value)


@pytest.mark.asyncio
async def test_get_video_status_success_completed(httpx_mock: HTTPXMock, mock_env_vars):
    service = VeoService()
    veo_video_id = "vid_completed_123"
    expected_response_json = {
        "veo_video_id": veo_video_id,
        "status": "completed",
        "download_url": f"{TEST_API_ENDPOINT}/downloads/{veo_video_id}.mp4"
    }
    
    httpx_mock.add_response(
        method="GET",
        url=f"{TEST_API_ENDPOINT}/videos/{veo_video_id}",
        json=expected_response_json,
        status_code=200
    )
    
    result = await service.get_video_status(veo_video_id)
    assert result == expected_response_json
    
    request = httpx_mock.get_request()
    assert request is not None
    assert request.method == "GET"
    assert request.url == f"{TEST_API_ENDPOINT}/videos/{veo_video_id}"
    assert request.headers["Authorization"] == f"Bearer {TEST_API_KEY}"

@pytest.mark.asyncio
async def test_get_video_status_success_processing(httpx_mock: HTTPXMock, mock_env_vars):
    service = VeoService()
    veo_video_id = "vid_processing_456"
    expected_response_json = {
        "veo_video_id": veo_video_id,
        "status": "processing",
        "download_url": None 
    }
    
    httpx_mock.add_response(
        method="GET",
        url=f"{TEST_API_ENDPOINT}/videos/{veo_video_id}",
        json=expected_response_json,
        status_code=200
    )
    
    result = await service.get_video_status(veo_video_id)
    assert result == expected_response_json

@pytest.mark.asyncio
async def test_get_video_status_not_found(httpx_mock: HTTPXMock, mock_env_vars):
    service = VeoService()
    veo_video_id = "vid_not_found_789"
    error_response_json = {"error": "Video not found"}
    
    httpx_mock.add_response(
        method="GET",
        url=f"{TEST_API_ENDPOINT}/videos/{veo_video_id}",
        json=error_response_json,
        status_code=404
    )
    
    with pytest.raises(VeoVideoNotFound) as exc_info:
        await service.get_video_status(veo_video_id)
    
    assert exc_info.value.status_code == 404
    assert exc_info.value.error_info == error_response_json
    assert f"Video with ID '{veo_video_id}' not found" in str(exc_info.value)

@pytest.mark.asyncio
async def test_get_video_status_api_error(httpx_mock: HTTPXMock, mock_env_vars):
    service = VeoService()
    veo_video_id = "vid_api_error_101"
    error_response_json = {"error": "Internal server error on Veo side"}
    
    httpx_mock.add_response(
        method="GET",
        url=f"{TEST_API_ENDPOINT}/videos/{veo_video_id}",
        json=error_response_json,
        status_code=500
    )
    
    with pytest.raises(VeoAPIError) as exc_info:
        await service.get_video_status(veo_video_id)
        
    assert exc_info.value.status_code == 500
    assert exc_info.value.error_info == error_response_json

@pytest.mark.asyncio
async def test_get_video_status_network_error(httpx_mock: HTTPXMock, mock_env_vars):
    service = VeoService()
    veo_video_id = "vid_network_error_112"
    httpx_mock.add_exception(TimeoutException("Simulated timeout"))
    
    with pytest.raises(VeoAPIError) as exc_info: # VeoService wraps httpx.RequestError in VeoAPIError
        await service.get_video_status(veo_video_id)
    assert exc_info.value.status_code == 503
    assert "Request to Veo API failed: Simulated timeout" in str(exc_info.value)
