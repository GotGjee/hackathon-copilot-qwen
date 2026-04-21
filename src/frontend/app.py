"""
Hackathon Copilot - Streamlit Frontend
Chat-style UI with agent avatars and real-time event streaming.
"""

import streamlit as st
import requests
import time
import os

# Configuration
API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8000")

# Agent avatar config
AGENT_AVATARS = {
    "Max": {"icon": "🧠", "color": "#FF6B6B"},
    "Sarah": {"icon": "⚖️", "color": "#4ECDC4"},
    "Dave": {"icon": "📋", "color": "#45B7D1"},
    "Luna": {"icon": "🏗️", "color": "#96CEB4"},
    "Kai": {"icon": "🔨", "color": "#FFEAA7"},
    "Rex": {"icon": "🔍", "color": "#DDA0DD"},
    "Nova": {"icon": "🎤", "color": "#F8B500"},
    "Nova (Slides)": {"icon": "📊", "color": "#9B59B6"},
    "Nova (Script)": {"icon": "🎙️", "color": "#E74C3C"},
    "System": {"icon": "🚀", "color": "#2ECC71"},
}


def api_request(method: str, endpoint: str, data: dict = None):
    """Make API request with error handling."""
    try:
        url = f"{API_BASE_URL}{endpoint}"
        if method == "GET":
            response = requests.get(url, timeout=10)
        elif method == "POST":
            response = requests.post(url, json=data or {}, timeout=10)
        else:
            return None
        response.raise_for_status()
        return response.json()
    except requests.exceptions.ConnectionError:
        return None
    except requests.exceptions.HTTPError:
        return None
    except requests.exceptions.Timeout:
        return None


def main():
    st.set_page_config(
        page_title="Hackathon Copilot",
        page_icon="🚀",
        layout="wide",
    )

    # Custom CSS
    st.markdown("""
        <style>
            .main .block-container { padding-top: 1rem; }
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
        </style>
    """, unsafe_allow_html=True)

    st.title("🚀 Hackathon Copilot")
    st.caption("AI-Powered Multi-Agent Team for Hackathon Success")

    # Initialize session state
    if "session_id" not in st.session_state:
        st.session_state.session_id = None
    if "workflow_started" not in st.session_state:
        st.session_state.workflow_started = False
    if "stream_messages" not in st.session_state:
        st.session_state.stream_messages = []
    if "event_index" not in st.session_state:
        st.session_state.event_index = 0
    if "prev_layer" not in st.session_state:
        st.session_state.prev_layer = ""

    # Sidebar
    with st.sidebar:
        st.header("⚙️ Controls")

        if st.button("🆕 New Session"):
            st.session_state.session_id = None
            st.session_state.workflow_started = False
            st.session_state.stream_messages = []
            st.session_state.event_index = 0
            st.session_state.prev_layer = ""
            st.rerun()

        if st.session_state.session_id:
            st.success(f"Session: `{st.session_state.session_id}`")
            if st.button("🔄 Refresh"):
                st.rerun()
        
        st.divider()
        st.caption("💡 Create a session and click Start to watch your AI team work!")

    # Main flow
    if not st.session_state.session_id:
        show_create_session()
    else:
        show_session_flow()


def show_create_session():
    """Show session creation form."""
    st.header("🎯 Create New Session")

    theme = st.text_input(
        "Hackathon Theme",
        placeholder="e.g., Sustainable Living, AI for Education, Healthcare Innovation",
    )

    constraints = st.text_area(
        "Constraints",
        placeholder="e.g., Must use FastAPI, 48 hours, team of 2, no external APIs",
        value="48-hour hackathon, solo developer",
    )

    if st.button("🚀 Start Session", type="primary", disabled=not theme):
        with st.spinner("Creating session..."):
            result = api_request("POST", "/sessions", {
                "theme": theme,
                "constraints": constraints,
            })

        if result:
            st.session_state.session_id = result["session_id"]
            st.session_state.workflow_started = False
            st.session_state.stream_messages = []
            st.session_state.event_index = 0
            st.session_state.prev_layer = ""
            st.success(f"Session created: `{result['session_id']}`")
            st.rerun()


