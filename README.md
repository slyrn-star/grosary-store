# Fresh Grocery Store

A learning project for a grocery storefront with a browser-based customer interface and a Python API. Customers can browse products, search and sort the catalogue, register or sign in, maintain a cart, and place Cash on Delivery orders. Admin-only API routes cover catalogue, stock, order, user, and store settings.

> This is a learning project, not a production-ready commerce system. Review the security and consistency limitations below before using it with real users or data.

## Project structure

```text
.
├── grosary.html                 # Storefront markup and embedded styles
├── app.js                       # Storefront interactions and customer flows
├── api.js                       # Fetch wrapper for the local API
├── .gitignore
└── backend/
    ├── main.py                  # FastAPI app and public routes
    ├── config.py                # Environment-backed configuration
    ├── database.py              # MongoDB connection, collections, indexes
    ├── schemas.py               # Pydantic request models
    ├── security.py              # Password hashing, JWT and auth cookie
    ├── seed.py                  # Initial admin/store seed data
    ├── utils.py                 # Serialization, timestamps, activity logging
    ├── requirements.txt
    └── routers/
        ├── auth.py
        ├── products.py
        ├── cart.py
        ├── orders.py
        └── admin.py
```

## Technology

- Frontend: HTML, CSS, and vanilla JavaScript
- Backend: Python, FastAPI, Uvicorn
- Data store: MongoDB through PyMongo
- Authentication: JWT, bcrypt password hashing, HTTP-only cookie

## Features present in source

- Public product listing, category filter, name search, and price/name sorting
- Sign-up, login, logout, session restoration, and account lookup
- User carts with stock-aware quantity changes
- Cash on Delivery checkout and customer order/payment history
- Admin endpoints for dashboard metrics, products, stock, users, login/activity history, orders, payments, and store settings
- Product stock is conditionally decremented during checkout and earlier decrements are restored if a later cart item cannot be reserved

UPI, card, and net banking are shown as unavailable in the interface. The source does not integrate those payment methods.

## Requirements

- Python 3.10 or newer (the code uses modern type syntax and Pydantic 2 APIs)
- A MongoDB deployment and connection URI
- A modern browser
- A local static HTTP server for the frontend (the default CORS origins expect port 5500)

## Configuration

Create `backend/.env` from `backend/.env.example` and set real values locally. Never commit credentials.

| Variable | Required | Default / use |
| --- | --- | --- |
| `MONGODB_URI` | Yes | MongoDB connection string |
| `JWT_SECRET` | Yes | Secret used to sign JWTs; use a long, random value |
| `DB_NAME` | No | `grocery_store` |
| `JWT_EXPIRE_MINUTES` | No | `720` |
| `CORS_ORIGINS` | No | `http://localhost:5500,http://127.0.0.1:5500` |
| `ADMIN_NAME` | No | `Store Admin` |
| `ADMIN_EMAIL` | No | `admin@freshgrocery.com` |
| `ADMIN_PASSWORD` | **Set before seeding** | Source fallback is `ChangeMe123!`; replace it with a unique secret before running `seed.py` |

## Run locally

From the repository root, in PowerShell:

```powershell
py -m venv backend/.venv
backend/.venv/Scripts/Activate.ps1
py -m pip install -r backend/requirements.txt
Copy-Item backend/.env.example backend/.env
# Edit backend/.env and set the required values before continuing.
Set-Location backend
py seed.py
py -m uvicorn main:app --reload
```

Open a second terminal at the repository root and serve the static files on port 5500. For example, with Python available:

```powershell
py -m http.server 5500
```

Then visit `http://localhost:5500/grosary.html`. The API is at `http://localhost:8000`; FastAPI's interactive API documentation is at `http://localhost:8000/docs`.

The backend imports modules as top-level modules, so start Uvicorn with `backend/` as the working directory (as shown). MongoDB must be reachable before startup and seeding.

## API overview

All routes are defined in `backend/main.py` and `backend/routers/`. Interactive request schemas are available at `/docs` when the server runs.

