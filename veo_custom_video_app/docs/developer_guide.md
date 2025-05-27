# Developer Guide

This guide provides information for developers working on the VEO Custom Video Application backend.

## Project Setup (Placeholder)

(Details on how to set up the development environment, install dependencies, and run the application locally will be added here. For now, ensure you have Python and FastAPI requirements installed.)

```bash
# Example:
# pip install fastapi uvicorn sqlalchemy psycopg2-binary pydantic python-dotenv httpx
# pip install pytest httpx # For running tests
```

## Running the Application (Placeholder)

To run the FastAPI application locally (assuming Uvicorn):

```bash
# From the veo_custom_video_app/backend directory:
uvicorn main:app --reload 
```
The application will typically be available at `http://127.0.0.1:8000`.

## Project Structure

The backend is organized as follows:

*   `veo_custom_video_app/`
    *   `backend/`
        *   `main.py`: Initializes the FastAPI application, includes routers, and can hold global configurations or dependencies (like the `VeoService` instance).
        *   `api/`
            *   `__init__.py`: Makes `api` a Python package.
            *   `routes.py`: Defines all API endpoints (routers), Pydantic schemas for request/response validation, and the core CRUD logic using in-memory data stores.
        *   `services/`
            *   `__init__.py`: Makes `services` a Python package.
            *   `veo_service.py`: Contains the `VeoService` class, responsible for abstracting interactions with the external Veo API. Currently, it provides mock implementations.
        *   `app/` (Potentially for core application logic and database interaction)
            *   `__init__.py`: Makes `app` a Python package.
            *   `models.py`: Defines SQLAlchemy models (`Agency`, `Vision`, `Video`). These are defined but not yet fully integrated with a persistent relational database in the current iteration (uses in-memory dicts in `routes.py`).
        *   `auth/`
            *   `__init__.py`: Makes `auth` a Python package.
            *   `auth.py`: Implements API key authentication logic, including the security scheme and dependency function (`get_api_key`).
        *   `tests/`: Contains all unit and integration tests.
            *   `__init__.py`: Makes `tests` a Python package.
            *   `conftest.py`: Pytest configuration and shared fixtures (e.g., `TestClient`).
            *   `test_api_routes.py`: Tests for the API endpoints.
            *   `test_veo_service.py`: Tests for the `VeoService`.
    *   `docs/`
        *   `api_documentation.md`: Detailed documentation for each API endpoint.
        *   `developer_guide.md`: This file.

## Models (`app/models.py`)

SQLAlchemy models define the structure for data that would eventually be stored in a persistent database.

### Agency
*   `id` (Integer, Primary Key): Unique identifier for the agency.
*   `name` (String, Not Null, Unique): Name of the agency.
*   `email` (String, Not Null, Unique): Contact email for the agency.
*   `created_at` (DateTime): Timestamp of creation.
*   `updated_at` (DateTime): Timestamp of the last update.
*   `visions` (Relationship): One-to-many relationship with `Vision` models.

### Vision
*   `id` (Integer, Primary Key): Unique identifier for the vision/campaign.
*   `agency_id` (Integer, Foreign Key to `agencies.id`, Not Null): ID of the parent agency.
*   `name` (String, Not Null): Name of the vision.
*   `description` (Text, Nullable): Detailed description of the vision.
*   `veo_parameters` (JSON, Nullable): JSON object storing parameters for the Veo API (e.g., prompt, style, duration).
*   `created_at` (DateTime): Timestamp of creation.
*   `updated_at` (DateTime): Timestamp of the last update.
*   `videos` (Relationship): One-to-many relationship with `Video` models.
*   `agency` (Relationship): Many-to-one relationship back to `Agency`.

### Video
*   `id` (Integer, Primary Key): Unique internal identifier for the video record.
*   `vision_id` (Integer, Foreign Key to `visions.id`, Not Null): ID of the parent vision.
*   `veo_video_id` (String, Nullable): Identifier returned by the Veo API for the generated video.
*   `status` (String, Default: "pending"): Current status of the video (e.g., "pending", "submitted", "processing", "completed", "failed").
*   `download_url` (String, Nullable): URL to download the generated video (available when status is "completed").
*   `created_at` (DateTime): Timestamp of creation.
*   `updated_at` (DateTime): Timestamp of the last update.
*   `vision` (Relationship): Many-to-one relationship back to `Vision`.

## Services (`services/veo_service.py`)

### VeoService
This service class is responsible for all communication with the (currently mock) Veo API.
*   **`__init__(self, api_key: str, api_endpoint: str)`**: Initializes the service with an API key and the Veo API endpoint.
*   **`async def submit_video_request(self, vision_parameters: dict) -> dict`**:
    *   Simulates submitting a video generation request to Veo.
    *   **Mock Logic:** Generates a unique mock Veo ID (`veo_mock_...`) and returns an initial status of `"submitted"`. Stores this status internally for `get_video_status`.
