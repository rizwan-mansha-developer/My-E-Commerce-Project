# Darling — Engineering Skills & Paradigms

> Constitutional reference for all agents and engineers working in the Darling monorepo (`darling.pk`).
> Specification-Driven Development (SDD) is mandatory: define behavior in specs before writing feature code.

---

## 1. Monorepo Topology

```
Darling/
├── skills.md          # This file — engineering paradigms
├── cursor.md          # Cursor agent coding standards
├── agent.md           # Roadmap diary & system state
├── frontend/          # Next.js 16 App Router (TypeScript)
└── backend/           # Django REST + Channels (Python)
```

| Layer    | Port (dev) | Runtime        |
|----------|------------|------------------|
| Frontend | `3000`     | Next.js dev server |
| Backend  | `8000`     | Uvicorn ASGI       |
| Redis    | `6379`     | Channel layer cache |

---

## 2. Frontend — Next.js 16.2.9 (App Router)

### 2.1 Server / Client Boundary (Core Web Vitals)

- **Default to Server Components.** Every file in `app/` is a Server Component unless it requires browser APIs, event handlers, or React hooks.
- **Client Components** live in `src/components/client/` or co-located molecules marked with `'use client'` at the top of the file — never on page or layout shells.
- **Data fetching** for SSR pages happens in Server Components via repository/adaptor calls. Never fetch in `useEffect` when SSR can serve the same data.
- **Streaming & Suspense:** Wrap slow server fetches in `<Suspense>` boundaries with skeleton fallbacks for LCP optimization.
- **Images:** Always use `next/image` with explicit `width`, `height`, and `priority` on above-the-fold hero assets.

### 2.2 Clean Architecture (Uncle Bob Pattern)

```
frontend/src/
├── domain/           # Entities, value objects, Zod schemas (pure TypeScript)
├── use-cases/        # Application business rules (framework-agnostic)
├── repositories/     # Abstract data access interfaces (ports)
├── adapters/         # Concrete implementations (HTTP, localStorage, etc.)
├── infrastructure/   # External service wiring (API client, query client)
├── components/
│   ├── ui/           # Shadcn / Aceternity primitives
│   ├── server/       # Server-only composites
│   └── client/       # Interactive molecules
└── app/              # Next.js routes (thin — delegate to use-cases)
```

**Dependency rule:** `app → use-cases → domain ← repositories ← adapters`. Inner layers never import from outer layers.

### 2.3 Frictionless Guest UX — Favorites & Express Checkout

**Principles:** zero login walls, zero long forms, one screen from intent to order.

#### Guest Favorites (Wishlist)

- Heart toggle works for **guests and logged-in users** — no sign-up prompt.
- Backend stores guest favorites on the Django **session cookie** (`session_key` on `WishlistItem`).
- Frontend calls `POST /api/v1/catalog/wishlist/toggle/` with `credentials: 'include'`.
- PLP/PDP hearts use optimistic toggle; `GET /api/v1/catalog/wishlist/` returns `product_ids` for filled-state UI.
- On future login, merge guest session favorites into the user account via `WishlistService.merge_session_into_user`.

#### Express Checkout (Minimal Flow)

Guest checkout stays available (no forced account). **Google / Meta social login is optional** and only used to reduce typing — especially important for Pakistani buyers who abandon long address forms.

| Field | Required | Notes |
|-------|----------|-------|
| Full name | Yes | Prefills from Google/Facebook when signed in |
| Phone | Yes | `03XXXXXXXXX` only |
| Address | Yes | min 5 chars — single line; remembered after first order |
| City | Yes | min 2 chars; remembered after first order |
| COD checkbox | Yes | pre-checked; **only** payment method at launch |
| Email / password | **No** | never required to place COD order |

#### Full Checkout Page (`/checkout`)

Stylo-style two-column layout. **COD is the only selectable payment at launch.**

