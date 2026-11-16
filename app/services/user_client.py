import httpx
from typing import Dict, Any
from fastapi import HTTPException, status
from app.core.config import settings

class UserServiceClient:
    @staticmethod
    def get_verified_address(address_id: int, user_token: str) -> Dict[str, Any]:
        url = f"{settings.USER_SERVICE_URL}/api/users/addresses/{address_id}"
        headers = {"Authorization": f"Bearer {user_token}"}
        try:
            with httpx.Client(timeout=5.0) as client:
                resp = client.get(url, headers=headers)
        except httpx.RequestError:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="User Management Service is currently unavailable.",
            )

        if resp.status_code == 404:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Shipping address ID {address_id} not found or does not belong to the authenticated user.",
            )
        if resp.status_code in (401, 403):
            raise HTTPException(
                status_code=resp.status_code,
                detail="Unauthorized to access the requested shipping address.",
            )
        if resp.status_code >= 400:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Error validating shipping address with User Management Service.",
            )

        return resp.json()
