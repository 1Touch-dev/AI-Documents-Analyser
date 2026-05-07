# 🧠 AI Financial Operating System (Fin-OS)

A professional, enterprise-grade SaaS financial modeling, treasury, and FP&A operating system. Transform raw documents (PDFs, Excel models, CSV spreadsheets) into dynamic, live-recalculating forecasts, CFO risk dashboards, governance approval registries, and executive PowerPoint narrative decks with a single click.

---

## 🚀 The Product Experience

Fin-OS turns static document analysis into a workflow-driven, modeling-driven, and scenario-driven strategic asset:

1.  **📊 Financial Data Layer**: Extracts structured line items (Sponsorship, Payroll, Debt Principal, Covenants, Taxes) into a normalized financial schema using Pandas, openpyxl, and LLM structured extraction.
2.  **🎛️ Scenario Forecasting Engine**: Supports interactive financial modeling. Adjust sliders (Sponsorship Variance, Payroll Variance, Refinancing Rate, Asset Liquidations, Collections) to see 30, 60, 90, 180 days cash flow, burn rate, liquidity runway, and EBITDA updates *live*.
3.  **🚨 CFO Risk & Compliance Dashboard**: Automatically audits balance sheets for covenant compliance, unpaid tax exposures, operational deficits, and runway depletion risks.
4.  **💬 Forensic Management Q&A**: Auto-generates critical forensic questions and suggested investigation paths for management.
5.  **📝 Executive Narrative Synthesis**: Real-time generation of custom briefs for different stakeholders, including Board summaries, Investor reports, Lender summaries, and internal Management directives.
6.  **🛡️ Governance & Accountabilities**: Manages budget approvals, department accountability (variance explanation logs), and vendor pricing auto-renew risk profiles.
7.  **💾 High-Fidelity Exports**: One-click download of live-recalculated Excel forecasting models (`.xlsx`) and board-ready PowerPoint decks (`.pptx`).

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
