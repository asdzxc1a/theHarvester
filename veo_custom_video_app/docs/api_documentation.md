# API Documentation

This document provides details about the backend API endpoints for the VEO Custom Video Application. All API endpoints are prefixed with `/api/v1`.

## Authentication

The API uses two primary methods for authentication:

1.  **X-API-KEY (Static API Key):**
    *   Many general backend endpoints are protected by a static API key.
    *   **Header:** `X-API-KEY: YOUR_STATIC_API_KEY`
    *   If the API key is missing or invalid, the server will respond with a `401 Unauthorized` error.
    *   For development purposes, a hardcoded key (`SECRET_API_KEY_FOR_NOW` in `auth/auth.py`) is used for these endpoints.

2.  **JWT Bearer Tokens (User Authentication):**
    *   User-specific actions and new user-centric endpoints are protected by JWT Bearer Tokens.
    *   To obtain a JWT, users must first authenticate via the `/api/v1/auth/login` endpoint.
    *   **Header:** `Authorization: Bearer <your_access_token>`
        (Replace `<your_access_token>` with the token received from the login endpoint).
    *   If the token is missing, invalid, or expired, the server will typically respond with a `401 Unauthorized` or `403 Forbidden` error.

Endpoints are progressively being transitioned to JWT-based authentication where appropriate. Check the specific authentication method required for each endpoint below.

## Authentication Endpoints

### 1. Login for Access Token

*   **Endpoint:** `POST /api/v1/auth/login`
*   **Description:** Authenticates a user based on email and password, and returns a JWT access token.
*   **Authentication:** None required for this endpoint.
*   **Request Body:** `application/x-www-form-urlencoded`
    *   `username`: The user's email address.
    *   `password`: The user's plain-text password.
*   **Example Request (`curl`):**
    ```bash
    curl -X POST "http://localhost:8000/api/v1/auth/login" \
         -H "Content-Type: application/x-www-form-urlencoded" \
         -d "username=user@example.com&password=securepassword123"
    ```
*   **Success Response (200 OK):**
    ```json
    {
        "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...", // Example JWT
        "token_type": "bearer"
    }
    ```
*   **Error Responses:**
    *   `401 Unauthorized`: If email/password is incorrect.
        ```json
        {
            "detail": "Incorrect email or password"
        }
        ```
    *   `400 Bad Request`: If the user is inactive.
        ```json
        {
            "detail": "Inactive user"
        }
        ```
    *   `422 Unprocessable Entity`: If form data is malformed (e.g., missing fields).

### 2. Create User (Signup)

*   **Endpoint:** `POST /api/v1/users/`
*   **Description:** Creates a new user account. This is typically used for user registration or initial user setup.
*   **Authentication:** None required for this endpoint.
*   **Request Body (`application/json`):**
    Based on the `UserCreate` schema.
    ```json
    {
      "email": "newuser@example.com",
      "password": "a_strong_password",
      "full_name": "New User Name (Optional)"
    }
    ```
*   **Success Response (201 Created):**
    Based on the `User` schema (excluding `hashed_password`).
    ```json
    {
      "id": 1,
      "email": "newuser@example.com",
      "full_name": "New User Name (Optional)",
      "is_active": true,
      "is_superuser": false,
      "created_at": "YYYY-MM-DDTHH:MM:SS.ffffff+ZZ:ZZ", 
      "updated_at": "YYYY-MM-DDTHH:MM:SS.ffffff+ZZ:ZZ"  
    }
    ```
    *(Note: `created_at` and `updated_at` will be actual timestamp values)*
*   **Error Responses:**
    *   `400 Bad Request`: If the email is already registered.
        ```json
        {
            "detail": "Email already registered"
        }
        ```
    *   `422 Unprocessable Entity`: If the request body fails validation (e.g., invalid email format, missing required fields).
        ```json
        {
          "detail": [
            {
              "loc": ["body", "email"],
              "msg": "value is not a valid email address",
              "type": "value_error.email"
            }
          ]
        }
        ```
        *(Example shown is for an invalid email; other validation errors will have different `loc`, `msg`, and `type` values.)*

## Agency Endpoints

Base URL: `/api/v1/agencies`

### 1. Create Agency

*   **Endpoint:** `POST /agencies/`
*   **Description:** Creates a new agency.
*   **Request Body:**
    ```json
    {
        "name": "Example Agency Inc.",
        "email": "contact@exampleagency.com"
    }
    ```
*   **Success Response (201 Created):**
    ```json
    {
        "id": 1,
        "name": "Example Agency Inc.",
        "email": "contact@exampleagency.com",
        "created_at": "2023-10-27T10:00:00.000Z",
        "updated_at": "2023-10-27T10:00:00.000Z"
    }
    ```
