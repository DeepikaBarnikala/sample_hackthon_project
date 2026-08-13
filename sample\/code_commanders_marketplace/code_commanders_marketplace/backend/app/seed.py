from sqlalchemy import select
from .db import Base, SessionLocal, engine
from .models import User, Vendor, Product
from .security import hash_password

Base.metadata.create_all(bind=engine)
db=SessionLocal()
try:
    if not db.scalar(select(User).where(User.email=="admin@codecommanders.local")):
        admin=User(email="admin@codecommanders.local",password_hash=hash_password("Admin@123"),full_name="Platform Admin",role="admin")
        db.add(admin); db.flush()
    if not db.scalar(select(User).where(User.email=="vendor@codecommanders.local")):
        u=User(email="vendor@codecommanders.local",password_hash=hash_password("Vendor@123"),full_name="Demo Vendor",role="vendor")
        db.add(u); db.flush(); v=Vendor(user_id=u.id,business_name="Demo Store",category="Electronics",bank_details="MOCK-1234",approved=True); db.add(v); db.flush()
        db.add_all([
            Product(vendor_id=v.id,name="Wireless Headphones",description="Bluetooth over-ear headphones",price=2499,stock=25,category="Electronics"),
            Product(vendor_id=v.id,name="Mechanical Keyboard",description="RGB mechanical keyboard",price=3499,stock=15,category="Electronics"),
            Product(vendor_id=v.id,name="USB-C Hub",description="7-in-1 USB-C hub",price=1499,stock=40,category="Accessories")])
    if not db.scalar(select(User).where(User.email=="customer@codecommanders.local")):
        db.add(User(email="customer@codecommanders.local",password_hash=hash_password("Customer@123"),full_name="Demo Customer",role="customer"))
    db.commit()
finally: db.close()
print("Seed complete")
