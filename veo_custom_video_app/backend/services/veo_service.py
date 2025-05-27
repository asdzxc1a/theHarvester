# veo_custom_video_app/backend/services/veo_service.py

# This service interacts with the Google Cloud Vertex AI Veo 3.0 API.
# The following outlines the API contract based on official documentation:
#
# Authentication:
# - Method: Bearer Token
# - Header: Authorization: Bearer <GCP_ACCESS_TOKEN>
#   (Note: <GCP_ACCESS_TOKEN> is typically obtained via Application Default Credentials
#    or a service account key when running in a GCP environment.
#    The VEO_API_KEY setting for this service should be this access token.)
#
# API Endpoint Base (example for us-central1):
# - https://us-central1-aiplatform.googleapis.com/v1
#
# Submit Video Generation Job (predictLongRunning):
# - HTTP Method: POST
# - Path: /projects/{PROJECT_ID}/locations/{REGION}/publishers/google/models/{MODEL_ID}:predictLongRunning
#   - PROJECT_ID: Your Google Cloud project ID.
#   - REGION: e.g., 'us-central1'.
#   - MODEL_ID: e.g., 'veo-3.0-generate-preview'.
# - Request Body (JSON):
#   {
#     "instances": [
#       { "prompt": "A text description of the video..." }
#       // Potentially other instance types like image_bytes for image-to-video
#     ],
#     "parameters": {
#       "storageUri": "gs://your-gcs-bucket/output-directory/", // Optional
#       "sampleCount": 1, // Optional (1-4)
#       "duration": 8, // Optional (5-8 seconds)
#       "aspectRatio": "16:9", // Optional ("16:9" or "9:16")
#       "negativePrompt": "blurry, low quality", // Optional
#       "personGeneration": "allow_adult", // Optional ("allow_adult", "disallow")
#       "seed": 12345 // Optional
#       // ... other Veo specific parameters ...
#     }
#   }
# - Success Response (typically 200 OK for async operation submission):
#   {
#     "name": "projects/{PROJECT_ID}/locations/{REGION}/operations/{OPERATION_ID}"
#   }
#   This 'name' is the OPERATION_NAME used for status checking.
#
# Check Operation Status:
# - HTTP Method: GET
# - Path: /{OPERATION_NAME} (e.g., /projects/{PROJECT_ID}/locations/{REGION}/operations/{OPERATION_ID})
# - Success Response:
#   {
#     "name": "projects/{PROJECT_ID}/locations/{REGION}/operations/{OPERATION_ID}",
#     "done": false, // If still processing
#     "metadata": { ... } // Optional, progress info
#   }
#   OR
#   {
#     "name": "projects/{PROJECT_ID}/locations/{REGION}/operations/{OPERATION_ID}",
#     "done": true,
#     "response": {
#       "@type": "type.googleapis.com/google.cloud.aiplatform.v1.PredictLongRunningResponse", // Or similar
#       "generatedVideos": [
#         { "video": "gs://your-gcs-bucket/output-directory/generated_video_01.mp4" }
#         // Potentially more videos if sampleCount > 1
#       ]
#     }
#   }
#   OR
#   {
#     "name": "projects/{PROJECT_ID}/locations/{REGION}/operations/{OPERATION_ID}",
#     "done": true,
#     "error": { // If the operation failed
#       "code": integer,
#       "message": "string",
#       "details": [ ... ]
#     }
#   }

import httpx
import os
from typing import Dict, Any, Optional, List # Added List

# --- Custom Exceptions ---
class VeoServiceError(Exception):
    '''Base class for VeoService errors.'''
    pass

class VeoAPIError(VeoServiceError):
    def __init__(self, status_code: int, error_info: Dict[str, Any] | str | None = None, message_override: Optional[str] = None):
        self.status_code = status_code
        self.error_info = error_info
        message = message_override if message_override else f"Google Cloud Veo API Error: Status {status_code}"
        if error_info and not message_override:
            message += f", Info: {error_info}"
        super().__init__(message)

class VeoOperationNotFound(VeoAPIError): # Renamed from VeoVideoNotFound
    def __init__(self, operation_name: str, error_info: Dict[str, Any] | str | None = None):
        super().__init__(status_code=404, error_info=error_info, message_override=f"Operation with name '{operation_name}' not found on Google Cloud Veo API.")

