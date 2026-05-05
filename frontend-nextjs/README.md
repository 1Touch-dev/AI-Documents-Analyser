# AI Knowledge Platform Frontend (Next.js)

Premium, SaaS-ready frontend for the AI Knowledge Platform. Built with Next.js, Tailwind CSS, and Lucide.

## 🚀 Features

- **Executive Dashboard**: Real-time business metrics with Recharts integration.
- **AI Assistant**: Conversational interface with multi-model support (OpenAI/Bedrock), translation, and currency conversion.
- **Business Intelligence**: One-click analysis workflows with structured executive insights.
- **Document Management**: Categorized file vault with AI auto-classification and indexing status tracking.
- **Report Vault**: Historical analysis storage with export capabilities (JSON/CSV).
- **Enterprise Ready**: Role-based access control (RBAC), usage tracking, and audit logging.

## 🛠️ Technology Stack

- **Framework**: Next.js 14+ (App Router)
- **Language**: TypeScript
- **Styling**: Tailwind CSS
- **Icons**: Lucide React
- **Charts**: Recharts
- **State Management**: React Context (Auth)

## 📖 Development

### 1. Install Dependencies
```bash
npm install
```

### 2. Configure Environment
Create a `.env.local` file:
```bash
NEXT_PUBLIC_BACKEND_API_URL=http://localhost:8000/api
```

### 3. Start Development Server
```bash
npm run dev
```

### 4. Build for Production
```bash
npm run build
npm start
```

## 📂 Project Structure

- `src/app`: App Router pages and layouts.
- `src/components`: Shared UI components.
- `src/contexts`: Auth and Theme contexts.
- `src/lib`: API clients and utility functions.
- `src/styles`: Global CSS and Tailwind configuration.

## 🔌 API Integration

The frontend communicates with the FastAPI backend (default port `8000`). All API calls are routed through `src/lib/api.ts` and use a consistent error-handling pattern.

---
Part of the AI Knowledge Platform.
