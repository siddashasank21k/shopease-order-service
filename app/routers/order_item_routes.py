from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.core.security import get_current_user
from app.schemas.order_item_schema import OrderItemResponse
from app.services.order_service import OrderService

router = APIRouter(prefix="/api/orders", tags=["Order Items"])

@router.get("/{order_id}/items", response_model=List[OrderItemResponse])
def get_order_items(order_id: int, db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    order = OrderService.get_order_by_id(db, order_id, user)
    return order.items
