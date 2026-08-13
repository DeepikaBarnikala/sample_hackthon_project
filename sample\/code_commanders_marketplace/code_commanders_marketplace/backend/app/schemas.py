from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field

class UserCreate(BaseModel):
    email: str
    password: str = Field(min_length=6)
    full_name: str
    role: str = "customer"

class Login(BaseModel):
    email: str
    password: str

class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int; email: str; full_name: str; role: str

class VendorCreate(BaseModel):
    business_name: str
    category: str
    bank_details: str = "MOCK-ACCOUNT"

class VendorOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int; user_id: int; business_name: str; category: str; bank_details: str; approved: bool

class ProductCreate(BaseModel):
    name: str
    description: str = ""
    price: float = Field(gt=0)
    stock: int = Field(ge=0)
    category: str

class ProductOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int; vendor_id: int; name: str; description: str; price: float; stock: int; category: str; is_active: bool

class CartItem(BaseModel):
    product_id: int
    quantity: int = Field(gt=0)

class Checkout(BaseModel):
    items: list[CartItem]

class SubOrderOut(BaseModel):
    id: int; vendor_id: int; total: float; status: str

class OrderOut(BaseModel):
    id: int; total_amount: float; status: str; created_at: datetime; suborders: list[SubOrderOut]

class StatusUpdate(BaseModel):
    status: str

class DisputeCreate(BaseModel):
    order_id: int
    vendor_id: int
    reason: str
    description: str

class DisputeUpdate(BaseModel):
    status: str
    resolution: str = ""
