import pytest
from veo_custom_video_app.backend.services.veo_service import VeoService

@pytest.fixture(scope="module")
def veo_service_instance() -> VeoService:
    """
    Pytest fixture to create an instance of VeoService for testing.
    Uses mock API key and endpoint.
    """
    return VeoService(api_key="test_mock_key", api_endpoint="https://mock-veo-api.com/test_v3")

@pytest.mark.asyncio
async def test_submit_video_request(veo_service_instance: VeoService):
    """
    Tests the submit_video_request method of VeoService.
    Ensures it returns a dictionary with 'veo_video_id' and 'status'.
    """
    vision_params = {"prompt": "A test prompt for Veo", "style": "cartoonish"}
    response = await veo_service_instance.submit_video_request(vision_params)

    assert "veo_video_id" in response
    assert isinstance(response["veo_video_id"], str)
    assert response["veo_video_id"].startswith("veo_mock_")
    
    assert "status" in response
    assert response["status"] == "submitted"
    
    assert "message" in response
    assert "vision_parameters_received" in response
    assert response["vision_parameters_received"] == vision_params

@pytest.mark.asyncio
async def test_get_video_status_cycle(veo_service_instance: VeoService):
    """
    Tests the get_video_status method of VeoService.
    Verifies the status cycling ('submitted' -> 'processing' -> 'completed')
    and the presence of 'download_url' when status is 'completed'.
    """
    vision_params_for_cycle_test = {"prompt": "Cycle test", "duration": 10}
    submit_response = await veo_service_instance.submit_video_request(vision_params_for_cycle_test)
    veo_video_id = submit_response["veo_video_id"]

    assert veo_video_id is not None, "Failed to get veo_video_id from submit_video_request"

    # 1. Initial status check (optional, as submit_video_request already sets it to 'submitted')
    # For this mock, the first get_video_status call after submit might still be 'submitted'
    # or directly 'processing' depending on the mock logic's call_count increment.
    # The current VeoService mock increments call_count on get_video_status.
    
    # Call 1: submit_video_request sets call_count to 0, status "submitted"
    # Call 2: get_video_status (call_count becomes 1) -> should still be "submitted" or "processing"
    status_response_1 = await veo_service_instance.get_video_status(veo_video_id)
    assert status_response_1["veo_video_id"] == veo_video_id
    # The mock logic has call_count starting at 0 for a new video.
    # First get_video_status increments call_count to 1. status remains 'submitted'.
    # if status_info["call_count"] > 1: current_status = "processing"
    # So, after one call to get_video_status, it should still be 'submitted'.
    assert status_response_1["status"] == "submitted" 
    assert "download_url" not in status_response_1

    # Call 3: get_video_status (call_count becomes 2) -> should be "processing"
    status_response_2 = await veo_service_instance.get_video_status(veo_video_id)
    assert status_response_2["veo_video_id"] == veo_video_id
    assert status_response_2["status"] == "processing"
    assert "download_url" not in status_response_2

    # Call 4: get_video_status (call_count becomes 3) -> should still be "processing"
    status_response_3 = await veo_service_instance.get_video_status(veo_video_id)
    assert status_response_3["veo_video_id"] == veo_video_id
    assert status_response_3["status"] == "processing"
    assert "download_url" not in status_response_3
    
    # Call 5: get_video_status (call_count becomes 4) -> should be "completed"
    # if current_status == "processing": if status_info["call_count"] > 3: current_status = "completed"
    status_response_4 = await veo_service_instance.get_video_status(veo_video_id)
    assert status_response_4["veo_video_id"] == veo_video_id
    assert status_response_4["status"] == "completed"
    assert "download_url" in status_response_4
    assert isinstance(status_response_4["download_url"], str)
    assert status_response_4["download_url"].endswith(".mp4")

    # Call 6: get_video_status (call_count becomes 5) -> should remain "completed"
    status_response_5 = await veo_service_instance.get_video_status(veo_video_id)
    assert status_response_5["veo_video_id"] == veo_video_id
    assert status_response_5["status"] == "completed"
    assert "download_url" in status_response_5

@pytest.mark.asyncio
async def test_get_video_status_non_existent(veo_service_instance: VeoService):
    """
    Tests get_video_status for a non-existent video ID.
    """
    non_existent_video_id = "veo_mock_nonexistent123"
    response = await veo_service_instance.get_video_status(non_existent_video_id)
    
    assert response["veo_video_id"] == non_existent_video_id
    assert response["status"] == "not_found" # Based on current mock implementation
    assert "download_url" not in response
