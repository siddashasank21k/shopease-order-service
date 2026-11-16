import httpx
from typing import Dict, Any
from fastapi import HTTPException, status
from app.core.config import settings
from app.core.security import generate_service_admin_token

class ProductServiceClient:
    @staticmethod
    def get_product(product_id: int) -> Dict[str, Any]:
        url = f"{settings.PRODUCT_SERVICE_URL}/api/products/{product_id}"
        try:
            with httpx.Client(timeout=5.0) as client:
                resp = client.get(url)
        except httpx.RequestError:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Product Catalog Service is currently unavailable.",
            )

        if resp.status_code == 404:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Product ID {product_id} does not exist or is inactive.",
            )
        if resp.status_code >= 400:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Failed to retrieve product {product_id} from Product Catalog Service.",
            )
        return resp.json()

    @staticmethod
    def reserve_stock(product_id: int, quantity: int, order_ref: str) -> None:
        url = f"{settings.PRODUCT_SERVICE_URL}/api/inventory/{product_id}/stock-out"
        admin_token = generate_service_admin_token()
        headers = {"Authorization": f"Bearer {admin_token}"}
        payload = {"quantity": quantity, "remarks": f"Order Reservation [{order_ref}]"}

        try:
            with httpx.Client(timeout=5.0) as client:
                resp = client.post(url, json=payload, headers=headers)
        except httpx.RequestError:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Product Catalog Service unavailable during stock reservation.",
            )

        if resp.status_code == 400:
            detail = resp.json().get("detail", "Insufficient stock.")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)
        if resp.status_code >= 400:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Stock reservation failed for product {product_id}.",
            )

    @staticmethod
    def restore_stock(product_id: int, quantity: int, order_ref: str) -> None:
        url = f"{settings.PRODUCT_SERVICE_URL}/api/inventory/{product_id}/stock-in"
        admin_token = generate_service_admin_token()
        headers = {"Authorization": f"Bearer {admin_token}"}
        payload = {"quantity": quantity, "remarks": f"Order Cancellation Restoration [{order_ref}]"}

        try:
            with httpx.Client(timeout=5.0) as client:
                resp = client.post(url, json=payload, headers=headers)
        except httpx.RequestError:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Product Catalog Service unavailable during stock restoration.",
            )

        if resp.status_code >= 400:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Failed to restore stock for product {product_id}.",
            )