class ConfigurationError(VeoServiceError):
    '''Indicates a configuration problem for VeoService.'''
    pass

class VeoService:
    """
    A service class to interact with the Google Cloud Vertex AI Veo 3.0 API.
    """

    def __init__(self):
        """
        Initializes the VeoService.
        Loads configuration from veo_custom_video_app.config.settings or environment variables.
        """
        config_source_log = ""
        try:
            from veo_custom_video_app.config.settings import (
                VEO_API_KEY, VEO_API_ENDPOINT, VEO_PROJECT_ID, VEO_REGION, VEO_MODEL_ID
            )
            self.gcp_access_token = VEO_API_KEY
            self.base_endpoint = VEO_API_ENDPOINT
            self.project_id = VEO_PROJECT_ID
            self.region = VEO_REGION
            self.model_id = VEO_MODEL_ID
            config_source_log = "INFO: Loaded VeoService config from veo_custom_video_app.config.settings"
        except (ImportError, AttributeError):
            config_source_log = "INFO: veo_custom_video_app.config.settings.py not found or missing variables. Falling back to environment variables."
            self.gcp_access_token = os.getenv('VEO_API_KEY')
            self.base_endpoint = os.getenv('VEO_API_ENDPOINT')
            self.project_id = os.getenv('VEO_PROJECT_ID')
            self.region = os.getenv('VEO_REGION')
            self.model_id = os.getenv('VEO_MODEL_ID', "veo-3.0-generate-preview") # Default model_id
        
        print(config_source_log)

        if not self.gcp_access_token:
            raise ConfigurationError("VEO_API_KEY (GCP Access Token) is not configured.")
        if not self.base_endpoint:
            raise ConfigurationError("VEO_API_ENDPOINT (e.g., https://us-central1-aiplatform.googleapis.com) is not configured.")
        if not self.project_id:
            raise ConfigurationError("VEO_PROJECT_ID is not configured.")
        if not self.region:
            # Attempt to parse region from endpoint if not explicitly set
            # Example: https://us-central1-aiplatform.googleapis.com -> us-central1
            try:
                self.region = self.base_endpoint.split('//')[1].split('-')[0]
                print(f"INFO: VEO_REGION not explicitly set, derived '{self.region}' from VEO_API_ENDPOINT.")
            except (IndexError, AttributeError):
                 raise ConfigurationError("VEO_REGION is not configured and could not be derived from VEO_API_ENDPOINT.")
        if not self.model_id: # Should be set by default now, but check anyway
            raise ConfigurationError("VEO_MODEL_ID is not configured.")


        self.client = httpx.AsyncClient(timeout=60.0) # Increased timeout
        token_display = f"{'*' * (len(self.gcp_access_token) - 7)}{self.gcp_access_token[-4:]}" if self.gcp_access_token and len(self.gcp_access_token) > 7 else "Token Not Set or Too Short"
        print(f"INFO: VeoService initialized. Endpoint: {self.base_endpoint}, Project: {self.project_id}, Region: {self.region}, Model: {self.model_id}, Token: {token_display}")

    async def submit_video_request(self, prompt: str, parameters: Dict[str, Any]) -> str:
        """
        Submits a video generation job to the Google Cloud Veo API.

        Args:
            prompt: The text prompt for video generation.
            parameters: A dictionary of parameters for the Veo API,
                        e.g., {"storageUri": "gs://...", "duration": 8, ...}.

        Returns:
            The name of the long-running operation.
        
        Raises:
            VeoAPIError: If the API call fails or returns an unexpected status code.
            ConfigurationError: If the service is not properly configured.
        """
        if not all([self.gcp_access_token, self.base_endpoint, self.project_id, self.region, self.model_id]):
             raise ConfigurationError("VeoService is not properly configured.")

        url = f"{self.base_endpoint}/v1/projects/{self.project_id}/locations/{self.region}/publishers/google/models/{self.model_id}:predictLongRunning"
        
        payload = {
            "instances": [{"prompt": prompt}],
            "parameters": parameters
        }
        headers = {
            "Authorization": f"Bearer {self.gcp_access_token}",
            "Content-Type": "application/json"
        }

        try:
            response = await self.client.post(url, json=payload, headers=headers)
        except httpx.RequestError as e:
            raise VeoAPIError(status_code=503, error_info=str(e), message_override=f"Request to Google Cloud Veo API failed: {e}")

        if response.status_code != 200: # Vertex AI LRO submission typically returns 200
            try:
                error_json = response.json()
            except ValueError: 
                error_json = response.text
            raise VeoAPIError(status_code=response.status_code, error_info=error_json)

        response_data = response.json()
        operation_name = response_data.get("name")
        if not operation_name:
            raise VeoAPIError(status_code=response.status_code, error_info=response_data, message_override="Veo API did not return an operation name.")
        return operation_name

    async def get_video_status(self, operation_name: str) -> Dict[str, Any]:
        """
        Fetches the status of a video generation operation from the Google Cloud Veo API.

        Args:
            operation_name: The name of the long-running operation.

        Returns:
            A dictionary representing the operation status, including `done`, `status`, 
            `video_uris`, and `error` if any.
        
        Raises:
            VeoOperationNotFound: If the operation is not found (404).
            VeoAPIError: For other API errors.
            ConfigurationError: If the service is not properly configured.
        """
        if not all([self.gcp_access_token, self.base_endpoint]):
             raise ConfigurationError("VeoService is not properly configured for status check.")

        url = f"{self.base_endpoint}/v1/{operation_name}"
        headers = {
            "Authorization": f"Bearer {self.gcp_access_token}"
        }

        try:
            response = await self.client.get(url, headers=headers)
        except httpx.RequestError as e:
            raise VeoAPIError(status_code=503, error_info=str(e), message_override=f"Request to Google Cloud Veo API failed: {e}")

        if response.status_code == 404:
            try:
                error_json = response.json()
            except ValueError:
                error_json = response.text
            raise VeoOperationNotFound(operation_name=operation_name, error_info=error_json)
        
        if response.status_code != 200:
            try:
                error_json = response.json()
            except ValueError:
                error_json = response.text
            raise VeoAPIError(status_code=response.status_code, error_info=error_json)

        op_data = response.json()
        done = op_data.get("done", False)
        op_name_from_response = op_data.get("name")

        result = {
            "operation_name": op_name_from_response or operation_name,
            "done": done,
            "status": "processing", # Default status if not done or error
            "video_uris": [],
            "error": None
        }

        if done:
            if op_data.get("error"):
                result["status"] = "failed"
                result["error"] = op_data["error"]
            elif op_data.get("response"):
                result["status"] = "completed"
                generated_videos_data = op_data["response"].get("generatedVideos", [])
                result["video_uris"] = [vid.get("video") for vid in generated_videos_data if vid.get("video")]
            else:
                # This case might indicate an issue or an unexpected response structure for a completed job
                result["status"] = "completed_unknown_response"
                result["error"] = {"message": "Operation is done but no 'response' or 'error' field was found."}
        
        return result

