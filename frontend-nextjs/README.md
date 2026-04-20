# AI Knowledge Platform Frontend (Next.js)

This is the active frontend for the current `feature/business-features-v1` branch.
It talks to the FastAPI backend and uses the backend's GPT-only runtime for chat,
translation, report generation, and financial extraction.

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
  - `POST /api/query`
  - `POST /api/analytics/financial_dashboard`
  - `GET /api/documents/status`

## Current branch features

- Chat page with:
  - translation toggle
  - currency selector
  - GPT-backed query flow
- Analytics page with:
  - financial extraction button
  - table + bar chart
- Documents page with:
  - document status check
- Protected app routes using the existing auth flow

## Run locally

1. Install dependencies:

```bash
npm install
```

2. Configure env:

```bash
cat <<'EOF' > .env.local
NEXT_PUBLIC_BACKEND_API_URL=http://127.0.0.1:8010/api
EOF
```

3. Start dev server:

```bash
npm run dev -- --hostname 0.0.0.0 --port 3000
```

4. Open:

- [http://localhost:3000/login](http://localhost:3000/login)
- [http://localhost:3000/register](http://localhost:3000/register)
- [http://localhost:3000/dashboard](http://localhost:3000/dashboard)
- [http://localhost:3000/chat](http://localhost:3000/chat)
- [http://localhost:3000/analytics](http://localhost:3000/analytics)
- [http://localhost:3000/documents](http://localhost:3000/documents)

## Environment variables

- `NEXT_PUBLIC_BACKEND_API_URL`
  Recommended local value: `http://127.0.0.1:8010/api`

Note: the frontend calls a same-origin proxy route (`/api/backend/*`) that forwards to this backend URL. This is more resilient against browser extension fetch interception and avoids CORS issues in development.

## Backend dependency

- The backend must be running separately on port `8010`.
- The backend now requires a valid `OPENAI_API_KEY` for GPT-powered features.
- Internet/API access is required for local testing of chat, translation, reports, and financial extraction.
