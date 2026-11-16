import time
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from app.core.config import settings
from app.database.connection import engine, Base
from app.models.order_model import Order
from app.models.order_item_model import OrderItem
from app.routers import order_routes, order_item_routes

logger = logging.getLogger("uvicorn")

@asynccontextmanager
async def lifespan(app: FastAPI):
    for attempt in range(1, 16):
        try:
            logger.info(f"Connecting to MySQL database (attempt {attempt}/15)...")
            Base.metadata.create_all(bind=engine)
            logger.info("Order Management database connected and schema initialized.")
            break
        except Exception as e:
            logger.warning(f"Database waiting: {e}. Retrying in 2s...")
            time.sleep(2)
    yield

app = FastAPI(
    title=settings.APP_NAME,
    description="Independent microservice managing customer orders, pricing calculation, status transitions, and Saga inventory orchestration.",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(order_routes.router)
app.include_router(order_item_routes.router)

@app.get("/health", tags=["Health"])
def health():
    return JSONResponse(status_code=200, content={"status": "healthy", "service": settings.APP_NAME})