# Example usage (for manual testing, ensure settings.py or env vars are set)
async def main():
    # This example will only work if VEO_API_KEY, VEO_API_ENDPOINT, VEO_PROJECT_ID, VEO_REGION, VEO_MODEL_ID
    # are correctly set in veo_custom_video_app.config.settings or environment variables.
    try:
        service = VeoService()
        print("VeoService initialized for example usage.")
        
        # Example: Submit a video request
        # prompt_text = "A majestic lion surveying the savannah at sunset"
        # video_params = {
        #     "storageUri": "gs://your-gcs-bucket-for-veo/outputs/", # Replace with your GCS bucket
        #     "duration": 6,
        #     "aspectRatio": "16:9"
        # }
        # try:
        #     print(f"Submitting video request for prompt: '{prompt_text}'...")
        #     operation_name = await service.submit_video_request(prompt=prompt_text, parameters=video_params)
        #     print(f"Video generation operation started: {operation_name}")
        #
        #     # Poll for status (simplified polling loop)
        #     for _ in range(10): # Poll up to 10 times
        #         await asyncio.sleep(30) # Wait 30 seconds between polls
        #         print(f"\nGetting status for operation: {operation_name}...")
        #         status_response = await service.get_video_status(operation_name)
        #         print(f"Status response: {status_response}")
        #         if status_response["done"]:
        #             if status_response["status"] == "completed":
        #                 print(f"Video generation completed! URIs: {status_response['video_uris']}")
        #             else:
        #                 print(f"Video generation failed or completed with unknown response: {status_response.get('error')}")
        #             break
        #     else:
        #         print("Polling finished, operation might still be processing.")
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