*   **`async def get_video_status(self, veo_video_id: str) -> dict`**:
    *   Simulates fetching the status of a previously submitted video.
    *   **Mock Logic:** Cycles through statuses: `"submitted"` -> `"processing"` -> `"completed"` based on how many times it's called for a specific `veo_video_id`. When `"completed"`, it also provides a mock `download_url`. If the ID is unknown, it returns a `"not_found"` status.

## Authentication (`auth/auth.py`)

API access is protected using an API key.
*   The client must send an `X-API-KEY` header with each request.
*   The `get_api_key` dependency function in `auth/auth.py` validates this key.
*   Currently, a single, hardcoded API key (`SECRET_API_KEY_FOR_NOW`) is used for all access.
*   If the key is missing or invalid, a `401 Unauthorized` HTTP response is returned.
*   This authentication is applied to all routes under `/api/v1/` by adding `Depends(get_api_key)` to the `APIRouter` in `api/routes.py`.

## Running Tests

The project uses `pytest` for unit and integration testing.

To run the tests:
1.  Ensure `pytest` and `httpx` (for `TestClient`) are installed in your environment:
    ```bash
    pip install pytest httpx
    ```
2.  Navigate to the `veo_custom_video_app/backend/` directory in your terminal.
3.  Run `pytest`:
    ```bash
    pytest
    ```
    Or, for more verbose output:
    ```bash
    pytest -v
    ```

Tests are located in the `veo_custom_video_app/backend/tests/` directory.
*   `conftest.py` contains shared fixtures, including a `TestClient` pre-configured with the valid API key for authenticated routes and one for unauthenticated requests. It also handles resetting the in-memory data stores before tests run.
*   `test_api_routes.py` tests the functionality of all API endpoints.
*   `test_veo_service.py` tests the logic of the mock `VeoService`.

## Future Enhancements (Conceptual)

*   **Database Integration:** Replace in-memory data storage with a persistent relational database (e.g., PostgreSQL) using SQLAlchemy.
*   **Real Veo API Integration:** Update `VeoService` to make actual HTTP requests to the Veo 3 API.
*   **Background Tasks:** Implement a proper background task manager (e.g., Celery) for handling video generation requests asynchronously instead of relying on mock service calls during HTTP requests.
*   **Advanced Authentication/Authorization:** Implement more granular user roles, permissions, or agency-specific API keys.
*   **Configuration Management:** Move hardcoded values (like API keys, Veo endpoint) to environment variables or configuration files.
*   **Comprehensive Logging and Error Handling.**The `api_documentation.md` and `developer_guide.md` files have been updated with the requested information.

**Summary of changes:**

**1. `veo_custom_video_app/docs/api_documentation.md`:**
    *   **Authentication:** Added a section explaining the `X-API-KEY` header requirement and mentioned the development key.
    *   **Agency Endpoints:** Documented `POST`, `GET` (list), `GET` (specific), `PUT`, and `DELETE` operations with example request/response JSON.
    *   **Vision Endpoints:** Documented `POST`, `GET` (list), `GET` (specific), `PUT`, and `DELETE` operations with example request/response JSON.
    *   **Video Endpoints:** Documented `POST` (create/request video) and `GET` (status/details) operations with example request/response JSON, showing different states like "processing" and "completed".
    *   Used the `/api/v1` prefix for all endpoints.
    *   Timestamp examples are illustrative (e.g., `2023-10-27T10:00:00.000Z`).

**2. `veo_custom_video_app/docs/developer_guide.md`:**
    *   **Project Structure:** Updated to reflect the current backend layout, including `main.py`, `api/routes.py`, `services/veo_service.py`, `app/models.py`, `auth/auth.py`, and `tests/`.
    *   **Models:** Added a section describing the `Agency`, `Vision`, and `Video` SQLAlchemy models and their key fields.
    *   **Services:** Described the `VeoService` and its current mock methods (`submit_video_request`, `get_video_status`) and their simulated behavior.
    *   **Authentication:** Briefly explained the API key mechanism using the `X-API-KEY` header and the `get_api_key` dependency.
    *   **Running Tests:** Added instructions on how to install `pytest` and run the tests from the `veo_custom_video_app/backend/` directory.
    *   Included placeholders for "Project Setup" and "Running the Application" as these were not explicitly part of this task but are standard for a developer guide.
    *   Added a "Future Enhancements" section for conceptual next steps.

All documentation updates have been made according to the subtask requirements.
