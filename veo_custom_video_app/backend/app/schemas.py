from typing import Optional, List # List might be needed for future User schema relationships
from pydantic import BaseModel, EmailStr

# --- Token Schemas ---
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[EmailStr] = None # Changed to EmailStr for validation
    # Add other fields like user_id, roles if they are part of your JWT payload

# --- User Schemas ---
class UserBase(BaseModel):
    email: EmailStr
    full_name: Optional[str] = None

class UserCreate(UserBase):
    password: str

class User(UserBase):
    id: int
    is_active: bool
    # Example of a relationship field, ensure Vision schema is also moved or accessible if used
    # visions: List['Vision'] = [] # Forward reference if Vision is in the same file or imported later

    class Config:
        orm_mode = True
