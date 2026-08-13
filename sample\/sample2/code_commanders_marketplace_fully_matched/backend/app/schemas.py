from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class UserCreate(BaseModel):
    email: str
    password: str = Field(min_length=8)
    full_name: str = Field(min_length=2, max_length=120)
    role: str = "customer"

    @field_validator("email")
    @classmethod
    def valid_email(cls, value: str) -> str:
        value = value.strip().lower()
        if "@" not in value or "." not in value.rsplit("@", 1)[-1]:
            raise ValueError("Enter a valid email address")
        return value


class Login(BaseModel):
    email: str
    password: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    email: str
    full_name: str
    role: str


class VendorCreate(BaseModel):
    business_name: str = Field(min_length=2, max_length=160)
    category: str = Field(min_length=2, max_length=80)
    bank_details: str = Field(default="MOCK-ACCOUNT", min_length=3, max_length=255)


class VendorPublicOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    user_id: int
    business_name: str
    category: str
    approved: bool


class VendorAdminOut(VendorPublicOut):
    bank_details: str


class ProductCreate(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    description: str = Field(default="", max_length=2000)
    price: float = Field(gt=0, le=10_000_000)
    stock: int = Field(ge=0, le=10_000_000)
    category: str = Field(min_length=2, max_length=80)


class ProductOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    vendor_id: int
    name: str
    description: str
    price: float
    stock: int
    category: str
    is_active: bool


class CartItem(BaseModel):
    product_id: int
    quantity: int = Field(gt=0, le=1000)


class Checkout(BaseModel):
    items: list[CartItem] = Field(min_length=1, max_length=100)


class OrderItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    product_id: int
    vendor_id: int
    quantity: int
    unit_price: float
    subtotal: float


class SubOrderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    vendor_id: int
    total: float
    status: str


class OrderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    total_amount: float
    status: str
    created_at: datetime
    items: list[OrderItemOut]
    suborders: list[SubOrderOut]


class StatusUpdate(BaseModel):
    status: str


class DisputeCreate(BaseModel):
    order_id: int
    vendor_id: int
    reason: str = Field(min_length=2, max_length=120)
    description: str = Field(min_length=5, max_length=2000)


class DisputeUpdate(BaseModel):
    status: str
    resolution: str = Field(default="", max_length=2000)


class CommissionRateUpdate(BaseModel):
    rate: float = Field(ge=0, le=1)
