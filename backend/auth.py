"""
Simplified authentication for development - NO HASHING for training data.
This is for ML development only, not production!
"""

from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from fastapi import HTTPException, status, Depends
from fastapi.security import OAuth2PasswordBearer
import logging

logger = logging.getLogger(__name__)

# ========== SIMPLE PASSWORD HANDLING (NO HASHING) ==========
# For ML training data only - we don't need real authentication

def get_password_hash(password: str) -> str:
    """
    Ultra-simple password "hashing" for ML data generation.
    Just returns the password as-is - DO NOT USE IN PRODUCTION!
    """
    logger.warning("⚠️ Using PLAIN TEXT password storage - FOR ML TRAINING ONLY")
    return password  # Just return the plain password

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Simple string comparison for ML data.
    """
    return plain_password == hashed_password

# ========== JWT TOKEN HANDLING (Keep for API) ==========
SECRET_KEY = "your-secret-key-change-this-in-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create a JWT access token"""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme)):
    """Extract username from JWT token"""
    if not token:
        return None
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        return username
    except JWTError:
        return None