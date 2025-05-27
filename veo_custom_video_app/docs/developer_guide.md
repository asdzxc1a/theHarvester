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
    Key authentication-related dependencies include `passlib[bcrypt]` (for password hashing) and `python-jose[cryptography]` (for JWT handling).
    ```bash
    pip install -r requirements.txt 
    ```
    If you also intend to run tests, ensure `pytest`, `httpx`, and `pytest-httpx` are installed (they are included in `requirements.txt` under dev dependencies).

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
            *   `veo_service.py`: Contains the `VeoService` class, now integrating with the official Google Cloud Vertex AI Veo 3.0 API.
        *   `app/`
            *   `__init__.py`: Makes `app` a Python package.
            *   `models.py`: Defines SQLAlchemy models (`Agency`, `Vision`, `Video`) which now inherit `Base` from `database.py`.
        *   `auth/`
            *   `__init__.py`: Makes `auth` a Python package.
            *   `auth.py`: Implements API key authentication, password hashing, JWT creation, and token-based user dependency functions (`get_current_user`, `get_current_active_user`).
        *   `tests/`: Contains all unit and integration tests.
    *   `config/`:
        *   `settings.py.example`: Example configuration file.
        *   `settings.py`: User-specific settings (gitignored), including `DATABASE_URL`.
    *   `docs/`
        *   `api_documentation.md`: Detailed documentation for each API endpoint.
        *   `developer_guide.md`: This file.

## Models (`app/models.py`)

SQLAlchemy models define the structure for data stored in the PostgreSQL database.
*   All models now inherit `Base` from `veo_custom_video_app.backend.database`.
*   Relationships (e.g., `Agency.visions`, `Vision.videos`) are configured with `cascade="all, delete-orphan"` options in the models to ensure that deleting a parent object (like an Agency) also deletes its child objects (Visions, and subsequently Videos).

Key model fields relevant to Veo integration:
*   **`Vision.prompt` (Text, Not Null):** Stores the main text prompt for video generation, used as the primary input for the Veo API.
*   **`Vision.veo_parameters` (JSON, Nullable):** Stores a JSON object of additional parameters for the Veo API. This structure should align with the `parameters` block of the Google Cloud Vertex AI Veo API, as defined by the `VeoApiParameters` Pydantic model in `api/routes.py` (e.g., `storageUri`, `duration`, `aspectRatio`).
*   **`Video.veo_video_id` (String, Nullable):** This field now stores the `operation_name` returned by the Google Cloud Vertex AI API after submitting a video generation job (e.g., `projects/.../locations/.../operations/...`). This name is crucial for polling the operation's status.
*   **`Video.download_url` (String, Nullable):** Stores the GCS URI of the generated video (e.g., `gs://bucket/path/video.mp4`). This is typically the first URI from the `video_uris` list returned by a completed Veo operation.
*   **`Video.status` (String):** Reflects the processed status derived from the Veo operation (e.g., "processing", "completed", "failed", "error_fetching_status").

The detailed model definitions (Agency, Vision, Video) remain largely the same but now reflect their persistence in PostgreSQL and the updated field meanings for Veo integration.
A new `User` model has been added for storing user credentials and information.

## Services and External Integrations

### Google Cloud Vertex AI Veo 3.0 API Integration (`services/veo_service.py`)

The `veo_custom_video_app/backend/services/veo_service.py` module contains the `VeoService` class, which is responsible for all communication with the **official Google Cloud Vertex AI Veo 3.0 API** (e.g., using a model like `veo-3.0-generate-preview` via the `predictLongRunning` endpoint).

**Role of `VeoService`:**
*   Abstracts the details of interacting with the Google Cloud Vertex AI Veo 3.0 API.
*   Handles request formatting, authentication with the GCP API, and parsing responses.
*   Manages errors related to API communication and configuration.

**Configuration:**
To connect to the Google Cloud Vertex AI Veo 3.0 API, `VeoService` requires specific GCP configurations. These must be set in `veo_custom_video_app/config/settings.py` (copied from `settings.py.example` and gitignored) or as environment variables. Refer to `veo_custom_video_app/config/settings.py.example` for detailed comments and placeholders:
*   `VEO_API_KEY`: This must be a valid **GCP Access Token**. It's used as a Bearer token for authenticating with the Vertex AI API.
*   `VEO_API_ENDPOINT`: The regional base URL for the Vertex AI API (e.g., `https://us-central1-aiplatform.googleapis.com`).
*   `VEO_PROJECT_ID`: Your Google Cloud Project ID.
*   `VEO_REGION`: The GCP region where your project and Veo model are available (e.g., `us-central1`). `VeoService` can derive this from `VEO_API_ENDPOINT` if not explicitly set.
*   `VEO_MODEL_ID`: The specific Veo model ID (e.g., `veo-3.0-generate-preview`). Defaults to `"veo-3.0-generate-preview"` if not set.
If these settings are not correctly configured, `VeoService` will raise a `ConfigurationError`.

**API Interaction Flow (Asynchronous Operations - `predictLongRunning`):**
The service uses the `predictLongRunning` pattern common in Google Cloud AI APIs:
1.  **Submission:** `VeoService.submit_video_request(prompt: str, parameters: dict)` sends a request to the Vertex AI API.
    *   The `prompt` is taken from the `Vision.prompt` field.
    *   The `parameters` argument is a dictionary derived from `Vision.veo_parameters` (which itself is structured by the `VeoApiParameters` Pydantic model). This dictionary should conform to the structure expected by the Vertex AI Veo API's `parameters` block (e.g., fields like `storageUri`, `duration`, `aspectRatio`, `sampleCount`, `negativePrompt`, `personGeneration`, `seed`).
    *   If successful, the API returns an `operation_name` (e.g., `projects/.../locations/.../operations/...`). This `operation_name` is what our application stores in the `Video.veo_video_id` field.
