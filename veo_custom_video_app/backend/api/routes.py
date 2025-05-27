from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel, EmailStr
import datetime

# Import the VeoService instance from main.py
# This is a simplified approach for this example.
# In larger applications, FastAPI's dependency injection (Depends)
# would be more robustly configured, perhaps with a shared utility.
from veo_custom_video_app.backend.main import veo_service_instance
from veo_custom_video_app.backend.services.veo_service import (
    VeoService,
    VeoAPIError,
    VeoVideoNotFound,
    ConfigurationError,
    VeoServiceError, # Base error for more generic catches if needed
)
# Updated auth import to bring in more functions
from veo_custom_video_app.backend import auth as auth_utils 
from veo_custom_video_app.backend.auth.auth import get_api_key, get_current_active_user # Import JWT dependency

# Security imports for login
from fastapi.security import OAuth2PasswordRequestForm

# Database related imports
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError # For handling duplicate entries
from veo_custom_video_app.backend.database import get_db
from veo_custom_video_app.backend.app import models as db_models # Renamed to avoid confusion

# --- Pydantic Schemas ---
# Schemas are defined below.
# Ensure Agency, Vision, Video schemas have Config.orm_mode = True (already done)

# --- Veo API Parameters Schema (NEW) ---
# Note: pydantic.Field is imported but not used in the new schemas below.
# It can be removed if not used elsewhere or kept for consistency.
from pydantic import Field 

class VeoApiParameters(BaseModel):
    storageUri: Optional[str] = Field(None, description="GCS URI for output. gs://bucket/path/")
    sampleCount: Optional[int] = Field(None, ge=1, le=4, description="Number of videos to generate (1-4).")
    duration: Optional[float] = Field(None, ge=5, le=8, description="Video duration in seconds (5-8).")
    aspectRatio: Optional[str] = Field(None, pattern=r"^(16:9|9:16)$", description="Aspect ratio ('16:9' or '9:16').")
    negativePrompt: Optional[str] = Field(None, description="Negative prompt.")
    personGeneration: Optional[str] = Field(None, pattern=r"^(allow_adult|disallow)$", description="Person generation setting.")
    seed: Optional[int] = Field(None, description="Seed for reproducible results.")
    # Add any other known Veo 3.0 parameters here if they become known

    class Config:
        extra = 'allow' # Allow other parameters not explicitly defined
        orm_mode = True # Though not directly from ORM, useful if nested in other ORM models

# Agency Schemas
class AgencyBase(BaseModel):
    name: str
    email: EmailStr

class AgencyCreate(AgencyBase):
    pass

class AgencyUpdate(AgencyBase):
    name: Optional[str] = None
    email: Optional[EmailStr] = None

class Agency(AgencyBase):
    id: int
    created_at: datetime.datetime
    updated_at: datetime.datetime

    class Config:
        orm_mode = True

# Vision Schemas
class VisionBase(BaseModel):
    name: str
    description: Optional[str] = None
    prompt: str # Added: Main text prompt for video generation
    veo_parameters: Optional[VeoApiParameters] = None # Updated: Use structured Pydantic model

class VisionCreate(VisionBase):
    pass

class VisionUpdate(BaseModel): # VisionUpdate needs to be flexible, not inherit all required fields from VisionBase
    name: Optional[str] = None
    description: Optional[str] = None
    prompt: Optional[str] = None
    veo_parameters: Optional[VeoApiParameters] = None


class Vision(VisionBase): # This is the response model
    id: int
    agency_id: int
    created_at: datetime.datetime
    updated_at: datetime.datetime

    class Config:
        orm_mode = True

# Video Schemas
class VideoBase(BaseModel):
    veo_video_id: Optional[str] = None
    status: str = "pending"
    download_url: Optional[str] = None

class VideoCreate(BaseModel):
    # Potentially empty, or could include override parameters for Veo
    pass

class Video(VideoBase):
    id: int
    vision_id: int
    created_at: datetime.datetime
    updated_at: datetime.datetime

    class Config:
        orm_mode = True


# --- API Routers ---
# The main router for most API endpoints, protected by API Key
router = APIRouter(dependencies=[Depends(get_api_key)], tags=["Legacy API Key Endpoints"])

