from datetime import datetime
from decimal import Decimal
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from app.schemas.order_item_schema import OrderItemCreate, OrderItemResponse

class OrderCreate(BaseModel):
    items: List[OrderItemCreate] = Field(..., min_length=1)
    shipping_address_id: int = Field(..., gt=0)
    notes: Optional[str] = Field(None, max_length=500)

class OrderStatusUpdate(BaseModel):
    order_status: str = Field(..., pattern="^(PENDING|CONFIRMED|PROCESSING|SHIPPED|DELIVERED|CANCELLED)$")

class OrderResponse(BaseModel):
    id: int
    order_number: str
    user_id: int
    shipping_address: Dict[str, Any]
    subtotal: Decimal
    discount_amount: Decimal
    shipping_charge: Decimal
    tax_amount: Decimal
    total_amount: Decimal
    order_status: str
    payment_status: str
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime
    items: List[OrderItemResponse]

    class Config:
        from_attributes = True

class PaginatedOrdersResponse(BaseModel):
    total: int
    page: int
    page_size: int
    total_pages: int
    items: List[OrderResponse]