| Section | Behavior |
|---------|----------|
| Contact | Google / Facebook autofill + optional email |
| Delivery | Name, address, city, PK phone only (no apartment/postal clutter) |
| Shipping | COD Standard · Free |
| Payment | COD selected; Card / JazzCash / EasyPaisa disabled with Coming soon |
| Summary | Cart lines, free shipping, PKR total |

- `POST /api/v1/orders/cart/` — multi-item COD order; rejects non-COD `payment_method`.
- Phase 4 will unlock online methods already scaffolded in `gateways/`.

```typescript
// domain/schemas/express-checkout.schema.ts
export const expressCheckoutSchema = z.object({
  variantId: z.string().uuid(),
  fullName: z.string().min(2),
  phone: z.string().regex(/^03\d{9}$/),
  shippingAddress: z.string().min(5),
  city: z.string().min(2),
  quantity: z.number().int().min(1).max(10).default(1),
  codConfirmed: z.literal(true, {
    errorMap: () => ({ message: 'Confirm Cash on Delivery to order' }),
  }),
});
```

- Single drawer/modal — **no multi-step wizard**, no address book UI.
- Default quantity `1`; variant/color picked on PDP before opening checkout.
- `POST /api/v1/orders/express/` — guest allowed, returns `tracking_number` immediately.
- Social auth via `POST /api/auth/callback` (`google` | `facebook`) + JWT cookies.

### 2.4 Form Validation — React Hook Form + Zod

```typescript
// domain/schemas/checkout.schema.ts
import { z } from 'zod';

export const checkoutSchema = z.object({
  fullName: z.string().min(2, 'Name is required'),
  phone: z.string().regex(/^03\d{9}$/, 'Valid PK mobile required'),
  address: z.string().min(10),
  city: z.string().min(2),
});

export type CheckoutFormValues = z.infer<typeof checkoutSchema>;
```

- Define schemas in `domain/schemas/`. Reuse the same schema on client forms and server action validation.
- Use `zodResolver(checkoutSchema)` with React Hook Form for real-time field-level errors.
- Server Actions must re-validate with the identical Zod schema — never trust client-only validation.

### 2.4 Data Fetching — TanStack Query

- Query client provider lives in `infrastructure/query-client.tsx` (Client Component wrapper).
- Repository interfaces define fetch/mutate contracts; adapters implement them with `fetch` or Axios.
- Query keys follow the pattern: `['entity', id]` / `['entity', 'list', filters]`.
- Mutations invalidate related query keys on success; optimistic updates only for cart quantity changes.
- Stale time defaults: product catalog `5 min`, cart `0`, user profile `10 min`.

### 2.5 SEO & JSON-LD

- Every product page exports `generateMetadata()` with Open Graph and Twitter card tags.
- Inject `<script type="application/ld+json">` via a dedicated `ProductJsonLd` Server Component.
- Use semantic HTML: `<article>`, `<nav aria-label>`, `<main>`, proper heading hierarchy (single `<h1>` per page).

### 2.6 Styling — Mobile-First Tailwind

Breakpoint order (always mobile-first, never `max-*` first):

| Prefix | Min-width | Target |
|--------|-----------|--------|
| (none) | 0         | Mobile (80–90% of orders) |
| `sm:`  | 640px     | Large phones |
| `md:`  | 768px     | Tablets |
| `lg:`  | 1024px    | Desktop |
| `xl:`  | 1280px    | Wide desktop |

- Shadcn UI for form controls, dialogs, sheets, toasts.
- Aceternity UI for hero animations, card hover effects, and premium visual flourishes — use sparingly on above-the-fold sections only.

---

## 3. Backend — Django Service Layer

### 3.1 Project Layout

```
backend/
├── config/              # Django project settings, ASGI, URLs
│   ├── settings/
│   │   ├── base.py
│   │   ├── development.py
│   │   └── production.py
│   ├── asgi.py
│   └── urls.py
├── apps/
│   ├── catalog/         # Products, categories, inventory
│   ├── orders/          # Checkout, COD, tracking numbers
│   └── notifications/   # WebSocket consumers
├── services/            # Business logic (Service Layer)
├── repositories/        # ORM query abstractions
└── requirements/
    ├── base.txt
    └── development.txt
```

