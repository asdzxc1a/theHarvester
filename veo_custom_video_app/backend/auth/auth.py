from fastapi import Security, HTTPException, status
from fastapi.security.api_key import APIKeyHeader

API_KEY_NAME = "X-API-KEY"
# For this task, the API key is hardcoded.
# In a production environment, this should come from a secure configuration or environment variable.
SECRET_API_KEY = "SECRET_API_KEY_FOR_NOW"

api_key_header_auth = APIKeyHeader(name=API_KEY_NAME, auto_error=True)

async def get_api_key(api_key_header: str = Security(api_key_header_auth)):
    """
    Dependency function to validate the API key from the X-API-KEY header.
    
    Raises HTTPException with 401 status if the key is invalid or missing.
    """
    if api_key_header == SECRET_API_KEY:
        return api_key_header
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API Key",
        )

# Placeholder for future authorization logic:
# The current API key grants access to all data.
# Future work would involve linking API keys to specific agencies or users.
# For example, a more advanced dependency might look like:
#
# from veo_custom_video_app.backend.app.models import Agency # Assuming models are accessible
# from veo_custom_video_app.backend.app.database import SessionLocal # Assuming DB session
#
# async def get_current_agency(api_key: str = Security(get_api_key)):
#     db = SessionLocal()
#     agency = db.query(Agency).filter(Agency.api_key == api_key).first() # Hypothetical Agency.api_key field
#     db.close()
#     if not agency:
#         raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="API Key valid but no associated agency")
#     return agency
#
# This is purely conceptual for now and not implemented.
