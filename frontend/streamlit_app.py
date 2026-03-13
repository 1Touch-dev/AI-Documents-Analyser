"""
Streamlit Frontend – AI Knowledge Platform

Tabs: Chat · Documents · Prompts · Conversations · Dashboards
Sidebar: Batch Upload, Model, Prompt, Category selectors
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timedelta
from urllib.parse import urlparse, urlunparse

import httpx
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

# ── Config ───────────────────────────────────────────────
import os
BACKEND_URL_ENV = os.getenv("BACKEND_API_URL", "http://127.0.0.1:8000/api")


def _normalize_api_url(url: str) -> str:
    """
    Force localhost URLs to IPv4 loopback to avoid ::1 connection-refused on macOS.
    """
    parsed = urlparse(url)
    if parsed.hostname != "localhost":
        return url.rstrip("/")
    host = "127.0.0.1"
    if parsed.port:
        host = f"{host}:{parsed.port}"
    netloc = host
    if parsed.username:
        auth = parsed.username
        if parsed.password:
            auth = f"{auth}:{parsed.password}"
        netloc = f"{auth}@{netloc}"
    return urlunparse(parsed._replace(netloc=netloc)).rstrip("/")


API_URL = _normalize_api_url(BACKEND_URL_ENV)

st.set_page_config(
    page_title="AI Knowledge Platform",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS (Theme-Aware) ─────────────────────────────
st.markdown(
    """
    <style>
    /* Theme-Aware Visibility Fixes */
    :root {
        --primary-brand: #4f46e5;
        --success-brand: #10b981;
    }

    /* Standardize background and text for visibility across ALL modes */
    .main .block-container {
        color: var(--text-color);
        background-color: var(--background-color);
    }

    /* Sidebar Styling */
    [data-testid="stSidebar"] {
        border-right: 1px solid rgba(128, 128, 128, 0.2);
    }

    /* Headers Contrast */
    h1, h2, h3, h4, h5, h6 {
        color: var(--text-color) !important;
        font-weight: 600 !important;
    }

    /* Metric Cards (Dynamic contrast) */
    .metric-card {
        background: rgba(128, 128, 128, 0.05);
        border: 1px solid rgba(128, 128, 128, 0.2);
        border-radius: 12px;
        padding: 20px;
        margin: 8px 0;
    }
    .metric-card h3 {
        font-size: 14px;
        color: var(--text-color) !important;
        opacity: 0.8;
        margin: 0 0 4px 0;
    }
    .metric-card p {
        font-size: 28px;
        font-weight: 700;
        color: var(--primary-color) !important;
        margin: 0;
    }

    /* Chat Bubbles (Contrast Fix) */
    .chat-user {
        background: rgba(79, 70, 229, 0.1);
        border: 1px solid rgba(79, 70, 229, 0.2);
        color: var(--text-color);
        border-radius: 16px 16px 4px 16px;
        padding: 14px 18px;
        margin: 8px 0;
    }
    .chat-assistant {
        background: rgba(128, 128, 128, 0.1);
        border: 1px solid rgba(128, 128, 128, 0.2);
        color: var(--text-color);
        border-radius: 16px 16px 16px 4px;
        padding: 14px 18px;
        margin: 8px 0;
    }

    /* Button Contrast */
    .stButton > button {
        border-radius: 8px;
        font-weight: 500;
        transition: all 0.2s;
    }

    /* Status Tags */
    .status-ready { color: #16a34a; font-weight: 600; }
    .status-processing { color: #d97706; font-weight: 600; }
    .status-failed { color: #dc2626; font-weight: 600; }

    /* Diagnosis Badge */
    .diag-badge {
        font-size: 10px;
        font-family: monospace;
        opacity: 0.6;
        padding: 2px 8px;
        border-radius: 4px;
        border: 1px solid rgba(128, 128, 128, 0.3);
        margin-bottom: 20px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ── HTTP helpers ─────────────────────────────────────────
def _headers() -> dict:
    token = st.session_state.get("auth_token", "")
    if token:
        return {"Authorization": f"Bearer {token}"}
    return {}


def api_get(path: str, params: dict | None = None, silent_codes: list[int] | None = None) -> dict | None:
    try:
        r = httpx.get(f"{API_URL}{path}", params=params, headers=_headers(), timeout=60)
        if silent_codes and r.status_code in silent_codes:
            return {"status_code": r.status_code, "error": True}
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.error(f"API error: {e}")
        return None


def api_post(path: str, json_data: dict | None = None, files=None, data=None) -> dict | None:
    try:
        r = httpx.post(
            f"{API_URL}{path}",
            json=json_data,
            files=files,
            data=data,
            headers=_headers(),
            timeout=300,
        )
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.error(f"API error: {e}")
        return None


def api_delete(path: str) -> dict | None:
    try:
        st.write(f"DEBUG: Calling DELETE {API_URL}{path}") # Temporary test
        r = httpx.delete(f"{API_URL}{path}", headers=_headers(), timeout=30)
        st.write(f"DEBUG: DELETE {API_URL}{path} -> Status: {r.status_code}") # Temporary test
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.error(f"API error: {e}")
        return None


def api_put(path: str, json_data: dict) -> dict | None:
    try:
        r = httpx.put(f"{API_URL}{path}", json=json_data, headers=_headers(), timeout=30)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.error(f"API error: {e}")
        return None


# ── Session state defaults ───────────────────────────────
for key, default in {
    "auth_token": "",
    "username": "",
    "session_id": None,
    "chat_messages": [],
    "selected_model": "auto",
    "selected_prompt": None,
    "selected_category": None,
    "batch_id": None,
    "openai_api_key": "",
    "anthropic_api_key": "",
    "gemini_api_key": "",
}.items():
    if key not in st.session_state:
        st.session_state[key] = default


# ══════════════════════════════════════════════════════════
#  SIDEBAR
# ══════════════════════════════════════════════════════════

with st.sidebar:
    st.markdown("## 🧠 AI Knowledge Platform")
    st.markdown("---")

    st.markdown("---")

    with st.expander("⚙️ Provider API Keys", expanded=False):
        st.caption("Optional: Override the server's default AI models with your own API keys. Keys are only temporarily stored in your browser session.")
        st.session_state.openai_api_key = st.text_input("OpenAI API Key (gpt-5.4 / o3)", value=st.session_state.openai_api_key, type="password")
        st.session_state.anthropic_api_key = st.text_input("Anthropic API Key (Claude 4.6)", value=st.session_state.anthropic_api_key, type="password")
        st.session_state.gemini_api_key = st.text_input("Gemini API Key (3.1 Pro)", value=st.session_state.gemini_api_key, type="password")

    st.markdown("---")

    # ── Batch Upload (Direct FastAPI Bypass) ─────────────
    st.markdown("#### 📄 Upload Documents")
    
    auth_token = st.session_state.auth_token
    
    html_code = f"""
    <!DOCTYPE html>
    <html>
    <head>
    <style>
      body {{ font-family: sans-serif; color: var(--text-color, #333); }}
      .dropzone {{
        border: 2px dashed #ccc;
        border-radius: 8px;
        padding: 20px;
        text-align: center;
        margin-bottom: 10px;
        background: rgba(128, 128, 128, 0.05);
        cursor: pointer;
        transition: background 0.2s;
      }}
      .dropzone:hover {{ background: rgba(128, 128, 128, 0.1); }}
      select, input, button {{
        width: 100%;
        padding: 10px;
        margin-bottom: 10px;
        border-radius: 4px;
        border: 1px solid #ccc;
        box-sizing: border-box;
      }}
      button {{
        background-color: #ff4b4b;
        color: white;
        font-weight: bold;
        border: none;
        cursor: pointer;
      }}
      button:hover {{ background-color: #ff3333; }}
      button:disabled {{ background-color: #ffa0a0; cursor: not-allowed; }}
      #status {{ font-size: 0.9em; margin-top: 5px; word-break: break-all; font-weight: bold; }}
    </style>
    </head>
    <body>
      <div class="dropzone" id="dropzone">
        <p style="margin: 0; font-weight: bold;">📁 Drag & drop specific files here</p>
        <p style="font-size: 0.75em; color: gray; margin-top: 5px;">Limit 1GB per file • PDF, DOCX, PPTX, XLSX, CSV, TXT, JSON</p>
        <input type="file" id="fileInput" multiple style="display:none;" />
      </div>
      
      <input type="text" id="categoryInput" value="general" placeholder="Category for batch" />
      <button id="uploadBtn">⬆️ Upload All Directly</button>
      <div id="status"></div>

      <script>
        const dropzone = document.getElementById('dropzone');
        const fileInput = document.getElementById('fileInput');
        const uploadBtn = document.getElementById('uploadBtn');
        const statusDiv = document.getElementById('status');
        const categoryInput = document.getElementById('categoryInput');
        
        dropzone.addEventListener('click', () => fileInput.click());
        dropzone.addEventListener('dragover', (e) => {{ e.preventDefault(); dropzone.style.background = 'rgba(128,128,128,0.2)'; }});
        dropzone.addEventListener('dragleave', () => {{ dropzone.style.background = 'rgba(128,128,128,0.05)'; }});
        dropzone.addEventListener('drop', (e) => {{
          e.preventDefault();
          dropzone.style.background = 'rgba(128,128,128,0.05)';
          if (e.dataTransfer.files.length) {{
            fileInput.files = e.dataTransfer.files;
            statusDiv.innerText = `${{fileInput.files.length}} files selected ready to upload.`;
            statusDiv.style.color = '#333';
          }}
        }});
        
        fileInput.addEventListener('change', () => {{
          if(fileInput.files.length) {{
             statusDiv.innerText = `${{fileInput.files.length}} files selected ready to upload.`;
             statusDiv.style.color = '#333';
          }}
        }});

        uploadBtn.addEventListener('click', async () => {{
          if (!fileInput.files.length) {{
            statusDiv.innerText = "⚠️ Please select files first.";
            statusDiv.style.color = "orange";
            return;
          }}
          
          statusDiv.innerText = `⏳ Uploading ${{fileInput.files.length}} files directly to backend... Please wait.`;
          statusDiv.style.color = "#0066cc";
          uploadBtn.disabled = true;
          
          const formData = new FormData();
          for (const file of fileInput.files) {{
             formData.append("files", file);
          }}
          formData.append("category", categoryInput.value || "general");

          try {{
            // Use origin to construct full URL - will use current protocol and host
            const backendUrl = `${{window.location.origin}}/api/upload_batch`;
            
            const response = await fetch(backendUrl, {{
              method: "POST",
              headers: {{
                "Authorization": "Bearer {auth_token}"
              }},
              body: formData
            }});
            
            if (!response.ok) {{
              const err = await response.text();
              throw new Error(`HTTP error ${{response.status}}: ${{err}}`);
            }}
            
            const result = await response.json();
            statusDiv.innerText = `✅ Success! ${{result.accepted}} processing | ⚠️ ${{result.duplicates}} duplicates | ❌ ${{result.rejected}} rejected. Check 'Documents' tab.`;
            statusDiv.style.color = "green";
            fileInput.value = ""; 
          }} catch (error) {{
            statusDiv.innerText = `❌ Upload failed: ${{error.message}}`;
            statusDiv.style.color = "red";
          }} finally {{
            uploadBtn.disabled = false;
          }}
        }});
      </script>
    </body>
    </html>
    """
    
    import streamlit.components.v1 as components
    components.html(html_code, height=360)
    
    st.session_state.batch_id = None

    st.markdown("---")

    # ── Model Selection ──────────────────────────────────
    st.markdown("#### 🤖 Model")
    model_options = ["auto", "llama3.2", "tinyllama", "llama3", "mistral", "mixtral", "gemma", "gpt-5.4", "o3-mini", "claude-4.6-sonnet", "claude-4.6-opus", "gemini-3.1-pro", "gemini-3-flash", "gemini-3.1-flash"]

    def format_model_label(m):
        if m == "auto": return "auto (Recommended)"
        if m in ["llama3.2", "tinyllama"]: return f"{m} (Ready)"
        if m in ["llama3", "mistral", "mixtral", "gemma"]: return f"{m} (Not installed - install yourself via Ollama)"
        return f"{m} (Requires API Key)"

    st.session_state.selected_model = st.selectbox(
        "Select LLM",
        model_options,
        index=0,
        format_func=format_model_label,
        label_visibility="collapsed",
    )

    st.markdown("---")

    # ── Prompt Template ──────────────────────────────────
    st.markdown("#### 📝 Prompt Template")
    prompts_resp = api_get("/prompts")
    prompt_names = ["Default (built-in)"]
    prompt_map = {}
    if prompts_resp:
        for p in prompts_resp.get("prompts", []):
            prompt_names.append(p["name"])
            prompt_map[p["name"]] = p["template"]

    selected_prompt_name = st.selectbox("Select template", prompt_names, label_visibility="collapsed")
    if selected_prompt_name != "Default (built-in)":
        st.session_state.selected_prompt = prompt_map.get(selected_prompt_name)
    else:
        st.session_state.selected_prompt = None

    st.markdown("---")

    # ── Conversation Category ────────────────────────────
    st.markdown("#### 🗂️ Category")
    cat_resp = api_get("/conversations/categories")
    categories = ["All"] + (cat_resp.get("categories", []) if cat_resp else [])
    sel_cat = st.selectbox("Filter conversations", categories, label_visibility="collapsed")
    st.session_state.selected_category = None if sel_cat == "All" else sel_cat

    new_cat = st.text_input("New category", placeholder="e.g. CFO analysis")
    if new_cat:
        st.session_state.selected_category = new_cat


# ══════════════════════════════════════════════════════════
#  MAIN AREA – TABS
# ══════════════════════════════════════════════════════════

tab_chat, tab_docs, tab_prompts, tab_convos, tab_dash = st.tabs(
    ["💬 Chat", "📁 Documents", "📝 Prompts", "🗂️ Conversations", "📊 Dashboards"]
)


# ──────────────────────────────────────────────────────────
#  TAB: Chat
# ──────────────────────────────────────────────────────────
with tab_chat:
    st.markdown("### 💬 Chat with your Documents")

    col1, col2 = st.columns([3, 1])
    with col2:
        if st.button("🆕 New Chat", use_container_width=True):
            st.session_state.session_id = None
            st.session_state.chat_messages = []
            st.rerun()

    # Display chat history
    for msg in st.session_state.chat_messages:
        role = "user" if msg["role"] == "user" else "assistant"
        with st.chat_message(role):
            st.markdown(msg["content"])
            
            # Show sources with indices matching [1], [2], etc.
            if msg.get("sources"):
                st.markdown("---")
                cols = st.columns(len(msg["sources"]))
                for i, s in enumerate(msg["sources"], 1):
                    with cols[(i-1) % len(cols)]:
                        st.markdown(
                            f'<div class="source-badge">[{i}] 📄 {s.get("title", s.get("doc_id", "?")[:8])}</div>',
                            unsafe_allow_html=True
                        )

    # Input
    question = st.chat_input("Ask a question about your documents…")
    if question:
        st.session_state.chat_messages.append({"role": "user", "content": question})

        with st.spinner("Thinking…"):
            payload = {
                "question": question,
                "model": st.session_state.selected_model,
                "top_k": 5,
                "temperature": 0.7,
                "category": st.session_state.selected_category,
                "openai_api_key": st.session_state.openai_api_key or None,
                "anthropic_api_key": st.session_state.anthropic_api_key or None,
                "gemini_api_key": st.session_state.gemini_api_key or None,
            }
            if st.session_state.session_id:
                payload["session_id"] = st.session_state.session_id
            if st.session_state.selected_prompt:
                payload["prompt_template"] = st.session_state.selected_prompt

            resp = api_post("/query", payload)

            if resp:
                st.session_state.session_id = resp.get("session_id")
                st.session_state.chat_messages.append(
                    {
                        "role": "assistant",
                        "content": resp["answer"],
                        "sources": resp.get("sources", []),
                    }
                )
            else:
                st.session_state.chat_messages.append(
                    {"role": "assistant", "content": "❌ Failed to get a response."}
                )

        st.rerun()


# ──────────────────────────────────────────────────────────
#  TAB: Documents
# ──────────────────────────────────────────────────────────
with tab_docs:
    st.markdown("### 📁 Document Library")

    docs_resp = api_get("/documents", {"limit": 200})

    if docs_resp and docs_resp.get("documents"):
        docs = docs_resp["documents"]

        # Metrics row
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.markdown(f'<div class="metric-card"><h3>Total Documents</h3><p>{docs_resp["total"]}</p></div>', unsafe_allow_html=True)
        with c2:
            ready = sum(1 for d in docs if d["status"] == "ready")
            st.markdown(f'<div class="metric-card"><h3>Ready</h3><p>{ready}</p></div>', unsafe_allow_html=True)
        with c3:
            total_chunks = sum(d.get("chunk_count", 0) for d in docs)
            st.markdown(f'<div class="metric-card"><h3>Total Chunks</h3><p>{total_chunks}</p></div>', unsafe_allow_html=True)
        with c4:
            total_size = sum(d.get("file_size", 0) for d in docs) / (1024 * 1024)
            st.markdown(f'<div class="metric-card"><h3>Total Size</h3><p>{total_size:.1f} MB</p></div>', unsafe_allow_html=True)

        # Table
        st.markdown("---")
        df = pd.DataFrame(docs)
        df["file_size"] = df["file_size"].apply(lambda x: f"{(x or 0)/1024:.1f} KB")
        status_map = {"ready": "🟢", "processing": "🟡", "failed": "🔴"}
        df["status_icon"] = df["status"].map(status_map).fillna("⚪") + " " + df["status"]

        st.dataframe(
            df[["title", "category", "file_type", "file_size", "chunk_count", "status_icon", "uploaded_by", "timestamp"]],
            use_container_width=True,
            hide_index=True,
            column_config={
                "title": "Title",
                "category": "Category",
                "file_type": "Type",
                "file_size": "Size",
                "chunk_count": "Chunks",
                "status_icon": "Status",
                "uploaded_by": "Uploaded By",
                "timestamp": "Date",
            },
        )

        # Delete
        st.markdown("---")
        del_id = st.text_input("Document ID to delete", key="del_doc_id")
        if st.button("🗑️ Delete Document") and del_id:
            resp = api_delete(f"/documents/{del_id}")
            if resp and resp.get("deleted"):
                st.success("Document deleted.")
                st.rerun()
    else:
        st.info("No documents uploaded yet. Use the sidebar to upload files.")


# ──────────────────────────────────────────────────────────
#  TAB: Prompts
# ──────────────────────────────────────────────────────────
with tab_prompts:
    st.markdown("### 📝 Prompt Templates")

    col_list, col_create = st.columns([2, 1])

    with col_list:
        st.markdown("##### Existing Templates")
        pr = api_get("/prompts")
        if pr:
            for p in pr.get("prompts", []):
                with st.expander(f"**{p['name']}** ({p.get('category', '—')})"):
                    st.markdown(f"*{p.get('description', 'No description')}*")
                    st.code(p["template"], language="text")
                    c1, c2 = st.columns(2)
                    with c2:
                        if st.button(f"🗑️ Delete", key=f"del_p_{p['id']}"):
                            api_delete(f"/prompts/{p['id']}")
                            st.rerun()

    with col_create:
        st.markdown("##### Create New")
        with st.form("create_prompt"):
            pn = st.text_input("Name")
            pc = st.text_input("Category")
            pd_desc = st.text_area("Description")
            pt = st.text_area("Template", help="Use ${context} and ${question} placeholders")
            if st.form_submit_button("Create") and pn and pt:
                resp = api_post("/prompts", {"name": pn, "template": pt, "category": pc, "description": pd_desc})
                if resp:
                    st.success(f"Created: {pn}")
                    st.rerun()


# ──────────────────────────────────────────────────────────
#  TAB: Conversations
# ──────────────────────────────────────────────────────────
with tab_convos:
    st.markdown("### 🗂️ Conversation History")

    params = {"limit": 50}
    if st.session_state.selected_category:
        params["category"] = st.session_state.selected_category

    convos_resp = api_get("/conversations", params)

    if convos_resp and convos_resp.get("conversations"):
        for c in convos_resp["conversations"]:
            title = c.get("title") or "Untitled"
            cat = c.get("category") or "—"
            msgs = c.get("message_count", 0)
            updated = c.get("updated_at", "")[:16]

            with st.expander(f"💬 {title}  |  🗂️ {cat}  |  📨 {msgs} msgs  |  ⏱️ {updated}"):
                conv_data = api_get(f"/conversations/{c['session_id']}")
                if conv_data and conv_data.get("messages"):
                    for m in conv_data["messages"]:
                        role_icon = "🧑" if m["role"] == "user" else "🤖"
                        st.markdown(f"{role_icon} **{m['role'].title()}**: {m['content'][:500]}")

                col_a, col_b = st.columns(2)
                with col_a:
                    if st.button("🔄 Resume", key=f"resume_{c['session_id']}"):
                        st.session_state.session_id = c["session_id"]
                        if conv_data and conv_data.get("messages"):
                            st.session_state.chat_messages = conv_data["messages"]
                        st.rerun()
                with col_b:
                    if st.button("🗑️ Delete", key=f"del_c_{c['session_id']}"):
                        api_delete(f"/conversations/{c['session_id']}")
                        st.rerun()
    else:
        st.info("No conversations yet. Start chatting in the Chat tab!")


# ──────────────────────────────────────────────────────────
#  TAB: Dashboards (Tableau-Level)
# ──────────────────────────────────────────────────────────
with tab_dash:
    st.markdown("### 📊 Analytics & Visualization")

    # ── Fetch all analytics data ─────────────────────────
    overview = api_get("/analytics/overview")
    content_data = api_get("/analytics/content")
    storage_data = api_get("/analytics/storage")
    docs_resp2 = api_get("/documents", {"limit": 500})

    if not overview or overview.get("total_documents", 0) == 0:
        st.info("No documents in the system yet. Upload files to see analytics.")
    else:
        docs_data = docs_resp2.get("documents", []) if docs_resp2 else []
        df_docs = pd.DataFrame(docs_data) if docs_data else pd.DataFrame()

        # ════════════════════════════════════════════════
        # SECTION 1: Interactive Filter Bar
        # ════════════════════════════════════════════════
        st.markdown("#### 🔍 Filters")
        fc1, fc2, fc3, fc4 = st.columns(4)

        with fc1:
            all_categories = list(overview.get("by_category", {}).keys())
            sel_cats = st.multiselect("Category", all_categories, default=all_categories, key="dash_cat")
        with fc2:
            all_types = list(overview.get("by_file_type", {}).keys())
            sel_types = st.multiselect("File Type", all_types, default=all_types, key="dash_type")
        with fc3:
            all_statuses = list(overview.get("by_status", {}).keys())
            sel_statuses = st.multiselect("Status", all_statuses, default=all_statuses, key="dash_status")
        with fc4:
            all_uploaders = list(overview.get("by_uploader", {}).keys())
            sel_uploaders = st.multiselect("Uploaded By", all_uploaders, default=all_uploaders, key="dash_uploader")

        # Apply filters
        if not df_docs.empty:
            mask = (
                df_docs["category"].isin(sel_cats) &
                df_docs["file_type"].isin(sel_types) &
                df_docs["status"].isin(sel_statuses) &
                df_docs["uploaded_by"].isin(sel_uploaders)
            )
            df_filtered = df_docs[mask].copy()
        else:
            df_filtered = pd.DataFrame()

        # ════════════════════════════════════════════════
        # SECTION 2: KPI Cards
        # ════════════════════════════════════════════════
        st.markdown("---")
        k1, k2, k3, k4, k5, k6 = st.columns(6)
        n_docs = len(df_filtered) if not df_filtered.empty else 0
        n_chunks = int(df_filtered["chunk_count"].sum()) if not df_filtered.empty and "chunk_count" in df_filtered.columns else 0
        total_mb = df_filtered["file_size"].sum() / (1024*1024) if not df_filtered.empty and "file_size" in df_filtered.columns else 0
        est_words = content_data.get("total_estimated_words", 0) if content_data else 0
        read_time = content_data.get("total_reading_time_min", 0) if content_data else 0
        n_cats = len(sel_cats)

        for col, label, val in [
            (k1, "Documents", n_docs), (k2, "Chunks", n_chunks),
            (k3, "Size (MB)", f"{total_mb:.1f}"), (k4, "Est. Words", f"{est_words:,}"),
            (k5, "Reading Time", f"{read_time:.0f} min"), (k6, "Categories", n_cats),
        ]:
            with col:
                st.markdown(f'<div class="metric-card"><h3>{label}</h3><p>{val}</p></div>', unsafe_allow_html=True)

        # ════════════════════════════════════════════════
        # FETCH CONTENT INSIGHTS (Phase 8)
        # ════════════════════════════════════════════════
        insights = api_get("/analytics/content_insights")

        if not df_filtered.empty:
            # ════════════════════════════════════════════════
            # SECTION 3: Topic Intelligence
            # ════════════════════════════════════════════════
            st.markdown("---")
            st.markdown("#### 🧠 Topic Intelligence")

            chart_theme = dict(
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                font_color="#1e293b", title_font_size=15,
                margin=dict(l=20, r=20, t=40, b=20),
            )

            if insights and insights.get("topics"):
                t_col1, t_col2 = st.columns([3, 2])

                with t_col1:
                    topics = insights["topics"]
                    topic_names = [t["topic"].title() for t in topics[:15]]
                    topic_freqs = [t["frequency"] for t in topics[:15]]
                    topic_types = [t["type"] for t in topics[:15]]

                    color_map_topics = ["#4f46e5" if t == "bigram" else "#7c3aed" for t in topic_types]

                    fig_topics = go.Figure(go.Bar(
                        y=topic_names[::-1], x=topic_freqs[::-1],
                        orientation="h",
                        marker_color=color_map_topics[::-1],
                        text=topic_freqs[::-1], textposition="outside",
                        textfont=dict(color="#1e293b", size=12),
                        hovertemplate="<b>%{y}</b><br>Frequency: %{x}<extra></extra>",
                    ))
                    fig_topics.update_layout(
                        **chart_theme, title="Dominant Themes Across All Documents",
                        height=max(400, len(topic_names) * 32),
                        xaxis_title="Frequency", yaxis_title="",
                    )
                    st.plotly_chart(fig_topics, use_container_width=True, key="topics_bar")

                with t_col2:
                    st.markdown("##### 🏷️ Theme Tags")
                    max_freq = max(topic_freqs) if topic_freqs else 1
                    tags_html = '<div style="line-height:2.2;">'
                    for t in topics[:20]:
                        size = 13 + int((t["frequency"] / max_freq) * 14)
                        weight = 700 if t["type"] == "bigram" else 500
                        bg = "rgba(79,70,229,0.1)" if t["type"] == "bigram" else "rgba(124,58,237,0.08)"
                        border_c = "rgba(79,70,229,0.3)" if t["type"] == "bigram" else "rgba(124,58,237,0.25)"
                        tags_html += (
                            f'<span style="display:inline-block; background:{bg}; '
                            f'border:1px solid {border_c}; border-radius:8px; '
                            f'padding:5px 14px; margin:4px; font-size:{size}px; '
                            f'color:#312e81; font-weight:{weight};">{t["topic"]}</span>'
                        )
                    tags_html += '</div>'
                    st.markdown(f'<div class="glass-panel">{tags_html}</div>', unsafe_allow_html=True)

                    # Summary KPIs
                    summary = insights.get("summary", {})
                    st.markdown(
                        f'<div class="glass-panel" style="padding:16px;">'
                        f'<div style="color:#475569; font-size:13px; line-height:1.8;">'
                        f'📊 Analyzed <b style="color:#1e293b;">{summary.get("chunks_analyzed", 0)}</b> chunks '
                        f'from <b style="color:#1e293b;">{summary.get("docs_analyzed", 0)}</b> documents<br>'
                        f'🏷️ <b style="color:#1e293b;">{summary.get("total_topics", 0)}</b> topics · '
                        f'🔍 <b style="color:#1e293b;">{summary.get("total_entities", 0)}</b> entities · '
                        f'💰 <b style="color:#1e293b;">{summary.get("total_financial_items", 0)}</b> financial items'
                        f'</div></div>',
                        unsafe_allow_html=True,
                    )
            else:
                st.info("Processing documents to extract topics…")

            # ════════════════════════════════════════════════
            # SECTION 4: Financial Data Overview
            # ════════════════════════════════════════════════
            if insights and (insights.get("entities", {}).get("monetary") or insights.get("financials")):
                st.markdown("---")
                st.markdown("#### 💰 Financial Data Overview")

                fin_col1, fin_col2 = st.columns(2)

                with fin_col1:
                    monetary = insights.get("entities", {}).get("monetary", [])
                    if monetary:
                        st.markdown("##### 💵 Monetary Values Found")
                        max_occ = max(m["occurrences"] for m in monetary)
                        for item in monetary[:12]:
                            bar_width = min(100, int((item["occurrences"] / max_occ) * 100))
                            st.markdown(
                                f'<div style="display:flex; align-items:center; margin:6px 0; line-height:1.6;">'
                                f'<span style="min-width:160px; color:#1e293b; font-family:monospace; font-size:14px; font-weight:600;">{item["value"]}</span>'
                                f'<div style="flex:1; background:#e2e8f0; height:20px; border-radius:4px; margin:0 10px; overflow:hidden;">'
                                f'<div style="background:linear-gradient(90deg,#16a34a,#22c55e); height:100%; width:{bar_width}%; border-radius:4px;"></div></div>'
                                f'<span style="color:#475569; font-size:13px; font-weight:600; min-width:40px;">×{item["occurrences"]}</span>'
                                f'</div>',
                                unsafe_allow_html=True,
                            )

                    pcts = insights.get("entities", {}).get("percentages", [])
                    if pcts:
                        st.markdown("##### 📊 Percentages Found")
                        pct_html = '<div style="line-height:2.4;">'
                        for item in pcts[:8]:
                            pct_html += (
                                f'<span style="display:inline-block; background:rgba(234,179,8,0.12); '
                                f'border:1px solid rgba(234,179,8,0.3); border-radius:6px; '
                                f'padding:5px 12px; margin:4px; color:#92400e; font-family:monospace; font-weight:600;">'
                                f'{item["value"]} <span style="color:#a16207; font-weight:400; font-size:11px;">×{item["occurrences"]}</span></span>'
                            )
                        pct_html += '</div>'
                        st.markdown(pct_html, unsafe_allow_html=True)

                with fin_col2:
                    financials = insights.get("financials", [])
                    if financials:
                        st.markdown("##### 📋 Financial Context Lines")
                        for i, f_item in enumerate(financials[:10]):
                            kw = f_item["keyword"]
                            ctx = f_item["context"]
                            # HTML-escape the context to prevent tag rendering
                            import html as html_mod
                            ctx_safe = html_mod.escape(ctx[:120])
                            vals = ", ".join(f_item.get("values_found", [])[:3])
                            st.markdown(
                                f'<div style="background:rgba(255,255,255,0.8); border:1px solid #e2e8f0; '
                                f'border-radius:8px; padding:12px; margin:6px 0; line-height:1.6;">'
                                f'<span style="background:rgba(220,38,38,0.1); border-radius:4px; padding:3px 8px; '
                                f'color:#b91c1c; font-size:11px; font-weight:700; letter-spacing:0.5px;">{kw.upper()}</span> '
                                f'<span style="color:#334155; font-size:13px;">{ctx_safe}{"…" if len(ctx) > 120 else ""}</span>'
                                f'{"<br><span style=font-size:12px;color:#64748b;>📎 Values: " + html_mod.escape(vals) + "</span>" if vals else ""}'
                                f'</div>',
                                unsafe_allow_html=True,
                            )

            # ════════════════════════════════════════════════
            # SECTION 5: Entity Intelligence
            # ════════════════════════════════════════════════
            if insights and insights.get("entities"):
                st.markdown("---")
                st.markdown("#### 🔍 Entity Intelligence")

                ent_col1, ent_col2, ent_col3 = st.columns(3)

                entities = insights["entities"]

                with ent_col1:
                    orgs = entities.get("organizations", [])
                    if orgs:
                        st.markdown("##### 🏢 Organizations")
                        for org in orgs[:10]:
                            st.markdown(
                                f'<div style="display:flex; justify-content:space-between; padding:6px 4px; '
                                f'border-bottom:1px solid #f1f5f9; line-height:1.6;">'
                                f'<span style="color:#1e293b; font-size:13px;">{org["value"]}</span>'
                                f'<span style="color:#4f46e5; font-weight:700; font-size:13px;">{org["occurrences"]}</span></div>',
                                unsafe_allow_html=True,
                            )

                with ent_col2:
                    dates = entities.get("dates", [])
                    if dates:
                        st.markdown("##### 📅 Dates Referenced")
                        for d in dates[:10]:
                            st.markdown(
                                f'<div style="display:flex; justify-content:space-between; padding:6px 4px; '
                                f'border-bottom:1px solid #f1f5f9; line-height:1.6;">'
                                f'<span style="color:#1e293b; font-size:13px;">{d["value"]}</span>'
                                f'<span style="color:#d97706; font-weight:700; font-size:13px;">{d["occurrences"]}</span></div>',
                                unsafe_allow_html=True,
                            )

                with ent_col3:
                    emails = entities.get("emails", [])
                    urls = entities.get("urls", [])
                    contact_items = emails + urls
                    if contact_items:
                        st.markdown("##### 🔗 Contacts & Links")
                        for c in contact_items[:8]:
                            import html as html_mod
                            val = html_mod.escape(c["value"])
                            display_val = val[:45] + "…" if len(val) > 45 else val
                            st.markdown(
                                f'<div style="padding:6px 4px; border-bottom:1px solid #f1f5f9; '
                                f'color:#2563eb; font-size:12px; word-break:break-all; line-height:1.6;">{display_val}</div>',
                                unsafe_allow_html=True,
                            )

            # ════════════════════════════════════════════════
            # SECTION 6: Document Similarity & Content Coverage
            # ════════════════════════════════════════════════
            if insights:
                st.markdown("---")
                sim_col, cov_col = st.columns(2)

                with sim_col:
                    sim_data = insights.get("similarity_matrix", {})
                    if sim_data.get("matrix") and len(sim_data["matrix"]) > 1:
                        st.markdown("#### 🔗 Document Similarity")
                        sim_matrix = np.array(sim_data["matrix"])
                        doc_labels = sim_data["documents"]

                        fig_sim = go.Figure(data=go.Heatmap(
                            z=sim_matrix, x=doc_labels, y=doc_labels,
                            colorscale="Blues", zmin=0, zmax=1,
                            hovertemplate="<b>%{y}</b> vs <b>%{x}</b><br>Similarity: %{z:.2f}<extra></extra>",
                            colorbar=dict(title="Sim.", tickfont=dict(color="#475569")),
                        ))
                        fig_sim.update_layout(
                            **chart_theme, title="Cross-Document Content Similarity",
                            height=450, xaxis_tickangle=-45,
                            xaxis=dict(tickfont=dict(size=10, color="#475569")),
                            yaxis=dict(tickfont=dict(size=10, color="#475569")),
                        )
                        st.plotly_chart(fig_sim, use_container_width=True, key="sim_heatmap")

                with cov_col:
                    cov_data = insights.get("coverage_matrix", {})
                    if cov_data.get("matrix") and cov_data.get("topics"):
                        st.markdown("#### 📊 Content Coverage Matrix")
                        cov_matrix = np.array(cov_data["matrix"])
                        fig_cov = go.Figure(data=go.Heatmap(
                            z=cov_matrix, x=cov_data["topics"], y=cov_data["documents"],
                            colorscale="Tealgrn",
                            hovertemplate="<b>%{y}</b><br>Topic: %{x}<br>Mentions: %{z}<extra></extra>",
                            colorbar=dict(title="Mentions", tickfont=dict(color="#475569")),
                        ))
                        fig_cov.update_layout(
                            **chart_theme, title="Topics × Documents",
                            height=450, xaxis_tickangle=-45,
                            xaxis=dict(tickfont=dict(size=10, color="#475569")),
                            yaxis=dict(tickfont=dict(size=10, color="#475569")),
                        )
                        st.plotly_chart(fig_cov, use_container_width=True, key="cov_heatmap")

            # ════════════════════════════════════════════════
            # SECTION 7: Per-Document Insight Cards
            # ════════════════════════════════════════════════
            if insights and insights.get("doc_insights"):
                st.markdown("---")
                st.markdown("#### 📄 Per-Document Insights")

                for doc_info in insights["doc_insights"]:
                    import html as html_mod
                    title = doc_info["title"]
                    ftype = doc_info.get("file_type", "")
                    category = doc_info.get("category", "general")
                    chunks = doc_info.get("chunk_count", 0)
                    phrases = doc_info.get("key_phrases", [])
                    values = doc_info.get("notable_values", [])
                    preview = doc_info.get("text_preview", "")

                    type_icon = {"pdf": "📕", "xlsx": "📊", "pptx": "📙", "csv": "📊", "docx": "📘", "txt": "📝"}.get(ftype, "📄")

                    with st.expander(f"{type_icon} **{title}**  ·  {ftype.upper()}  ·  {category}  ·  {chunks} chunks"):
                        # ── Row 1: Key themes as styled pills ──
                        if phrases:
                            st.markdown("**🏷️ Key Themes in This Document:**")
                            pill_html = '<div style="line-height:2.2; margin-bottom:8px;">'
                            for p in phrases[:10]:
                                pill_html += (
                                    f'<span style="display:inline-block; background:rgba(79,70,229,0.08); '
                                    f'border:1px solid rgba(79,70,229,0.2); border-radius:20px; '
                                    f'padding:4px 14px; margin:3px; color:#3730a3; font-size:13px; '
                                    f'font-weight:500;">{html_mod.escape(p)}</span>'
                                )
                            pill_html += '</div>'
                            st.markdown(pill_html, unsafe_allow_html=True)

                        # ── Row 2: Financial data found (only if present) ──
                        if values:
                            clean_vals = [html_mod.escape(v.strip()) for v in values if v.strip() and len(v.strip()) > 1]
                            if clean_vals:
                                st.markdown("**💰 Financial Values Found:**")
                                val_html = '<div style="line-height:2.2; margin-bottom:8px;">'
                                for v in clean_vals[:10]:
                                    val_html += (
                                        f'<span style="display:inline-block; background:rgba(22,163,74,0.08); '
                                        f'border:1px solid rgba(22,163,74,0.2); border-radius:20px; '
                                        f'padding:4px 14px; margin:3px; color:#166534; font-family:monospace; '
                                        f'font-size:13px; font-weight:600;">{v}</span>'
                                    )
                                val_html += '</div>'
                                st.markdown(val_html, unsafe_allow_html=True)

                        # ── Row 3: Content preview (escaped, no HTML leak) ──
                        if preview:
                            safe_preview = html_mod.escape(preview[:300])
                            st.markdown(
                                f'<div style="background:#f8fafc; border:1px solid #e2e8f0; border-radius:8px; '
                                f'padding:12px; margin-top:8px; font-size:13px; color:#475569; '
                                f'line-height:1.7; font-style:italic;">'
                                f'📝 {safe_preview}{"…" if len(preview) > 300 else ""}</div>',
                                unsafe_allow_html=True,
                            )

            # ════════════════════════════════════════════════
            # SECTION 8: Dynamic Chart Builder
            # ════════════════════════════════════════════════
            st.markdown("---")
            st.markdown("#### 🔧 Custom Chart Builder")

            if not df_filtered.empty:
                bc1, bc2, bc3, bc4 = st.columns(4)
                numeric_cols = [c for c in df_filtered.columns if df_filtered[c].dtype in ['int64', 'float64']]
                string_cols = [c for c in df_filtered.columns if df_filtered[c].dtype == 'object']

                with bc1:
                    chart_type = st.selectbox("Chart Type", ["bar", "scatter", "line", "histogram", "box", "violin", "sunburst"], key="ct_type")
                with bc2:
                    x_col = st.selectbox("X-Axis", string_cols + numeric_cols, key="ct_x")
                with bc3:
                    y_col = st.selectbox("Y-Axis", numeric_cols + ["count"], key="ct_y")
                with bc4:
                    color_col = st.selectbox("Color By", ["None"] + string_cols, key="ct_color")

                color_val = None if color_col == "None" else color_col

                try:
                    if chart_type == "bar":
                        if y_col == "count":
                            plot_df = df_filtered[x_col].value_counts().reset_index()
                            plot_df.columns = [x_col, "count"]
                            fig_custom = px.bar(plot_df, x=x_col, y="count", color=color_val if color_val and color_val in plot_df.columns else None, text="count")
                        else:
                            fig_custom = px.bar(df_filtered, x=x_col, y=y_col, color=color_val)
                    elif chart_type == "scatter":
                        y_actual = "file_size" if y_col == "count" else y_col
                        fig_custom = px.scatter(df_filtered, x=x_col, y=y_actual, color=color_val, hover_name="title" if "title" in df_filtered.columns else None)
                    elif chart_type == "line":
                        y_actual = "file_size" if y_col == "count" else y_col
                        fig_custom = px.line(df_filtered.sort_values(x_col), x=x_col, y=y_actual, color=color_val)
                    elif chart_type == "histogram":
                        fig_custom = px.histogram(df_filtered, x=x_col, color=color_val)
                    elif chart_type == "box":
                        y_actual = "file_size" if y_col == "count" else y_col
                        fig_custom = px.box(df_filtered, x=x_col, y=y_actual, color=color_val)
                    elif chart_type == "violin":
                        y_actual = "file_size" if y_col == "count" else y_col
                        fig_custom = px.violin(df_filtered, x=x_col, y=y_actual, color=color_val, box=True)
                    elif chart_type == "sunburst":
                        path_cols = [c for c in ["category", "file_type", "status"] if c in df_filtered.columns]
                        fig_custom = px.sunburst(df_filtered, path=path_cols, values="chunk_count" if "chunk_count" in df_filtered.columns else None)
                    else:
                        fig_custom = px.bar(df_filtered, x=x_col, y=y_col)

                    fig_custom.update_layout(**chart_theme, title=f"Custom: {chart_type.title()} — {x_col} vs {y_col}")
                    st.plotly_chart(fig_custom, use_container_width=True, key="custom_chart")
                except Exception as e:
                    st.warning(f"Chart rendering issue: {e}. Try different column selections.")

            # ════════════════════════════════════════════════
            # SECTION 9: Data Explorer (Sortable Table)
            # ════════════════════════════════════════════════
            st.markdown("---")
            st.markdown("#### 🔎 Data Explorer")
            if not df_filtered.empty:
                all_cols = list(df_filtered.columns)
                # Default useful columns
                default_cols = [c for c in ["title", "category", "file_type", "file_size", "chunk_count", "status", "uploaded_by", "timestamp"] if c in all_cols]
                selected_cols = st.multiselect("Columns", all_cols, default=default_cols, key="explorer_cols")

                search_term = st.text_input("🔍 Search documents", "", key="explorer_search")

                display_df = df_filtered[selected_cols].copy() if selected_cols else df_filtered.copy()
                if search_term:
                    mask = display_df.astype(str).apply(lambda x: x.str.contains(search_term, case=False, na=False)).any(axis=1)
                    display_df = display_df[mask]

                st.dataframe(display_df, use_container_width=True, hide_index=True, height=400)
                st.caption(f"Showing {len(display_df)} of {len(df_filtered)} documents")

            # ════════════════════════════════════════════════
            # SECTION 10: Report Generation + Export
            # ════════════════════════════════════════════════
            st.markdown("---")
            st.markdown("#### 📄 Report Generation")
            with st.form("report_form"):
                r_topic = st.text_input("Report Topic", placeholder="e.g. Market Analysis Q4 2025")
                r_query = st.text_input("Research Query", placeholder="e.g. What are the key market trends?")
                r_col1, r_col2 = st.columns(2)
                with r_col1:
                    r_type = st.selectbox("Report Type", ["general", "market_analysis", "financial_summary", "strategy_comparison"])
                with r_col2:
                    r_format = st.selectbox("Output Format", ["markdown", "table", "json"])

                submitted = st.form_submit_button("🚀 Generate Report")

            if submitted and r_topic and r_query:
                with st.spinner("Generating report…"):
                    resp = api_post(
                        "/generate_report",
                        {
                            "topic": r_topic, "query": r_query,
                            "report_type": r_type, "output_format": r_format,
                            "model": st.session_state.selected_model,
                            "openai_api_key": st.session_state.openai_api_key or None,
                            "anthropic_api_key": st.session_state.anthropic_api_key or None,
                            "gemini_api_key": st.session_state.gemini_api_key or None,
                        },
                    )
                    if resp:
                        st.markdown("---")
                        st.markdown(f"**Report: {r_topic}**")
                        if r_format == "json":
                            st.json(json.loads(resp["report"]) if isinstance(resp["report"], str) else resp["report"])
                        else:
                            st.markdown(resp["report"])
                        st.download_button(
                            "📥 Download Report",
                            data=resp["report"],
                            file_name=f"report_{r_type}.{'json' if r_format == 'json' else 'md'}",
                        )

            # ════════════════════════════════════════════════
            # SECTION 11: Export Data (BI Integration)
            # ════════════════════════════════════════════════
            st.markdown("---")
            st.markdown("#### 📤 Export Data (BI Integration)")

            if not df_filtered.empty:
                ex1, ex2, ex3 = st.columns(3)
                with ex1:
                    csv_data = df_filtered.to_csv(index=False)
                    st.download_button(
                        "📥 CSV (Tableau / PowerBI)",
                        data=csv_data, file_name="documents_export.csv", mime="text/csv",
                        use_container_width=True,
                    )
                with ex2:
                    json_export = df_filtered.to_json(orient="records", indent=2)
                    st.download_button(
                        "📥 JSON Export",
                        data=json_export, file_name="documents_export.json", mime="application/json",
                        use_container_width=True,
                    )
                with ex3:
                    # Analytics summary export
                    if content_data:
                        summary = json.dumps({
                            "overview": overview,
                            "storage": storage_data,
                            "content_summary": {
                                "total_words": content_data.get("total_estimated_words", 0),
                                "total_reading_time": content_data.get("total_reading_time_min", 0),
                                "top_keywords": dict(list(content_data.get("word_frequencies", {}).items())[:20]),
                            },
                        }, indent=2, default=str)
                        st.download_button(
                            "📥 Analytics Summary",
                            data=summary, file_name="analytics_summary.json", mime="application/json",
                            use_container_width=True,
                        )
