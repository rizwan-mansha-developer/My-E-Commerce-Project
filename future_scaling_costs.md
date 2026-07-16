# Darling — Scaling Costs & Infrastructure Philosophy

> Darling is built on a **$0-at-scale open-source stack**. This document tracks current guarantees and future paid components before any vendor contract is signed.

---

## Current Stack — Zero Marginal Auth & API Cost

| Component | Choice | Scaling Cost |
|-----------|--------|--------------|
| Authentication | django-allauth + dj-rest-auth + SimpleJWT (self-hosted) | **$0** |
| API / WebSocket | Django + Uvicorn on your VPS/container | Infra only |
| Database | Neon Postgres (free tier → paid tier by usage) | Usage-based |
| Frontend | Next.js on Vercel/self-host | Plan-dependent |
| OAuth | Google & Meta developer apps | **$0** (within free quotas) |

Social login tokens are exchanged server-side. JWT access/refresh tokens live in **HttpOnly cookies** (`darling-access-token`, `darling-refresh-token`) — no Clerk, Auth0, or Firebase Auth fees as customer count grows.

---

## Explicitly Deferred Paid Services

These are **not** in the launch path. Evaluate here before signing:

| Service | Trigger | Estimated Cost Driver |
|---------|---------|---------------------|
| SMS OTP (COD phone verify) | Fraud spike on COD orders | Per-SMS gateway (Jazz, Twilio, etc.) |
| Premium courier webhooks | Auto tracking at scale | Trax/Leopards API tiers |
| Payment gateways | Online payments enabled | MDR per transaction (JazzCash, Stripe) |
| Email transactional (SendGrid/Resend) | High-volume lifecycle email | Per 1k emails |
| CDN / image optimization | Global traffic | Bandwidth |
| **S3 product media** | Admin image upload (configured) | AWS storage + egress |

---

## Decision Rule

1. Prefer self-hosted open-source when security parity exists.
2. Document any new SaaS in this file with **why**, **cost model**, and **exit plan**.
3. Never add auth SaaS — JWT cookie rotation is handled in-house.

---

*Last updated: 2026-06-22 — Open-source Google/Meta auth pipeline.*
