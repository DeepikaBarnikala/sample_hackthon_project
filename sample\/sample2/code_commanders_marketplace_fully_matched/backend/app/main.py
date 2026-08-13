from collections import defaultdict
from datetime import datetime, timedelta

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session, selectinload

from .config import settings
from .db import Base, SessionLocal, engine, get_db
from .models import Commission, Dispute, Order, OrderItem, PlatformSetting, Product, SubOrder, User, Vendor
from .schemas import (
    Checkout,
    CommissionRateUpdate,
    DisputeCreate,
    DisputeUpdate,
    Login,
    OrderOut,
    ProductCreate,
    ProductOut,
    StatusUpdate,
    UserCreate,
    UserOut,
    VendorAdminOut,
    VendorCreate,
    VendorPublicOut,
)
from .security import create_token, current_user, hash_password, require_roles, verify_password

app = FastAPI(title=settings.app_name, version="3.0.0")
origins = [x.strip() for x in settings.cors_origins.split(",") if x.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

STATUS_TRANSITIONS = {
    "pending": {"processing", "cancelled"},
    "processing": {"shipped", "cancelled"},
    "shipped": {"delivered"},
    "delivered": set(),
    "cancelled": set(),
}


@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        setting = db.scalar(select(PlatformSetting))
        if not setting:
            db.add(PlatformSetting(commission_rate=0.10))
            db.commit()
    finally:
        db.close()


def get_commission_rate(db: Session) -> float:
    setting = db.scalar(select(PlatformSetting))
    if not setting:
        setting = PlatformSetting(commission_rate=0.10)
        db.add(setting)
        db.commit()
        db.refresh(setting)
    return setting.commission_rate


def refresh_parent_order_status(order: Order):
    statuses = [sub.status for sub in order.suborders]
    if not statuses:
        order.status = "placed"
    elif all(status == "delivered" for status in statuses):
        order.status = "delivered"
    elif all(status == "cancelled" for status in statuses):
        order.status = "cancelled"
    else:
        order.status = "processing"


def ensure_admin(user: User):
    if user.role != "admin":
        raise HTTPException(403, "Admin access required")


@app.get("/")
def root():
    return {"message": "Code Commanders Marketplace API", "docs": "/docs", "version": "3.0.0"}


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.post("/api/auth/register", response_model=UserOut)
def register(data: UserCreate, db: Session = Depends(get_db)):
    if data.role not in {"customer", "vendor"}:
        raise HTTPException(400, "Only customer or vendor registration is allowed")
    email = data.email.strip().lower()
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(409, "Email already registered")
    user = User(email=email, password_hash=hash_password(data.password), full_name=data.full_name.strip(), role=data.role)
    db.add(user)
    db.flush()
    if data.role == "vendor":
        db.add(Vendor(user_id=user.id, business_name=f"{user.full_name} Store", category="General", bank_details="MOCK-ACCOUNT"))
    db.commit()
    db.refresh(user)
    return user


@app.post("/api/auth/login")
def login(data: Login, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == data.email.strip().lower()))
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(401, "Invalid email or password")
    return {"access_token": create_token(user), "user": UserOut.model_validate(user)}


@app.get("/api/me", response_model=UserOut)
def me(user: User = Depends(current_user)):
    return user


@app.get("/api/vendor/profile", response_model=VendorAdminOut)
def get_vendor_profile(user: User = Depends(require_roles("vendor")), db: Session = Depends(get_db)):
    if not user.vendor:
        raise HTTPException(404, "Vendor profile not found")
    return user.vendor


@app.post("/api/vendor/profile", response_model=VendorPublicOut)
def vendor_profile(data: VendorCreate, user: User = Depends(require_roles("vendor")), db: Session = Depends(get_db)):
    vendor = user.vendor
    if not vendor:
        raise HTTPException(404, "Vendor profile not found")
    vendor.business_name = data.business_name.strip()
    vendor.category = data.category.strip()
    vendor.bank_details = data.bank_details.strip()
    db.commit()
    db.refresh(vendor)
    return vendor


@app.get("/api/vendors", response_model=list[VendorPublicOut])
def vendors(db: Session = Depends(get_db)):
    return list(db.scalars(select(Vendor).order_by(Vendor.id)).all())


