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
from veo_custom_video_app.backend.auth.auth import get_api_key

# Database related imports
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError # For handling duplicate entries
from veo_custom_video_app.backend.database import get_db
from veo_custom_video_app.backend.app import models as db_models # Renamed to avoid confusion

# --- Pydantic Schemas ---
# Schemas are defined below.
# Ensure Agency, Vision, Video schemas have Config.orm_mode = True (already done)

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
    veo_parameters: Optional[Dict] = None

class VisionCreate(VisionBase):
    pass

class VisionUpdate(VisionBase):
    name: Optional[str] = None
    description: Optional[str] = None
    veo_parameters: Optional[Dict] = None


class Vision(VisionBase):
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
router = APIRouter(dependencies=[Depends(get_api_key)])

# Dependency function for VeoService (remains the same)
async def get_veo_service():
    return veo_service_instance


# --- Agency Endpoints ---
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

@router.get("/agencies/", response_model=List[Agency])
async def list_agencies(db: Session = Depends(get_db)):
    agencies = db.query(db_models.Agency).all()
    return agencies

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
    
    db_vision = db_models.Vision(**vision.dict(), agency_id=agency_id)
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

    if not db_vision.veo_parameters:
        raise HTTPException(status_code=400, detail="Vision is missing veo_parameters needed for video creation.")

    try:
        # Pass vision_name if your VeoService's submit_video_request expects it
        veo_response = await veo_service.submit_video_request(
            vision_name=db_vision.name, 
            vision_parameters=db_vision.veo_parameters
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


    db_video = db_models.Video(
        vision_id=vision_id,
        veo_video_id=veo_response.get("veo_video_id"),
        status=veo_response.get("status", "submission_failed") # Default if Veo doesn't provide status
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
    if db_video.status in non_terminal_statuses and db_video.veo_video_id:
        try:
            veo_status_response = await veo_service.get_video_status(veo_video_id=db_video.veo_video_id)
            
            needs_update = False
            if veo_status_response.get("status") and db_video.status != veo_status_response.get("status"):
                db_video.status = veo_status_response["status"]
                needs_update = True
            if veo_status_response.get("download_url") and db_video.download_url != veo_status_response.get("download_url"):
                db_video.download_url = veo_status_response["download_url"]
                needs_update = True
            
            if needs_update:
                db_video.updated_at = datetime.datetime.utcnow() # Manually update timestamp
                db.commit()
                db.refresh(db_video)
        except ConfigurationError as exc:
            # Log error: print(f"Configuration error for VeoService: {exc}")
            # For a GET request, we might not want to expose this as a 500 to the client if the primary resource (db_video) was found.
            # However, if the status update is critical, a 500 might be appropriate.
            # For now, let's log and proceed with potentially stale data, or raise a specific error.
            print(f"Warning: Configuration error for VeoService when trying to update status for video {video_id}: {exc}. Returning last known status.")
            # Or raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Server configuration error for video status update.")
        except VeoVideoNotFound as exc:
            # This means the video is in our DB but not found on Veo anymore. This is an inconsistency.
            # Log warning: print(f"Video {db_video.veo_video_id} for internal ID {video_id} not found on Veo API: {exc}")
            # We could set a special status here, e.g., "status_unknown" or "error_fetching_status"
            # For now, we'll just return the last known status.
            db_video.status = "error_fetching_status" # Example of updating status
            db.commit()
            db.refresh(db_video)
            # Alternatively, re-raise as a 404 for the video if it's considered critical that it's on Veo
            # raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
        except VeoAPIError as exc:
            # Log error: print(f"Veo API error during status update for video {video_id}: {exc.status_code} - {exc.error_info}")
            # Similar to ConfigurationError, decide if this should break the request or just log.
            print(f"Warning: Veo API error when trying to update status for video {video_id}: {exc}. Returning last known status.")
            # Or raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Video status API error: {exc.status_code} - {exc.error_info}")
        except VeoServiceError as exc:
            # Log error: print(f"VeoService error during status update for video {video_id}: {exc}")
            print(f"Warning: VeoService error when trying to update status for video {video_id}: {exc}. Returning last known status.")
        except Exception as exc: # Generic fallback
            # Log error: print(f"Generic error during video status update for video {video_id}: {exc}")
            print(f"Warning: Generic error when trying to update status for video {video_id}: {exc}. Returning last known status.")

    return db_video