| Method | Path | Access | Purpose |
| --- | --- | --- | --- |
| `GET` | `/` | Public | API health response |
| `GET` | `/company` | Public | Public store contact/settings fields |
| `POST` | `/auth/signup` | Public | Create customer and sign in |
| `POST` | `/auth/login` | Public | Sign in |
| `POST` | `/auth/logout` | Signed in | Revoke current session and clear cookie |
| `GET` | `/auth/me` | Signed in | Current account |
| `GET` | `/products` | Public | List/filter/sort active products |
| `GET` | `/products/{product_id}` | Public | Read one active product |
| `GET`, `POST`, `DELETE` | `/cart`, `/cart/items`, `/cart/items/{product_id}` | Signed in | Read and change cart |
| `POST` | `/orders` | Signed in | Place Cash on Delivery order |
| `GET` | `/orders/my`, `/orders/{order_id}` | Signed in | Read own order history/detail (admins can read any order) |
| `GET` | `/payments/my` | Signed in | Read own payment history |
| `GET` | `/admin/dashboard`, `/admin/users`, `/admin/users/{user_id}/overview` | Admin | Dashboard, user list, and user overview/history |
| `PATCH` | `/admin/users/{user_id}/active` | Admin | Enable/disable a user |
| `GET` | `/admin/login-history`, `/admin/activity` | Admin | Search login and activity records |
| `GET`, `PATCH` | `/admin/orders`, `/admin/orders/{order_id}/status` | Admin | List and update orders |
| `GET` | `/admin/payments` | Admin | List payment records |
| `GET`, `POST`, `PUT`, `PATCH`, `DELETE` | `/admin/products` and `/admin/products/{product_id}[/stock]` | Admin | List, create, update, adjust stock, or hide products |
| `GET`, `PUT` | `/admin/company` | Admin | Read/update store settings |

The `/admin/products` route supports `GET` and `POST`; `/admin/products/{product_id}` supports `PUT` and `DELETE`; `/admin/products/{product_id}/stock` supports `PATCH`.

## Screenshots

No committed screenshots were present in the inspected repository. Add genuine screenshots here when available; none are fabricated in this README.

## Security and known limitations

These findings come from source inspection and are not a penetration test.

- **Default admin password:** `backend/config.py` falls back to `ChangeMe123!`, and `seed.py` creates the admin account from configuration. Set a strong `ADMIN_PASSWORD` before seeding; remove the fallback in a separately reviewed security change.
- **Cookie transport:** the auth cookie is HTTP-only and `SameSite=Lax`, but `secure=False` is hard-coded. Production deployment over HTTPS needs a secure cookie setting. Cookie-authenticated state-changing routes have no explicit CSRF token; assess CSRF protection before production use.
- **Cross-document checkout consistency:** stock changes are guarded per product and earlier stock decrements are rolled back when a later item is unavailable. Order, payment, cart, inventory, and activity writes are separate MongoDB operations rather than one transaction; failures between writes can leave inconsistent records or reserved stock.
- **Sensitive admin data:** admin user-overview and history endpoints expose customer identifiers/contact details and operational history to an authenticated admin. Keep admin access tightly controlled and avoid using real personal data in a public demo.
- **Validation:** passwords may be as short as six characters. Rate limiting, stronger password policy, and broader input validation are not present in the inspected code.
- **Testing:** no automated tests or test configuration were present in the repository.
- **Errors/operations:** database failures and partial write failures do not have a centralized recovery path. No deployment, monitoring, or production hardening configuration is included.

## Future improvements

- Add automated tests for auth/session handling, cart stock limits, order lifecycle, and admin access.
- Require an explicitly configured admin password and JWT secret, and enable secure cookies for HTTPS deployments.
- Add CSRF defenses for cookie-authenticated mutations and rate limiting for authentication endpoints.
- Use a MongoDB transaction or a documented compensating-action strategy for multi-document checkout writes.
- Add setup validation, operational error handling, and genuine UI screenshots.

## Status and author

Learning project; no deployment URL is provided.  
Author: [Bristi Santra](https://github.com/slyrn-star) · [Repository](https://github.com/slyrn-star/grosary-store)