# Auth router - for login, no API key needed
auth_router = APIRouter(tags=["Authentication"])

# New router for JWT-protected user-specific endpoints
user_router = APIRouter(tags=["User Endpoints (JWT Secured)"])


# --- Login Endpoint ---
@auth_router.post("/auth/login", response_model=Token) 
async def login_for_access_token(db: Session = Depends(get_db), form_data: OAuth2PasswordRequestForm = Depends()):
    user = db.query(db_models.User).filter(db_models.User.email == form_data.username).first()
    
    if not user or not auth_utils.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
        
    access_token_data = {"sub": user.email}
    access_token = auth_utils.create_access_token(data=access_token_data)
    
    return {"access_token": access_token, "token_type": "bearer"}


# Dependency function for VeoService (remains the same)
async def get_veo_service():
    return veo_service_instance


# --- Agency Endpoints ---
# POST /agencies/ remains on the old API key router for now
@router.post("/agencies/", response_model=Agency, status_code=status.HTTP_201_CREATED)
async def create_agency(agency: AgencyCreate, db: Session = Depends(get_db)):
    # Check for existing agency by name or email
    existing_agency_email = db.query(db_models.Agency).filter(db_models.Agency.email == agency.email).first()
    if existing_agency_email:
        raise HTTPException(status_code=400, detail="Agency with this email already exists")
    existing_agency_name = db.query(db_models.Agency).filter(db_models.Agency.name == agency.name).first()
    if existing_agency_name:
        raise HTTPException(status_code=400, detail="Agency with this name already exists")

    db_agency = db_models.Agency(name=agency.name, email=agency.email)
    db.add(db_agency)
    try:
        db.commit()
        db.refresh(db_agency)
    except IntegrityError: # Should be caught by above checks, but as a safeguard
        db.rollback()
        raise HTTPException(status_code=400, detail="Agency already exists (email or name).")
    return db_agency

# GET /agencies/ is moved to user_router and protected by JWT
@user_router.get("/agencies/", response_model=List[Agency])
async def list_agencies(
    db: Session = Depends(get_db), 
    current_user: db_models.User = Depends(get_current_active_user)
):
    # current_user is now available, but not used for filtering in this step
    # Future: could filter agencies based on current_user if there's a relationship
    agencies = db.query(db_models.Agency).all()
    return agencies

# GET /agencies/{agency_id} remains on the old API key router for now
@router.get("/agencies/{agency_id}", response_model=Agency)
async def get_agency(agency_id: int, db: Session = Depends(get_db)):
    db_agency = db.query(db_models.Agency).filter(db_models.Agency.id == agency_id).first()
    if db_agency is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agency not found")
    return db_agency

@router.put("/agencies/{agency_id}", response_model=Agency)
async def update_agency(agency_id: int, agency_update: AgencyUpdate, db: Session = Depends(get_db)):
    db_agency = db.query(db_models.Agency).filter(db_models.Agency.id == agency_id).first()
    if db_agency is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agency not found")

    update_data = agency_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_agency, key, value)
    
    # Check for potential unique constraint violations if email/name are being changed
    if "email" in update_data:
        existing_email = db.query(db_models.Agency).filter(db_models.Agency.email == update_data["email"], db_models.Agency.id != agency_id).first()
        if existing_email:
            raise HTTPException(status_code=400, detail="Another agency with this email already exists.")
    if "name" in update_data:
        existing_name = db.query(db_models.Agency).filter(db_models.Agency.name == update_data["name"], db_models.Agency.id != agency_id).first()
        if existing_name:
            raise HTTPException(status_code=400, detail="Another agency with this name already exists.")
            
    db_agency.updated_at = datetime.datetime.utcnow() # Manually update timestamp if not auto by DB
    try:
        db.commit()
        db.refresh(db_agency)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Update failed due to conflict (e.g. email/name exists).")
    return db_agency

