# Darling — Cursor Agent Coding Standards

> Explicit instructions for AI agents and developers using Cursor in this repository.
> Zero tolerance for messy, incomplete, or untyped code blocks.

---

## 1. Absolute Rules (Non-Negotiable)

1. **No incomplete logic.** Every function, hook, service, and view must be fully implemented or explicitly marked with a `// TODO(DARLING-XXX):` ticket reference. Never leave stub bodies, empty catch blocks, or `pass` without context.
2. **No `any` in TypeScript.** Use `unknown` + type guards, generics, or Zod inference. ESLint `@typescript-eslint/no-explicit-any` is set to `error`.
3. **No business logic in views or page components.** Frontend pages delegate to use-cases; backend views delegate to services.
4. **No direct ORM calls in Django views.** All database access goes through repository modules.
5. **No client-side-only validation.** Every form field validated on the client must be re-validated on the server.
6. **No secrets in source code.** Environment variables only; `.env*` files are gitignored.
7. **No force-push to main.** Feature branches only until blueprint is locked.

---

## 2. TypeScript Standards (Frontend)

```typescript
// ✅ CORRECT — explicit return type, Zod-inferred props
interface ProductCardProps {
  product: Product;
  priority?: boolean;
}

export function ProductCard({ product, priority = false }: ProductCardProps): JSX.Element {
  return (/* ... */);
}

// ❌ WRONG — implicit any, inline untyped props
export function ProductCard(props) {
  return <div onClick={() => props.onClick()} />;
}
```

### File Naming

| Type | Convention | Example |
|------|------------|---------|
| Components | PascalCase | `ProductCard.tsx` |
| Hooks | camelCase, `use` prefix | `useCart.ts` |
| Schemas | camelCase + `.schema.ts` | `checkout.schema.ts` |
| Repositories | PascalCase + `.repository.ts` | `ProductRepository.ts` |
| Adapters | PascalCase + `.adapter.ts` | `HttpProductAdapter.ts` |
| Use-cases | camelCase + `.use-case.ts` | `addToCart.use-case.ts` |

### Import Order

1. React / Next.js
2. Third-party libraries
3. `@/domain/*`
4. `@/use-cases/*`
5. `@/repositories/*`
6. `@/adapters/*`
7. `@/components/*`
8. Relative imports

---

## 3. Python Standards (Backend)

```python
# ✅ CORRECT — typed service with explicit transaction boundary
from django.db import transaction

class OrderService:
    @staticmethod
    @transaction.atomic
    def create_cod_order(*, user: User, payload: dict) -> Order:
        ...

# ❌ WRONG — ORM in view, no type hints, bare except
def create_order(request):
    try:
        order = Order.objects.create(**request.data)
    except:
        pass
```

- Use `from __future__ import annotations` in all new Python files.
- Type-hint all function signatures. Use `TypedDict` or dataclasses for structured payloads.
- Format with **Black** (line length 88). Lint with **Ruff**.
- Docstrings on public service methods only — not on every private helper.

---

## 4. Mobile-First Responsive Requirements

Every UI component must be designed and coded mobile-first:

```tsx
// ✅ CORRECT — mobile base, progressive enhancement
<div className="grid grid-cols-2 gap-3 px-4 sm:grid-cols-3 md:grid-cols-4 lg:gap-6 lg:px-8">

// ❌ WRONG — desktop-first with max-width overrides
<div className="grid grid-cols-4 max-md:grid-cols-2">
```

- Touch targets: minimum `44×44px` for all interactive elements.
- Font sizes: base `16px` on mobile (never below `14px` for body text).
- Test layouts at `375px` (iPhone SE) before any desktop breakpoint.

---

## 4.1 Premium Luxury Aesthetic Guardrails (darling.pk)

Darling targets a **high-luxury, female-forward** brand. All UI must feel editorial, not marketplace-generic.

| Token | Guidance |
|-------|----------|
| Palette | Soft neutrals (`stone`, `rose`, `cream`), restrained accent (dusty rose / champagne gold) — never saturated primaries |
| Typography | Serif display for headings (`font-serif` or brand face), clean sans for body; generous letter-spacing on labels |
| Spacing | Extra whitespace on mobile; `py-12`+ section rhythm; avoid cramped product grids |
| Motion | Aceternity fade/float **below the fold only** — hero must stay static for LCP |
| Imagery | Full-bleed hero crops, subtle rounded corners (`rounded-xl` max), no harsh drop shadows |
| Touch | Primary CTAs full-width on mobile; secondary actions as ghost/outline buttons |
| Favorites | Heart icon on PLP/PDP — **one tap**, no login modal; optimistic UI |
| Checkout | `/checkout` page or Buy It Now drawer — 4 delivery fields + COD selected; Card/JazzCash/EasyPaisa shown Coming soon until Phase 4 |

