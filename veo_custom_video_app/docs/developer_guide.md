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

## Models (`app/models.py`)

SQLAlchemy models define the structure for data stored in the PostgreSQL database.
*   All models now inherit `Base` from `veo_custom_video_app.backend.database`.
*   Relationships (e.g., `Agency.visions`, `Vision.videos`) are configured with `cascade="all, delete-orphan"` options in the models to ensure that deleting a parent object (like an Agency) also deletes its child objects (Visions, and subsequently Videos).
The detailed model definitions (Agency, Vision, Video) remain largely the same but now reflect their persistence in PostgreSQL.

## Services (`services/veo_service.py`)

The `VeoService` remains responsible for interactions with the (mock) Veo API. Its functionality is unchanged by the database migration.

## Authentication (`auth/auth.py`)

The API key authentication mechanism (`X-API-KEY` header) is also unchanged.

## Running Tests

The project uses `pytest` for unit and integration testing.

1.  **Test Environment:**
    *   API tests (`test_api_routes.py`) now run against an **in-memory SQLite database**. This is configured in `veo_custom_video_app/backend/tests/conftest.py`.
    *   Using SQLite in-memory provides fast and isolated tests for API logic without requiring a running PostgreSQL server for most development testing.
    *   The `conftest.py` file handles:
        *   Setting up the SQLite engine.
        *   Creating the database schema before tests run and tearing it down afterwards.
        *   Providing a transactional database session to each test, ensuring changes are rolled back and tests are isolated.
        *   Overriding the application's `get_db` dependency to use this test database session.
    *   For full end-to-end testing that precisely mirrors the production PostgreSQL environment, a separate PostgreSQL test database and configuration would be ideal. However, for unit and most integration tests, SQLite offers a good balance of speed and realism.

2.  **Running Test Commands:**
    *   Ensure `pytest` and `httpx` are installed (they are included in `veo_custom_video_app/backend/requirements.txt`).
    *   Navigate to the `veo_custom_video_app/backend/` directory.
    *   Run `pytest`:
        ```bash
        pytest
        ```
        Or, for more verbose output:
        ```bash
        pytest -v
        ```
    *   No new commands are needed; `conftest.py` automatically configures the test environment.

## Future Enhancements (Conceptual)

*   **Real Veo API Integration:** Update `VeoService` to make actual HTTP requests.
*   **Background Tasks:** Implement a proper background task manager (e.g., Celery) for video generation.
*   **Advanced Authentication/Authorization:** Implement more granular user roles or agency-specific API keys.
*   **Configuration Management:** Further enhance configuration management (e.g., using Pydantic's settings management).
*   **Database Migrations:** Implement Alembic for managing database schema changes.
*   **Comprehensive Logging and Error Handling.**
