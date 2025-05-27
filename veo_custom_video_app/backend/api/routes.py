from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel, EmailStr
import datetime

# Import the VeoService instance from main.py
# This is a simplified approach for this example.
# In larger applications, FastAPI's dependency injection (Depends)
# would be more robustly configured, perhaps with a shared utility.
from veo_custom_video_app.backend.main import veo_service_instance
from veo_custom_video_app.backend.services.veo_service import VeoService
from veo_custom_video_app.backend.auth.auth import get_api_key


# In-memory storage
db_agencies: Dict[int, Dict[str, Any]] = {}
db_visions: Dict[int, Dict[str, Any]] = {}
db_videos: Dict[int, Dict[str, Any]] = {}
next_agency_id = 1
next_vision_id = 1
next_video_id = 1

# --- Pydantic Schemas ---

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

# Dependency function for VeoService
async def get_veo_service():
    return veo_service_instance


# --- Agency Endpoints ---
@router.post("/agencies/", response_model=Agency, status_code=status.HTTP_201_CREATED)
async def create_agency(agency: AgencyCreate):
    global next_agency_id
    now = datetime.datetime.utcnow()
    new_agency = {
        "id": next_agency_id,
        "name": agency.name,
        "email": agency.email,
        "created_at": now,
        "updated_at": now,
    }
    # Check for duplicate email or name before adding
    for _, ag in db_agencies.items():
        if ag["email"] == agency.email:
            raise HTTPException(status_code=400, detail="Agency with this email already exists")
        if ag["name"] == agency.name:
            raise HTTPException(status_code=400, detail="Agency with this name already exists")
    db_agencies[next_agency_id] = new_agency
    next_agency_id += 1
    return new_agency

@router.get("/agencies/", response_model=List[Agency])
async def list_agencies():
    return list(db_agencies.values())

@router.get("/agencies/{agency_id}", response_model=Agency)
async def get_agency(agency_id: int):
    agency = db_agencies.get(agency_id)
    if not agency:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agency not found")
    return agency

@router.put("/agencies/{agency_id}", response_model=Agency)
async def update_agency(agency_id: int, agency_update: AgencyUpdate):
    agency = db_agencies.get(agency_id)
    if not agency:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agency not found")

    update_data = agency_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        agency[key] = value
    agency["updated_at"] = datetime.datetime.utcnow()
    db_agencies[agency_id] = agency
    return agency

@router.delete("/agencies/{agency_id}", status_code=status.HTTP_200_OK)
async def delete_agency(agency_id: int):
    if agency_id not in db_agencies:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agency not found")
    # Also delete associated visions and their videos
    visions_to_delete = [vision_id for vision_id, vision in db_visions.items() if vision["agency_id"] == agency_id]
    for vision_id in visions_to_delete:
        videos_to_delete = [video_id for video_id, video in db_videos.items() if video["vision_id"] == vision_id]
        for video_id in videos_to_delete:
            del db_videos[video_id]
        del db_visions[vision_id]
    del db_agencies[agency_id]
    return {"message": "Agency and associated visions and videos deleted successfully"}

# --- Vision Endpoints ---
@router.post("/agencies/{agency_id}/visions/", response_model=Vision, status_code=status.HTTP_201_CREATED)
async def create_vision_for_agency(agency_id: int, vision: VisionCreate):
    global next_vision_id
    if agency_id not in db_agencies:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agency not found")
    now = datetime.datetime.utcnow()
    new_vision = {
        "id": next_vision_id,
        "agency_id": agency_id,
        "name": vision.name,
        "description": vision.description,
        "veo_parameters": vision.veo_parameters,
        "created_at": now,
        "updated_at": now,
    }
    db_visions[next_vision_id] = new_vision
    next_vision_id += 1
    return new_vision

@router.get("/agencies/{agency_id}/visions/", response_model=List[Vision])
async def list_visions_for_agency(agency_id: int):
    if agency_id not in db_agencies:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agency not found")
    return [v for v in db_visions.values() if v["agency_id"] == agency_id]

