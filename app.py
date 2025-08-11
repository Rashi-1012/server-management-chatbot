import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import json
from chatbot import ServerChatbot
from datetime import datetime
import os
from dotenv import load_dotenv

# Page configuration
st.set_page_config(
    page_title="Chennai Server Management Dashboard",
    page_icon="",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #1f77b4;
    }
    .server-card {
        border: 1px solid #ddd;
        border-radius: 0.5rem;
        padding: 1rem;
        margin: 0.5rem 0;
    }
    .status-up { color: #28a745; }
    .status-down { color: #dc3545; }
    .status-maintenance { color: #ffc107; }

    /* Preserve line breaks in Markdown paragraphs */
    [data-testid="stMarkdownContainer"] p {
        white-space: pre-line;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []

if 'chatbot' not in st.session_state:
    st.session_state.chatbot = ServerChatbot()

# Load environment variables
load_dotenv()

# API base URL (can be overridden via .env)
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

@st.cache_data(ttl=60)  # Cache for 1 minute
def fetch_api_data(endpoint, params=None):
    """Fetch data from API with caching"""
    try:
        url = f"{API_BASE_URL}{endpoint}"
        response = requests.get(url, params=params or {}, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Failed to fetch data: {str(e)}")
        return None

def format_datetime_iso(s):
    """Format an ISO 8601 string to 'YYYY-MM-DD HH:MM:SS'. Returns 'N/A' on failure."""
    if not s:
        return "N/A"
    try:
        # Handle common variants (strip trailing Z)
        if isinstance(s, str):
            s_clean = s.rstrip('Z')
            return datetime.fromisoformat(s_clean).strftime("%Y-%m-%d %H:%M:%S")
        # If already a datetime
        if isinstance(s, datetime):
            return s.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        pass
    return str(s)

def main():
    # Header
    st.markdown('<h1 class="main-header"> Chennai Server Management Dashboard</h1>', unsafe_allow_html=True)
    
    # Sidebar
    st.sidebar.title("Navigation")
    page = st.sidebar.selectbox("Choose a page", 
                               ["Dashboard", "Server List", "Chat Assistant", "Analytics"])
    
    if page == "Dashboard":
        show_dashboard()
    elif page == "Server List":
        show_server_list()
    elif page == "Chat Assistant":
        show_chat_assistant()
    elif page == "Analytics":
        show_analytics()

def show_dashboard():
    st.header(" Dashboard Overview")
    
    # Fetch summary data
    summary = fetch_api_data("/api/summary")
    if not summary:
        st.error("Unable to load dashboard data")
        return
    
    # Metrics row
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric("Total Servers", summary['total_servers'])
    
    with col2:
        st.metric("Active Servers", summary['active_servers'])
    
    with col3:
        st.metric(" Up", summary['servers_up'])
    
    with col4:
        st.metric(" Down", summary['servers_down'])
    
    with col5:
        st.metric(" Maintenance", summary['servers_maintenance'])
    
    # Charts row
    col1, col2 = st.columns(2)
    
    with col1:
        # Status distribution pie chart
        status_data = {
            'Status': ['Up', 'Down', 'Maintenance'],
            'Count': [summary['servers_up'], summary['servers_down'], summary['servers_maintenance']]
        }
        fig_status = px.pie(status_data, values='Count', names='Status', 
                           title="Server Status Distribution",
                           color_discrete_map={'Up': '#28a745', 'Down': '#dc3545', 'Maintenance': '#ffc107'})
        st.plotly_chart(fig_status, use_container_width=True)
    
    with col2:
        # Environment distribution bar chart
        env_data = summary['environments']
        if env_data:
            fig_env = px.bar(x=list(env_data.keys()), y=list(env_data.values()),
                            title="Servers by Environment",
                            labels={'x': 'Environment', 'y': 'Count'},
                            color=list(env_data.values()),
                            color_continuous_scale='viridis')
            st.plotly_chart(fig_env, use_container_width=True)
    
    # Recent activity (simulated)
    st.subheader(" Recent Activity")
    activity_data = [
        {"Time": "2 minutes ago", "Event": "Server chennai-web-01 status checked", "User": "Admin"},
        {"Time": "5 minutes ago", "Event": "Server chennai-db-01 backup completed", "User": "System"},
        {"Time": "12 minutes ago", "Event": "New query: 'Show production servers'", "User": "Priya Sharma"},
        {"Time": "18 minutes ago", "Event": "Server chennai-api-01 health check passed", "User": "System"},
        {"Time": "25 minutes ago", "Event": "Server summary requested", "User": "Rajesh Kumar"}
    ]
    
    activity_df = pd.DataFrame(activity_data)
    st.dataframe(activity_df, use_container_width=True, hide_index=True)

def show_server_list():
    st.header(" Server Inventory")
    
    # Filters
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        env_filter = st.selectbox("Environment", ["All", "production", "staging", "development"])
    
    with col2:
        status_filter = st.selectbox("Status", ["All", "up", "down", "maintenance"])
    
    with col3:
        search_term = st.text_input("Search servers")
    
    with col4:
        if st.button(" Refresh"):
            st.cache_data.clear()
    
    # Build query parameters
    params = {}
    if env_filter != "All":
        params['environment'] = env_filter
    if status_filter != "All":
        params['status'] = status_filter
    if search_term:
        params['search'] = search_term
    
    # Fetch server data
    servers = fetch_api_data("/api/servers", params)
    if not servers:
        st.error("Unable to load server data")
        return
    
    if not servers:
        st.info("No servers found matching the criteria")
        return
    
    # Display servers
    st.subheader(f"Found {len(servers)} servers")
    
    # Convert to DataFrame for better display
    server_data = []
    for server in servers:
        server_data.append({
            'Name': server['name'],
            'IP Address': server['ip_address'],
            'Status': server['status'],
            'Environment': server['environment'],
            'OS': f"{server.get('os', 'N/A')} {server.get('os_version', '')}".strip(),
            'CPU Cores': server.get('cpu_cores', 'N/A'),
            'Memory (GB)': server.get('memory_gb', 'N/A'),
            'Owner': server.get('owner_name', 'N/A'),
            'Last Seen': format_datetime_iso(server.get('last_seen'))
        })
    
    df = pd.DataFrame(server_data)
    
    # Style the dataframe
    def style_status(val):
        if val == 'up':
            return 'background-color: #d4edda; color: #155724'
        elif val == 'down':
            return 'background-color: #f8d7da; color: #721c24'
        elif val == 'maintenance':
            return 'background-color: #fff3cd; color: #856404'
        return ''
    
    styled_df = df.style.applymap(style_status, subset=['Status'])
    st.dataframe(styled_df, use_container_width=True, hide_index=True)
    
    # Server details expander
    if servers:
        st.subheader("Server Details")
        server_names = [server['name'] for server in servers]
        selected_server = st.selectbox("Select a server for details", server_names)
        
        if selected_server:
            server_detail = next(s for s in servers if s['name'] == selected_server)
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown(f"""
                **Name:** {server_detail['name']}
                **IP Address:** {server_detail['ip_address']}
                **FQDN:** {server_detail.get('fqdn', 'N/A')}
                **Status:** {server_detail['status'].upper()}
                **Environment:** {server_detail['environment']}
                """)
            
            with col2:
                st.markdown(f"""
                **OS:** {server_detail.get('os', 'N/A')} {server_detail.get('os_version', '')}
                **CPU Cores:** {server_detail.get('cpu_cores', 'N/A')}
                **Memory:** {server_detail.get('memory_gb', 'N/A')} GB
                **Disk:** {server_detail.get('disk_gb', 'N/A')} GB
                **Owner:** {server_detail.get('owner_name', 'N/A')}
                **Last Seen:** {format_datetime_iso(server_detail.get('last_seen'))}
                """)
            
            if server_detail.get('notes'):
                st.markdown(f"**Notes:** {server_detail['notes']}")
            
            if server_detail.get('tags'):
                tags = ', '.join(server_detail['tags'])
                st.markdown(f"**Tags:** {tags}")

def show_chat_assistant():
    st.header(" AI Chat Assistant")
    st.markdown("Ask me anything about your Chennai servers!")
    
    # Chat interface
    chat_container = st.container()
    
    # Display chat history
    with chat_container:
        for message in st.session_state.chat_history:
            if message['role'] == 'user':
                st.markdown("**You:**")
                st.markdown(message['content'])
            else:
                st.markdown("**Assistant:**")
                st.markdown(message['content'])
            st.markdown("---")
    
    # Chat input
    user_input = st.text_input("Ask about your servers...", key="chat_input", 
                              placeholder="e.g., 'Which servers are down?' or 'Show me production servers'")
    
    col1, col2 = st.columns([1, 4])
    with col1:
        send_button = st.button("Send", type="primary")
    with col2:
        if st.button("Clear Chat"):
            st.session_state.chat_history = []
            st.rerun()
    
    if send_button and user_input:
        # Add user message to history
        st.session_state.chat_history.append({"role": "user", "content": user_input})
        
        # Get bot response
        with st.spinner("Thinking..."):
            try:
                response = st.session_state.chatbot.generate_response(user_input)
                st.session_state.chat_history.append({"role": "assistant", "content": response})
            except Exception as e:
                error_msg = f"Sorry, I encountered an error: {str(e)}"
                st.session_state.chat_history.append({"role": "assistant", "content": error_msg})
        
        st.rerun()
    
    # Suggested questions
    st.subheader(" Try these questions:")
    suggestions = [
        "How many servers do we have?",
        "Which servers are down?",
        "Show me production servers",
        "What's the status of chennai-web-01?",
        "List servers in maintenance",
        "Who owns the database servers?"
    ]
    
    cols = st.columns(2)
    for i, suggestion in enumerate(suggestions):
        with cols[i % 2]:
            if st.button(suggestion, key=f"suggestion_{i}"):
                st.session_state.chat_history.append({"role": "user", "content": suggestion})
                with st.spinner("Thinking..."):
                    try:
                        response = st.session_state.chatbot.generate_response(suggestion)
                        st.session_state.chat_history.append({"role": "assistant", "content": response})
                    except Exception as e:
                        error_msg = f"Sorry, I encountered an error: {str(e)}"
                        st.session_state.chat_history.append({"role": "assistant", "content": error_msg})
                st.rerun()

def show_analytics():
    st.header(" Analytics & Insights")
    
    # Fetch all servers for analytics
    servers = fetch_api_data("/api/servers")
    if not servers:
        st.error("Unable to load analytics data")
        return
    
    # Create analytics
    df = pd.DataFrame(servers)
    
    # Resource utilization chart
    col1, col2 = st.columns(2)
    
    with col1:
        # CPU cores distribution
        if 'cpu_cores' in df.columns:
            cpu_data = df.groupby('cpu_cores')['name'].count().reset_index()
            cpu_data.columns = ['CPU Cores', 'Count']
            fig_cpu = px.bar(cpu_data, x='CPU Cores', y='Count', 
                            title="CPU Cores Distribution")
            st.plotly_chart(fig_cpu, use_container_width=True)
    
    with col2:
        # Memory distribution
        if 'memory_gb' in df.columns:
            memory_data = df.groupby('memory_gb')['name'].count().reset_index()
            memory_data.columns = ['Memory (GB)', 'Count']
            fig_memory = px.bar(memory_data, x='Memory (GB)', y='Count', 
                               title="Memory Distribution")
            st.plotly_chart(fig_memory, use_container_width=True)
    
    # OS distribution
    if 'os' in df.columns:
        os_counts = df['os'].value_counts()
        fig_os = px.pie(values=os_counts.values, names=os_counts.index, 
                       title="Operating System Distribution")
        st.plotly_chart(fig_os, use_container_width=True)
    
    # Environment vs Status heatmap
    if 'environment' in df.columns and 'status' in df.columns:
        heatmap_data = df.groupby(['environment', 'status']).size().unstack(fill_value=0)
        fig_heatmap = px.imshow(heatmap_data.values, 
                               x=heatmap_data.columns, 
                               y=heatmap_data.index,
                               title="Environment vs Status Heatmap",
                               labels=dict(x="Status", y="Environment", color="Count"))
        st.plotly_chart(fig_heatmap, use_container_width=True)
    
    # Resource recommendations
    st.subheader(" Recommendations")
    
    total_cpu = df['cpu_cores'].sum() if 'cpu_cores' in df.columns else 0
    total_memory = df['memory_gb'].sum() if 'memory_gb' in df.columns else 0
    down_servers = len(df[df['status'] == 'down']) if 'status' in df.columns else 0
    
    recommendations = []
    
    if down_servers > 0:
        recommendations.append(f" {down_servers} servers are currently down and need attention")
    
    if total_cpu > 0:
        avg_cpu = total_cpu / len(df)
        if avg_cpu < 4:
            recommendations.append(" Consider upgrading CPU cores for better performance")
    
    if total_memory > 0:
        avg_memory = total_memory / len(df)
        if avg_memory < 8:
            recommendations.append(" Consider increasing memory allocation")
    
    if not recommendations:
        recommendations.append(" All systems look healthy!")
    
    for rec in recommendations:
        st.markdown(f"- {rec}")

if __name__ == "__main__":
    main()
