# AI Knowledge Platform Frontend (Next.js)

This is the new Next.js frontend foundation for the existing FastAPI backend in this repository.

## What is implemented

- App Router + TypeScript + Tailwind setup
- Auth baseline:
  - Login page (`/login`)
  - Register page (`/register`)
  - Protected dashboard route (`/dashboard`)
  - Client auth context with token storage
  - Next middleware guard for protected/auth routes
- FastAPI integration baseline:
  - `POST /api/auth/login`
  - `POST /api/auth/register`
  - `GET /api/health`
  - `GET /api/models`

## Run locally

1) Install dependencies:

```bash
npm install
```

2) Configure env:

```bash
cp .env.example .env.local
```

3) Start dev server:

```bash
npm run dev
```

4) Open:

- [http://localhost:3000/login](http://localhost:3000/login)
- [http://localhost:3000/register](http://localhost:3000/register)
- [http://localhost:3000/dashboard](http://localhost:3000/dashboard)

## Environment variables

- `NEXT_PUBLIC_BACKEND_API_URL` (default: `http://127.0.0.1:8000/api`)

Note: the frontend calls a same-origin proxy route (`/api/backend/*`) that forwards to this backend URL. This is more resilient against browser extension fetch interception and avoids CORS issues in development.

## Next steps (recommended)

- Migrate Streamlit pages feature-by-feature:
  - Chat
  - Documents
  - Prompts
  - Conversations
  - Analytics dashboards
- Move to HTTP-only cookie auth from backend for stronger security in production.