@router.get("/visions/{vision_id}", response_model=Vision)
async def get_vision(vision_id: int):
    vision = db_visions.get(vision_id)
    if not vision:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vision not found")
    return vision

@router.put("/visions/{vision_id}", response_model=Vision)
async def update_vision(vision_id: int, vision_update: VisionUpdate):
    vision = db_visions.get(vision_id)
    if not vision:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vision not found")

    update_data = vision_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        vision[key] = value
    vision["updated_at"] = datetime.datetime.utcnow()
    db_visions[vision_id] = vision
    return vision

@router.delete("/visions/{vision_id}", status_code=status.HTTP_200_OK)
async def delete_vision(vision_id: int):
    if vision_id not in db_visions:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vision not found")
    # Also delete associated videos
    videos_to_delete = [video_id for video_id, video in db_videos.items() if video["vision_id"] == vision_id]
    for video_id in videos_to_delete:
        del db_videos[video_id]
    del db_visions[vision_id]
    return {"message": "Vision and associated videos deleted successfully"}

# --- Video Endpoints ---
@router.post("/visions/{vision_id}/videos/", response_model=Video, status_code=status.HTTP_201_CREATED)
async def create_video_for_vision(
    vision_id: int, 
    # video_create: VideoCreate, # video_create is currently empty and not used.
    # If it were to contain overrides, they'd be passed to VeoService.
    veo_service: VeoService = Depends(get_veo_service)
):
    global next_video_id
    vision = db_visions.get(vision_id)
    if not vision:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vision not found")

    veo_parameters = vision.get("veo_parameters")
    if not veo_parameters:
        # Or handle as a default if appropriate
        raise HTTPException(status_code=400, detail="Vision is missing veo_parameters needed for video creation.")

    try:
        veo_response = await veo_service.submit_video_request(vision_parameters=veo_parameters)
    except Exception as e: # Catch potential errors from the service
        raise HTTPException(status_code=503, detail=f"Veo service unavailable or error: {str(e)}")

    now = datetime.datetime.utcnow()
    new_video_internal_id = next_video_id
    
    video_data = {
        "id": new_video_internal_id,
        "vision_id": vision_id,
        "veo_video_id": veo_response.get("veo_video_id"),
        "status": veo_response.get("status", "submission_failed"), # Use status from Veo or a fallback
        "download_url": None, # Not available at creation
        "created_at": now,
        "updated_at": now,
    }
    db_videos[new_video_internal_id] = video_data
    next_video_id += 1
    return video_data

@router.get("/videos/{video_id}", response_model=Video)
async def get_video(
    video_id: int, 
    veo_service: VeoService = Depends(get_veo_service)
):
    video_record = db_videos.get(video_id)
    if not video_record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Video not found")

    # Check if status needs update from VeoService
    # Typically, 'pending', 'submitted', 'processing' might warrant an update check.
    # 'completed', 'failed' are terminal states.
    non_terminal_statuses = ["pending", "submitted", "processing"] 
    if video_record.get("status") in non_terminal_statuses and video_record.get("veo_video_id"):
        try:
            veo_status_response = await veo_service.get_video_status(veo_video_id=video_record["veo_video_id"])
            
            # Update our record with the latest from Veo
            video_record["status"] = veo_status_response.get("status", video_record["status"]) # Keep old if not present
            video_record["download_url"] = veo_status_response.get("download_url", video_record.get("download_url"))
            video_record["updated_at"] = datetime.datetime.utcnow()
            db_videos[video_id] = video_record # Save updated record

        except Exception as e:
            # Log the error, but potentially return the last known status to avoid breaking the user flow.
            # Or, you could raise an HTTPException here.
            print(f"Error updating video status from VeoService for video {video_id}: {str(e)}")
            # Not raising HTTPException here to allow users to see last known status even if Veo is temporarily down.

    return video_record
