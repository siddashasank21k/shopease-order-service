import uuid
from math import ceil
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.core.config import settings
from app.models.order_model import Order
from app.models.order_item_model import OrderItem
from app.schemas.order_schema import OrderCreate, OrderStatusUpdate, PaginatedOrdersResponse, OrderResponse
from app.services.user_client import UserServiceClient
from app.services.product_client import ProductServiceClient

ALLOWED_TRANSITIONS = {
    "PENDING": {"CONFIRMED", "CANCELLED"},
    "CONFIRMED": {"PROCESSING", "CANCELLED"},
    "PROCESSING": {"SHIPPED", "CANCELLED"},
    "SHIPPED": {"DELIVERED"},
    "DELIVERED": set(),
    "CANCELLED": set(),
}

class OrderService:
    @staticmethod
    def _quantize(val: Decimal) -> Decimal:
        return val.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    @staticmethod
    def create_order(db: Session, user: Dict[str, Any], payload: OrderCreate) -> Order:
        # 1. Validate shipping address ownership via User Management Service
        address_snapshot = UserServiceClient.get_verified_address(
            payload.shipping_address_id, user["raw_token"]
        )

        # 2. Aggregate quantities per product_id in case duplicate IDs are submitted
        aggregated_qty: Dict[int, int] = {}
        for item in payload.items:
            aggregated_qty[item.product_id] = aggregated_qty.get(item.product_id, 0) + item.quantity

        # 3. Fetch product snapshots & verify availability/stock
        order_number = f"ORD-{datetime.utcnow().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
        prepared_items = []
        subtotal = Decimal("0.00")
        total_discount = Decimal("0.00")

        for prod_id, qty in aggregated_qty.items():
            product = ProductServiceClient.get_product(prod_id)
            if not product.get("is_active", False):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Product '{product.get('name')}' is currently inactive.",
                )
            available_stock = int(product.get("stock_quantity", 0))
            if available_stock < qty:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Insufficient stock for '{product.get('name')}'. Available: {available_stock}, Requested: {qty}.",
                )

            base_price = Decimal(str(product["price"]))
            disc_price = Decimal(str(product["discount_price"])) if product.get("discount_price") is not None else base_price
            item_discount_unit = max(Decimal("0.00"), base_price - disc_price)

            item_subtotal = OrderService._quantize(base_price * qty)
            item_discount_total = OrderService._quantize(item_discount_unit * qty)
            item_final = OrderService._quantize(item_subtotal - item_discount_total)

            subtotal += item_subtotal
            total_discount += item_discount_total

            prepared_items.append({
                "product_id": prod_id,
                "product_name": product["name"],
                "sku": product["sku"],
                "unit_price": base_price,
                "quantity": qty,
                "discount_amount": item_discount_total,
                "total_price": item_final,
            })

        # 4. Calculate taxes and shipping on the backend
        net_after_discount = subtotal - total_discount
        tax_amount = OrderService._quantize(net_after_discount * settings.TAX_RATE)
        shipping_charge = (
            Decimal("0.00")
            if net_after_discount >= settings.FREE_SHIPPING_THRESHOLD
            else OrderService._quantize(settings.FLAT_SHIPPING_CHARGE)
        )
        total_amount = OrderService._quantize(net_after_discount + tax_amount + shipping_charge)

        # 5. Saga Step A: Reserve stock across Product Catalog Service with rollback compensation
        reserved_records = []
        try:
            for item_data in prepared_items:
                ProductServiceClient.reserve_stock(
                    item_data["product_id"], item_data["quantity"], order_number
                )
                reserved_records.append((item_data["product_id"], item_data["quantity"]))
        except Exception as exc:
            # Compensate already reserved items
            for r_prod_id, r_qty in reserved_records:
                try:
                    ProductServiceClient.restore_stock(r_prod_id, r_qty, f"ROLLBACK-{order_number}")
                except Exception:
                    pass
            raise exc

        # 6. Saga Step B: Persist local Order & OrderItems atomically
        try:
            new_order = Order(
                order_number=order_number,
                user_id=user["user_id"],
                shipping_address=address_snapshot,
                subtotal=subtotal,
                discount_amount=total_discount,
                shipping_charge=shipping_charge,
                tax_amount=tax_amount,
                total_amount=total_amount,
                order_status="PENDING",
                payment_status="PENDING",
                inventory_restored=False,
                notes=payload.notes,
            )
            db.add(new_order)
            db.flush()

            for item_data in prepared_items:
                db.add(OrderItem(order_id=new_order.id, **item_data))

            db.commit()
            db.refresh(new_order)
            return new_order
        except Exception as db_exc:
            db.rollback()
            # Compensate stock reservations because local DB persistence failed
            for r_prod_id, r_qty in reserved_records:
                try:
                    ProductServiceClient.restore_stock(r_prod_id, r_qty, f"DB-FAIL-{order_number}")
                except Exception:
                    pass
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to save order locally: {str(db_exc)}",
            )

    @staticmethod
    def list_orders(
        db: Session,
        user: Dict[str, Any],
        status_filter: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        page: int = 1,
        page_size: int = 10,
    ) -> PaginatedOrdersResponse:
        q = db.query(Order)
        if user["role"] not in ("admin", "superadmin"):
            q = q.filter(Order.user_id == user["user_id"])

        if status_filter:
            q = q.filter(Order.order_status == status_filter.upper())
        if start_date:
            q = q.filter(Order.created_at >= start_date)
        if end_date:
            q = q.filter(Order.created_at <= end_date)

        total = q.count()
        items = q.order_by(Order.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
        total_pages = ceil(total / page_size) if total > 0 else 0

        return PaginatedOrdersResponse(
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            items=[OrderResponse.model_validate(o) for o in items],
        )

    @staticmethod
    def get_order_by_id(db: Session, order_id: int, user: Dict[str, Any]) -> Order:
        order = db.query(Order).filter(Order.id == order_id).first()
        if not order:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Order ID {order_id} not found.")
        if user["role"] not in ("admin", "superadmin") and order.user_id != user["user_id"]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied to this order.")
        return order

    @staticmethod
    def get_order_by_number(db: Session, order_number: str, user: Dict[str, Any]) -> Order:
        order = db.query(Order).filter(Order.order_number == order_number).first()
        if not order:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Order '{order_number}' not found.")
        if user["role"] not in ("admin", "superadmin") and order.user_id != user["user_id"]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied to this order.")
        return order

    @staticmethod
    def update_order_status(db: Session, order_id: int, payload: OrderStatusUpdate) -> Order:
        order = db.query(Order).filter(Order.id == order_id).with_for_update().first()
        if not order:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Order ID {order_id} not found.")

        new_status = payload.order_status.upper()
        current_status = order.order_status.upper()

        if new_status == current_status:
            return order

        if new_status not in ALLOWED_TRANSITIONS.get(current_status, set()):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status transition from '{current_status}' to '{new_status}'.",
            )

        if new_status == "CANCELLED" and not order.inventory_restored:
            for item in order.items:
                ProductServiceClient.restore_stock(item.product_id, item.quantity, order.order_number)
            order.inventory_restored = True

        order.order_status = new_status
        db.commit()
        db.refresh(order)
        return order

    @staticmethod
    def cancel_order(db: Session, order_id: int, user: Dict[str, Any]) -> Order:
        order = db.query(Order).filter(Order.id == order_id).with_for_update().first()
        if not order:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Order ID {order_id} not found.")

        if user["role"] not in ("admin", "superadmin") and order.user_id != user["user_id"]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot cancel another user's order.")

        # Idempotent return if already cancelled
        if order.order_status == "CANCELLED":
            return order

        if order.order_status in ("SHIPPED", "DELIVERED"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot cancel order in '{order.order_status}' status.",
            )

        # Idempotent inventory restoration guard
        if not order.inventory_restored:
            for item in order.items:
                ProductServiceClient.restore_stock(item.product_id, item.quantity, order.order_number)
            order.inventory_restored = True

        order.order_status = "CANCELLED"
        db.commit()
        db.refresh(order)
        return order
