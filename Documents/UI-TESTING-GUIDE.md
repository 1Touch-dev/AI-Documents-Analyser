# AI Business Intelligence — UI Testing Guide

This guide provides a comprehensive checklist and workflow for validating the **AI-Documents-Analyser** SaaS experience.

---

## 1. Executive Console (Dashboard)
**URL:** `/dashboard`

- [ ] **KPI Accuracy**: Verify that "Total Documents" and "Saved Reports" match the actual counts in the database.
- [ ] **Growth Chart**: Ensure the "Knowledge Growth" area chart renders and reflects upload activity.
- [ ] **Recent Activity**: Check that the 5 most recent documents and reports appear correctly with their respective icons (indigo for docs, emerald for reports).
- [ ] **AI Assistant Card**: Click "Review Insights" and verify it redirects to the Analysis page.
- [ ] **Responsiveness**: Resize the browser to ensure the dashboard grid stacks correctly on mobile.

## 2. Document Vault (Management)
**URL:** `/documents`

- [ ] **Category Grouping**: Verify that documents are grouped into clear sections (F&B, Ticketing, Retail, etc.).
- [ ] **AI Auto-Categorization**: Upload a document without a category and verify the AI assigns it one automatically.
- [ ] **Search & Filter**: Type a filename or category in the search bar and verify real-time filtering.
- [ ] **Batch Upload**: Select multiple files (PDF, XLSX) and verify the parallel upload progress bars.
- [ ] **Delete Action**: Click the trash icon and confirm deletion; verify the document disappears from the list.

## 3. Business Analysis (One-Click)
**URL:** `/workflows`

- [ ] **NL Search Entry**: Type a business question (e.g., "What is our revenue trend?") and verify it routes to the correct analysis.
- [ ] **Analysis Workflow**: Click "Analyze Business" and monitor the multi-step progress (Retrieve → Extract → Summarize).
- [ ] **Executive Result UI**: Verify the results appear in the tiered structure:
    - [ ] **Summary Card**: Plain-English overview.
    - [ ] **Tiers**: Findings (Green), Risks (Red), Recommendations (Indigo).
    - [ ] **Supporting Data**: Collapsible section with raw metrics.
- [ ] **Save Report**: Click "Save to Vault" and verify the success toast appears.

## 4. AI Assistant (Chat)
**URL:** `/chat`

- [ ] **Clean Thread**: Verify the message bubbles look premium and distinguish clearly between User and Assistant.
- [ ] **Markdown Rendering**: Ask for a table or list and verify it renders with full styling (not raw markdown).
- [ ] **Source Citations**: Check that citations appear at the bottom of assistant responses as clickable/hoverable pills.
- [ ] **Settings Modal**: Open settings and verify only "Document Focus" and "Translation" are shown (no technical models/providers).

## 5. Report Vault (History)
**URL:** `/reports`

- [ ] **Report Cards**: Verify reports are shown as cards with type-specific icons (BarChart for Financial, Lightbulb for Consulting).
- [ ] **Full Report Viewer**: Click a report card and verify the high-fidelity modal opens with the full analysis result.
- [ ] **Export (JSON)**: Click the JSON download button and verify the file contains the full report structure.
- [ ] **Export (CSV)**: Click the CSV download button and verify it generates a Tableau-compatible flat file.

## 6. Usage & Security
**URL:** `/usage`

- [ ] **Cost Summary**: Verify the USD cost estimates are visible for the current session.
- [ ] **Audit Trail**: Check the table of recent actions (Login, Upload, Analysis) with accurate timestamps and IP addresses.

---

## 🧪 Quick Smoke Test Script

1. **Login** as a Business Analyst.
2. **Upload** a sample Excel file (`revenue.xlsx`).
3. Wait for **Ready** status and verify it's categorized as `Financial`.
4. Go to **Analysis** and click "Analyze Business".
5. **Review** the Executive Summary and Key Findings.
6. Click **Save to Vault**.
7. Go to **Report Vault**, open the saved report, and **Export to CSV**.
8. Verify the CSV opens in Excel with correct data.