def poll_events(session_id: str, since_index: int = 0):
    """Poll for new events from the server."""
    try:
        url = f"{API_BASE_URL}/sessions/{session_id}/events"
        params = {"since_index": since_index}
        response = requests.get(url, params=params, timeout=3)
        if response.status_code == 200:
            return response.json()
    except Exception:
        pass
    return {"events": [], "total": since_index}


def show_session_flow():
    """Show main workflow with chat-style UI."""
    session_id = st.session_state.session_id

    # Poll for new events
    event_data = poll_events(session_id, st.session_state.event_index)
    new_events = event_data.get("events", [])
    
    if new_events:
        for event in new_events:
            st.session_state.stream_messages.append(event)
            st.session_state.event_index = event.get("index", 0) + 1
    
    # Get session state
    state = api_request("GET", f"/sessions/{session_id}")
    if not state:
        st.error("Failed to load session")
        return

    # Track layer changes
    prev_layer = st.session_state.prev_layer
    current_layer = state.get("current_layer", "")
    if current_layer != prev_layer:
        st.session_state.prev_layer = current_layer

    # Progress indicator
    st.progress(get_progress_value(current_layer))
    status_text = get_status_text(current_layer)
    st.caption(f"Current Phase: **{status_text}**")

    # Chat container
    st.subheader("💬 Team Chat")
    
    for msg in st.session_state.stream_messages:
        render_chat_bubble(msg)
    
    # Show agent_log messages (avoid duplicates)
    if state.get("agent_log"):
        shown_messages = {m.get("message", "") for m in st.session_state.stream_messages}
        for msg in state["agent_log"]:
            if msg.get("message", "") not in shown_messages:
                render_chat_bubble({
                    "event_type": "message",
                    "agent": msg.get("agent", "system"),
                    "agent_name": msg.get("agent_name", "System"),
                    "emoji": msg.get("emoji", "🤖"),
                    "role": msg.get("role", ""),
                    "message": msg.get("message", ""),
                })

    # Phase-specific UI
    if current_layer == "hitl_1" and not state.get("selected_idea"):
        handle_idea_selection(state)
    elif current_layer == "hitl_1" and state.get("selected_idea"):
        selected = state.get("selected_idea", {})
        st.success(f"✅ Selected: **{selected.get('title', '')}** - AI is now developing...")
    elif current_layer == "judging":
        st.info("⏳ AI is evaluating ideas... Please wait.")
    elif current_layer == "hitl_2":
        handle_code_review(state)
    elif current_layer == "complete":
        handle_completion(state)
    elif current_layer == "error":
        st.error(f"❌ Error: {state.get('pause_reason', 'Unknown error')}")
    elif not state.get("is_paused") and not st.session_state.workflow_started:
        handle_auto_start(state)
    elif not state.get("is_paused") and st.session_state.workflow_started:
        st.info(f"🔄 AI is working... {get_status_text(current_layer)}")
        # Auto-refresh with delay when workflow is active (no flickering)
        time.sleep(1)
        st.rerun()