### 3.2 Service Layer Pattern

**Views are thin.** They parse request → call service → serialize response.

```python
# apps/orders/views.py  (thin)
class CreateOrderView(APIView):
    def post(self, request):
        serializer = OrderCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        order = OrderService.create_cod_order(
            user=request.user,
            payload=serializer.validated_data,
        )
        return Response(OrderSerializer(order).data, status=201)

# services/order_service.py  (business logic)
class OrderService:
    @staticmethod
    def create_cod_order(*, user, payload) -> Order:
        with transaction.atomic():
            order = OrderRepository.create(user=user, **payload)
            order.tracking_number = TrackingNumberGenerator.generate()
            order.save()
            InventoryService.decrement(order.items)
            NotificationService.push_order_created(order)
            return order
```

### 3.3 Database Conventions

- **PostgreSQL** via Neon serverless (`DATABASE_URL` env var, parsed with `dj-database-url`).
- **Soft deletes:** All user-facing models include `is_active = models.BooleanField(default=True)`. Default managers filter `is_active=True`.
- **Indexes:** Add `db_index=True` or composite indexes on fields used in list/filter queries (`slug`, `category_id`, `created_at`, `tracking_number`).
- **Tracking numbers:** Format `DRLNG-{YEAR}-{4-digit-seq}` — generated in `services/tracking.py`, never in views.

### 3.4 Real-Time — Django Channels + Redis

```
Browser ←WebSocket→ Uvicorn (ASGI) → Channel Layer (Redis) → Consumer
```

- ASGI entry: `config/asgi.py` routes HTTP to Django and WebSocket to Channels routing.
- Channel layer: `channels_redis` with in-memory Redis (`REDIS_URL=redis://127.0.0.1:6379/0`).
- Consumers live in `apps/notifications/consumers.py`.
- Push events: order status updates, low-stock alerts, promotional flash notifications.
- Authentication: WebSocket connections validated via JWT/session middleware before joining groups.

### 3.5 REST API Conventions

- Base path: `/api/v1/`
- Pagination: cursor-based for product feeds, page-number for admin.
- Errors: `{ "detail": "...", "code": "ERROR_CODE" }` — consistent across all endpoints.
- COD workflow: `POST /api/v1/orders/` → status `pending_cod` → manual confirmation → `confirmed`.

---

## 4. Cross-Cutting Concerns

| Concern | Frontend | Backend |
|---------|----------|---------|
| Auth | HTTP-only cookies / JWT in memory | Django REST + SimpleJWT |
| Env vars | `.env.local` (never committed) | `.env` (never committed) |
| Types | Zod schemas + TypeScript interfaces | DRF serializers |
| Linting | ESLint + Prettier + Husky pre-commit | Ruff + Black |
| Testing | Vitest + Testing Library | pytest + pytest-django |

---

## 5. Master Build — Phase Execution Strategy

Phases are **sequential gates**. Do not start Phase N+1 until Phase N migrations pass, services are tested, and `agent.md` milestones are logged.

### Phase 1 — Database Models & Service Layer (Backend) `[ACTIVE]`

| Step | Action | Validation |
|------|--------|------------|
| 1 | Define ORM models in `apps/catalog/` and `apps/orders/` | `makemigrations` + `migrate` clean |
| 2 | Register Django admin for inventory visibility | Manual smoke in `/admin` |
| 3 | Implement `inventory_service.py` with `select_for_update()` | pytest: concurrent decrement, oversell rejection |
| 4 | Implement `order_service.py` with tracking + status FSM | pytest: create order, cancel restores stock |
| 5 | Guest favorites + express checkout APIs | pytest: session toggle, 4-field COD order |
| 6 | Export `InsufficientStockError` via `config/exceptions.py` | API handler returns `{ detail, code }` |

