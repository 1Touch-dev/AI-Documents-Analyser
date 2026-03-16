"""
Enterprise-Level Analytics Dashboard
PowerBI/Tableau style dashboard with real-time metrics, KPIs, and interactive charts.
"""

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
import requests
from datetime import datetime, timedelta
import time

# ══════════════════════════════════════════════════════════
#  Page Configuration
# ══════════════════════════════════════════════════════════

st.set_page_config(
    page_title="Analytics Dashboard - AI Documents Analyser",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS for enterprise look
st.markdown("""
<style>
    /* Main container */
    .main {
        background-color: #f5f7fa;
    }

    /* Metric cards */
    [data-testid="stMetricValue"] {
        font-size: 32px;
        font-weight: 700;
        color: #1f2937;
    }

    [data-testid="stMetricLabel"] {
        font-size: 14px;
        font-weight: 600;
        color: #6b7280;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }

    [data-testid="stMetricDelta"] {
        font-size: 14px;
    }

    /* Card styling */
    .metric-card {
        background: white;
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        border-left: 4px solid #3b82f6;
    }

    /* Header styling */
    h1 {
        color: #1f2937;
        font-weight: 700;
        padding-bottom: 10px;
        border-bottom: 3px solid #3b82f6;
    }

    h2 {
        color: #374151;
        font-weight: 600;
        margin-top: 30px;
    }

    h3 {
        color: #4b5563;
        font-weight: 600;
    }

    /* Sidebar */
    [data-testid="stSidebar"] {
        background-color: #1f2937;
    }

    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] {
        color: white;
    }

    /* Success/Info boxes */
    .stAlert {
        border-radius: 8px;
    }
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════
#  Helper Functions
# ══════════════════════════════════════════════════════════

@st.cache_data(ttl=30)
def fetch_analytics_data():
    """Fetch real-time analytics data from backend."""
    try:
        # Fetch from all analytics endpoints
        overview = requests.get("http://localhost:8000/api/analytics/overview", timeout=5).json()
        content = requests.get("http://localhost:8000/api/analytics/content", timeout=5).json()
        storage = requests.get("http://localhost:8000/api/analytics/storage", timeout=5).json()

        return {
            "overview": overview,
            "content": content,
            "storage": storage,
            "timestamp": datetime.now()
        }
    except Exception as e:
        st.error(f"Failed to fetch analytics data: {e}")
        return None

def create_kpi_card(label, value, delta=None, delta_color="normal", icon="📊"):
    """Create a professional KPI card."""
    col1, col2 = st.columns([1, 4])
    with col1:
        st.markdown(f"<div style='font-size: 48px;'>{icon}</div>", unsafe_allow_html=True)
    with col2:
        st.metric(label=label, value=value, delta=delta, delta_color=delta_color)

def create_gauge_chart(value, max_value, title, color="#3b82f6"):
    """Create a professional gauge chart."""
    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=value,
        domain={'x': [0, 1], 'y': [0, 1]},
        title={'text': title, 'font': {'size': 18, 'color': '#1f2937'}},
        delta={'reference': max_value * 0.8, 'increasing': {'color': "#10b981"}},
        gauge={
            'axis': {'range': [None, max_value], 'tickwidth': 1, 'tickcolor': "#d1d5db"},
            'bar': {'color': color},
            'bgcolor': "white",
            'borderwidth': 2,
            'bordercolor': "#e5e7eb",
            'steps': [
                {'range': [0, max_value * 0.5], 'color': '#f3f4f6'},
                {'range': [max_value * 0.5, max_value * 0.8], 'color': '#e5e7eb'}
            ],
            'threshold': {
                'line': {'color': "#ef4444", 'width': 4},
                'thickness': 0.75,
                'value': max_value * 0.9
            }
        }
    ))

    fig.update_layout(
        height=250,
        margin=dict(l=20, r=20, t=60, b=20),
        paper_bgcolor='white',
        font={'color': "#1f2937", 'family': "Arial"}
    )

    return fig

def create_time_series_chart(data, title):
    """Create an interactive time series chart."""
    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=data['date'],
        y=data['value'],
        mode='lines+markers',
        name='Documents',
        line=dict(color='#3b82f6', width=3),
        marker=dict(size=8, color='#3b82f6', line=dict(width=2, color='white')),
        fill='tonexty',
        fillcolor='rgba(59, 130, 246, 0.1)'
    ))

    fig.update_layout(
        title=dict(text=title, font=dict(size=20, color='#1f2937', family='Arial Bold')),
        xaxis=dict(
            title='Date',
            showgrid=True,
            gridcolor='#e5e7eb',
            color='#6b7280'
        ),
        yaxis=dict(
            title='Count',
            showgrid=True,
            gridcolor='#e5e7eb',
            color='#6b7280'
        ),
        plot_bgcolor='white',
        paper_bgcolor='white',
        hovermode='x unified',
        height=350,
        margin=dict(l=50, r=50, t=80, b=50)
    )

    return fig

def create_category_distribution_chart(data):
    """Create a beautiful donut chart for category distribution."""
    fig = go.Figure(data=[go.Pie(
        labels=data['category'],
        values=data['count'],
        hole=0.5,
        marker=dict(
            colors=['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899'],
            line=dict(color='white', width=2)
        ),
        textinfo='label+percent',
        textfont=dict(size=14, color='white'),
        hovertemplate='<b>%{label}</b><br>Count: %{value}<br>Percentage: %{percent}<extra></extra>'
    )])

    fig.update_layout(
        title=dict(
            text='Document Distribution by Category',
            font=dict(size=20, color='#1f2937', family='Arial Bold'),
            x=0.5,
            xanchor='center'
        ),
        showlegend=True,
        legend=dict(
            orientation="v",
            yanchor="middle",
            y=0.5,
            xanchor="left",
            x=1.02,
            font=dict(size=12, color='#1f2937')
        ),
        height=400,
        paper_bgcolor='white',
        plot_bgcolor='white',
        margin=dict(l=20, r=150, t=80, b=20)
    )

    return fig

def create_performance_chart(embedding_time, query_time):
    """Create a bar chart showing performance metrics."""
    fig = go.Figure()

    categories = ['Embedding', 'Query Processing']
    times = [embedding_time, query_time]
    colors = ['#3b82f6', '#10b981']

    fig.add_trace(go.Bar(
        x=categories,
        y=times,
        marker=dict(
            color=colors,
            line=dict(color='white', width=2)
        ),
        text=[f'{t:.2f}s' for t in times],
        textposition='outside',
        textfont=dict(size=14, color='#1f2937', family='Arial Bold'),
        hovertemplate='<b>%{x}</b><br>Time: %{y:.2f}s<extra></extra>'
    ))

    fig.update_layout(
        title=dict(
            text='Average Processing Times',
            font=dict(size=20, color='#1f2937', family='Arial Bold')
        ),
        xaxis=dict(
            title='',
            showgrid=False,
            color='#6b7280'
        ),
        yaxis=dict(
            title='Time (seconds)',
            showgrid=True,
            gridcolor='#e5e7eb',
            color='#6b7280'
        ),
        plot_bgcolor='white',
        paper_bgcolor='white',
        height=350,
        margin=dict(l=50, r=50, t=80, b=50),
        showlegend=False
    )

    return fig

# ══════════════════════════════════════════════════════════
#  Main Dashboard
# ══════════════════════════════════════════════════════════

# Header
st.title("📊 Enterprise Analytics Dashboard")
st.markdown("Real-time insights into your AI Documents Analyser performance")
st.markdown("---")

# Sidebar
with st.sidebar:
    st.markdown("### ⚙️ Dashboard Controls")
    st.markdown("---")

    auto_refresh = st.checkbox("🔄 Auto-refresh", value=True)
    if auto_refresh:
        refresh_interval = st.slider("Refresh interval (seconds)", 5, 60, 30)
        st.info(f"Dashboard refreshes every {refresh_interval}s")

    st.markdown("---")
    st.markdown("### 📅 Date Range")
    date_range = st.selectbox(
        "Time period",
        ["Last 24 Hours", "Last 7 Days", "Last 30 Days", "All Time"]
    )

    st.markdown("---")
    st.markdown("### 🎨 Theme")
    st.radio("Color scheme", ["Professional Blue", "Success Green", "Premium Purple"], index=0)

    st.markdown("---")
    if st.button("🔄 Refresh Now", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

# Fetch data
with st.spinner("Loading analytics data..."):
    analytics = fetch_analytics_data()

if not analytics:
    st.error("Unable to load analytics data. Please check if the backend is running.")
    st.stop()

overview = analytics["overview"]
content = analytics["content"]
storage = analytics["storage"]

# ══════════════════════════════════════════════════════════
#  KPI Section
# ══════════════════════════════════════════════════════════

st.markdown("## 📈 Key Performance Indicators")

kpi_col1, kpi_col2, kpi_col3, kpi_col4 = st.columns(4)

with kpi_col1:
    create_kpi_card(
        "Total Documents",
        f"{overview.get('total_documents', 0):,}",
        delta=f"+{overview.get('documents_this_week', 0)} this week",
        delta_color="normal",
        icon="📄"
    )

with kpi_col2:
    create_kpi_card(
        "Total Queries",
        f"{overview.get('total_conversations', 0):,}",
        delta=f"+{overview.get('conversations_this_week', 0)} this week",
        delta_color="normal",
        icon="💬"
    )

with kpi_col3:
    chunks = content.get('total_chunks', 0)
    create_kpi_card(
        "Knowledge Chunks",
        f"{chunks:,}",
        delta=f"{content.get('avg_chunks_per_doc', 0):.0f} avg/doc",
        delta_color="off",
        icon="🧩"
    )

with kpi_col4:
    total_size_mb = storage.get('total_size_mb', 0)
    create_kpi_card(
        "Storage Used",
        f"{total_size_mb:.1f} MB",
        delta=f"{storage.get('avg_size_mb', 0):.2f} MB avg",
        delta_color="off",
        icon="💾"
    )

st.markdown("---")

# ══════════════════════════════════════════════════════════
#  Charts Section Row 1
# ══════════════════════════════════════════════════════════

st.markdown("## 📊 Performance Metrics")

chart_col1, chart_col2 = st.columns(2)

with chart_col1:
    # Gauge chart for system health
    total_docs = overview.get('total_documents', 0)
    max_capacity = 10000  # Adjust based on your system

    gauge_fig = create_gauge_chart(
        value=total_docs,
        max_value=max_capacity,
        title="System Capacity",
        color="#3b82f6"
    )
    st.plotly_chart(gauge_fig, use_container_width=True)

with chart_col2:
    # Performance metrics
    perf_fig = create_performance_chart(
        embedding_time=1.2,  # Replace with actual data
        query_time=0.8       # Replace with actual data
    )
    st.plotly_chart(perf_fig, use_container_width=True)

# ══════════════════════════════════════════════════════════
#  Charts Section Row 2
# ══════════════════════════════════════════════════════════

st.markdown("---")
st.markdown("## 📁 Content Analysis")

chart_col3, chart_col4 = st.columns(2)

with chart_col3:
    # Category distribution
    category_dist = overview.get('documents_by_category', {})
    if category_dist:
        cat_data = {
            'category': list(category_dist.keys()),
            'count': list(category_dist.values())
        }
        cat_fig = create_category_distribution_chart(cat_data)
        st.plotly_chart(cat_fig, use_container_width=True)
    else:
        st.info("No category data available yet")

with chart_col4:
    # File type distribution
    file_types = storage.get('by_file_type', {})
    if file_types:
        fig = px.bar(
            x=list(file_types.keys()),
            y=list(file_types.values()),
            labels={'x': 'File Type', 'y': 'Count'},
            title='Documents by File Type',
            color=list(file_types.values()),
            color_continuous_scale='Blues'
        )
        fig.update_layout(
            title_font=dict(size=20, color='#1f2937', family='Arial Bold'),
            paper_bgcolor='white',
            plot_bgcolor='white',
            height=400,
            showlegend=False,
            xaxis=dict(showgrid=False, color='#6b7280'),
            yaxis=dict(showgrid=True, gridcolor='#e5e7eb', color='#6b7280')
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No file type data available yet")

# ══════════════════════════════════════════════════════════
#  Time Series Section
# ══════════════════════════════════════════════════════════

st.markdown("---")
st.markdown("## 📅 Activity Timeline")

# Generate sample time series data (replace with actual data from backend)
dates = pd.date_range(end=datetime.now(), periods=30, freq='D')
values = [10, 15, 13, 18, 22, 20, 25, 28, 24, 30, 35, 32, 38, 40, 42, 45, 43, 48, 50, 52, 55, 53, 58, 60, 62, 65, 63, 68, 70, 72]

time_series_data = {
    'date': dates,
    'value': values[:len(dates)]
}

timeline_fig = create_time_series_chart(time_series_data, "Document Upload Trend (Last 30 Days)")
st.plotly_chart(timeline_fig, use_container_width=True)

# ══════════════════════════════════════════════════════════
#  Data Tables Section
# ══════════════════════════════════════════════════════════

st.markdown("---")
st.markdown("## 📋 Detailed Metrics")

table_col1, table_col2 = st.columns(2)

with table_col1:
    st.markdown("### Top Categories")
    if category_dist:
        cat_df = pd.DataFrame({
            'Category': list(category_dist.keys()),
            'Documents': list(category_dist.values())
        }).sort_values('Documents', ascending=False)

        # Add percentage
        cat_df['Percentage'] = (cat_df['Documents'] / cat_df['Documents'].sum() * 100).round(1)
        cat_df['Percentage'] = cat_df['Percentage'].astype(str) + '%'

        st.dataframe(
            cat_df,
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("No data available")

with table_col2:
    st.markdown("### System Statistics")
    stats_df = pd.DataFrame({
        'Metric': [
            'Avg Chunks/Document',
            'Avg File Size',
            'Total Storage',
            'Embedding Dimension',
            'Cache Hit Rate'
        ],
        'Value': [
            f"{content.get('avg_chunks_per_doc', 0):.0f}",
            f"{storage.get('avg_size_mb', 0):.2f} MB",
            f"{storage.get('total_size_mb', 0):.1f} MB",
            "768",  # From bge-base model
            "N/A"  # Add cache stats when available
        ]
    })
    st.dataframe(stats_df, use_container_width=True, hide_index=True)

# ══════════════════════════════════════════════════════════
#  Footer
# ══════════════════════════════════════════════════════════

st.markdown("---")
col1, col2, col3 = st.columns(3)

with col1:
    st.markdown(f"**Last Updated:** {analytics['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}")

with col2:
    st.markdown(f"**System Status:** 🟢 Healthy")

with col3:
    st.markdown(f"**Backend:** Connected")

# Auto-refresh
if auto_refresh:
    time.sleep(refresh_interval)
    st.rerun()
