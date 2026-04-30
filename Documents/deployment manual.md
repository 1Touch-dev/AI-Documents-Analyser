# AI Knowledge Platform — Deployment Manual

This manual provides step-by-step instructions to deploy the AI Knowledge Platform on an AWS EC2 instance or any Linux server. The application uses Docker Compose for production deployment.

---

## 1. System Requirements

The platform is API-first: all language model generation runs through the **OpenAI GPT API** — no local LLM is required. Hardware requirements are therefore minimal.

### Minimum Specifications
| Resource | Minimum | Recommended |
|---|---|---|
| CPU | 2 vCPU | 4 vCPU |
| RAM | 4 GB | 8 GB |
| Storage | 20 GB SSD | 50 GB SSD |
| OS | Ubuntu 22.04+ | Ubuntu 22.04 LTS |

> **Note:** The embedding model runs locally for vector search. The default is `BAAI/bge-base-en-v1.5` (~440 MB, 768-dim). For higher quality embeddings, override with `EMBEDDING_MODEL=BAAI/bge-large-en-v1.5` (~1.2 GB, 1024-dim). No GPU is required for either model.

### Recommended AWS EC2 Instance
- **Instance Type:** `t3.medium` (2 vCPU, 4 GB RAM) — sufficient for most workloads
- **Instance Type:** `t3.large` (2 vCPU, 8 GB RAM) — recommended for concurrent users or bge-large model
- **Storage:** 30 GB GP3 EBS volume

---

## 2. Prerequisites

### Install Docker & Docker Compose
```bash
sudo apt update && sudo apt install -y docker.io docker-compose-v2
sudo systemctl enable --now docker
sudo usermod -aG docker $USER
# Log out and back in for group changes to take effect
```

### Required External Accounts
- **OpenAI API Key** — required for all GPT features when using the OpenAI provider. Get one at [platform.openai.com](https://platform.openai.com).
- **AWS Account** — required for S3 document storage **and** Bedrock multi-model generation. Both use the same IAM credentials.

---

## AWS Bedrock Setup

### 1. Enable Model Access in the AWS Console

1. Open [AWS Bedrock → Model Access](https://console.aws.amazon.com/bedrock/home#/modelaccess)
2. Click **Manage model access** and enable:
   - Anthropic (Claude Opus, Sonnet, Haiku)
   - Amazon (Nova Micro, Lite, Pro)
   - Meta (Llama 3)
   - Mistral (Mistral Large, Mixtral)
   - Cohere (Command R+)
3. Wait 1–5 minutes for access to propagate.

### 2. IAM Permissions

Add this policy to the IAM user used by the platform:

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": [
      "bedrock:InvokeModel",
      "bedrock:InvokeModelWithResponseStream",
      "bedrock:Converse",
      "bedrock:ConverseStream"
    ],
    "Resource": [
      "arn:aws:bedrock:*::foundation-model/*",
      "arn:aws:bedrock:*:*:inference-profile/*"
    ]
  }]
}
```

> The same `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` used for S3 work for Bedrock — just attach the policy above.

### 3. Environment Variables

```ini
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret
AWS_REGION=us-east-1
BEDROCK_DEFAULT_MODEL=amazon.nova-lite-v1:0   # used when provider=bedrock and no model given
AWS_BEARER_TOKEN_BEDROCK=                      # optional: for enterprise/SSO setups
```

### 4. Region Constraints

- **Cross-region inference profiles** (model IDs prefixed `us.`) work in `us-east-1` and `us-west-2`.
- Direct model IDs (e.g. `amazon.nova-lite-v1:0`) are region-specific — ensure you are in the correct region.
- Recommended region: **us-east-1** (widest model availability).

### 5. Using Custom / New Models

No code change is needed. Pass the model ID directly in any API request:

```bash
curl -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Summarize this document",
    "provider": "bedrock",
    "model": "us.anthropic.claude-opus-4-7-20260416-v1:0"
  }'
```

The Converse API passes the `model` field straight through — any valid Bedrock model ID is accepted without updating a whitelist.

### 6. Verify Bedrock Access

```bash
# Quick connectivity test via the platform API
curl -X POST http://localhost:8000/api/skills/run \
  -H "Content-Type: application/json" \
  -d '{"skill":"report_generation","input":{},"provider":"bedrock","model":"amazon.nova-lite-v1:0"}'
# Expected: {"skill":"report_generation","result":{...}}
```

---

## 3. Clone and Configure

### 1. Clone the Repository
```bash
git clone <your-repository-url> ai-knowledge-platform
cd ai-knowledge-platform
```

### 2. Configure Environment Variables
```bash
cp .env.example .env
nano .env
```

Populate these required values:

```ini
# ── Database ─────────────────────────────────────────────────────
DATABASE_URL=postgresql://postgres:your_secure_password@db:5432/ai_knowledge_platform
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_secure_password
POSTGRES_DB=ai_knowledge_platform