**Model contracts:**
- `Product`: UUID PK, indexed `slug`, soft-delete, `video_url`, JSON `image_urls` + relational `ProductImage`
- `ProductVariant`: color, SKU, `price_override`, `quantity_in_stock`, `safety_threshold`
- `Order`: `DRLNG-{YEAR}-{A-Z0-9}{4}` tracking, PK mobile `03XXXXXXXXX`, COD default
- `WishlistItem`: `user` OR `session_key` + `product` uniqueness

### Phase 2 — Next.js SSR Views & SEO `[COMPLETE]`

| Step | Action | Validation |
|------|--------|------------|
| 1 | Masonry PLP (Server Component) | Lighthouse mobile LCP < 2.5s |
| 2 | PDP `app/products/[slug]/page.tsx` + JSON-LD | Rich Results Test pass |
| 3 | Checkout drawer + wishlist (`'use client'`, RHF + Zod) | Phone regex live errors |
| 4 | `next/image` with explicit dimensions | CLS ≈ 0 |

### Phase 3 — API Integration & Real-Time `[COMPLETE]`

| Step | Action | Validation |
|------|--------|------------|
| 1 | Next.js `/api/*` route handlers proxy to Django | Wishlist session cookies forwarded |
| 2 | Client TanStack mutations use `useProxy: true` | Checkout + heart toggle via BFF |
| 3 | `NotificationService` on `transaction.on_commit` | pytest with `capture_on_commit_callbacks` |
| 4 | Admin dashboard at `/admin` + WebSocket hook | Live card on express checkout |

### Phase 4 — Online Payment Integrations `[POSTPONED — COD-only launch]`

JazzCash / EasyPaisa / Stripe adapters exist under `backend/gateways/` for future use. **Do not expose payment method UI** until launch strategy changes.

### Phase 5 — Courier & Fulfillment `[POSTPONED]`

Trax / Leopards integration deferred. Manual COD confirmation via Django admin + `/admin` WebSocket feed is sufficient for launch.

---

## 7. Open-Source JWT Cookie Authentication

Darling uses **django-allauth + dj-rest-auth + djangorestframework-simplejwt** — fully self-hosted, no Clerk/Auth0.

### 7.1 Token Flow

```
Browser → Next.js BFF (/api/auth/*) → Django (/api/auth/*)
                ↓
     HttpOnly cookies set on response:
     - darling-access-token  (short-lived JWT)
     - darling-refresh-token (rotated on refresh)
```

- **Never** store JWTs in `localStorage` or log them to the console.
- Next.js route handlers proxy auth requests and forward `Set-Cookie` headers from Django unchanged.
- Client mutations use `credentials: "include"` via `http-client.adapter.ts`.

### 7.2 Social OAuth Exchange

1. Client opens Google GSI / Facebook SDK popup → receives provider `access_token`.
2. `POST /api/auth/callback` (Next.js) forwards `{ access_token }` to Django:
   - `POST /api/auth/google/` or `POST /api/auth/facebook/`
3. Django allauth validates token with provider, creates/links user, returns JWT pair in cookies.
4. TanStack Query invalidates `queryKeys.authUser`.

### 7.3 JWT Rotation

- `ROTATE_REFRESH_TOKENS: True` in `SIMPLE_JWT` settings.
- On refresh, Django issues a new refresh token; old one is invalidated.
- `JWT_AUTH_HTTPONLY=True`, `JWT_AUTH_SECURE=not DEBUG`, `SameSite=Lax`.

### 7.4 Staff Admin CRUD

- Product admin API: `GET/POST /api/v1/catalog/admin/products/` (staff only).
- Frontend panel: `/admin/catalog` — requires staff JWT from login.

---

## 6. SDD Workflow Checklist

Before implementing any feature:

1. Update `agent.md` → **Current Goal** with the feature spec.
2. Define Zod schemas (frontend) and DRF serializers (backend) first.
3. Write repository interfaces before adapters.
4. Implement service layer before views/routes.
5. Add JSON-LD / metadata if the feature is user-facing.
6. Mark milestone complete in `agent.md` → **Completed Milestones**.

---

*Last updated: 2026-06-22 — Open-source auth pipeline + Khaadi landing.*
