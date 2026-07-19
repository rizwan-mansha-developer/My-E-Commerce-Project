# Darling — Agent Roadmap Diary

> Persistent log for AI agents and developers. Update this file at the start and end of every work session.

---

## Current Goal

**Phase: Catalog CMS — categories, featured landing sections, S3 uploads**

Wire storefront landing to DB products; staff manage categories, Top Picks, Bestsellers, and product images via admin.

### Launch Scope (Active)

| Item | Status |
|------|--------|
| SSR catalog + PDP + JSON-LD | Done |
| Express COD checkout (4 fields + checkbox) | Done |
| Full cart checkout page (`/checkout`) COD-only | Done |
| Guest wishlist / favorites | Done |
| Admin WebSocket order alerts | Done |
| BFF `/api/*` proxies | Done |
| Khaadi-style landing (hero, carousels, footer) | Done |
| Animated search popup | Done |
| Staff product CRUD API + `/admin/products` | Done |
| Superuser-only admin + `/admin/login` remember me | Done |
| RHF + Zod + Zustand form kit (`CustomInput` etc.) | Done |
| Slug routes: admin CRUD + `/collections/[slug]` SEO | Done |
| Categories/collections + landing filters | Done |
| Top Picks / Bestsellers from DB flags | Done |
| Hero slides from category hero media | Done |
| S3 (or local media) product image upload | Done |
| JWT + Google/Facebook auth (django-allauth) | Done |
| Wishlist / cart / checkout auth panels | Done |
| PDP Add to Cart + Buy It Now (Stylo-style) | Done |
| Social auth inside Buy It Now + delivery memory | Done |
| Guest localStorage cart | Done |
| `POST /api/v1/orders/cart/` multi-item COD | Done |

### Postponed (Do Not Expose as Selectable)

| Phase | Scope | Notes |
|-------|-------|-------|
| **4** | JazzCash / EasyPaisa / Card | UI shows Coming soon; backend rejects non-COD |
| **5** | Trax / Leopards courier APIs | Not started |

---

## Dev Quick Start

```bash
# Backend (ASGI for WebSocket admin feed)
cd backend && .venv\Scripts\uvicorn config.asgi:application --reload --reload-exclude "media/*" --reload-exclude "*.pyc" --port 8000

# Frontend
cd frontend && pnpm dev

# Seed categories + demo products
cd backend && .venv\Scripts\python.exe manage.py seed_catalog

# Storefront: http://localhost:3000
# Admin products: http://localhost:3000/admin/products
# Admin inventory: http://localhost:3000/admin/inventory
# API docs (Swagger): http://127.0.0.1:8000/api/v1/docs/
```

### Auth Environment Variables

**Backend** (`.env`):
- `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`
- `FACEBOOK_APP_ID`, `FACEBOOK_APP_SECRET`
- Media: leave `AWS_*` empty for local `backend/media/`; set bucket + keys for S3
- `PUBLIC_MEDIA_BASE_URL=http://localhost:8000` (local absolute image URLs)
- Optional: `AWS_S3_CUSTOM_DOMAIN=cdn.darling.pk`

**Frontend** (`.env.local`):
- `NEXT_PUBLIC_GOOGLE_CLIENT_ID`
- `NEXT_PUBLIC_FACEBOOK_APP_ID`
- `AUTH_API_URL=http://localhost:8000/api/auth` (optional)

---

## Strategic Phases

| Phase | Scope | Status |
|-------|-------|--------|
| **1–3** | Backend, storefront, real-time admin | **Complete** |
| **Auth + Landing** | Social JWT, Khaadi landing, admin CRUD | **Complete** |
| **Buy friction** | PDP dual CTAs + social prefill | **Complete** |
| **Catalog CMS** | Categories, featured flags, S3 upload | **Complete** |
| **4** | Online payment gateways | **Postponed** (COD-only launch) |
| **5** | Courier & fulfillment | **Postponed** |

---

## Completed Milestones

| Date | Milestone |
|------|-----------|
| 2026-06-22 | Phases 1–3 — full COD storefront + admin WebSocket |
| 2026-06-22 | Launch pivot — COD-only; Phases 4 & 5 deferred |
| 2026-06-22 | Open-source auth pipeline + Khaadi landing + staff product CRUD |
| 2026-07-14 | Stylo-style Add to Cart / Buy It Now + Google/Meta on checkout drawer |
| 2026-07-14 | Full `/checkout` page — COD live; Card/JazzCash/EasyPaisa Coming soon |
| 2026-07-15 | Categories + Top Picks/Bestsellers from DB + S3/local image upload |

---

*Next agent: Wire Phase 4 payment selection when gateways go live. Guest cart remains localStorage until account sync ships.*