@app.get("/api/admin/vendors", response_model=list[VendorAdminOut])
def admin_vendors(_: User = Depends(require_roles("admin")), db: Session = Depends(get_db)):
    return list(db.scalars(select(Vendor).order_by(Vendor.approved, Vendor.id)).all())


@app.post("/api/admin/vendors/{vendor_id}/approve", response_model=VendorAdminOut)
def approve_vendor(vendor_id: int, _: User = Depends(require_roles("admin")), db: Session = Depends(get_db)):
    vendor = db.get(Vendor, vendor_id)
    if not vendor:
        raise HTTPException(404, "Vendor not found")
    vendor.approved = True
    db.commit()
    db.refresh(vendor)
    return vendor


@app.post("/api/products", response_model=ProductOut)
def create_product(data: ProductCreate, user: User = Depends(require_roles("vendor")), db: Session = Depends(get_db)):
    vendor = user.vendor
    if not vendor:
        raise HTTPException(404, "Vendor profile not found")
    if not vendor.approved:
        raise HTTPException(403, "Vendor must be approved before listing products")
    product = Product(vendor_id=vendor.id, **data.model_dump())
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


@app.get("/api/products", response_model=list[ProductOut])
def products(
    search: str = Query("", max_length=100),
    category: str = Query("", max_length=80),
    vendor_id: int | None = Query(None, ge=1),
    min_price: float | None = Query(None, ge=0),
    max_price: float | None = Query(None, ge=0),
    db: Session = Depends(get_db),
):
    if min_price is not None and max_price is not None and min_price > max_price:
        raise HTTPException(400, "min_price cannot exceed max_price")
    q = select(Product).join(Vendor).where(Product.is_active.is_(True), Product.stock >= 0, Vendor.approved.is_(True))
    if search.strip():
        term = f"%{search.strip()}%"
        q = q.where((Product.name.ilike(term)) | (Product.description.ilike(term)))
    if category.strip():
        q = q.where(Product.category == category.strip())
    if vendor_id:
        q = q.where(Product.vendor_id == vendor_id)
    if min_price is not None:
        q = q.where(Product.price >= min_price)
    if max_price is not None:
        q = q.where(Product.price <= max_price)
    return list(db.scalars(q.order_by(Product.id.desc())).all())


@app.get("/api/products/categories")
def product_categories(db: Session = Depends(get_db)):
    rows = db.scalars(
        select(Product.category).join(Vendor).where(Product.is_active.is_(True), Vendor.approved.is_(True)).distinct().order_by(Product.category)
    ).all()
    return list(rows)


@app.put("/api/products/{product_id}", response_model=ProductOut)
def update_product(product_id: int, data: ProductCreate, user: User = Depends(require_roles("vendor")), db: Session = Depends(get_db)):
    product = db.get(Product, product_id)
    if not product or not user.vendor or product.vendor_id != user.vendor.id:
        raise HTTPException(404, "Product not found")
    if not user.vendor.approved:
        raise HTTPException(403, "Vendor must be approved")
    for key, value in data.model_dump().items():
        setattr(product, key, value)
    db.commit()
    db.refresh(product)
    return product


@app.delete("/api/products/{product_id}")
def delete_product(product_id: int, user: User = Depends(require_roles("vendor")), db: Session = Depends(get_db)):
    product = db.get(Product, product_id)
    if not product or not user.vendor or product.vendor_id != user.vendor.id:
        raise HTTPException(404, "Product not found")
    product.is_active = False
    db.commit()
    return {"message": "Product archived"}


