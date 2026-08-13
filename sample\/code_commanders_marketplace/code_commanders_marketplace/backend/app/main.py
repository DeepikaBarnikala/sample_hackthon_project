from collections import defaultdict
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from .config import settings
from .db import Base, engine, get_db
from .models import Commission, Dispute, Order, OrderItem, Product, SubOrder, User, Vendor
from .schemas import Checkout, DisputeCreate, DisputeUpdate, Login, OrderOut, ProductCreate, ProductOut, StatusUpdate, UserCreate, UserOut, VendorCreate, VendorOut
from .security import create_token, current_user, hash_password, require_roles, verify_password

app = FastAPI(title=settings.app_name, version="1.0.0")
origins = [x.strip() for x in settings.cors_origins.split(",")]
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)

@app.get("/")
def root(): return {"message": "Code Commanders Marketplace API", "docs": "/docs"}

@app.post("/api/auth/register", response_model=UserOut)
def register(data: UserCreate, db: Session = Depends(get_db)):
    if data.role not in {"customer", "vendor"}:
        raise HTTPException(400, "Role must be customer or vendor")
    if db.scalar(select(User).where(User.email == data.email.lower())):
        raise HTTPException(409, "Email already registered")
    user = User(email=data.email.lower(), password_hash=hash_password(data.password), full_name=data.full_name, role=data.role)
    db.add(user); db.commit(); db.refresh(user)
    if data.role == "vendor":
        db.add(Vendor(user_id=user.id, business_name=data.full_name + " Store", category="General", bank_details="MOCK-ACCOUNT")); db.commit()
    return user

@app.post("/api/auth/login")
def login(data: Login, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == data.email.lower()))
    if not user or not verify_password(data.password, user.password_hash): raise HTTPException(401, "Invalid email or password")
    return {"access_token": create_token(user), "user": UserOut.model_validate(user)}

@app.get("/api/me", response_model=UserOut)
def me(user: User = Depends(current_user)): return user

@app.post("/api/vendor/profile", response_model=VendorOut)
def vendor_profile(data: VendorCreate, user: User = Depends(require_roles("vendor")), db: Session = Depends(get_db)):
    vendor = user.vendor
    vendor.business_name, vendor.category, vendor.bank_details = data.business_name, data.category, data.bank_details
    db.commit(); db.refresh(vendor); return vendor

@app.get("/api/vendors", response_model=list[VendorOut])
def vendors(db: Session = Depends(get_db)): return list(db.scalars(select(Vendor)).all())

@app.post("/api/admin/vendors/{vendor_id}/approve", response_model=VendorOut)
def approve_vendor(vendor_id: int, admin: User = Depends(require_roles("admin")), db: Session = Depends(get_db)):
    vendor = db.get(Vendor, vendor_id)
    if not vendor: raise HTTPException(404, "Vendor not found")
    vendor.approved = True; db.commit(); db.refresh(vendor); return vendor

@app.post("/api/products", response_model=ProductOut)
def create_product(data: ProductCreate, user: User = Depends(require_roles("vendor")), db: Session = Depends(get_db)):
    vendor = user.vendor
    if not vendor or not vendor.approved: raise HTTPException(403, "Vendor must be approved before listing products")
    product = Product(vendor_id=vendor.id, **data.model_dump()); db.add(product); db.commit(); db.refresh(product); return product

@app.get("/api/products", response_model=list[ProductOut])
def products(search: str = "", category: str = "", db: Session = Depends(get_db)):
    q = select(Product).where(Product.is_active == True, Product.stock >= 0)
    if search: q = q.where(Product.name.ilike(f"%{search}%"))
    if category: q = q.where(Product.category == category)
    return list(db.scalars(q.order_by(Product.id.desc())).all())

@app.put("/api/products/{product_id}", response_model=ProductOut)
def update_product(product_id: int, data: ProductCreate, user: User = Depends(require_roles("vendor")), db: Session = Depends(get_db)):
    product = db.get(Product, product_id)
    if not product or product.vendor_id != user.vendor.id: raise HTTPException(404, "Product not found")
    for k, v in data.model_dump().items(): setattr(product, k, v)
    db.commit(); db.refresh(product); return product

@app.delete("/api/products/{product_id}")
def delete_product(product_id: int, user: User = Depends(require_roles("vendor")), db: Session = Depends(get_db)):
    product = db.get(Product, product_id)
    if not product or product.vendor_id != user.vendor.id: raise HTTPException(404, "Product not found")
    product.is_active = False; db.commit(); return {"message": "Product archived"}

@app.post("/api/orders/checkout", response_model=OrderOut)
def checkout(data: Checkout, user: User = Depends(require_roles("customer")), db: Session = Depends(get_db)):
    if not data.items: raise HTTPException(400, "Cart is empty")
    order = Order(customer_id=user.id, total_amount=0)
    db.add(order); db.flush()
    grouped = defaultdict(float)
    vendors_for_group = {}
    total = 0
    for item in data.items:
        product = db.get(Product, item.product_id)
        if not product or not product.is_active: raise HTTPException(404, f"Product {item.product_id} not found")
        if product.stock < item.quantity: raise HTTPException(400, f"Insufficient stock for {product.name}")
        subtotal = round(product.price * item.quantity, 2)
        product.stock -= item.quantity
        db.add(OrderItem(order_id=order.id, product_id=product.id, vendor_id=product.vendor_id, quantity=item.quantity, unit_price=product.price, subtotal=subtotal))
        grouped[product.vendor_id] += subtotal; vendors_for_group[product.vendor_id] = True; total += subtotal
    order.total_amount = round(total, 2)
    for vendor_id, vendor_total in grouped.items():
        sub = SubOrder(order_id=order.id, vendor_id=vendor_id, total=round(vendor_total, 2), status="pending")
        db.add(sub); db.flush()
        db.add(Commission(suborder_id=sub.id, vendor_id=vendor_id, rate=0.10, amount=round(vendor_total * 0.10, 2)))
    db.commit(); db.refresh(order); return order

