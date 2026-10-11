import hashlib
import secrets
import json
import base64
import time
from typing import Optional
from fastapi import Depends, HTTPException, status, Header
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.models import User
from backend.config import settings

def hash_password(password: str) -> str:
    """Hashes a password using PBKDF2 HMAC SHA-256 with a unique salt."""
    salt = secrets.token_hex(16)
    key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100000)
    return f"{salt}${key.hex()}"

def verify_password(password: str, hashed: str) -> bool:
    """Verifies a password against the stored salt$hash format."""
    try:
        salt, key_hex = hashed.split("$")
        key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100000)
        return secrets.compare_digest(key.hex(), key_hex)
    except Exception:
        return False

def create_access_token(data: dict, expires_in_seconds: int = 86400) -> str:
    """Creates a signed token containing payload, expiration, and HMAC signature."""
    payload = data.copy()
    payload["exp"] = int(time.time()) + expires_in_seconds
    raw_json = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    payload_b64 = base64.urlsafe_b64encode(raw_json).decode("utf-8").rstrip("=")
    
    sig = hashlib.sha256(f"{payload_b64}:{settings.SECRET_KEY}".encode("utf-8")).hexdigest()
    return f"{payload_b64}.{sig}"

def decode_access_token(token: str) -> Optional[dict]:
    """Validates signature and expiration of a token."""
    try:
        parts = token.split(".")
        if len(parts) != 2:
            return None
        payload_b64, sig = parts
        expected_sig = hashlib.sha256(f"{payload_b64}:{settings.SECRET_KEY}".encode("utf-8")).hexdigest()
        if not secrets.compare_digest(sig, expected_sig):
            return None
        
        # Add padding back if necessary
        padded = payload_b64 + "=" * (-len(payload_b64) % 4)
        raw_json = base64.urlsafe_b64decode(padded.encode("utf-8"))
        payload = json.loads(raw_json.decode("utf-8"))
        if payload.get("exp", 0) < int(time.time()):
            return None # Expired
        return payload
    except Exception:
        return None

def get_current_user(authorization: Optional[str] = Header(None), db: Session = Depends(get_db)) -> User:
    """FastAPI dependency to extract and authenticate current user from Bearer header."""
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header missing"
        )
    
    token = authorization.replace("Bearer ", "").strip()
    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )
    
    user = db.query(User).filter(User.username == payload["sub"]).first()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive"
        )
    return user

def require_role(*allowed_roles: str):
    """Enforces specific roles on endpoints."""
    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if "admin" in allowed_roles and current_user.role == "admin":
            return current_user # Admin always has access
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access forbidden: requires one of {allowed_roles}"
            )
        return current_user
    return role_checker