```tsx
// ✅ CORRECT — guest heart toggle (client molecule)
<button
  type="button"
  aria-pressed={favorited}
  aria-label={favorited ? 'Remove from favorites' : 'Add to favorites'}
  onClick={() => toggleFavorite(product.id)}
  className="h-11 w-11 rounded-full"
>
  <HeartIcon filled={favorited} />
</button>

// ✅ CORRECT — editorial product card
<article className="group space-y-3 px-1">
  <div className="relative aspect-[3/4] overflow-hidden rounded-xl bg-stone-100">
    <Image … className="object-cover transition-transform duration-700 group-hover:scale-105" />
  </div>
  <h3 className="font-serif text-base tracking-wide text-stone-900">{title}</h3>
  <p className="text-sm text-stone-500">{price}</p>
</article>
```

---

## 5. Server / Client Component Rules

| Needs | Component Type | Location |
|-------|---------------|----------|
| `useState`, `useEffect`, event handlers | Client | `components/client/` |
| Data fetch, metadata, JSON-LD | Server | `app/` or `components/server/` |
| Form with RHF | Client wrapper | `components/client/forms/` |
| Static layout shells | Server | `app/layout.tsx` |

- Never import a Client Component into a Server Component's render tree without it being a leaf node.
- Pass serializable props only across the server/client boundary (no functions, no class instances).

---

## 6. Error Handling

### Frontend

```typescript
// adapters/http-client.adapter.ts
export async function apiFetch<T>(url: string, options?: RequestInit): Promise<T> {
  const response = await fetch(url, options);
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
    throw new ApiError(response.status, error.detail ?? 'Request failed');
  }
  return response.json() as Promise<T>;
}
```

- TanStack Query: use `onError` callbacks to surface toast notifications via Shadcn Toast.
- Error boundaries on route segments that fetch critical data.

### Backend

```python
# Consistent API error responses
from rest_framework.exceptions import APIException

class InsufficientStockError(APIException):
    status_code = 400
    default_detail = "Insufficient stock for one or more items."
    default_code = "insufficient_stock"
```

- Never return raw tracebacks in production responses.
- Log exceptions with structured logging (`structlog` or Python `logging` with JSON formatter).

---

## 7. Git Hooks — Husky Pre-Commit

Frontend pre-commit pipeline (configured in `frontend/.husky/pre-commit`):

```bash
npx lint-staged
```

`lint-staged` runs:
- ESLint `--fix` on `*.{ts,tsx}`
- Prettier `--write` on `*.{ts,tsx,json,css,md}`

**Agents must not bypass hooks.** If lint fails, fix the code — do not use `--no-verify`.

---

## 8. Commit Message Format

```
type(scope): concise description

feat(catalog): add product JSON-LD server component
fix(orders): correct DRLNG tracking number sequence reset
chore(deps): bump next to 16.2.9
docs(agent): log monorepo initialization milestone
```

Types: `feat`, `fix`, `chore`, `docs`, `refactor`, `test`, `style`

---

## 9. Agent Behavior in Cursor

When working in this repo, agents must:

1. Read `agent.md` first to understand current goal and system state.
2. Read `skills.md` before implementing any feature in an unfamiliar layer.
3. Follow the Clean Architecture dependency rule — never shortcut across layers.
4. Update `agent.md` after completing any milestone.
5. Stop and ask for developer validation before implementing business feature routes (per SDD model).
6. Prefer editing existing files over creating new ones unless the architecture demands it.
7. Run linter after substantive edits and fix all introduced errors.

---

## 10. Environment Variables Reference

### Frontend (`.env.local`)

```
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
NEXT_PUBLIC_WS_URL=ws://localhost:8000/ws
NEXT_PUBLIC_SITE_URL=http://localhost:3000
```

### Backend (`.env`)

```
DEBUG=True
SECRET_KEY=change-me-in-production
DATABASE_URL=postgresql://user:pass@host/db?sslmode=require
REDIS_URL=redis://127.0.0.1:6379/0
ALLOWED_HOSTS=localhost,127.0.0.1
CORS_ALLOWED_ORIGINS=http://localhost:3000
```

---

*Enforced by ESLint, Ruff, Husky, and code review. No exceptions without explicit team approval.*