# ── OpenAI (Required for all GPT features) ───────────────────────
OPENAI_API_KEY=sk-your-openai-key

# ── AWS S3 (Required for production document storage) ────────────
AWS_ACCESS_KEY_ID=your_aws_access_key
AWS_SECRET_ACCESS_KEY=your_aws_secret_key
AWS_REGION=us-east-1
S3_BUCKET_NAME=your-bucket-name

# ── Redis (Query caching — 100× speedup on repeated queries) ─────
REDIS_URL=redis://redis:6379/0

# ── Auth ─────────────────────────────────────────────────────────
SECRET_KEY=generate_a_long_random_string_here

# ── Embeddings (Optional — defaults to bge-base-en-v1.5) ─────────
# Uncomment for higher quality embeddings (uses ~1.2 GB RAM):
# EMBEDDING_MODEL=BAAI/bge-large-en-v1.5
```

---

## 4. Deploy the Stack

```bash
docker compose up --build -d
```

Wait 60–90 seconds for databases to initialise, then verify:

```bash
docker compose ps
```

Expected running containers:

| Container | Port | Purpose |
|---|---|---|
| `ai-backend` | 8010 | FastAPI backend |
| `ai-frontend` | 3001 | Next.js frontend |
| `ai-db` | 5432 | PostgreSQL |
| `ai-chroma` | 8001 | ChromaDB vector store |
| `ai-redis` | 6379 | Redis cache |

---

## 5. Accessing the Platform

| Service | URL |
|---|---|
| Main Application (Next.js UI) | `http://<your-server-ip>:3001` |
| Backend API Docs (Swagger) | `http://<your-server-ip>:8010/docs` |
| Health Check | `http://<your-server-ip>:8010/api/health` |
| Currency Detection | `http://<your-server-ip>:8010/api/detect_currency` |

> **Firewall Note:** Open TCP ports **3001** and **8010** in your AWS Security Group. Port **8501** (legacy Streamlit) is no longer used.

---

## 6. Local Development (Without Docker)

### First-Time Setup
```bash
cd /home/ubuntu/AI-Documents-Analyser
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env — add OPENAI_API_KEY at minimum
```

### Start Services

**Terminal 1 — Backend (port 8010):**
```bash
cd /home/ubuntu/AI-Documents-Analyser
source .venv/bin/activate
uvicorn backend.main:app --host 0.0.0.0 --port 8010
```

**Terminal 2 — Frontend (port 3001):**
```bash
cd /home/ubuntu/AI-Documents-Analyser/frontend-nextjs
npm install       # first time only
npm run build     # first time or after code changes
npm run start -- --hostname 0.0.0.0 --port 3001
```

### Health Checks
```bash
curl -sS http://localhost:8010/api/health
# → {"status":"healthy","app":"AI Knowledge Platform"}

curl -sS http://localhost:8010/api/detect_currency
# → {"currency":"BRL","confidence":"high","counts":{"BRL":1224}}

curl -o /dev/null -w "%{http_code}" http://localhost:3001
# → 200
```

### Clean Restart
```bash
pkill -f "uvicorn backend.main:app" || true
pkill -f "next.*3001" || true
```

---

## 7. Key Environment Variables Reference

| Variable | Required | Default | Description |
|---|---|---|---|
| `OPENAI_API_KEY` | **Yes** | — | GPT API key for all AI features |
| `DATABASE_URL` | Yes | `postgresql://...` | PostgreSQL connection string |
| `REDIS_URL` | No | `redis://localhost:6379/0` | Redis for query caching |
| `S3_BUCKET_NAME` | No* | — | AWS S3 bucket for documents |
| `AWS_ACCESS_KEY_ID` | No* | — | AWS credentials |
| `SECRET_KEY` | Yes | `change-me` | JWT signing secret |
| `EMBEDDING_MODEL` | No | `BAAI/bge-base-en-v1.5` | Local embedding model (override to `bge-large-en-v1.5` for higher quality) |
| `VECTOR_STORE_TYPE` | No | `chroma` | `chroma` or `qdrant` |
| `CHUNK_SIZE` | No | `1000` | Document chunk size (chars) |

> *S3 falls back to local `data/uploads/` directory when not configured.

---

## 8. Architecture Diagram

```
┌──────────────────┐      ┌──────────────────┐      ┌──────────────────┐
│  Next.js (React) │─────▶│   FastAPI        │─────▶│   PostgreSQL     │
│  frontend-nextjs │      │   backend        │      │   :5432          │
│  :3001           │      │   :8010          │      └──────────────────┘
└──────────────────┘      └──────┬───────────┘
                                 │
                    ┌────────────┼────────────┐
                    ▼            ▼            ▼
              ┌──────────┐  ┌──────────┐  ┌──────────┐
              │ ChromaDB │  │ OpenAI   │  │  Redis   │
              │ :8001    │  │ GPT API  │  │  :6379   │
              └──────────┘  └──────────┘  └──────────┘
```

> **No local LLM required.** All generation runs through the OpenAI GPT API.
