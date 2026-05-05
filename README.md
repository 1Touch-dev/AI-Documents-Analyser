# 🧠 AI Business Intelligence Platform

A production-grade, SaaS-ready platform for automated document analysis and business intelligence. Transform raw documents (PDF, Excel, Word) into actionable executive insights with a single click.

---

## 🚀 The Product Experience

This platform is designed for **Business Users**, not just engineers. It follows a simple, high-impact workflow:

1.  **📂 Intelligent Ingestion**: Upload documents; AI automatically categorizes them (F&B, Ticketing, Retail, etc.).
2.  **💬 AI Assistant**: Chat with your document knowledge base in plain English.
3.  **⚡ One-Click Analysis**: Run complex business intelligence workflows across your entire data set with a single search.
4.  **📊 Executive Insights**: View structured summaries, key findings, risks, and actionable recommendations.
5.  **📑 Report Vault**: Access, manage, and export your history of saved reports in JSON/CSV formats.

---

## 🛠️ Technology Stack

- **Frontend**: Next.js (Tailwind, Lucide, Recharts, GSAP) - *Premium Glassmorphism UI*
- **Backend**: FastAPI (Python 3.10+)
- **Database**: PostgreSQL (Relational data) + ChromaDB (Vector Knowledge Base)
- **AI Engine**: OpenAI GPT-4o & AWS Bedrock (Universal Multi-Model Router)
- **Storage**: AWS S3 (Scalable document storage)

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
- **API Docs**: [http://localhost:8010/docs](http://localhost:8010/docs)

---

## 📂 Core Business Modules

| Module | Purpose |
|---|---|
| **Executive Dashboard** | High-level KPI tracking and system health. |
| **Document Management** | Categorized, searchable document vault with AI auto-classification. |
| **Business Analysis** | One-click intelligence engine for Financials, Consulting, and Operations. |
| **Report Vault** | Persistent history of analysis results with BI-compatible exports (CSV/JSON). |
| **AI Assistant** | Natural language interface to your document knowledge. |
| **Usage & Audit** | Enterprise-grade cost tracking and security logging. |

---

## 🔧 Recovered + Verified Features
The following features have been restored for parity with the core technical baseline:
- **Skills Workbench**: Manual execution of specialized AI tasks (Financial, Consulting).
- **Advanced Chat Control**: Deep selection of Models (GPT/Bedrock), Providers, and Prompt Templates.
- **Index Lifecycle Tracking**: Real-time modal for document indexing status and vector store health.
- **Workflow Templates**: One-click access to legacy Financial and Consulting pipelines.

---

## 📄 Documentation
- 🚀 **[Deployment Manual](Documents/deployment%20manual.md)**: Installation & Cloud setup.
- 📖 **[User Manual](Documents/user%20manual.md)**: How to use the business features.
- 🧪 **[UI Testing Guide](Documents/UI-TESTING-GUIDE.md)**: Validating the SaaS product experience.

---
MIT License. Created for high-performance business intelligence.
