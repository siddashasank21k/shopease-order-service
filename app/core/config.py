from decimal import Decimal
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    APP_NAME: str = "ShopEase Order Management Service"
    ENVIRONMENT: str = "development"
    PORT: int = 8004
    DATABASE_URL: str
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    USER_SERVICE_URL: str = "http://host.docker.internal:8002"
    PRODUCT_SERVICE_URL: str = "http://host.docker.internal:8003"
    TAX_RATE: Decimal = Decimal("0.18")
    FLAT_SHIPPING_CHARGE: Decimal = Decimal("50.00")
    FREE_SHIPPING_THRESHOLD: Decimal = Decimal("1000.00")

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