def render_chat_bubble(msg: dict):
    """Render a chat bubble message."""
    event_type = msg.get("event_type", "message")
    emoji = msg.get("emoji", "")
    agent_name = msg.get("agent_name", "System")
    role = msg.get("role", "")
    message = msg.get("message", "")
    avatar = AGENT_AVATARS.get(agent_name, {"icon": "🤖", "color": "#95A5A6"})
    
    if event_type == "thinking":
        st.info(f"{emoji} **{agent_name}** *({role})* is thinking...\n\n{message}")
    elif event_type == "phase_start":
        st.success(f"{emoji} **{agent_name}**: {message}")
    elif event_type == "phase_complete":
        st.success(f"{emoji} **{agent_name}**: {message}")
    elif event_type == "error":
        st.error(f"{emoji} **{agent_name}**: {message}")
    elif event_type == "message":
        st.markdown(
            f"""
            <div style="margin-bottom: 8px; display: flex; align-items: flex-start; gap: 10px;">
                <div style="width: 36px; height: 36px; border-radius: 50%; background: {avatar['color']}; 
                            display: flex; align-items: center; justify-content: center; flex-shrink: 0; font-size: 18px;">
                    {avatar['icon']}
                </div>
                <div style="flex: 1;">
                    <div style="margin-bottom: 2px;">
                        <strong style="color: {avatar['color']};">{agent_name}</strong>
                        <span style="color: #888; font-size: 0.85em; margin-left: 8px;">{role}</span>
                    </div>
                    <div style="background: #f0f2f6; border-radius: 12px; padding: 12px 16px; 
                                max-width: 85%; color: #333; line-height: 1.5;">
                        {message}
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )


def get_status_text(layer: str) -> str:
    """Convert workflow layer to status text."""
    return {
        "idle": "🟡 Waiting to start",
        "ideation": "🧠 Brainstorming ideas...",
        "judging": "⚖️ Evaluating ideas...",
        "hitl_1": "⏸️ Waiting for your input",
        "planning": "📋 Planning milestones...",
        "architecting": "🏗️ Designing architecture...",
        "building": "🔨 Writing code...",
        "critiquing": "🔍 Reviewing code...",
        "hitl_2": "⏸️ Code review pending",
        "pitching": "🎤 Preparing pitch...",
        "complete": "✅ Complete!",
        "error": "❌ Error occurred",
    }.get(layer, layer)


def handle_auto_start(state):
    """Start the workflow."""
    st.session_state.workflow_started = True
    result = api_request("POST", f"/sessions/{st.session_state.session_id}/start")
    if result:
        st.info("🚀 Workflow started! Watch the AI team work below...")
        st.rerun()
    else:
        st.error("Failed to start workflow")
        st.session_state.workflow_started = False


def handle_idea_selection(state):
    """Handle idea selection HITL."""
    st.subheader("🎯 Select an Idea")

    if state.get("ideas"):
        cols = st.columns(min(len(state["ideas"]), 3))
        for i, idea in enumerate(state["ideas"]):
            with cols[i % 3]:
                with st.container(border=True):
                    st.write(f"### {idea.get('title', '')}")
                    st.write(idea.get("description", ""))
                    if idea.get("key_features"):
                        st.write("**Features:**")
                        for f in idea["key_features"]:
                            st.write(f"• {f}")
                    if st.button(f"Select #{idea.get('id')}", key=f"select_{idea.get('id')}"):
                        with st.spinner("Processing selection..."):
                            result = api_request("POST", f"/sessions/{st.session_state.session_id}/select-idea", {
                                "idea_id": idea.get("id"),
                            })
                        if result:
                            st.rerun()
    else:
        st.info("Waiting for ideas to be generated...")


def handle_code_review(state):
    """Handle code review HITL."""
    st.subheader("🔍 Code Review")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("✅ Approve Code", type="primary"):
            with st.spinner("Processing..."):
                result = api_request("POST", f"/sessions/{st.session_state.session_id}/review-code", {
                    "approved": True,
                })
            if result:
                st.rerun()
    with col2:
        feedback = st.text_area("Change Requests (optional)")
        if st.button("❌ Request Changes"):
            with st.spinner("Processing..."):
                result = api_request("POST", f"/sessions/{st.session_state.session_id}/review-code", {
                    "approved": False,
                    "feedback": feedback,
                })
            if result:
                st.rerun()


def handle_completion(state):
    """Handle workflow completion."""
    st.success("🎉 Hackathon project complete!")

    st.subheader("📦 Export")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("📥 Download Code"):
            result = api_request("GET", f"/sessions/{st.session_state.session_id}/export/code")
            if result:
                st.success(f"Code exported to: `{result['filepath']}`")
    with col2:
        if st.button("📥 Download Pitch Materials"):
            result = api_request("GET", f"/sessions/{st.session_state.session_id}/export/pitch")
            if result:
                st.success(f"Pitch materials exported to: `{result['filepath']}`")

    st.subheader("📊 Project Summary")
    if state.get("selected_idea"):
        st.write(f"**Project:** {state['selected_idea'].get('title', '')}")
        st.write(f"**Description:** {state['selected_idea'].get('description', '')}")
    if state.get("slides"):
        st.write(f"**Slides:** {len(state['slides'])} slides created")
    if state.get("script"):
        st.write(f"**Script:** {len(state['script'])} sections")


def get_progress_value(layer: str) -> float:
    """Convert workflow layer to progress value."""
    layers = [
        "idle", "ideation", "judging", "hitl_1", "planning",
        "architecting", "building", "critiquing", "hitl_2",
        "pitching", "complete"
    ]
    try:
        idx = layers.index(layer)
        return (idx + 1) / len(layers)
    except ValueError:
        return 0.0


if __name__ == "__main__":
    main()