@app.post("/api/orders/checkout", response_model=OrderOut)
def checkout(data: Checkout, user: User = Depends(require_roles("customer")), db: Session = Depends(get_db)):
    quantities: dict[int, int] = defaultdict(int)
    for item in data.items:
        quantities[item.product_id] += item.quantity

    products_to_buy: list[tuple[Product, int]] = []
    grouped: dict[int, float] = defaultdict(float)
    total = 0.0

    for product_id, quantity in quantities.items():
        product = db.get(Product, product_id)
        if not product or not product.is_active:
            raise HTTPException(404, f"Product {product_id} is not available")
        vendor = db.get(Vendor, product.vendor_id)
        if not vendor or not vendor.approved:
            raise HTTPException(400, f"Vendor for {product.name} is not currently approved")
        if product.stock < quantity:
            raise HTTPException(400, f"Insufficient stock for {product.name}. Available: {product.stock}")
        products_to_buy.append((product, quantity))
        subtotal = round(product.price * quantity, 2)
        grouped[product.vendor_id] += subtotal
        total += subtotal

    if not products_to_buy:
        raise HTTPException(400, "Cart is empty")

    order = Order(customer_id=user.id, total_amount=round(total, 2), status="placed")
    db.add(order)
    db.flush()

    for product, quantity in products_to_buy:
        subtotal = round(product.price * quantity, 2)
        product.stock -= quantity
        db.add(OrderItem(
            order_id=order.id,
            product_id=product.id,
            vendor_id=product.vendor_id,
            quantity=quantity,
            unit_price=product.price,
            subtotal=subtotal,
        ))

    for vendor_id, vendor_total in grouped.items():
        db.add(SubOrder(order_id=order.id, vendor_id=vendor_id, total=round(vendor_total, 2), status="pending"))

    db.commit()
    order = db.scalar(
        select(Order).options(selectinload(Order.items), selectinload(Order.suborders)).where(Order.id == order.id)
    )
    return order


@app.get("/api/orders/my", response_model=list[OrderOut])
def my_orders(user: User = Depends(require_roles("customer")), db: Session = Depends(get_db)):
    q = (
        select(Order)
        .options(selectinload(Order.items), selectinload(Order.suborders))
        .where(Order.customer_id == user.id)
        .order_by(Order.id.desc())
    )
    return list(db.scalars(q).all())


@app.get("/api/vendor/products", response_model=list[ProductOut])
def vendor_products(user: User = Depends(require_roles("vendor")), db: Session = Depends(get_db)):
    if not user.vendor:
        raise HTTPException(404, "Vendor profile not found")
    return list(db.scalars(select(Product).where(Product.vendor_id == user.vendor.id).order_by(Product.id.desc())).all())


@app.get("/api/vendor/orders")
def vendor_orders(user: User = Depends(require_roles("vendor")), db: Session = Depends(get_db)):
    if not user.vendor:
        raise HTTPException(404, "Vendor profile not found")
    subs = list(
        db.scalars(
            select(SubOrder)
            .options(selectinload(SubOrder.order))
            .where(SubOrder.vendor_id == user.vendor.id)
            .order_by(SubOrder.id.desc())
        ).all()
    )
    return [
        {"id": s.id, "order_id": s.order_id, "total": s.total, "status": s.status, "customer_id": s.order.customer_id}
        for s in subs
    ]


@app.patch("/api/vendor/orders/{suborder_id}")
def update_suborder(suborder_id: int, data: StatusUpdate, user: User = Depends(require_roles("vendor")), db: Session = Depends(get_db)):
    allowed = set(STATUS_TRANSITIONS)
    if data.status not in allowed:
        raise HTTPException(400, "Invalid status")
    if not user.vendor:
        raise HTTPException(404, "Vendor profile not found")
    sub = db.get(SubOrder, suborder_id)
    if not sub or sub.vendor_id != user.vendor.id:
        raise HTTPException(404, "Sub-order not found")
    if data.status != sub.status and data.status not in STATUS_TRANSITIONS[sub.status]:
        raise HTTPException(400, f"Invalid transition: {sub.status} -> {data.status}")

    sub.status = data.status
    if data.status == "delivered" and not db.scalar(select(Commission).where(Commission.suborder_id == sub.id)):
        rate = get_commission_rate(db)
        db.add(Commission(suborder_id=sub.id, vendor_id=sub.vendor_id, rate=rate, amount=round(sub.total * rate, 2)))

    order = db.scalar(select(Order).options(selectinload(Order.suborders)).where(Order.id == sub.order_id))
    if order:
        refresh_parent_order_status(order)
    db.commit()
    return {"message": "Status updated", "status": data.status}


