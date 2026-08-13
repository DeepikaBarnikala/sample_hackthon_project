# Code Commanders — Multi-Vendor Marketplace Order Management

A hackathon-ready full-stack implementation of the Codegnan problem statement: vendors list products, customers use a unified multi-vendor cart, orders split into vendor-wise sub-orders, vendors fulfil their sub-orders, and admins manage vendor approval, commission and disputes.

## Stack
- Frontend: React + Vite
- Backend: FastAPI + SQLAlchemy
- Database: PostgreSQL in Docker; SQLite by default for quick local development
- Auth: JWT + role-based access

## Implemented requirements
- Customer, Vendor and Platform Admin roles
- Registration and login
- Vendor onboarding + admin approval
- Vendor product listing and stock management
- Unified catalog and multi-vendor cart
- Checkout with automatic vendor-wise order splitting
- Vendor sub-order status tracking
- Automatic 10% commission records and payout calculation
- Admin GMV, commission, order and vendor sales dashboard
- Basic dispute creation API and admin resolution API
- Validation, authorization and meaningful relational database
- README, Docker Compose and smoke test

## Quick start — easiest local demo

### 1. Backend
```bash
cd backend
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python -m app.seed
uvicorn app.main:app --reload
```
Backend: http://localhost:8000
Swagger: http://localhost:8000/docs

### 2. Frontend
In another terminal:
```bash
cd frontend
npm install
npm run dev
```
Frontend: http://localhost:5173

### Demo accounts
- Admin: `admin@codecommanders.local` / `Admin@123`
- Vendor: `vendor@codecommanders.local` / `Vendor@123`
- Customer: `customer@codecommanders.local` / `Customer@123`

## PostgreSQL / Docker
```bash
docker compose up --build
```
This starts PostgreSQL, FastAPI and React. The backend uses PostgreSQL automatically through `DATABASE_URL`.

## Suggested live demo flow
1. Login as admin and approve a pending vendor.
2. Login/register as vendor and list products.
3. Login as customer and add products from different vendors to the same cart.
4. Checkout. The API creates one parent order and one sub-order per vendor.
5. Login as vendor and change the sub-order from pending → processing → shipped → delivered.
6. Login as admin and show GMV, commission, vendor sales and disputes.

## API highlights
- `POST /api/auth/register`
- `POST /api/auth/login`
- `GET /api/products`
- `POST /api/products`
- `POST /api/orders/checkout`
- `GET /api/orders/my`
- `GET /api/vendor/orders`
- `PATCH /api/vendor/orders/{suborder_id}`
- `GET /api/admin/dashboard`
- `POST /api/admin/vendors/{vendor_id}/approve`
- `GET /api/admin/disputes`
- `PATCH /api/admin/disputes/{dispute_id}`
- `POST /api/disputes`

## Database design
`users → vendors → products`

`users → orders → order_items`

`orders → suborders → commissions`

`orders → disputes`

The order model deliberately separates the customer-facing parent order from vendor-specific sub-orders so one checkout can contain products from multiple vendors while each vendor manages only its own fulfilment.

## Notes for production
- Replace demo passwords and `SECRET_KEY`.
- Add refresh tokens, email verification, payment gateway and object storage if required.
- Add database migrations with Alembic before production deployment.
- Add stricter ownership checks and audit logs for financial operations.
