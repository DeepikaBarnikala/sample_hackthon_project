# Code Commanders — Multi-Vendor Marketplace Order Management

**Codegnan Hackathon | Domain: E-commerce**

This repository is the complete implementation of the provided problem statement. It is designed as a demonstrable hackathon application, not a static UI mockup.

## Problem solved

Small businesses share one marketplace while retaining independent control over their products, stock and fulfilment. Customers see one unified catalog and can place a single cart/checkout containing products from multiple vendors. The platform admin controls vendor onboarding, commission rates and dispute resolution.

## Requirement coverage

| Problem-statement requirement | Implementation | Status |
|---|---|---|
| Customer / Vendor / Platform Admin roles | JWT authentication + role guards + role dashboards | ✅ |
| Customer registration | `/api/auth/register` with customer role | ✅ |
| Vendor registration | `/api/auth/register` with vendor role | ✅ |
| Vendor approval before listing | Admin approval endpoint; product creation blocked until approved | ✅ |
| Role-based dashboards | Customer orders, Vendor dashboard, Admin dashboard | ✅ |
| Vendor business profile | Business name, category, mock bank/payout details | ✅ |
| Product listing | Name, vendor, price, stock, category, description | ✅ |
| Vendor product management | Create, edit, archive, stock update through edit | ✅ |
| Unified customer catalog | React storefront using approved vendor products | ✅ |
| Search / filter | Product search, category filter, vendor filter | ✅ |
| Multi-vendor cart | Cart can contain products from multiple vendors | ✅ |
| Single checkout | One checkout request creates one parent order | ✅ |
| Vendor-wise order splitting | Parent order automatically creates one sub-order per vendor | ✅ |
| Vendor-specific fulfilment | Vendors only see/update their own sub-orders | ✅ |
| Fulfilment statuses | Pending → Processing → Shipped → Delivered; cancellation supported | ✅ |
| Admin vendor approval | Admin onboarding screen | ✅ |
| Admin commission rate | Configurable 0–100% rate | ✅ |
| Commission on completed orders | Commission is created only when sub-order reaches `delivered` | ✅ |
| Vendor payout | Completed sales − earned commission | ✅ |
| Vendor-wise sales performance | Admin vendor sales/payout report | ✅ |
| Platform GMV trend | 7-day GMV analytics endpoint + dashboard chart | ✅ |
| Commission earned report | Admin commission report | ✅ |
| Dispute workflow | Customer opens vendor-specific dispute; admin investigates/resolves/rejects | ✅ |
| Input validation | Pydantic validation + business validation | ✅ |
| Sensible error handling | HTTP 4xx messages for invalid role, stock, state, permissions, etc. | ✅ |
| Authentication / RBAC | JWT + role dependencies + ownership checks | ✅ |
| Database relationships | Users, Vendors, Products, Orders, OrderItems, SubOrders, Commissions, Disputes, PlatformSettings | ✅ |
| Basic core-flow testing | End-to-end pytest covering onboarding → checkout → splitting → fulfilment → commission → payout → dispute → reports | ✅ |
| README / setup documentation | This file + `docs/PROJECT_DETAILS.md` | ✅ |
| Live-demo flow | Seeded two-vendor data + exact demo script below | ✅ |

## Architecture

```text
React/Vite frontend
        |
        | REST + JWT
        v
FastAPI backend
        |
        v
SQLAlchemy ORM
        |
        v
PostgreSQL (Docker) / SQLite (local)
```

## Important business flow

```text
Vendor registers
      ↓
Admin approves vendor
      ↓
Vendor lists products
      ↓
Customer browses unified catalog
      ↓
Customer adds Vendor A + Vendor B products to one cart
      ↓
One checkout
      ↓
Parent Order
   ├── Vendor A SubOrder
   └── Vendor B SubOrder
      ↓
Each vendor fulfils only its own SubOrder
      ↓
SubOrder reaches Delivered
      ↓
Commission is calculated automatically
      ↓
Vendor payout = completed sales − commission
      ↓
Admin reviews GMV, vendor sales, commission, payouts and disputes
```

## Project structure

```text
code_commanders_marketplace/
├── backend/
│   ├── app/
│   │   ├── config.py       # Environment settings
│   │   ├── db.py           # SQLAlchemy engine/session
│   │   ├── main.py         # REST API + business rules
│   │   ├── models.py       # Database entities/relationships
│   │   ├── schemas.py      # Request/response validation
│   │   ├── security.py     # Password hashing + JWT
│   │   └── seed.py         # Repeatable demo data
│   ├── tests/
│   │   └── test_marketplace.py
│   ├── pytest.ini
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── main.jsx       # Customer/Vendor/Admin UI
│   │   ├── api.js         # API client
│   │   └── styles.css
│   ├── package.json
│   ├── vite.config.js
│   └── .env.example
├── docs/
│   └── PROJECT_DETAILS.md
├── .github/workflows/test.yml
├── docker-compose.yml
├── .gitignore
└── README.md
```

