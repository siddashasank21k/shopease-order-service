from typing import Any, Dict, List
from datetime import datetime, timedelta
from jose import JWTError, jwt
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.core.config import settings

security_scheme = HTTPBearer(auto_error=False)

def decode_access_token(token: str) -> Dict[str, Any]:
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security_scheme)) -> Dict[str, Any]:
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Bearer authentication token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    payload = decode_access_token(credentials.credentials)
    user_id = payload.get("user_id") or payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing user identity.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return {
        "user_id": int(user_id),
        "role": payload.get("role", "customer").lower(),
        "raw_token": credentials.credentials,
    }

def require_role(allowed_roles: List[str]):
    def checker(user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
        if user["role"] not in [r.lower() for r in allowed_roles]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{user['role']}' is not authorized for this action.",
            )
        return user
    return checker

require_admin = require_role(["admin", "superadmin"])

def generate_service_admin_token() -> str:
    """Generates a short-lived service-to-service admin JWT for authorized inventory reservation/restoration."""
    payload = {
        "sub": "0",
        "user_id": 0,
        "role": "admin",
        "service": "order-service",
        "exp": datetime.utcnow() + timedelta(minutes=5),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
