import httpx
import os
from typing import Dict, Any, Optional # Added Optional

# --- Custom Exceptions ---
class VeoServiceError(Exception):
    '''Base class for VeoService errors.'''
    pass

class VeoAPIError(VeoServiceError):
    def __init__(self, status_code: int, error_info: Dict[str, Any] | str | None = None, message_override: Optional[str] = None):
        self.status_code = status_code
        self.error_info = error_info
        message = message_override if message_override else f"Veo API Error: Status {status_code}"
        if error_info and not message_override:
            message += f", Info: {error_info}"
        super().__init__(message)

class VeoVideoNotFound(VeoAPIError):
    def __init__(self, veo_video_id: str, error_info: Dict[str, Any] | str | None = None):
        super().__init__(status_code=404, error_info=error_info, message_override=f"Video with ID '{veo_video_id}' not found on Veo API.")

class ConfigurationError(VeoServiceError):
    '''Indicates a configuration problem for VeoService.'''
    pass

class VeoService:
    """
    A service class to interact with the Veo 3 API.
    """
    # Removed: _mock_video_statuses

    def __init__(self):
        """
        Initializes the VeoService.
        Loads API key and endpoint from config/settings.py or environment variables.
        """
        # Attempt to load from config.settings module first
        try:
            from veo_custom_video_app.config.settings import VEO_API_KEY, VEO_API_ENDPOINT
            self.api_key = VEO_API_KEY
            self.api_endpoint = VEO_API_ENDPOINT
            print("INFO: Loaded VeoService config from settings.py")
        except ImportError:
            print("INFO: veo_custom_video_app.config.settings.py not found or VEO_API_KEY/VEO_API_ENDPOINT not defined. Falling back to environment variables.")
            self.api_key = os.getenv('VEO_API_KEY')
            self.api_endpoint = os.getenv('VEO_API_ENDPOINT')
        except AttributeError: # In case settings.py exists but variables are missing
             print("INFO: VEO_API_KEY or VEO_API_ENDPOINT not found in settings.py. Falling back to environment variables.")
             self.api_key = os.getenv('VEO_API_KEY')
             self.api_endpoint = os.getenv('VEO_API_ENDPOINT')


        if not self.api_key:
            raise ConfigurationError("VEO_API_KEY is not configured. Please set it in settings.py or as an environment variable.")
        if not self.api_endpoint:
            raise ConfigurationError("VEO_API_ENDPOINT is not configured. Please set it in settings.py or as an environment variable.")

        self.client = httpx.AsyncClient(timeout=30.0)
        print(f"INFO: VeoService initialized. Endpoint: {self.api_endpoint}, Key: {'*' * (len(self.api_key) - 4) + self.api_key[-4:] if self.api_key else 'Not Set'}")


    async def submit_video_request(self, vision_name: str, vision_parameters: dict) -> dict:
        """
        Submits a video creation request to the Veo API.

        Args:
            vision_name: The name of the vision/campaign.
            vision_parameters: A dictionary of parameters for the video creation.

        Returns:
            A dictionary containing `veo_video_id` and `status` from the Veo API.
        
        Raises:
            VeoAPIError: If the API call fails or returns an unexpected status code.
            ConfigurationError: If the service is not properly configured.
        """
        if not self.api_key or not self.api_endpoint:
             raise ConfigurationError("VeoService is not properly configured with API key and/or endpoint.")

        payload = {
            "vision_name": vision_name,
            "custom_parameters": vision_parameters
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        try:
            response = await self.client.post(f"{self.api_endpoint}/videos", json=payload, headers=headers)
        except httpx.RequestError as e:
            # Catch network errors, DNS failures, timeouts etc.
            raise VeoAPIError(status_code=503, error_info=str(e), message_override=f"Request to Veo API failed: {e}")


        if response.status_code != 201:
            try:
                error_json = response.json()
            except ValueError: # If response is not JSON
                error_json = response.text
            raise VeoAPIError(status_code=response.status_code, error_info=error_json)

        response_data = response.json()
        return {
            "veo_video_id": response_data.get("veo_video_id"), # Assuming Veo API returns these keys
            "status": response_data.get("status", "submitted") # Provide a default status if not in response
        }

    async def get_video_status(self, veo_video_id: str) -> dict:
        """
        Fetches the status of a video from the Veo API.

        Args:
            veo_video_id: The ID of the video in the Veo system.

        Returns:
            A dictionary containing `veo_video_id`, `status`, and `download_url` (if available).
        
        Raises:
            VeoVideoNotFound: If the video ID is not found (404).
            VeoAPIError: For other API errors.
            ConfigurationError: If the service is not properly configured.
        """
        if not self.api_key or not self.api_endpoint:
             raise ConfigurationError("VeoService is not properly configured with API key and/or endpoint.")

        headers = {
            "Authorization": f"Bearer {self.api_key}"
        }

        try:
            response = await self.client.get(f"{self.api_endpoint}/videos/{veo_video_id}", headers=headers)
        except httpx.RequestError as e:
            raise VeoAPIError(status_code=503, error_info=str(e), message_override=f"Request to Veo API failed: {e}")

        if response.status_code == 404:
            try:
                error_json = response.json()
            except ValueError:
                error_json = response.text
            raise VeoVideoNotFound(veo_video_id=veo_video_id, error_info=error_json)
        
        if response.status_code != 200:
            try:
                error_json = response.json()
            except ValueError:
                error_json = response.text
            raise VeoAPIError(status_code=response.status_code, error_info=error_json)

        response_data = response.json()
        return {
            "veo_video_id": response_data.get("veo_video_id"), # Assuming Veo API returns these keys
            "status": response_data.get("status"),
            "download_url": response_data.get("download_url")
        }

# Example usage (for manual testing, ensure settings.py or env vars are set)
async def main():
    # This example will only work if VEO_API_KEY and VEO_API_ENDPOINT are correctly set
    # in veo_custom_video_app.config.settings or environment variables.
    try:
        service = VeoService() # Now initializes from settings/env
        print("VeoService initialized for example usage.")
        
        # Note: The following calls will interact with the LIVE Veo API if configured.
        # Use with caution and with appropriate test data/endpoints.
        # For this example, we'll comment out the actual API calls.
        
        # Example: Submit a video request
        # vision_params = {"prompt": "A real test prompt for Veo API", "style": "documentary"}
        # vision_name = "My Test Vision"
        # try:
        #     print(f"Submitting video request for '{vision_name}'...")
        #     submit_response = await service.submit_video_request(vision_name=vision_name, vision_parameters=vision_params)
        #     print(f"Submit response: {submit_response}")
        #     veo_id = submit_response.get("veo_video_id")
        #
        #     if veo_id:
        #         print(f"\nGetting status for Veo ID: {veo_id}...")
        #         status_response = await service.get_video_status(veo_id)
        #         print(f"Status response: {status_response}")
        #
        # except VeoAPIError as e:
        #     print(f"Veo API Error: {e.status_code} - {e.error_info} - {e}")
        # except VeoServiceError as e:
        #     print(f"Veo Service Error: {e}")

    except ConfigurationError as e:
        print(f"Configuration Error for example usage: {e}")
    except Exception as e:
        print(f"An unexpected error occurred during example usage: {e}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
