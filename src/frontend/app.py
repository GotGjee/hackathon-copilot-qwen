"""
Hackathon Copilot - Streamlit Frontend
LINE/WhatsApp-style chat UI with Alibaba orange-white theme.
"""

import streamlit as st
import requests
import time
import os
import base64
from datetime import datetime

# Configuration
API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8000")

# Agent config with Alibaba theme colors
AGENTS = {
    "Max": {"icon": "🧠", "color": "#FF6B00", "bg": "#FFF3E0", "align": "right"},
    "Sarah": {"icon": "⚖️", "color": "#E65100", "bg": "#FFF8E1", "align": "left"},
    "Dave": {"icon": "📋", "color": "#F57C00", "bg": "#FFF3E0", "align": "left"},
    "Luna": {"icon": "🏗️", "color": "#FF8F00", "bg": "#FFF8E1", "align": "left"},
    "Kai": {"icon": "🔨", "color": "#FFB300", "bg": "#FFF3E0", "align": "right"},
    "Rex": {"icon": "🔍", "color": "#E65100", "bg": "#FFF8E1", "align": "left"},
    "Nova": {"icon": "🎤", "color": "#FF6B00", "bg": "#FFF3E0", "align": "right"},
    "Nova (Slides)": {"icon": "📊", "color": "#F57C00", "bg": "#FFF3E0", "align": "right"},
    "Nova (Script)": {"icon": "🎙️", "color": "#FF8F00", "bg": "#FFF3E0", "align": "right"},
    "System": {"icon": "🚀", "color": "#FF6B00", "bg": "#FFF3E0", "align": "center"},
}

# Dialogue pairs
DIALOGUE_PAIRS = {
    "Max": "Sarah",
    "Sarah": "Max",
    "Kai": "Rex",
    "Rex": "Kai",
    "Nova (Slides)": "Nova",
    "Nova (Script)": "Nova (Slides)",
}


def api_request(method: str, endpoint: str, data: dict | None = None):
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
    except requests.exceptions.RequestException:
        return None


def format_time():
    """Get current time string."""
    return datetime.now().strftime("%H:%M")


