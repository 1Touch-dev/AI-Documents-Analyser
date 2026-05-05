# 🧠 AI Business Intelligence Platform

A production-grade, SaaS-ready platform for automated document analysis and business intelligence. Transform raw documents (PDF, Excel, Word) into actionable executive insights with a single click.

---

## 🚀 The Product Experience

This platform is designed for **Business Users**, not just engineers. It follows a simple, high-impact workflow:

1.  **📂 Intelligent Ingestion**: Upload documents; AI automatically categorizes them (F&B, Ticketing, Retail, etc.).
2.  **💬 AI Assistant**: Chat with your document knowledge base in plain English with translation and currency conversion.
3.  **⚡ One-Click Analysis**: Run complex business intelligence workflows (Financial, Strategy, Operations) across your entire data set.
4.  **📊 Executive Insights**: View structured summaries, key findings, risks, and actionable recommendations.
5.  **📑 Report Vault**: Access, manage, and export your history of saved reports in JSON/CSV formats.
6.  **🔌 MCP Orchestration**: Seamlessly integrate AI tools and workflows via the Model Context Protocol (MCP).

---

## 🛠️ Technology Stack

- **Frontend**: Next.js (Tailwind, Lucide, Recharts) - *Premium Glassmorphism UI*
- **Backend**: FastAPI (Python 3.10+)
- **Database**: PostgreSQL (Relational) + ChromaDB (Vector Store)
- **AI Engine**: OpenAI GPT-4o & AWS Bedrock (Universal Multi-Model Router)
- **Protocols**: Model Context Protocol (MCP) for tool & skill execution
- **Security**: RBAC (Admin/Analyst/Viewer), Audit Logs, Rate Limiting

---

## 📖 Quick Start

### 1. Configure Environment
```bash
cp .env.example .env
# Edit .env with your OpenAI API Key and AWS Credentials
```

### 2. Launch with Docker
```bash
docker compose up --build -d
```

### 3. Access the Platform
- **UI**: [http://localhost:3000](http://localhost:3000)
- **API Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **MCP Endpoint**: `POST /api/mcp/execute`

---

## 📂 Core Business Modules

| Module | Purpose |
|---|---|
| **Executive Dashboard** | High-level KPI tracking, document distribution, and system health. |
| **Document Management** | Categorized document vault with AI auto-classification and indexing tracking. |
| **Business Intelligence** | One-click analysis engine using Workflows and Skills. |
| **Report Vault** | Persistent history of analysis results with BI-compatible exports. |
| **AI Assistant** | Natural language interface with advanced model selection (OpenAI/Bedrock). |
| **Usage & Audit** | Enterprise-grade cost tracking (USD estimates) and security logging. |

---

## 🔧 Key System Features
- **MCP Server**: Real JSON-RPC 2.0 tool execution. Exposes all Skills as callable tools.
- **Universal LLM Router**: Seamless switching between OpenAI and AWS Bedrock models.
- **One-Click Workflows**: Intent-based analysis that maps user queries to multi-step pipelines.
- **SaaS Readiness**: Integrated rate limiting, audit logging, and role-based access control.

---

## 📄 Documentation
- 🚀 **[Deployment Manual](Documents/deployment%20manual.md)**: Installation & Cloud setup.
- 📖 **[User Manual](Documents/user%20manual.md)**: How to use the business features.
- 🔌 **[MCP Overview](backend/mcp/README.md)**: Technical details of the tool execution server.

---
MIT License. Created for high-performance business intelligence.
