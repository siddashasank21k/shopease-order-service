from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.core.security import get_current_user, require_admin
from app.schemas.order_schema import OrderCreate, OrderStatusUpdate, OrderResponse, PaginatedOrdersResponse
from app.services.order_service import OrderService

router = APIRouter(prefix="/api/orders", tags=["Orders"])

@router.post("/", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
def create_order(payload: OrderCreate, db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    return OrderService.create_order(db, user, payload)

@router.get("/", response_model=PaginatedOrdersResponse)
def list_orders(
    order_status: Optional[str] = Query(None),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    return OrderService.list_orders(db, user, order_status, start_date, end_date, page, page_size)

@router.get("/number/{order_number}", response_model=OrderResponse)
def get_order_by_number(order_number: str, db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    return OrderService.get_order_by_number(db, order_number, user)

@router.get("/{order_id}", response_model=OrderResponse)
def get_order(order_id: int, db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    return OrderService.get_order_by_id(db, order_id, user)

@router.patch("/{order_id}/status", response_model=OrderResponse)
def update_order_status(
    order_id: int,
    payload: OrderStatusUpdate,
    db: Session = Depends(get_db),
    admin: dict = Depends(require_admin),
):
    return OrderService.update_order_status(db, order_id, payload)

@router.post("/{order_id}/cancel", response_model=OrderResponse)
def cancel_order(order_id: int, db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    return OrderService.cancel_order(db, order_id, user)
