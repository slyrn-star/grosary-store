from typing import Literal, Optional
from pydantic import BaseModel, EmailStr, Field


class SignupIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    email: EmailStr
    password: str = Field(min_length=6, max_length=64)


class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(max_length=64)


class CartChangeIn(BaseModel):
    product_id: str
    change: int = Field(description="+1 to add, -1 to remove one")


class OrderIn(BaseModel):
    payment_method: Literal["COD"] = "COD"
    delivery_address: Optional[str] = Field(default=None, max_length=300)
    phone: Optional[str] = Field(default=None, max_length=20)


class ProductIn(BaseModel):
    name: str
    category: str
    price: float = Field(ge=0)
    unit: str
    stock: int = Field(ge=0)
    image: str = ""
    emoji: str = ""
    description: str = ""
    is_active: bool = True


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    price: Optional[float] = Field(default=None, ge=0)
    unit: Optional[str] = None
    stock: Optional[int] = Field(default=None, ge=0)
    image: Optional[str] = None
    emoji: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


class StockIn(BaseModel):
    stock: int = Field(ge=0)


class OrderStatusIn(BaseModel):
    status: Literal["confirmed", "out_for_delivery", "delivered", "cancelled"]


class ActiveIn(BaseModel):
    is_active: bool


class CompanyIn(BaseModel):
    name: str
    address: str = ""
    phone: str = ""
    email: str = ""
    currency: str = "INR"
    delivery_fee: float = Field(default=0, ge=0)
    opening_hours: str = ""
    settings: dict = {}