## Quick start — Docker

### Prerequisite

Install Docker Desktop.

### Run

From the project root:

```bash
docker compose up --build
```

Open:

- Frontend: `http://localhost:5173`
- Backend: `http://localhost:8000`
- Swagger/OpenAPI: `http://localhost:8000/docs`

The compose stack starts PostgreSQL, FastAPI and React and seeds the demo accounts/products.

To stop:

```bash
docker compose down
```

To remove the PostgreSQL demo data as well:

```bash
docker compose down -v
```

## Quick start — local development

### Backend

```bash
cd backend
python -m venv .venv
```

Windows:

```bash
.venv\Scripts\activate
```

macOS/Linux:

```bash
source .venv/bin/activate
```

Install:

```bash
pip install -r requirements.txt
```

Copy `.env.example` to `.env`, then:

```bash
python -m app.seed
uvicorn app.main:app --reload
```

Backend: `http://localhost:8000`

Swagger: `http://localhost:8000/docs`

### Frontend

Open another terminal:

```bash
cd frontend
npm install
npm run dev
```

Frontend: `http://localhost:5173`

## Demo accounts

| Role | Email | Password |
|---|---|---|
| Admin | `admin@codecommanders.local` | `Admin@123` |
| Vendor 1 | `vendor@codecommanders.local` | `Vendor@123` |
| Vendor 2 | `vendor2@codecommanders.local` | `Vendor2@123` |
| Customer | `customer@codecommanders.local` | `Customer@123` |

These are demonstration credentials only.

## Recommended evaluator demo

1. **Admin:** Login and show vendor approval, commission rate, GMV, completed GMV, payout and disputes.
2. **Vendor:** Register a new vendor account to demonstrate the real onboarding path. The new vendor initially cannot list products.
3. **Admin:** Approve the new vendor.
4. **Vendor:** Update business profile and mock payout details, then list a product.
5. **Customer:** Login and add one product from Vendor A and one product from Vendor B to the same cart.
6. **Customer:** Checkout once.
7. **Customer:** Open My Orders and show one parent order containing two vendor-wise sub-orders.
8. **Vendor A:** Move its sub-order Pending → Processing → Shipped → Delivered.
9. **Vendor B:** Do the same.
10. **Admin:** Show that completed GMV, commission and vendor payout now reflect the completed sub-orders.
11. **Customer:** Raise a dispute against one vendor/sub-order.
12. **Admin:** Investigate and resolve/reject the dispute.
13. **Admin:** Show 7-day GMV trend and commission-earned report.

## Commission example

If a completed vendor sub-order is ₹2,500 and the platform rate is 10%:

```text
Completed sales = ₹2,500
Commission      = ₹250
Vendor payout   = ₹2,250
```

Commission is deliberately **not** created at checkout. It is created exactly when the vendor's sub-order becomes `delivered`.

## API highlights

### Auth

- `POST /api/auth/register`
- `POST /api/auth/login`
- `GET /api/me`

### Catalog

- `GET /api/products`
- `GET /api/products/categories`
- `GET /api/vendors`
- `POST /api/products`
- `PUT /api/products/{product_id}`
- `DELETE /api/products/{product_id}`

### Vendor

- `GET /api/vendor/profile`
- `POST /api/vendor/profile`
- `GET /api/vendor/products`
- `GET /api/vendor/orders`
- `PATCH /api/vendor/orders/{suborder_id}`
- `GET /api/vendor/summary`

### Customer

- `POST /api/orders/checkout`
- `GET /api/orders/my`
- `POST /api/disputes`
- `GET /api/disputes/my`

### Admin

- `GET /api/admin/vendors`
- `POST /api/admin/vendors/{vendor_id}/approve`
- `GET /api/admin/dashboard`
- `GET /api/admin/commission-rate`
- `PATCH /api/admin/commission-rate`
- `GET /api/admin/reports/gmv-trend`
- `GET /api/admin/reports/commission`
- `GET /api/admin/reports/vendor-payouts`
- `GET /api/admin/disputes`
- `PATCH /api/admin/disputes/{dispute_id}`

## Testing

Run:

```bash
cd backend
pytest -q
```

The included end-to-end test verifies the major business requirements, including vendor approval, multi-vendor checkout, order splitting, status transition rules, completion-based commission, payout, analytics reports, disputes and product archiving.

## Scope / honest hackathon limitations

- Payments are simulated; no real payment gateway is connected.
- Bank/payout details are explicitly mock data.
- No real money transfer is performed.
- Product images are represented by simple UI icons.
- Disputes are a basic workflow rather than a full ticketing/SLA system.
- `create_all` is used for the hackathon build instead of a migration framework.

These limitations do not block the requirements in the supplied problem statement.