@app.post("/api/disputes")
def create_dispute(data: DisputeCreate, user: User = Depends(require_roles("customer")), db: Session = Depends(get_db)):
    order = db.scalar(select(Order).options(selectinload(Order.suborders)).where(Order.id == data.order_id, Order.customer_id == user.id))
    if not order:
        raise HTTPException(404, "Order not found")
    if data.vendor_id not in {sub.vendor_id for sub in order.suborders}:
        raise HTTPException(400, "Vendor is not part of this order")
    open_existing = db.scalar(
        select(Dispute).where(
            Dispute.order_id == data.order_id,
            Dispute.vendor_id == data.vendor_id,
            Dispute.customer_id == user.id,
            Dispute.status.in_(["open", "investigating"]),
        )
    )
    if open_existing:
        raise HTTPException(409, "An active dispute already exists for this vendor and order")
    dispute = Dispute(customer_id=user.id, **data.model_dump())
    db.add(dispute)
    db.commit()
    db.refresh(dispute)
    return {"id": dispute.id, "status": dispute.status}


@app.get("/api/disputes/my")
def my_disputes(user: User = Depends(require_roles("customer")), db: Session = Depends(get_db)):
    return list(db.scalars(select(Dispute).where(Dispute.customer_id == user.id).order_by(Dispute.id.desc())).all())


@app.get("/api/admin/disputes")
def admin_disputes(_: User = Depends(require_roles("admin")), db: Session = Depends(get_db)):
    return list(db.scalars(select(Dispute).order_by(Dispute.id.desc())).all())


@app.patch("/api/admin/disputes/{dispute_id}")
def update_dispute(dispute_id: int, data: DisputeUpdate, _: User = Depends(require_roles("admin")), db: Session = Depends(get_db)):
    if data.status not in {"open", "investigating", "resolved", "rejected"}:
        raise HTTPException(400, "Invalid dispute status")
    dispute = db.get(Dispute, dispute_id)
    if not dispute:
        raise HTTPException(404, "Dispute not found")
    if dispute.status in {"resolved", "rejected"} and data.status != dispute.status:
        raise HTTPException(400, "Closed disputes cannot be reopened")
    dispute.status = data.status
    dispute.resolution = data.resolution.strip()
    db.commit()
    return {"message": "Dispute updated", "status": dispute.status}


@app.get("/api/admin/commission-rate")
def admin_commission_rate(_: User = Depends(require_roles("admin")), db: Session = Depends(get_db)):
    return {"rate": get_commission_rate(db)}


@app.patch("/api/admin/commission-rate")
def update_commission_rate(data: CommissionRateUpdate, _: User = Depends(require_roles("admin")), db: Session = Depends(get_db)):
    setting = db.scalar(select(PlatformSetting))
    if not setting:
        setting = PlatformSetting(commission_rate=data.rate)
        db.add(setting)
    else:
        setting.commission_rate = data.rate
    db.commit()
    return {"rate": setting.commission_rate}


def vendor_sales_rows(db: Session):
    rows = db.execute(
        select(Vendor.id, Vendor.business_name, func.coalesce(func.sum(SubOrder.total), 0.0))
        .join(SubOrder, and_(SubOrder.vendor_id == Vendor.id, SubOrder.status == "delivered"), isouter=True)
        .group_by(Vendor.id)
        .order_by(Vendor.id)
    ).all()
    return [{"vendor_id": vid, "vendor": name, "sales": round(value or 0, 2)} for vid, name, value in rows]


@app.get("/api/admin/dashboard")
def admin_dashboard(_: User = Depends(require_roles("admin")), db: Session = Depends(get_db)):
    gmv = db.scalar(select(func.coalesce(func.sum(Order.total_amount), 0.0))) or 0
    completed_gmv = db.scalar(select(func.coalesce(func.sum(SubOrder.total), 0.0)).where(SubOrder.status == "delivered")) or 0
    commission = db.scalar(select(func.coalesce(func.sum(Commission.amount), 0.0))) or 0
    vendors_count = db.scalar(select(func.count(Vendor.id))) or 0
    pending_vendors = db.scalar(select(func.count(Vendor.id)).where(Vendor.approved.is_(False))) or 0
    orders_count = db.scalar(select(func.count(Order.id))) or 0
    completed_orders = db.scalar(select(func.count(func.distinct(SubOrder.order_id))).where(SubOrder.status == "delivered")) or 0
    disputes_open = db.scalar(select(func.count(Dispute.id)).where(Dispute.status.in_(["open", "investigating"]))) or 0
    return {
        "gmv": round(gmv, 2),
        "completed_gmv": round(completed_gmv, 2),
        "commission": round(commission, 2),
        "vendor_payout": round(completed_gmv - commission, 2),
        "vendors": vendors_count,
        "pending_vendors": pending_vendors,
        "orders": orders_count,
        "completed_orders": completed_orders,
        "open_disputes": disputes_open,
        "vendor_sales": vendor_sales_rows(db),
        "commission_rate": get_commission_rate(db),
    }


