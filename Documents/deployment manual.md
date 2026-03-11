# AI Knowledge Platform — Deployment Manual

This manual provides step-by-step instructions to deploy the AI Knowledge Platform. The application has been designed as a fully containerized, production-ready stack using Docker.

---

## 1. System Requirements

The platform runs a lightweight, robust microservice architecture but integrates a Local AI Model (`Llama 3.2 3B`) and a local Embedding Model by default.

### Minimum Specifications:
- **CPU:** 2+ vCPUs
- **RAM:** 8 GB minimum (Required to run the 3B parameter local LLM and embedding models in memory).
- **Storage:** 50 GB SSD (For operating system, Docker images, database volumes, and vector store data).
- **OS:** Any Linux distribution (Ubuntu 22.04+ recommended) or macOS.

### Recommended AWS EC2 Instance:
- **Instance Type:** `t3a.large` or `t3.large` (2 vCPU, 8 GB RAM).
- **Purchasing Option:** Spot Instance (for minimal cost, ~$15-18/month).

---

## 2. Prerequisites Setup

Before deploying the application, ensure the host machine has the following tools installed.

### Install Docker & Docker Compose plugin
On Ubuntu/Debian:
```bash
sudo apt update
sudo apt install -y docker.io docker-compose-v2
sudo systemctl enable --now docker
sudo usermod -aG docker $USER
# (Log out and back in for group changes to take effect)
```

### Install Ollama (For Local Models)
Ollama serves the local LLM used by the platform.
```bash
curl -fsSL https://ollama.com/install.sh | sh

# Pull the default Llama 3 model
ollama pull llama3.2
```

---

## 3. Clone and Configure the Application

### 1. Clone the Repository
Clone the application code to your deployment server:
```bash
git clone <your-repository-url> ai-knowledge-platform
cd ai-knowledge-platform
```

### 2. Configure Environment Variables
You must configure the application secrets and AWS connectivity. The application expects an AWS S3 bucket to store uploaded documents securely.

```bash
cp .env.example .env
nano .env
```

Ensure the following variables are correctly populated:
```ini
# PostgreSQL (Change the password for production!)
DATABASE_URL=postgresql://postgres:postgres@db:5432/ai_platform
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_secure_password
POSTGRES_DB=ai_platform

# AWS S3 Configuration
AWS_ACCESS_KEY_ID=your_aws_access_key
AWS_SECRET_ACCESS_KEY=your_aws_secret_key
AWS_REGION=us-east-1
S3_BUCKET_NAME=your-bucket-name

# Security
JWT_SECRET_KEY=generate_a_random_secure_string
```

---

## 4. Deploying the Stack

Once Docker is installed and `.env` is configured, deploying the entire stack takes a single command. This will build both the FastAPI backend and the Streamlit frontend, and provision the Postgres and ChromaDB databases.

```bash
docker compose up --build -d
```

### Verification
Wait 1-2 minutes for the databases to initialize, then verify the services:
```bash
docker compose ps
```
You should see 4 containers running:
1. `ai-frontend` (Port 8501)
2. `ai-backend` (Port 8000)
3. `ai-db` (Port 5432)
4. `ai-chroma` (Port 8001)

---

## 5. Accessing the Platform

If deploying on a local machine or a cloud server with a Public IP, open your web browser and navigate to:

- **Main Application (Streamlit UI):** `http://<your-server-ip>:8501`
- **Backend API Docs (FastAPI):** `http://<your-server-ip>:8000/docs`

> **Firewall Note:** Ensure that TCP Port **8501** is open in your AWS Security Group, DigitalOcean Firewall, or local firewall (e.g., `sudo ufw allow 8501`).

---

## 6. (Optional) Local Development Deployment Without Docker

If you wish to run the app directly on your host machine for development:

1. **Install Python 3.11+**
2. **Setup Virtual Environment:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```
3. **Start PostgreSQL Locally** (e.g., via Homebrew or Docker run).
4. **Start the Backend:**
   ```bash
   uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
   ```
5. **Start the Frontend (in a new terminal):**
   ```bash
   streamlit run frontend/streamlit_app.py
   ```
