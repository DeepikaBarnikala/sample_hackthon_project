from sqlalchemy import select

from .db import Base, SessionLocal, engine
from .models import Product, User, Vendor
from .security import hash_password

Base.metadata.create_all(bind=engine)
db = SessionLocal()

try:
    def get_or_create_user(email, password, name, role):
        user = db.scalar(select(User).where(User.email == email))
        if not user:
            user = User(email=email, password_hash=hash_password(password), full_name=name, role=role)
            db.add(user)
            db.flush()
        return user

    admin = get_or_create_user("admin@codecommanders.local", "Admin@123", "Platform Admin", "admin")
    customer = get_or_create_user("customer@codecommanders.local", "Customer@123", "Demo Customer", "customer")
    vendor1_user = get_or_create_user("vendor@codecommanders.local", "Vendor@123", "Demo Vendor", "vendor")
    vendor2_user = get_or_create_user("vendor2@codecommanders.local", "Vendor2@123", "Fashion Vendor", "vendor")

    vendor1 = db.scalar(select(Vendor).where(Vendor.user_id == vendor1_user.id))
    if not vendor1:
        vendor1 = Vendor(user_id=vendor1_user.id, business_name="Demo Electronics Store", category="Electronics", bank_details="MOCK-1234", approved=True)
        db.add(vendor1)
        db.flush()
    else:
        vendor1.approved = True

    vendor2 = db.scalar(select(Vendor).where(Vendor.user_id == vendor2_user.id))
    if not vendor2:
        vendor2 = Vendor(user_id=vendor2_user.id, business_name="Demo Fashion Store", category="Fashion", bank_details="MOCK-5678", approved=True)
        db.add(vendor2)
        db.flush()
    else:
        vendor2.approved = True

    products = [
        (vendor1.id, "Wireless Headphones", "Bluetooth over-ear headphones", 2499, 25, "Electronics"),
        (vendor1.id, "Mechanical Keyboard", "RGB mechanical keyboard", 3499, 15, "Electronics"),
        (vendor1.id, "USB-C Hub", "7-in-1 USB-C hub", 1499, 40, "Accessories"),
        (vendor2.id, "Classic Hoodie", "Comfortable cotton-blend hoodie", 1799, 30, "Fashion"),
        (vendor2.id, "Running Shoes", "Lightweight everyday running shoes", 2999, 20, "Fashion"),
    ]
    for vendor_id, name, description, price, stock, category in products:
        exists = db.scalar(select(Product).where(Product.vendor_id == vendor_id, Product.name == name))
        if not exists:
            db.add(Product(vendor_id=vendor_id, name=name, description=description, price=price, stock=stock, category=category))

    db.commit()
    print("Seed complete: 1 admin, 1 customer, 2 approved vendors, 5 products")
finally:
    db.close()