@app.get("/api/admin/reports/gmv-trend")
def gmv_trend(_: User = Depends(require_roles("admin")), db: Session = Depends(get_db)):
    today = datetime.utcnow().date()
    start = today - timedelta(days=6)
    rows = db.execute(
        select(func.date(Order.created_at), func.coalesce(func.sum(Order.total_amount), 0.0))
        .where(Order.created_at >= datetime.combine(start, datetime.min.time()))
        .group_by(func.date(Order.created_at))
        .order_by(func.date(Order.created_at))
    ).all()
    by_date = {str(day): round(value or 0, 2) for day, value in rows}
    return [{"date": str(start + timedelta(days=i)), "gmv": by_date.get(str(start + timedelta(days=i)), 0)} for i in range(7)]


@app.get("/api/admin/reports/commission")
def commission_report(_: User = Depends(require_roles("admin")), db: Session = Depends(get_db)):
    rows = db.execute(
        select(Commission.id, Commission.suborder_id, Commission.vendor_id, Vendor.business_name, Commission.rate, Commission.amount, Commission.created_at)
        .join(Vendor, Vendor.id == Commission.vendor_id)
        .order_by(Commission.id.desc())
    ).all()
    return [
        {
            "id": rid,
            "suborder_id": sid,
            "vendor_id": vid,
            "vendor": vendor,
            "rate": rate,
            "amount": round(amount, 2),
            "created_at": created_at,
        }
        for rid, sid, vid, vendor, rate, amount, created_at in rows
    ]


@app.get("/api/admin/reports/vendor-payouts")
def vendor_payout_report(_: User = Depends(require_roles("admin")), db: Session = Depends(get_db)):
    sales = {row["vendor_id"]: row for row in vendor_sales_rows(db)}
    commissions = db.execute(
        select(Commission.vendor_id, func.coalesce(func.sum(Commission.amount), 0.0)).group_by(Commission.vendor_id)
    ).all()
    commission_map = {vid: round(amount or 0, 2) for vid, amount in commissions}
    result = []
    for vendor in db.scalars(select(Vendor).order_by(Vendor.id)).all():
        completed_sales = sales.get(vendor.id, {}).get("sales", 0)
        commission = commission_map.get(vendor.id, 0)
        result.append({
            "vendor_id": vendor.id,
            "vendor": vendor.business_name,
            "completed_sales": completed_sales,
            "commission": commission,
            "payout": round(completed_sales - commission, 2),
        })
    return result


@app.get("/api/vendor/summary")
def vendor_summary(user: User = Depends(require_roles("vendor")), db: Session = Depends(get_db)):
    if not user.vendor:
        raise HTTPException(404, "Vendor profile not found")
    vid = user.vendor.id
    completed_sales = db.scalar(select(func.coalesce(func.sum(SubOrder.total), 0.0)).where(SubOrder.vendor_id == vid, SubOrder.status == "delivered")) or 0
    commission = db.scalar(select(func.coalesce(func.sum(Commission.amount), 0.0)).where(Commission.vendor_id == vid)) or 0
    pending_sales = db.scalar(select(func.coalesce(func.sum(SubOrder.total), 0.0)).where(SubOrder.vendor_id == vid, SubOrder.status.not_in(["delivered", "cancelled"]))) or 0
    products_count = db.scalar(select(func.count(Product.id)).where(Product.vendor_id == vid, Product.is_active.is_(True))) or 0
    return {
        "completed_sales": round(completed_sales, 2),
        "commission": round(commission, 2),
        "payout": round(completed_sales - commission, 2),
        "pending_sales": round(pending_sales, 2),
        "products": products_count,
        "commission_rate": get_commission_rate(db),
        "approved": user.vendor.approved,
    }
