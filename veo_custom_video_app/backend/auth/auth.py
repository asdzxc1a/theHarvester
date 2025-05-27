import os
from datetime import datetime, timedelta, timezone # Ensure timezone is imported
from typing import Optional, Dict, Any
from jose import JWTError, jwt

from fastapi import Security, HTTPException, status
from fastapi.security.api_key import APIKeyHeader
from passlib.context import CryptContext

# Attempt to import settings, fallback to os.getenv for robustness
try:
    from veo_custom_video_app.config import settings as app_settings
except ImportError:
    app_settings = None # Will rely on getenv if settings.py is not found or structured differently


# --- Password Hashing Setup ---
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plain password against a hashed password."""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Hashes a plain password."""
    return pwd_context.hash(password)


# --- JWT Configuration & Utilities ---
# JWT Configuration Loader
# Fallback to environment variables if app_settings is not available or var is not in it.
# It's preferable for these to be explicitly set.

def get_jwt_secret_key() -> str:
    if app_settings and hasattr(app_settings, 'JWT_SECRET_KEY'):
        return app_settings.JWT_SECRET_KEY
    secret = os.getenv("JWT_SECRET_KEY")
    if not secret:
        print("WARNING: JWT_SECRET_KEY not found in settings or environment. Using insecure default.")
        return "insecure_default_dev_key_please_replace" 
    return secret

def get_jwt_algorithm() -> str:
    if app_settings and hasattr(app_settings, 'JWT_ALGORITHM'):
        return app_settings.JWT_ALGORITHM
    return os.getenv("JWT_ALGORITHM", "HS256")

def get_access_token_expire_minutes() -> int:
    if app_settings and hasattr(app_settings, 'JWT_ACCESS_TOKEN_EXPIRE_MINUTES'):
        return int(app_settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    return int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

SECRET_KEY = get_jwt_secret_key()
ALGORITHM = get_jwt_algorithm()
ACCESS_TOKEN_EXPIRE_MINUTES = get_access_token_expire_minutes()

def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


# --- API Key Authentication (Current) ---
# This section might be deprecated or used alongside JWT for different purposes.

# --- OAuth2 Password Bearer Scheme & User Dependencies ---
# This assumes your login endpoint (where tokens are issued) is available at /api/v1/auth/login
# The path is relative to the application root.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/login")

# Imports for get_current_user dependency
from sqlalchemy.orm import Session
from veo_custom_video_app.backend.database import get_db
from veo_custom_video_app.backend.app import models as db_models
# Import TokenData from routes.py (as established in previous steps)
# Ideally, schemas would be in their own module (e.g., api.schemas) to avoid potential circular imports.
from veo_custom_video_app.backend.api.routes import TokenData 


async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> db_models.User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: Optional[str] = payload.get("sub") # Changed to Optional[str] for safety
        if email is None:
            raise credentials_exception
        # TokenData schema can be used here if you need to validate more fields in the payload
        # For this case, checking 'sub' (email) is sufficient.
        # token_data = TokenData(email=email) 
    except JWTError:
        raise credentials_exception
    
    user = db.query(db_models.User).filter(db_models.User.email == email).first()
    if user is None:
        # This case means the token was valid, but the user it refers to doesn't exist.
        # This could happen if a user is deleted after a token is issued.
        raise credentials_exception 
    return user

async def get_current_active_user(current_user: db_models.User = Depends(get_current_user)) -> db_models.User:
    if not current_user.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user")
    return current_user


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