*   **Error Responses:**
    *   `400 Bad Request`: If email or name already exists.

### 2. List Agencies

*   **Endpoint:** `GET /agencies/`
*   **Description:** Retrieves a list of all agencies.
*   **Authentication:** JWT Bearer Token (`Authorization: Bearer <token>`)
*   **Success Response (200 OK):**
    ```json
    [
        {
            "id": 1,
            "name": "Example Agency Inc.",
            "email": "contact@exampleagency.com",
            "created_at": "2023-10-27T10:00:00.000Z",
            "updated_at": "2023-10-27T10:00:00.000Z"
        },
        {
            "id": 2,
            "name": "Another Creative Co.",
            "email": "hello@anothercreative.co",
            "created_at": "2023-10-28T11:00:00.000Z",
            "updated_at": "2023-10-28T11:00:00.000Z"
        }
    ]
    ```

### 3. Get Specific Agency

*   **Endpoint:** `GET /agencies/{agency_id}`
*   **Description:** Retrieves details for a specific agency.
*   **Path Parameter:** `agency_id` (integer, required) - The ID of the agency to retrieve.
*   **Success Response (200 OK):**
    ```json
    {
        "id": 1,
        "name": "Example Agency Inc.",
        "email": "contact@exampleagency.com",
        "created_at": "2023-10-27T10:00:00.000Z",
        "updated_at": "2023-10-27T10:00:00.000Z"
    }
    ```
*   **Error Responses:**
    *   `404 Not Found`: If the agency with the specified ID does not exist.

### 4. Update Agency

*   **Endpoint:** `PUT /agencies/{agency_id}`
*   **Description:** Updates details for an existing agency.
*   **Path Parameter:** `agency_id` (integer, required) - The ID of the agency to update.
*   **Request Body:** (Fields are optional; only include fields to be updated)
    ```json
    {
        "name": "Updated Example Agency Name",
        "email": "newcontact@exampleagency.com"
    }
    ```
*   **Success Response (200 OK):**
    ```json
    {
        "id": 1,
        "name": "Updated Example Agency Name",
        "email": "newcontact@exampleagency.com",
        "created_at": "2023-10-27T10:00:00.000Z",
        "updated_at": "2023-10-28T12:00:00.000Z" 
    }
    ```
*   **Error Responses:**
    *   `404 Not Found`: If the agency with the specified ID does not exist.

### 5. Delete Agency

*   **Endpoint:** `DELETE /agencies/{agency_id}`
*   **Description:** Deletes a specific agency and all its associated visions and videos.
*   **Path Parameter:** `agency_id` (integer, required) - The ID of the agency to delete.
*   **Success Response (200 OK):**
    ```json
    {
        "message": "Agency and associated visions and videos deleted successfully"
    }
    ```
*   **Error Responses:**
    *   `404 Not Found`: If the agency with the specified ID does not exist.

## Vision Endpoints

### 1. Create Vision for Agency

*   **Endpoint:** `POST /agencies/{agency_id}/visions/`
*   **Description:** Creates a new vision (campaign) for a specific agency.
*   **Path Parameter:** `agency_id` (integer, required) - The ID of the agency to which this vision belongs.
*   **Request Body:**
    ```json
    {
        "name": "Spring Campaign 2024",
        "description": "A campaign focusing on spring collection.",
        "veo_parameters": {
            "prompt": "A sunny spring day with blooming flowers, cinematic style",
            "duration_sec": 15,
            "custom_logo_url": "https://example.com/logo.png"
        }
    }
    ```
*   **Success Response (201 Created):**
    ```json
    {
        "id": 101,
        "agency_id": 1,
        "name": "Spring Campaign 2024",
        "description": "A campaign focusing on spring collection.",
        "veo_parameters": {
            "prompt": "A sunny spring day with blooming flowers, cinematic style",
            "duration_sec": 15,
            "custom_logo_url": "https://example.com/logo.png"
        },
        "created_at": "2023-10-29T10:00:00.000Z",
        "updated_at": "2023-10-29T10:00:00.000Z"
    }
    ```
*   **Error Responses:**
    *   `404 Not Found`: If the agency with the specified `agency_id` does not exist.

### 2. List Visions for Agency

*   **Endpoint:** `GET /agencies/{agency_id}/visions/`
*   **Description:** Retrieves all visions associated with a specific agency.
*   **Path Parameter:** `agency_id` (integer, required) - The ID of the agency.
*   **Success Response (200 OK):**
    ```json
    [
        {
            "id": 101,
            "agency_id": 1,
            "name": "Spring Campaign 2024",
            "description": "A campaign focusing on spring collection.",
            "veo_parameters": {"prompt": "A sunny spring day..."},
            "created_at": "2023-10-29T10:00:00.000Z",
            "updated_at": "2023-10-29T10:00:00.000Z"
        }
    ]
    ```
