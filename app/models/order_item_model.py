from datetime import datetime
from sqlalchemy import Column, Integer, String, Numeric, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.database.connection import Base

class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    order_id = Column(Integer, ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id = Column(Integer, nullable=False)
    product_name = Column(String(200), nullable=False)
    sku = Column(String(100), nullable=False)
    unit_price = Column(Numeric(12, 2), nullable=False)
    quantity = Column(Integer, nullable=False)
    discount_amount = Column(Numeric(12, 2), default=0.00, nullable=False)
    total_price = Column(Numeric(12, 2), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    order = relationship("Order", back_populates="items")