2.  **Polling for Status:** `VeoService.get_video_status(operation_name: str)` is used to check the status of the long-running operation.
    *   This method polls the operation endpoint (`/v1/{operation_name}`).

**Interpreting Video Status and Output (from `VeoService.get_video_status`):**
The `VeoService.get_video_status` method returns a dictionary with the following key information parsed from the Vertex AI operation object:
*   `operation_name`: The name of the operation.
*   `done` (boolean): True if the operation has finished (successfully or with an error).
*   `status` (str): Interpreted by `VeoService` as "processing" (if not `done`), "completed" (if `done` and successful), or "failed" (if `done` with an error).
*   `error` (dict, optional): If the operation failed, this contains error details from the API.
*   `video_uris` (list, optional): If the operation completed successfully, this is a list of GCS URIs pointing to the generated video(s) (e.g., `["gs://bucket/path/video.mp4"]`). Our application typically uses the first URI from this list to populate the `Video.download_url` field.

**Custom Exceptions:**
`VeoService` may raise the following custom exceptions (defined in `services/veo_service.py`):
*   `ConfigurationError`: If required GCP configurations are missing.
*   `VeoAPIError`: For general errors when interacting with the GCP Veo API.
*   `VeoOperationNotFound`: Specifically for 404 errors when an operation name is not found on GCP.
The API routes in `api/routes.py` catch these exceptions and translate them into appropriate HTTP error responses.

## Authentication System

The application is transitioning to a more robust authentication system. Phase 1 introduces JWT-based authentication for user-specific actions, while the existing static X-API-KEY may still protect some general backend endpoints.

### Components:
*   **`User` Model (`app/models.py`):**
    *   A new SQLAlchemy model for storing user information, including `id`, `email`, `hashed_password`, `full_name`, `is_active`, `is_superuser`, `created_at`, and `updated_at`.
*   **Password Hashing (`auth/auth.py`):**
    *   Uses `passlib` with `bcrypt` for securely hashing and verifying user passwords.
    *   Provides `get_password_hash()` and `verify_password()` utility functions.
*   **JWT Configuration & Creation (`auth/auth.py` and `config/settings.py.example`):**
    *   JWTs (JSON Web Tokens) are used for authenticating users.
    *   **Configuration (in `config/settings.py`):**
        *   `JWT_SECRET_KEY`: A strong, secret key used to sign and verify JWTs. **This must be kept secret and be unique for your deployment.** Generate a secure key (e.g., using `openssl rand -hex 32`).
        *   `JWT_ALGORITHM`: The algorithm used for JWT signing (e.g., "HS256").
        *   `JWT_ACCESS_TOKEN_EXPIRE_MINUTES`: The duration for which an access token is valid.
    *   **Token Creation:** The `create_access_token(data: dict, expires_delta: timedelta = None)` function in `auth/auth.py` generates JWTs. The "sub" (subject) claim typically stores the user's email.
*   **JWT Verification & User Retrieval (`auth/auth.py`):**
    *   `oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/login")`: Defines the OAuth2 password bearer flow, pointing to the login endpoint.
    *   `get_current_user(token: str, db: Session)`: A FastAPI dependency that decodes the JWT from the `Authorization: Bearer <token>` header, validates it, and retrieves the corresponding user from the database.
    *   `get_current_active_user(current_user: User)`: A FastAPI dependency that builds upon `get_current_user` to also ensure the user is active.
*   **API Key Authentication (`auth/auth.py`):**
    *   The existing static `X-API-KEY` mechanism is still in place for some endpoints. Endpoints are being progressively moved to JWT-based authentication.

### Creating an Initial User
To test the login functionality and JWT-protected endpoints, you first need a user in the database. A script is provided for this purpose:

*   **Script Location:** `veo_custom_video_app/backend/create_initial_user.py`
*   **Purpose:** Allows direct creation of a user in the database via a command-line interface.
*   **Setup:**
    1.  Ensure your `DEV_DATABASE_URL` environment variable is set correctly and points to your development PostgreSQL database.
    2.  Make sure database tables (especially `users`) have been created by running the main FastAPI application at least once (`uvicorn main:app --reload`).
    3.  Install dependencies from `requirements.txt`.
*   **Usage:**
    ```bash
    # Navigate to veo_custom_video_app/backend/
    python create_initial_user.py 
    ```
    The script will prompt for the user's email, password, superuser status, active status, and full name.

### How to Login (Obtain JWT)
Clients authenticate by sending a POST request to the `/api/v1/auth/login` endpoint.
*   **Request Type:** `application/x-www-form-urlencoded` (standard for OAuth2 password flow).
*   **Form Data:**
    *   `username`: The user's email address.
    *   `password`: The user's plain-text password.
*   **Response:** If successful, the API returns a JSON object containing an `access_token` (the JWT) and `token_type` ("bearer").

### Making Authenticated Requests (Using JWT)
For endpoints protected by JWT authentication (e.g., `GET /api/v1/agencies/`):
*   The client must include the JWT in the `Authorization` header.
*   The header format is: `Authorization: Bearer <your_access_token>`
    (Replace `<your_access_token>` with the actual token received from the login endpoint).

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
