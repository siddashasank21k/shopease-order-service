from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, Numeric, DateTime, JSON, Boolean
from sqlalchemy.orm import relationship
from app.database.connection import Base

class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    order_number = Column(String(50), unique=True, nullable=False, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    shipping_address = Column(JSON, nullable=False)
    subtotal = Column(Numeric(12, 2), nullable=False)
    discount_amount = Column(Numeric(12, 2), default=0.00, nullable=False)
    shipping_charge = Column(Numeric(12, 2), default=0.00, nullable=False)
    tax_amount = Column(Numeric(12, 2), default=0.00, nullable=False)
    total_amount = Column(Numeric(12, 2), nullable=False)
    order_status = Column(String(30), default="PENDING", nullable=False, index=True)
    payment_status = Column(String(30), default="PENDING", nullable=False)
    inventory_restored = Column(Boolean, default=False, nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
