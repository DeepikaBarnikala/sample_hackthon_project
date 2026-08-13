import os
from pathlib import Path

TEST_DB = Path(__file__).with_name("test_marketplace.db")
if TEST_DB.exists():
    TEST_DB.unlink()
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB}"
os.environ["SECRET_KEY"] = "test-secret-for-code-commanders-2026"
os.environ["CORS_ORIGINS"] = "http://test"

from fastapi.testclient import TestClient
from app.db import Base, SessionLocal, engine
from app.main import app
from app.models import User
from app.security import hash_password

Base.metadata.create_all(bind=engine)
client = TestClient(app)


def login(email, password):
    r = client.post("/api/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def auth(token):
    return {"Authorization": f"Bearer {token}"}


def test_complete_requirements_flow():
    db = SessionLocal()
    db.add(User(email="admin@test.local", password_hash=hash_password("Admin@123"), full_name="Admin", role="admin"))
    db.commit(); db.close()

    # Customer and two vendors register normally.
    assert client.post("/api/auth/register", json={"email":"customer@test.local","password":"Customer@123","full_name":"Customer","role":"customer"}).status_code == 200
    assert client.post("/api/auth/register", json={"email":"vendor@test.local","password":"Vendor@123","full_name":"Vendor One","role":"vendor"}).status_code == 200
    assert client.post("/api/auth/register", json={"email":"vendor2@test.local","password":"Vendor2@123","full_name":"Vendor Two","role":"vendor"}).status_code == 200

    admin = login("admin@test.local", "Admin@123")
    customer = login("customer@test.local", "Customer@123")
    vendor1 = login("vendor@test.local", "Vendor@123")
    vendor2 = login("vendor2@test.local", "Vendor2@123")

    vendors = client.get("/api/vendors").json()
    v1 = next(v for v in vendors if v["business_name"] == "Vendor One Store")
    v2 = next(v for v in vendors if v["business_name"] == "Vendor Two Store")

    # Vendor cannot list before approval.
    blocked = client.post("/api/products", headers=auth(vendor1), json={"name":"Blocked","description":"x","price":100,"stock":2,"category":"Test"})
    assert blocked.status_code == 403

    # Admin approves both vendors and can see mock payout details.
    assert client.post(f"/api/admin/vendors/{v1['id']}/approve", headers=auth(admin)).status_code == 200
    assert client.post(f"/api/admin/vendors/{v2['id']}/approve", headers=auth(admin)).status_code == 200
    admin_vendors = client.get("/api/admin/vendors", headers=auth(admin)).json()
    assert all("bank_details" in v for v in admin_vendors)

    # Vendor profile / mock payout details.
    profile_get = client.get("/api/vendor/profile", headers=auth(vendor1))
    assert profile_get.status_code == 200
    profile = client.post("/api/vendor/profile", headers=auth(vendor1), json={"business_name":"Vendor One Store","category":"Electronics","bank_details":"MOCK-PAYOUT-001"})
    assert profile.status_code == 200
    assert client.get("/api/vendor/profile", headers=auth(vendor1)).json()["bank_details"] == "MOCK-PAYOUT-001"
    assert client.get("/api/admin/dashboard", headers=auth(customer)).status_code == 403

    # Search/filter capability exists.
    p1 = client.post("/api/products", headers=auth(vendor1), json={"name":"Test Phone Case","description":"Phone accessory","price":500,"stock":5,"category":"Accessories"})
    p2 = client.post("/api/products", headers=auth(vendor2), json={"name":"Test Hoodie","description":"Fashion demo","price":1000,"stock":5,"category":"Fashion"})
    assert p1.status_code == 200 and p2.status_code == 200
    assert len(client.get("/api/products?search=Phone").json()) >= 1
    assert all(x["category"] == "Fashion" for x in client.get("/api/products?category=Fashion").json())

    # Vendor can edit/archive own product.
    edited = client.put(f"/api/products/{p1.json()['id']}", headers=auth(vendor1), json={"name":"Edited Phone Case","description":"Edited","price":550,"stock":5,"category":"Accessories"})
    assert edited.status_code == 200 and edited.json()["name"] == "Edited Phone Case"

    # Customer places one cart containing products from two vendors.
    order = client.post("/api/orders/checkout", headers=auth(customer), json={"items":[{"product_id":p1.json()["id"],"quantity":2},{"product_id":p2.json()["id"],"quantity":1}]})
    assert order.status_code == 200, order.text
    body = order.json()
    assert body["total_amount"] == 2100
    assert len(body["suborders"]) == 2
    ids = {s["vendor_id"]: s["id"] for s in body["suborders"]}

    # Commission is NOT created at checkout.
    from app.models import Commission
    db = SessionLocal()
    assert db.query(Commission).count() == 0
    db.close()

    # Status workflow is enforced.
    assert client.patch(f"/api/vendor/orders/{ids[v1['id']]}" , headers=auth(vendor1), json={"status":"delivered"}).status_code == 400
    assert client.patch(f"/api/vendor/orders/{ids[v1['id']]}" , headers=auth(vendor1), json={"status":"processing"}).status_code == 200
    assert client.patch(f"/api/vendor/orders/{ids[v1['id']]}" , headers=auth(vendor1), json={"status":"shipped"}).status_code == 200
    assert client.patch(f"/api/vendor/orders/{ids[v1['id']]}" , headers=auth(vendor1), json={"status":"delivered"}).status_code == 200
    assert client.patch(f"/api/vendor/orders/{ids[v2['id']]}" , headers=auth(vendor2), json={"status":"processing"}).status_code == 200
    assert client.patch(f"/api/vendor/orders/{ids[v2['id']]}" , headers=auth(vendor2), json={"status":"shipped"}).status_code == 200
    assert client.patch(f"/api/vendor/orders/{ids[v2['id']]}" , headers=auth(vendor2), json={"status":"delivered"}).status_code == 200

    # Completed order creates commission and payout.
    summary = client.get("/api/vendor/summary", headers=auth(vendor1)).json()
    assert summary["completed_sales"] == 1100
    assert summary["commission"] == 110
    assert summary["payout"] == 990

    # Admin can change commission rate for future completions and access reports.
    assert client.patch("/api/admin/commission-rate", headers=auth(admin), json={"rate":0.15}).status_code == 200
    dashboard = client.get("/api/admin/dashboard", headers=auth(admin)).json()
    assert dashboard["gmv"] == 2100
    assert dashboard["completed_gmv"] == 2100
    assert dashboard["commission"] == 210
    assert dashboard["vendor_payout"] == 1890
    assert len(dashboard["vendor_sales"]) >= 2
    assert len(client.get("/api/admin/reports/gmv-trend", headers=auth(admin)).json()) == 7
    assert len(client.get("/api/admin/reports/commission", headers=auth(admin)).json()) == 2
    assert len(client.get("/api/admin/reports/vendor-payouts", headers=auth(admin)).json()) >= 2

    # Customer can raise a vendor-specific dispute; admin can investigate and resolve it.
    dispute = client.post("/api/disputes", headers=auth(customer), json={"order_id":body["id"],"vendor_id":v1["id"],"reason":"Item issue","description":"Demo dispute for evaluation"})
    assert dispute.status_code == 200
    did = dispute.json()["id"]
    assert client.patch(f"/api/admin/disputes/{did}", headers=auth(admin), json={"status":"investigating","resolution":"Checking"}).status_code == 200
    assert client.patch(f"/api/admin/disputes/{did}", headers=auth(admin), json={"status":"resolved","resolution":"Resolved"}).status_code == 200

    # Archive product and verify it disappears from active storefront.
    assert client.delete(f"/api/products/{p1.json()['id']}", headers=auth(vendor1)).status_code == 200
    assert all(p["id"] != p1.json()["id"] for p in client.get("/api/products").json())