*   **Error Responses:**
    *   `404 Not Found`: If the agency with the specified `agency_id` does not exist.

### 3. Get Specific Vision

*   **Endpoint:** `GET /visions/{vision_id}`
*   **Description:** Retrieves details for a specific vision.
*   **Path Parameter:** `vision_id` (integer, required) - The ID of the vision to retrieve.
*   **Success Response (200 OK):**
    ```json
    {
        "id": 101,
        "agency_id": 1,
        "name": "Spring Campaign 2024",
        "description": "A campaign focusing on spring collection.",
        "veo_parameters": {"prompt": "A sunny spring day..."},
        "created_at": "2023-10-29T10:00:00.000Z",
        "updated_at": "2023-10-29T10:00:00.000Z"
    }
    ```
*   **Error Responses:**
    *   `404 Not Found`: If the vision with the specified ID does not exist.

### 4. Update Vision

*   **Endpoint:** `PUT /visions/{vision_id}`
*   **Description:** Updates details for an existing vision.
*   **Path Parameter:** `vision_id` (integer, required) - The ID of the vision to update.
*   **Request Body:** (Fields are optional)
    ```json
    {
        "name": "Updated Spring Campaign",
        "description": "An updated description.",
        "veo_parameters": {"prompt": "A vibrant spring day..."}
    }
    ```
*   **Success Response (200 OK):**
    ```json
    {
        "id": 101,
        "agency_id": 1,
        "name": "Updated Spring Campaign",
        "description": "An updated description.",
        "veo_parameters": {"prompt": "A vibrant spring day..."},
        "created_at": "2023-10-29T10:00:00.000Z",
        "updated_at": "2023-10-29T14:00:00.000Z"
    }
    ```
*   **Error Responses:**
    *   `404 Not Found`: If the vision with the specified ID does not exist.

### 5. Delete Vision

*   **Endpoint:** `DELETE /visions/{vision_id}`
*   **Description:** Deletes a specific vision and its associated videos.
*   **Path Parameter:** `vision_id` (integer, required) - The ID of the vision to delete.
*   **Success Response (200 OK):**
    ```json
    {
        "message": "Vision and associated videos deleted successfully"
    }
    ```
*   **Error Responses:**
    *   `404 Not Found`: If the vision with the specified ID does not exist.

## Video Endpoints

### 1. Create Video for Vision (Request Video Generation)

*   **Endpoint:** `POST /visions/{vision_id}/videos/`
*   **Description:** Initiates a video generation request for a specific vision. The actual video generation is a background process simulated by the `VeoService`.
*   **Path Parameter:** `vision_id` (integer, required) - The ID of the vision for which to generate a video.
*   **Request Body:** (Currently empty, as Veo parameters are taken from the parent Vision. This could be extended to allow overrides.)
    ```json
    {}
    ```
*   **Success Response (201 Created):**
    ```json
    {
        "id": 5001,
        "vision_id": 101,
        "veo_video_id": "veo_mock_abc123xyz",
        "status": "submitted", 
        "download_url": null,
        "created_at": "2023-10-30T09:00:00.000Z",
        "updated_at": "2023-10-30T09:00:00.000Z"
    }
    ```
*   **Error Responses:**
    *   `404 Not Found`: If the vision with the specified `vision_id` does not exist.
    *   `400 Bad Request`: If the vision is missing `veo_parameters`.
    *   `503 Service Unavailable`: If the Veo service encounters an error during submission.

### 2. Get Video Status and Details

*   **Endpoint:** `GET /videos/{video_id}`
*   **Description:** Retrieves the status and details of a specific video. If the video is still processing, this endpoint will query the `VeoService` for the latest status.
*   **Path Parameter:** `video_id` (integer, required) - The internal ID of the video.
*   **Success Response (200 OK):**
    *   **If processing:**
        ```json
        {
            "id": 5001,
            "vision_id": 101,
            "veo_video_id": "veo_mock_abc123xyz",
            "status": "processing", 
            "download_url": null,
            "created_at": "2023-10-30T09:00:00.000Z",
            "updated_at": "2023-10-30T09:05:00.000Z"
        }
        ```
    *   **If completed:**
        ```json
        {
            "id": 5001,
            "vision_id": 101,
            "veo_video_id": "veo_mock_abc123xyz",
            "status": "completed",
            "download_url": "https://fake-veo-api.com/v3/downloads/veo_mock_abc123xyz.mp4",
            "created_at": "2023-10-30T09:00:00.000Z",
            "updated_at": "2023-10-30T09:10:00.000Z"
        }
        ```
*   **Error Responses:**
    *   `404 Not Found`: If the video with the specified ID does not exist.
