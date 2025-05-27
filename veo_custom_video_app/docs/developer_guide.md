# Developer Guide

This guide provides information for developers working on the VEO Custom Video Application backend.

## Project Setup

To set up the development environment:

1.  **Clone the repository** (if you haven't already).
2.  **Navigate to the backend directory:** `cd veo_custom_video_app/backend`
3.  **Create a Python virtual environment** (recommended):
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```
4.  **Install dependencies:**
    The application now uses PostgreSQL. Ensure you have `psycopg2-binary` (listed in `requirements.txt`) and other dependencies installed.
    ```bash
    pip install -r requirements.txt 
    ```
    If you also intend to run tests, ensure `pytest` and `httpx` are installed (they are included in `requirements.txt` under dev dependencies).

## Database Setup and Configuration (PostgreSQL)

The application now uses PostgreSQL for data persistence.

1.  **Install PostgreSQL:** Ensure you have a PostgreSQL server installed and running.
2.  **Create a Database:** Create a new database for this application (e.g., `veo_app_db`).
3.  **Configure Database Connection:**
    *   The database connection is configured via `veo_custom_video_app/config/settings.py`.
    *   This file is **not** committed to version control (it's listed in `veo_custom_video_app/.gitignore`).
    *   You must create `settings.py` by copying the example file:
        ```bash
        cp veo_custom_video_app/config/settings.py.example veo_custom_video_app/config/settings.py
        ```
    *   Edit `veo_custom_video_app/config/settings.py` and set the `DATABASE_URL` variable with your actual PostgreSQL connection string. For example:
        ```python
        # In veo_custom_video_app/config/settings.py
        DATABASE_URL = "postgresql://your_db_user:your_db_password@localhost:5432/your_veo_app_db"
        ```
        Refer to the comments in `settings.py.example` for details on the `DATABASE_URL` format.
4.  **SQLAlchemy Setup (`veo_custom_video_app/backend/database.py`):**
    *   This file manages the database connection using SQLAlchemy.
    *   It defines the SQLAlchemy `engine`, the `SessionLocal` class for creating database sessions, and the declarative `Base` for models.
    *   It also includes a `get_db` dependency function used by API routes to obtain a database session.
    *   The `init_db()` function in this file is responsible for creating all database tables based on the defined models.

## Running the Application

To run the FastAPI application locally (using Uvicorn, which is included via `uvicorn[standard]` in `requirements.txt`):

1.  Ensure your PostgreSQL server is running and `settings.py` is correctly configured.
2.  From the `veo_custom_video_app/backend` directory:
    ```bash
    uvicorn main:app --reload 
    ```
3.  The application will typically be available at `http://127.0.0.1:8000`.
4.  **Database Initialization:** The `init_db()` function (from `database.py`) is automatically called when the FastAPI application starts up (configured in `main.py`). This will create all necessary tables in your PostgreSQL database if they don't already exist.

## Project Structure

The backend is organized as follows:

*   `veo_custom_video_app/`
    *   `backend/`
        *   `main.py`: Initializes the FastAPI application, includes routers, handles startup events (like `init_db`), and can hold global configurations.
        *   `database.py`: Configures SQLAlchemy, database engine, session management, and `init_db` function.
        *   `api/`
            *   `__init__.py`: Makes `api` a Python package.
            *   `routes.py`: Defines all API endpoints (routers), Pydantic schemas for request/response validation, and the core CRUD logic using SQLAlchemy ORM.
        *   `services/`
            *   `__init__.py`: Makes `services` a Python package.
            *   `veo_service.py`: Contains the `VeoService` class (currently mock).
        *   `app/`
            *   `__init__.py`: Makes `app` a Python package.
            *   `models.py`: Defines SQLAlchemy models (`Agency`, `Vision`, `Video`) which now inherit `Base` from `database.py`.
        *   `auth/`
            *   `__init__.py`: Makes `auth` a Python package.
            *   `auth.py`: Implements API key authentication.
        *   `tests/`: Contains all unit and integration tests.
    *   `config/`:
        *   `settings.py.example`: Example configuration file.
        *   `settings.py`: User-specific settings (gitignored), including `DATABASE_URL`.
    *   `docs/`
        *   `api_documentation.md`: Detailed documentation for each API endpoint.
        *   `developer_guide.md`: This file.

The detailed model definitions (Agency, Vision, Video) remain largely the same but now reflect their persistence in PostgreSQL.

## Services and External Integrations

### Veo 3 API Integration (`services/veo_service.py`)

The `veo_custom_video_app/backend/services/veo_service.py` module contains the `VeoService` class, which is responsible for all communication with the external Veo 3 API. This service now makes real HTTP requests.

**Role of `VeoService`:**
*   Abstracts the details of interacting with the Veo 3 API.
*   Handles request formatting, authentication with the Veo API, and parsing responses.
*   Manages errors related to API communication and configuration.

**Configuration:**
*   To connect to the Veo 3 API, `VeoService` requires an API key and the API endpoint URL.
*   These must be configured in `veo_custom_video_app/config/settings.py` (which should be created by copying `settings.py.example` and is gitignored) or as environment variables:
    *   `VEO_API_KEY`: Your secret API key for the Veo 3 API.
    *   `VEO_API_ENDPOINT`: The base URL for the Veo 3 API (e.g., `https://api.veo.com/v3`).
*   If these settings are not found, `VeoService` will raise a `ConfigurationError` upon initialization.

**Assumed Veo 3 API Contract:**
The current implementation of `VeoService` assumes the following contract with the Veo 3 API. *This is an assumed contract based on the requirements and may need adjustment if official Veo 3 API documentation differs.*

*   **Authentication:** Uses Bearer Token authentication. The `VEO_API_KEY` is sent in the `Authorization` header as `Bearer <VEO_API_KEY>`.
*   **Submit Video Request (`POST /videos` relative to `VEO_API_ENDPOINT`):**
    *   **Request Payload:** A JSON object like:
        ```json
        {
            "vision_name": "Name of the Vision/Campaign",
            "custom_parameters": { ... } // Parameters specific to the vision
        }
        ```
    *   **Success Response (201 Created):** A JSON object expected to contain at least:
        ```json
        {
            "veo_video_id": "unique_video_id_from_veo",
            "status": "initial_status_from_veo" // e.g., "submitted"
        }
        ```
*   **Get Video Status (`GET /videos/{veo_video_id}` relative to `VEO_API_ENDPOINT`):**
    *   **Success Response (200 OK):** A JSON object expected to contain:
        ```json
        {
            "veo_video_id": "unique_video_id_from_veo",
            "status": "current_video_status", // e.g., "processing", "completed", "failed"
            "download_url": "url_to_video_if_completed_or_null"
        }
        ```
    *   **Not Found Response (404 Not Found):** If the video ID does not exist on the Veo API.

**Custom Exceptions:**
`VeoService` may raise the following custom exceptions (defined in `services/veo_service.py`):
*   `ConfigurationError`: If `VEO_API_KEY` or `VEO_API_ENDPOINT` are not configured.
*   `VeoAPIError`: For general errors when interacting with the Veo API (e.g., unexpected status codes, request failures). Contains `status_code` and `error_info` attributes.
*   `VeoVideoNotFound`: A subclass of `VeoAPIError`, specifically for 404 errors when trying to fetch a video's status.
The API routes in `api/routes.py` are designed to catch these exceptions and generally translate them into appropriate HTTP error responses (e.g., 500 Internal Server Error for configuration issues, 502 Bad Gateway for API errors, 404 Not Found for video not found on Veo).

## Authentication (`auth/auth.py`)

The API key authentication mechanism (`X-API-KEY` header) for accessing *this application's API* (not the external Veo API) is unchanged.

## Running Tests

The project uses `pytest` for unit and integration testing.

1.  **Test Environment:**
    *   **API Tests (`test_api_routes.py`):** These tests run against an **in-memory SQLite database**, configured in `veo_custom_video_app/backend/tests/conftest.py`. This provides fast and isolated tests for API logic without requiring a running PostgreSQL server for most development testing. `conftest.py` handles schema creation, session management, and overriding the `get_db` dependency.
    *   **`VeoService` Tests (`test_veo_service.py`):**
        *   Tests for `VeoService` now use **`pytest-httpx`** to mock external HTTP calls to the Veo 3 API.
        *   This approach allows testing of request formatting (URL, headers, payload), response parsing, and error handling logic within `VeoService` without making actual network calls to the Veo API.
        *   It also allows testing of the `VeoService`'s configuration loading mechanism (`__init__`) by mocking environment variables and the settings module.

2.  **Running Test Commands:**
    *   Ensure `pytest`, `httpx`, and `pytest-httpx` are installed (they are included in `veo_custom_video_app/backend/requirements.txt`).
    *   Navigate to the `veo_custom_video_app/backend/` directory.
    *   Run `pytest`:
        ```bash
        pytest
        ```
        Or, for more verbose output:
        ```bash
        pytest -v
        ```
    *   No new commands are needed; `conftest.py` automatically configures the test environment for both API and service tests.

## Future Enhancements (Conceptual)

*   **Real Veo API Integration:** (This is now largely complete, further refinements might be needed based on actual API behavior).
*   **Background Tasks:** Implement a proper background task manager (e.g., Celery) for video generation.
*   **Advanced Authentication/Authorization:** Implement more granular user roles or agency-specific API keys.
*   **Configuration Management:** Further enhance configuration management (e.g., using Pydantic's settings management for `settings.py`).
*   **Database Migrations:** Implement Alembic for managing database schema changes.
*   **Comprehensive Logging and Error Handling.**