@router.delete("/agencies/{agency_id}", status_code=status.HTTP_200_OK)
async def delete_agency(agency_id: int, db: Session = Depends(get_db)):
    db_agency = db.query(db_models.Agency).filter(db_models.Agency.id == agency_id).first()
    if db_agency is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agency not found")
    
    # Cascading delete for visions and videos should be handled by SQLAlchemy relationships
    # if `cascade="all, delete-orphan"` is set on Agency.visions and Vision.videos.
    db.delete(db_agency)
    db.commit()
    return {"message": "Agency and associated visions and videos deleted successfully"}

# --- Vision Endpoints ---
@router.post("/agencies/{agency_id}/visions/", response_model=Vision, status_code=status.HTTP_201_CREATED)
async def create_vision_for_agency(agency_id: int, vision: VisionCreate, db: Session = Depends(get_db)):
    db_agency = db.query(db_models.Agency).filter(db_models.Agency.id == agency_id).first()
    if not db_agency:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agency not found")
    
    db_vision_data = vision.dict(exclude_unset=True) # Use exclude_unset for partial updates if needed, though create usually has all
    
    # Handle nested Pydantic model for veo_parameters
    if vision.veo_parameters is not None:
        db_vision_data["veo_parameters"] = vision.veo_parameters.dict(exclude_none=True)
    else:
        db_vision_data["veo_parameters"] = None # Ensure it's explicitly None if not provided

    db_vision = db_models.Vision(**db_vision_data, agency_id=agency_id)
    db.add(db_vision)
    db.commit()
    db.refresh(db_vision)
    return db_vision

@router.get("/agencies/{agency_id}/visions/", response_model=List[Vision])
async def list_visions_for_agency(agency_id: int, db: Session = Depends(get_db)):
    db_agency = db.query(db_models.Agency).filter(db_models.Agency.id == agency_id).first()
    if not db_agency:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agency not found")
    visions = db.query(db_models.Vision).filter(db_models.Vision.agency_id == agency_id).all()
    return visions

@router.get("/visions/{vision_id}", response_model=Vision)
async def get_vision(vision_id: int, db: Session = Depends(get_db)):
    db_vision = db.query(db_models.Vision).filter(db_models.Vision.id == vision_id).first()
    if db_vision is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vision not found")
    return db_vision

@router.put("/visions/{vision_id}", response_model=Vision)
async def update_vision(vision_id: int, vision_update: VisionUpdate, db: Session = Depends(get_db)):
    db_vision = db.query(db_models.Vision).filter(db_models.Vision.id == vision_id).first()
    if db_vision is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vision not found")

    update_data = vision_update.dict(exclude_unset=True) 
    
    for key, value in update_data.items():
        if key == "veo_parameters" and value is not None:
            # If veo_parameters is being updated, convert Pydantic model to dict
            setattr(db_vision, key, value.dict(exclude_none=True))
        elif value is not None: # Ensure other fields are also set if provided
            setattr(db_vision, key, value)

    db_vision.updated_at = datetime.datetime.utcnow() # Manually update timestamp
    db.commit()
    db.refresh(db_vision)
    return db_vision

@router.delete("/visions/{vision_id}", status_code=status.HTTP_200_OK)
async def delete_vision(vision_id: int, db: Session = Depends(get_db)):
    db_vision = db.query(db_models.Vision).filter(db_models.Vision.id == vision_id).first()
    if db_vision is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vision not found")
    
    # Cascading delete for videos should be handled by SQLAlchemy relationships
    # if `cascade="all, delete-orphan"` is set on Vision.videos.
    db.delete(db_vision)
    db.commit()
    return {"message": "Vision and associated videos deleted successfully"}

