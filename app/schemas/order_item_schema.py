from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, Field

class OrderItemCreate(BaseModel):
    product_id: int = Field(..., gt=0)
    quantity: int = Field(..., gt=0)

class OrderItemResponse(BaseModel):
    id: int
    order_id: int
    product_id: int
    product_name: str
    sku: str
    unit_price: Decimal
    quantity: int
    discount_amount: Decimal
    total_price: Decimal
    created_at: datetime

    class Config:
        from_attributes = True
