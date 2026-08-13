# Project Details — Code Commanders Marketplace

## 1. Project title

**Multi-Vendor Marketplace Order Management**

## 2. Domain

E-commerce / Multi-vendor marketplace

## 3. Objective

Build a marketplace where multiple small businesses can sell through one platform without losing independent control of products, inventory and fulfilment. Customers receive one unified shopping experience. The platform admin controls vendor onboarding, commission calculation and dispute resolution.

## 4. Requirement-to-module mapping

### User roles

- **Customer:** registration, login, catalog, multi-vendor cart, checkout, orders, disputes.
- **Vendor:** registration, approval dependency, profile, products, stock, sub-orders, fulfilment, payout summary.
- **Platform Admin:** vendor approval, commission rate, GMV/analytics, vendor sales/payouts, disputes.

### Registration & login

- Customers and vendors can register.
- Public registration cannot create an admin account.
- Vendor registration creates an unapproved vendor profile.
- JWT authentication identifies the logged-in user and role.

### Data entry

Vendor profile:

- Business name
- Category
- Mock bank/payout details

Product:

- Vendor
- Name
- Price
- Stock
- Category
- Description
- Active/archive state

Order:

- Customer
- Items
- Parent total
- Vendor-wise sub-orders
- Per-vendor fulfilment status

### Core functional requirements

1. Vendor manages only its own products and stock.
2. Customer sees only products from approved vendors.
3. Customer can place one cart containing products from multiple vendors.
4. Checkout creates one parent order and one sub-order per vendor.
5. Each vendor can see and update only its own sub-orders.
6. Parent order status is derived from child sub-order states.
7. Admin controls vendor approval and commission rate.
8. Commission is automatically created on delivery/completion.
9. Vendor payout is completed sales minus commission.
10. Customer can open a dispute for a vendor participating in the order.
11. Admin can investigate, resolve or reject disputes.

## 5. Business rules

### Vendor approval

```text
Vendor registers
      ↓
approved = false
      ↓
Admin approves
      ↓
approved = true
      ↓
Vendor may list products
```

### Multi-vendor order split

```text
Cart
├── Product A → Vendor 1 → ₹2,000
└── Product B → Vendor 2 → ₹3,000

Checkout
└── Parent Order = ₹5,000
    ├── SubOrder 1 = ₹2,000
    └── SubOrder 2 = ₹3,000
```

### Fulfilment state machine

```text
pending → processing → shipped → delivered
    └──────────────→ cancelled
```

Invalid jumps such as `pending → delivered` are rejected.
Delivered/cancelled sub-orders are terminal.

### Commission

Commission is calculated only when a sub-order reaches `delivered`.

```text
commission = delivered_suborder_total × current_platform_rate
payout     = completed_sales − commission
```

The rate used is stored with each commission record, so historical commission values do not change when the admin changes the rate later.

## 6. Database entities

### Users

Authentication identities for customers, vendors and admin.

### Vendors

One-to-one with a vendor user. Stores business profile, mock payout details and approval state.

### Products

Belongs to one vendor. Stores price, stock, category, description and active/archive state.

### Orders

Parent customer checkout.

### OrderItems

Immutable purchase snapshot: product, vendor, quantity, unit price and subtotal.

### SubOrders

Vendor-specific fulfilment unit created from a parent order.

### Commissions

One unique record per delivered sub-order, storing the rate and amount used at completion.

### Disputes

Customer-to-vendor issue associated with a parent order and handled by admin.

### PlatformSettings

Current platform commission rate.

## 7. Relationships

```text
User 1 ───── 0..1 Vendor
User 1 ───── * Order
Vendor 1 ─── * Product
Order 1 ──── * OrderItem
Order 1 ──── * SubOrder
Vendor 1 ─── * SubOrder
SubOrder 1 ─ 0..1 Commission
Order 1 ──── * Dispute
User 1 ───── * Dispute
Vendor 1 ─── * Dispute
```

## 8. Analytics

### Vendor-wise sales

Completed/delivered sub-order totals are grouped by vendor.

### Platform GMV

All parent order totals are summed for total GMV. A separate completed GMV is calculated from delivered vendor sub-orders.

### 7-day GMV trend

`GET /api/admin/reports/gmv-trend` returns seven calendar days, including zero-value days, so the frontend can always render a complete seven-day chart.

### Commission earned report

`GET /api/admin/reports/commission` returns every earned commission with vendor, sub-order, rate, amount and timestamp.

### Vendor payout report

`GET /api/admin/reports/vendor-payouts` returns completed sales, commission and payout for every vendor.

## 9. Frontend screens

### Storefront

- Search
- Category filter
- Vendor filter
- Product cards
- Stock display
- Multi-vendor cart
- Quantity controls
- Checkout

### Customer orders

- Parent order total/status
- Purchased item summary
- Vendor-wise sub-order cards
- Vendor-specific dispute action

### Vendor dashboard

- Completed sales
- Commission
- Payout
- Product count
- Approval state
- Vendor profile + mock payout details
- Product create/edit/archive
- Vendor sub-orders + status updates

### Admin dashboard

- GMV
- Completed GMV
- Commission earned
- Vendor payout
- Order count
- Open disputes
- Vendor approval
- Commission rate
- Seven-day GMV trend
- Vendor sales/payout report
- Commission-earned report
- Dispute management

## 10. Security / validation

- Passwords are hashed with PBKDF2-HMAC-SHA256.
- JWT is used for authenticated API calls.
- Role guards prevent customer/vendor/admin privilege crossing.
- Vendors can only modify their own products and sub-orders.
- Customers can only create disputes for their own orders and participating vendors.
- Admin endpoints require the admin role.
- Pydantic validates prices, quantities, lengths, email format, commission rate and statuses.
- Business rules validate stock, vendor approval and fulfilment transitions.

## 11. Exact hackathon demo

### A. Onboarding

Create a fresh vendor account. Try to list a product before approval; the API returns 403. Login as admin and approve it. Return to vendor and list the product.

### B. Multi-vendor cart

Use the seeded two vendors. Login as customer. Add a product from Vendor 1 and a product from Vendor 2. Checkout once.

### C. Order splitting

Open My Orders. Show one parent order with two vendor-specific sub-orders.

### D. Fulfilment

Login as each vendor separately. Each vendor sees only its own sub-order. Move it through the status workflow until delivered.

### E. Commission and payout

Login as admin. Completed GMV and commission increase. Vendor payout is completed sales minus commission.

### F. Dispute

Customer opens a dispute against a selected vendor. Admin changes it to investigating and then resolved/rejected.

### G. Analytics

Show the seven-day GMV trend, vendor sales/payout report and commission-earned report.

## 12. Demo credentials

```text
Admin:
admin@codecommanders.local / Admin@123

Vendor 1:
vendor@codecommanders.local / Vendor@123

Vendor 2:
vendor2@codecommanders.local / Vendor2@123

Customer:
customer@codecommanders.local / Customer@123
```

## 13. Testing

The test suite verifies:

- Registration
- Unapproved vendor restriction
- Admin approval
- Vendor profile
- Product creation
- Search/filter
- Product edit/archive
- Two-vendor checkout
- Parent order + sub-order creation
- No commission at checkout
- Fulfilment transition rules
- Commission on delivery
- Vendor payout
- Admin commission rate
- GMV trend
- Commission report
- Vendor payout report
- Customer dispute
- Admin dispute investigation/resolution

Run with:

```bash
cd backend
pytest -q
```

## 14. Hackathon scope

The application intentionally simulates payments and payout transfers. Bank details are mock values. No real payment gateway or banking integration is required by the problem statement.