def render_chat_ui():
    """Render LINE-style chat interface."""
    messages = st.session_state.stream_messages
    prev_agent = None
    
    # Build HTML for all messages
    html_parts = []
    
    for msg in messages:
        event_type = msg.get("event_type", "message")
        agent_name = msg.get("agent_name", "System")
        role = msg.get("role", "")
        message = msg.get("message", "")
        timestamp = msg.get("timestamp", "")
        
        agent_info = AGENTS.get(agent_name, {"icon": "🤖", "color": "#95A5A6", "bg": "#F5F5F5", "align": "left"})
        icon = agent_info["icon"]
        color = agent_info["color"]
        bg_color = agent_info["bg"]
        align = agent_info["align"]
        
        # Check if this is a dialogue message
        expected_reply = DIALOGUE_PAIRS.get(agent_name)
        is_dialogue = expected_reply is not None and prev_agent == expected_reply
        prev_agent = agent_name
        
        # Skip thinking events (they're shown as status)
        if event_type == "thinking":
            html_parts.append(f'<!-- thinking: {agent_name} -->')
            continue
        
        # Phase start/complete - system notifications
        if event_type in ("phase_start", "phase_complete"):
            html_parts.append(
                f'<div class="system-msg">{message}</div>'
            )
            continue
        
        # Error messages
        if event_type == "error":
            html_parts.append(
                f'<div class="system-msg error">{message}</div>'
            )
            continue
        
        # Regular messages - LINE/WhatsApp style bubbles
        if event_type == "message":
            dialogue_indicator = '<span class="dialogue-badge">↩️</span>' if is_dialogue else ''
            
            if align == "right":
                # Right-aligned message (like sent message)
                html_parts.append(
                    f'<div class="msg-row right">'
                    f'<div class="msg-bubble right" style="background: {color}; color: white;">'
                    f'<div class="msg-header right">{icon} {agent_name}</div>'
                    f'<div class="msg-text">{message}</div>'
                    f'<div class="msg-time right">{dialogue_indicator}{format_time()}</div>'
                    f'</div>'
                    f'</div>'
                )
            elif align == "center":
                # Center system message
                html_parts.append(
                    f'<div class="msg-row center">'
                    f'<div class="msg-bubble center">{message}</div>'
                    f'</div>'
                )
            else:
                # Left-aligned message (like received message)
                reply_line = f'<div class="reply-to">↩️ ตอบกลับ {expected_reply}</div>' if is_dialogue else ''
                html_parts.append(
                    f'<div class="msg-row left">'
                    f'<div class="avatar">{icon}</div>'
                    f'<div>'
                    f'{reply_line}'
                    f'<div class="msg-bubble left" style="background: {bg_color}; border: 1px solid {color}33;">'
                    f'<div class="msg-header left" style="color: {color};">{agent_name}</div>'
                    f'<div class="msg-text">{message}</div>'
                    f'<div class="msg-time left">{dialogue_indicator}{format_time()}</div>'
                    f'</div>'
                    f'</div>'
                    f'</div>'
                )
    
    # Build complete HTML page
    full_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
    <meta charset="UTF-8">
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #FFF3E0 0%, #FFFFFF 50%, #FFF8E1 100%);
            min-height: 100vh;
            padding: 16px;
        }}
        
        .system-msg {{
            text-align: center;
            padding: 8px 16px;
            margin: 12px 0;
            font-size: 0.85em;
            color: #666;
            background: rgba(255, 107, 0, 0.05);
            border-radius: 16px;
            max-width: 80%;
            margin-left: auto;
            margin-right: auto;
        }}
        .system-msg.error {{ background: rgba(244, 67, 54, 0.1); color: #D32F2F; }}
        
        .msg-row {{
            display: flex;
            align-items: flex-end;
            margin-bottom: 12px;
            gap: 8px;
        }}
        .msg-row.left {{ justify-content: flex-start; }}
        .msg-row.right {{ justify-content: flex-end; }}
        .msg-row.center {{ justify-content: center; }}
        
        .avatar {{
            width: 40px;
            height: 40px;
            border-radius: 50%;
            background: linear-gradient(135deg, #FF6B00, #FF8F00);
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 20px;
            flex-shrink: 0;
            box-shadow: 0 2px 8px rgba(255, 107, 0, 0.3);
        }}
        
        .msg-bubble {{
            max-width: 75%;
            padding: 12px 16px;
            border-radius: 18px;
            position: relative;
            box-shadow: 0 1px 4px rgba(0,0,0,0.08);
        }}
        .msg-bubble.left {{
            border-bottom-left-radius: 4px;
        }}
        .msg-bubble.right {{
            border-bottom-right-radius: 4px;
        }}
        .msg-bubble.center {{
            background: rgba(255, 255, 255, 0.8);
            font-size: 0.85em;
        }}
        
        .msg-header {{
            font-size: 0.75em;
            font-weight: 600;
            margin-bottom: 4px;
        }}
        .msg-header.left {{ color: #FF6B00; }}
        .msg-header.right {{ color: white; text-align: right; }}
        
        .msg-text {{
            font-size: 0.95em;
            line-height: 1.5;
            word-wrap: break-word;
        }}
        
        .msg-time {{
            font-size: 0.65em;
            margin-top: 4px;
            opacity: 0.7;
        }}
        .msg-time.left {{ text-align: left; color: #888; }}
        .msg-time.right {{ text-align: right; color: rgba(255,255,255,0.8); }}
        
        .reply-to {{
            font-size: 0.75em;
            color: #888;
            padding: 4px 12px;
            margin-bottom: -8px;
            margin-left: 8px;
        }}
        
        .dialogue-badge {{
            display: inline-block;
            background: #FF6B00;
            color: white;
            border-radius: 50%;
            width: 16px;
            height: 16px;
            line-height: 16px;
            text-align: center;
            font-size: 10px;
            margin-left: 4px;
        }}
    </style>
    </head>
    <body>
    {''.join(html_parts)}
    </body>
    </html>
    """
    
    return full_html


def main():
    st.set_page_config(
        page_title="Hackathon Copilot",
        page_icon="🚀",
        layout="wide",
    )

    # Alibaba theme CSS
    st.markdown("""
        <style>
            .main { background: white; }
            .main .block-container { padding: 1rem 2rem; }
            #MainMenu, footer {visibility: hidden;}
            
            /* Header styling */
            h1 { 
                color: #FF6B00 !important;
                border-bottom: 3px solid #FF6B00;
                padding-bottom: 0.5rem;
            }
            h1 span { color: #FF6B00; }
            
            /* Sidebar styling */
            section[data-testid="stSidebar"] {
                background: linear-gradient(180deg, #FFF3E0, #FFFFFF);
                border-right: 2px solid #FF6B00;
            }
            section[data-testid="stSidebar"] h2 { color: #FF6B00; }
            
            /* Buttons */
            .stButton > button {
                background: linear-gradient(135deg, #FF6B00, #FF8F00) !important;
                border: none !important;
                color: white !important;
            }
            .stButton > button:hover {
                background: linear-gradient(135deg, #E65100, #FF6B00) !important;
            }
            
            /* Progress bar */
            .stProgress > div > div {
                background: linear-gradient(90deg, #FF6B00, #FFB300);
            }
            
            /* Idea selection cards */
            div[style*="border"] {
                border-color: #FF6B00 !important;
            }
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

    # Render LINE-style chat UI
    chat_html = render_chat_ui()
    st.components.v.html(chat_html, height=600, scrolling=True)

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
        time.sleep(1)
        st.rerun()


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
                            st.session_state.stream_messages.append({
                                "event_type": "message",
                                "agent": "system",
                                "agent_name": "System",
                                "emoji": "🚀",
                                "role": "HITL",
                                "message": f"Selected idea #{idea.get('id')}: '{idea.get('title', '')}'. Starting development phase...",
                            })
                            st.session_state.event_index += 1
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
                st.session_state.stream_messages.append({
                    "event_type": "message",
                    "agent": "system",
                    "agent_name": "System",
                    "emoji": "✅",
                    "role": "HITL",
                    "message": "Human approved the code!",
                })
                st.session_state.event_index += 1
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
                st.session_state.stream_messages.append({
                    "event_type": "message",
                    "agent": "system",
                    "agent_name": "System",
                    "emoji": "❌",
                    "role": "HITL",
                    "message": f"Human requested changes: {feedback}" if feedback else "Human requested changes!",
                })
                st.session_state.event_index += 1
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