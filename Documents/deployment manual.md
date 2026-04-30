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
- **OpenAI API Key** — required for all GPT features (chat, translation, reports, financial extraction). Get one at [platform.openai.com](https://platform.openai.com).
- **AWS Account** — required for S3 document storage **and** Bedrock multi-model access. The system falls back to local disk when S3 is not configured (not recommended for production).

---

## AWS Bedrock Setup

### 1. Enable Bedrock Model Access

AWS Bedrock models must be explicitly enabled per AWS account before they can be called.

1. Open the [AWS Bedrock console](https://console.aws.amazon.com/bedrock/)
2. Navigate to **Model Access** → **Manage model access**
3. Enable the following model families:
   - ✅ **Anthropic** — Claude Opus 4.x, Sonnet 4.x, Haiku
   - ✅ **Amazon** — Nova Micro, Nova Lite, Nova Pro
   - ✅ **Meta** — Llama 3 (8B, 70B)
   - ✅ **Mistral** — Mistral Large, Mixtral 8x7B
   - ✅ **Cohere** — Command R+
4. Wait 1–5 minutes for access to propagate.

### 2. Required IAM Permissions

Attach the following policy to the IAM user / role used by the platform:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "BedrockConverse",
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
    }
  ]
}
```

The same `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` used for S3 can be used for Bedrock — just add the policy above to the same IAM user.

### 3. Environment Variables for Bedrock

Add to your `.env`:

```ini
# ── AWS Bedrock ───────────────────────────────────────────
AWS_ACCESS_KEY_ID=your_aws_access_key        # same key as S3
AWS_SECRET_ACCESS_KEY=your_aws_secret_key    # same key as S3
AWS_REGION=us-east-1                          # Bedrock region (us-east-1 recommended)
BEDROCK_DEFAULT_MODEL=nova-lite               # default model when provider=bedrock
```

### 4. Verify Bedrock Access

```bash
# From the server, test with AWS CLI:
aws bedrock-runtime converse \
  --model-id amazon.nova-lite-v1:0 \
  --messages '[{"role":"user","content":[{"text":"Hello"}]}]' \
  --region us-east-1

# Or via the platform API:
curl -X POST http://localhost:8000/api/skills/run \
  -H "Content-Type: application/json" \
  -d '{"skill":"report_generation","input":{},"provider":"bedrock"}'
```

### 5. Supported Bedrock Models

| Friendly Name | Bedrock Model ID | Provider | Use Case |
|---|---|---|---|
| `nova-micro` | `amazon.nova-micro-v1:0` | Amazon | Fastest, cheapest |
| `nova-lite` | `amazon.nova-lite-v1:0` | Amazon | Fast + multimodal |
| `nova-pro` | `amazon.nova-pro-v1:0` | Amazon | Highest quality Nova |
| `claude-sonnet-4.6` | `us.anthropic.claude-sonnet-4-5-20251203-v1:0` | Anthropic | Balanced |
| `claude-haiku` | `us.anthropic.claude-haiku-3-5-20241022-v1:0` | Anthropic | Fast |
| `claude-opus-4.6` | `us.anthropic.claude-opus-4-5-20251101-v1:0` | Anthropic | High reasoning |
| `claude-opus-4.7` | `us.anthropic.claude-opus-4-7-20260416-v1:0` | Anthropic | Latest flagship |
| `llama3-70b` | `us.meta.llama3-70b-instruct-v1:0` | Meta | Open weights |
| `llama3-8b` | `us.meta.llama3-8b-instruct-v1:0` | Meta | Lightweight |
| `mistral-large` | `mistral.mistral-large-2402-v1:0` | Mistral | Strong reasoning |
| `mixtral-8x7b` | `mistral.mixtral-8x7b-instruct-v0:1` | Mistral | MoE efficiency |
| `cohere-command-r+` | `cohere.command-r-plus-v1:0` | Cohere | RAG-optimised |

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