@app.get("/api/orders/my", response_model=list[OrderOut])
def my_orders(user: User = Depends(require_roles("customer")), db: Session = Depends(get_db)):
    return list(db.scalars(select(Order).where(Order.customer_id == user.id).order_by(Order.id.desc())).all())

@app.get("/api/vendor/products", response_model=list[ProductOut])
def vendor_products(user: User = Depends(require_roles("vendor")), db: Session = Depends(get_db)):
    return list(db.scalars(select(Product).where(Product.vendor_id == user.vendor.id).order_by(Product.id.desc())).all())

@app.get("/api/vendor/orders")
def vendor_orders(user: User = Depends(require_roles("vendor")), db: Session = Depends(get_db)):
    vendor = user.vendor
    subs = list(db.scalars(select(SubOrder).where(SubOrder.vendor_id == vendor.id).order_by(SubOrder.id.desc())).all())
    return [{"id": s.id, "order_id": s.order_id, "total": s.total, "status": s.status} for s in subs]

@app.patch("/api/vendor/orders/{suborder_id}")
def update_suborder(suborder_id: int, data: StatusUpdate, user: User = Depends(require_roles("vendor")), db: Session = Depends(get_db)):
    allowed = {"pending", "processing", "shipped", "delivered", "cancelled"}
    if data.status not in allowed: raise HTTPException(400, "Invalid status")
    sub = db.get(SubOrder, suborder_id)
    if not sub or sub.vendor_id != user.vendor.id: raise HTTPException(404, "Sub-order not found")
    sub.status = data.status
    order = db.get(Order, sub.order_id)
    statuses = [x.status for x in order.suborders]
    order.status = "delivered" if statuses and all(x == "delivered" for x in statuses) else "processing"
    db.commit(); return {"message": "Status updated"}

@app.post("/api/disputes")
def create_dispute(data: DisputeCreate, user: User = Depends(require_roles("customer")), db: Session = Depends(get_db)):
    order = db.get(Order, data.order_id)
    if not order or order.customer_id != user.id: raise HTTPException(404, "Order not found")
    dispute = Dispute(customer_id=user.id, **data.model_dump()); db.add(dispute); db.commit(); db.refresh(dispute)
    return {"id": dispute.id, "status": dispute.status}

@app.get("/api/admin/disputes")
def admin_disputes(admin: User = Depends(require_roles("admin")), db: Session = Depends(get_db)):
    return list(db.scalars(select(Dispute).order_by(Dispute.id.desc())).all())

@app.patch("/api/admin/disputes/{dispute_id}")
def update_dispute(dispute_id: int, data: DisputeUpdate, admin: User = Depends(require_roles("admin")), db: Session = Depends(get_db)):
    dispute = db.get(Dispute, dispute_id)
    if not dispute: raise HTTPException(404, "Dispute not found")
    if data.status not in {"open", "investigating", "resolved", "rejected"}: raise HTTPException(400, "Invalid status")
    dispute.status, dispute.resolution = data.status, data.resolution; db.commit(); return {"message": "Dispute updated"}

@app.get("/api/admin/dashboard")
def admin_dashboard(admin: User = Depends(require_roles("admin")), db: Session = Depends(get_db)):
    gmv = db.scalar(select(func.coalesce(func.sum(Order.total_amount), 0.0))) or 0
    commission = db.scalar(select(func.coalesce(func.sum(Commission.amount), 0.0))) or 0
    vendors_count = db.scalar(select(func.count(Vendor.id))) or 0
    pending_vendors = db.scalar(select(func.count(Vendor.id)).where(Vendor.approved == False)) or 0
    orders_count = db.scalar(select(func.count(Order.id))) or 0
    vendor_rows = db.execute(select(Vendor.business_name, func.coalesce(func.sum(SubOrder.total), 0.0)).join(SubOrder, SubOrder.vendor_id == Vendor.id, isouter=True).group_by(Vendor.id)).all()
    return {"gmv": round(gmv,2), "commission": round(commission,2), "vendors": vendors_count, "pending_vendors": pending_vendors, "orders": orders_count, "vendor_sales": [{"vendor": n, "sales": round(v or 0,2)} for n,v in vendor_rows]}

@app.get("/api/vendor/summary")
def vendor_summary(user: User = Depends(require_roles("vendor")), db: Session = Depends(get_db)):
    vid = user.vendor.id
    sales = db.scalar(select(func.coalesce(func.sum(SubOrder.total), 0.0)).where(SubOrder.vendor_id == vid)) or 0
    commission = db.scalar(select(func.coalesce(func.sum(Commission.amount), 0.0)).where(Commission.vendor_id == vid)) or 0
    products_count = db.scalar(select(func.count(Product.id)).where(Product.vendor_id == vid, Product.is_active == True)) or 0
    return {"sales": round(sales,2), "commission": round(commission,2), "payout": round(sales-commission,2), "products": products_count}