# --- Video Endpoints ---
@router.post("/visions/{vision_id}/videos/", response_model=Video, status_code=status.HTTP_201_CREATED)
async def create_video_for_vision(
    vision_id: int,
    # video_create: VideoCreate, # This schema is empty, so not directly used for db_video fields
    db: Session = Depends(get_db),
    veo_service: VeoService = Depends(get_veo_service)
):
    db_vision = db.query(db_models.Vision).filter(db_models.Vision.id == vision_id).first()
    if not db_vision:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vision not found")

    if not db_vision.prompt: # Check for prompt explicitly
        raise HTTPException(status_code=400, detail="Vision is missing the required prompt for video creation.")
    
    # veo_parameters can be None or an empty dict if not provided, which is fine for VeoService
    api_params = db_vision.veo_parameters if db_vision.veo_parameters is not None else {}

    try:
        # Pass vision_name if your VeoService's submit_video_request expects it
        # The VeoService now expects `prompt` and `parameters` separately
        operation_name = await veo_service.submit_video_request(
            prompt=db_vision.prompt,
            parameters=api_params # This should be a dict
        )
    except ConfigurationError as exc:
        # Log error: print(f"Configuration error for VeoService: {exc}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Server configuration error related to video service.")
    except VeoAPIError as exc:
        # Log error: print(f"Veo API error during submission: {exc.status_code} - {exc.error_info}")
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Video API error: {exc.status_code} - {exc.error_info}")
    except VeoServiceError as exc: # Catch other VeoService specific errors
        # Log error: print(f"VeoService error during submission: {exc}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An unexpected error occurred with the video service: {exc}")
    except Exception as exc: # Generic fallback
        # Log error: print(f"Generic error during video submission: {exc}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An unexpected error occurred: {exc}")


    # The Veo API (Vertex AI) returns an operation name, not directly veo_video_id and status.
    # Store the operation name in veo_video_id for now. Status will be 'submitted' or 'processing'.
    db_video = db_models.Video(
        vision_id=vision_id,
        veo_video_id=operation_name, # Store operation_name here
        status="processing" # Initial status after submitting to Vertex AI
    )
    db.add(db_video)
    db.commit()
    db.refresh(db_video)
    return db_video

@router.get("/videos/{video_id}", response_model=Video)
async def get_video(
    video_id: int, 
    db: Session = Depends(get_db),
    veo_service: VeoService = Depends(get_veo_service)
):
    db_video = db.query(db_models.Video).filter(db_models.Video.id == video_id).first()
    if not db_video:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Video not found")

    non_terminal_statuses = ["pending", "submitted", "processing"]
    # veo_video_id now stores the operation_name from Vertex AI
    if db_video.status in non_terminal_statuses and db_video.veo_video_id: 
        try:
            # veo_video_id is actually the operation_name here
            operation_status_response = await veo_service.get_video_status(operation_name=db_video.veo_video_id) 
            
            needs_db_update = False
            new_status = db_video.status # Keep current status unless changed by API response

            if operation_status_response["done"]:
                if operation_status_response.get("error"):
                    new_status = "failed"
                elif operation_status_response.get("video_uris"):
                    new_status = "completed"
                    # Assuming we only store one download URL for now, take the first one.
                    # The Video model's download_url field would store this.
                    if operation_status_response["video_uris"]:
                        if db_video.download_url != operation_status_response["video_uris"][0]:
                            db_video.download_url = operation_status_response["video_uris"][0]
                            needs_db_update = True
                else: # Done, but no error and no video_uris (unexpected state)
                    new_status = "completed_unknown_response"
            else: # Not done yet
                new_status = "processing" # Or keep current if it's more specific like 'submitted'

            if db_video.status != new_status:
                db_video.status = new_status
                needs_db_update = True
            
            if needs_db_update:
                db_video.updated_at = datetime.datetime.utcnow()
                db.commit()
                db.refresh(db_video)

        except ConfigurationError as exc:
            print(f"Warning: Configuration error for VeoService when trying to update status for video {video_id}: {exc}. Returning last known status.")
        except VeoOperationNotFound as exc: # Updated exception name
            print(f"Warning: Operation {db_video.veo_video_id} for internal video ID {video_id} not found on Veo API: {exc}. Setting status to 'error_fetching_status'.")
            db_video.status = "error_fetching_status"
            db_video.updated_at = datetime.datetime.utcnow()
            db.commit()
            db.refresh(db_video)
        except VeoAPIError as exc:
            print(f"Warning: Veo API error when trying to update status for video {video_id}: {exc}. Returning last known status.")
        except VeoServiceError as exc:
            print(f"Warning: VeoService error when trying to update status for video {video_id}: {exc}. Returning last known status.")
        except Exception as exc: 
            print(f"Warning: Generic error when trying to update status for video {video_id}: {exc}. Returning last known status.")

    return db_video
