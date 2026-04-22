"""
Hackathon Copilot - Streamlit Frontend
Full-screen LINE-style chat UI with Alibaba orange-white theme.
"""

import streamlit as st
import requests
import time
import os
from datetime import datetime

# Configuration
API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8000")

# Agent config
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
    "Human": {"icon": "👤", "color": "#2196F3", "bg": "#E3F2FD", "align": "right"},
}

DIALOGUE_PAIRS = {
    "Max": "Sarah",
    "Sarah": "Max",
    "Kai": "Rex",
    "Rex": "Kai",
    "Nova (Slides)": "Nova",
    "Nova (Script)": "Nova (Slides)",
}


def api_request(method: str, endpoint: str, data: dict | None = None):
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
    return datetime.now().strftime("%H:%M")


def render_full_chat(messages, show_idea_modal=False, ideas=None, show_review_modal=False):
    """Render full-screen LINE-style chat."""
    prev_agent = None
    html_parts = []
    
    for msg in messages:
        event_type = msg.get("event_type", "message")
        agent_name = msg.get("agent_name", "System")
        message = msg.get("message", "")
        
        agent_info = AGENTS.get(agent_name, {"icon": "🤖", "color": "#95A5A6", "bg": "#F5F5F5", "align": "left"})
        icon = agent_info["icon"]
        color = agent_info["color"]
        bg_color = agent_info["bg"]
        align = agent_info["align"]
        
        expected_reply = DIALOGUE_PAIRS.get(agent_name)
        is_dialogue = expected_reply is not None and prev_agent == expected_reply
        prev_agent = agent_name
        
        # Skip thinking events
        if event_type == "thinking":
            continue
        
        # System messages (phase start/complete)
        if event_type in ("phase_start", "phase_complete"):
            html_parts.append(f'<div class="system-msg">{message}</div>')
            continue
        
        if event_type == "error":
            html_parts.append(f'<div class="system-msg error">{message}</div>')
            continue
        
        # Regular messages
        if event_type == "message":
            dialogue_indicator = '<span class="dialogue-badge">↩️</span>' if is_dialogue else ''
            reply_line = f'<div class="reply-to">↩️ ตอบกลับ {expected_reply}</div>' if is_dialogue else ''
            
            if align == "right":
                html_parts.append(
                    f'<div class="msg-row right">'
                    f'<div class="msg-bubble right" style="background: {color}; color: white;">'
                    f'<div class="msg-header right">{icon} {agent_name}</div>'
                    f'<div class="msg-text">{message}</div>'
                    f'<div class="msg-time right">{dialogue_indicator}{format_time()}</div>'
                    f'</div></div>'
                )
            elif align == "center":
                html_parts.append(f'<div class="msg-row center"><div class="msg-bubble center">{message}</div></div>')
            else:
                html_parts.append(
                    f'<div class="msg-row left">'
                    f'<div class="avatar">{icon}</div>'
                    f'<div>'
                    f'{reply_line}'
                    f'<div class="msg-bubble left" style="background: {bg_color}; border: 1px solid {color}33;">'
                    f'<div class="msg-header left" style="color: {color};">{agent_name}</div>'
                    f'<div class="msg-text">{message}</div>'
                    f'<div class="msg-time left">{dialogue_indicator}{format_time()}</div>'
                    f'</div></div></div>'
                )
    
    # Build idea selection modal if needed
    idea_modal = ""
    if show_idea_modal and ideas:
        idea_cards = ""
        for idea in ideas:
            features = "".join([f"<li>{f}</li>" for f in idea.get("key_features", [])])
            idea_cards += f"""
            <div class="idea-card" onclick="selectIdea({idea.get('id')})">
                <div class="idea-title">{idea.get('title', '')}</div>
                <div class="idea-desc">{idea.get('description', '')}</div>
                <div class="idea-features"><ul>{features}</ul></div>
                <div class="idea-tech">Tech: {', '.join(idea.get('tech_stack', []))}</div>
                <div class="idea-btn">คลิกเพื่อเลือก</div>
            </div>"""
        
        idea_modal = f"""
        <div class="modal-overlay" id="ideaModal">
            <div class="modal-content">
                <div class="modal-title">🎯 เลือกไอเดียที่ต้องการ</div>
                <div class="modal-subtitle">คลิกที่การ์ดเพื่อเลือกไอเดีย แล้ว AI จะเริ่มพัฒนาต่อ</div>
                <div class="idea-list">{idea_cards}</div>
            </div>
        </div>"""
    
    # Build review modal if needed
    review_modal = ""
    if show_review_modal:
        review_modal = """
        <div class="modal-overlay" id="reviewModal">
            <div class="modal-content">
                <div class="modal-title">🔍 ตรวจสอบโค้ด</div>
                <div class="modal-subtitle">โค้ดถูกสร้างเรียบร้อยแล้ว คุณต้องการอนุมัติหรือแก้ไข?</div>
                <div class="modal-actions">
                    <button class="btn-approve" onclick="approveCode()">✅ อนุมัติ</button>
                    <button class="btn-reject" onclick="rejectCode()">❌ แก้ไข</button>
                </div>
            </div>
        </div>"""
    
    full_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
    <meta charset="UTF-8">
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: white;
        }}
        
        .chat-container {{
            width: 100%;
            max-width: 100%;
            padding: 12px 16px;
            overflow-y: auto;
        }}
        
        .system-msg {{
            text-align: center;
            padding: 6px 14px;
            margin: 10px auto;
            font-size: 0.8em;
            color: #888;
            background: #FFF3E0;
            border-radius: 14px;
            max-width: 70%;
        }}
        .system-msg.error {{ background: #FFEBEE; color: #D32F2F; }}
        
        .msg-row {{
            display: flex;
            align-items: flex-end;
            margin-bottom: 10px;
            gap: 8px;
        }}
        .msg-row.left {{ justify-content: flex-start; }}
        .msg-row.right {{ justify-content: flex-end; }}
        .msg-row.center {{ justify-content: center; }}
        
        .avatar {{
            width: 36px;
            height: 36px;
            border-radius: 50%;
            background: linear-gradient(135deg, #FF6B00, #FF8F00);
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 18px;
            flex-shrink: 0;
        }}
        
        .msg-bubble {{
            max-width: 70%;
            padding: 10px 14px;
            border-radius: 16px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }}
        .msg-bubble.left {{ border-bottom-left-radius: 4px; }}
        .msg-bubble.right {{ border-bottom-right-radius: 4px; }}
        .msg-bubble.center {{ background: #FFF3E0; font-size: 0.85em; max-width: 80%; }}
        
        .msg-header {{ font-size: 0.7em; font-weight: 600; margin-bottom: 3px; }}
        .msg-header.left {{ color: #FF6B00; }}
        .msg-header.right {{ color: white; text-align: right; }}
        
        .msg-text {{ font-size: 0.9em; line-height: 1.5; word-wrap: break-word; }}
        
        .msg-time {{ font-size: 0.6em; margin-top: 3px; opacity: 0.7; }}
        .msg-time.left {{ text-align: left; color: #888; }}
        .msg-time.right {{ text-align: right; color: rgba(255,255,255,0.8); }}
        
        .reply-to {{ font-size: 0.7em; color: #888; padding: 2px 10px; margin-bottom: -6px; margin-left: 6px; }}
        .dialogue-badge {{ background: #FF6B00; color: white; border-radius: 50%; padding: 1px 5px; font-size: 0.7em; margin-left: 3px; }}
        
        /* Modal styles */
        .modal-overlay {{
            position: fixed;
            top: 0; left: 0; right: 0; bottom: 0;
            background: rgba(0,0,0,0.5);
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 1000;
        }}
        .modal-content {{
            background: white;
            border-radius: 20px;
            padding: 24px;
            max-width: 90%;
            max-height: 80vh;
            overflow-y: auto;
            width: 800px;
        }}
        .modal-title {{ font-size: 1.4em; font-weight: bold; color: #FF6B00; margin-bottom: 8px; }}
        .modal-subtitle {{ color: #666; margin-bottom: 20px; }}
        
        .idea-list {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 16px; }}
        .idea-card {{
            background: #FFF8E1;
            border: 2px solid #FF6B00;
            border-radius: 16px;
            padding: 16px;
            cursor: pointer;
            transition: all 0.2s;
        }}
        .idea-card:hover {{ background: #FFF3E0; transform: scale(1.02); }}
        .idea-title {{ font-size: 1.1em; font-weight: bold; color: #FF6B00; margin-bottom: 8px; }}
        .idea-desc {{ color: #555; font-size: 0.9em; margin-bottom: 10px; }}
        .idea-features {{ color: #666; font-size: 0.85em; margin-bottom: 10px; }}
        .idea-features ul {{ padding-left: 20px; }}
        .idea-tech {{ color: #888; font-size: 0.8em; margin-bottom: 12px; }}
        .idea-btn {{ background: #FF6B00; color: white; text-align: center; padding: 8px; border-radius: 8px; font-weight: bold; }}
        
        .modal-actions {{ display: flex; gap: 12px; }}
        .btn-approve, .btn-reject {{
            flex: 1;
            padding: 14px;
            border: none;
            border-radius: 12px;
            font-size: 1em;
            font-weight: bold;
            cursor: pointer;
        }}
        .btn-approve {{ background: #4CAF50; color: white; }}
        .btn-reject {{ background: #FF6B00; color: white; }}
    </style>
    </head>
    <body>
    <div class="chat-container">
    {''.join(html_parts)}
    </div>
    {idea_modal}
    {review_modal}
    <script>
        function selectIdea(id) {{
            const msg = JSON.stringify({{type: "select_idea", idea_id: id}});
            window.parent.postMessage(msg, "*");
        }}
        function approveCode() {{
            window.parent.postMessage(JSON.stringify({{type: "approve_code", approved: true}}), "*");
        }}
        function rejectCode() {{
            window.parent.postMessage(JSON.stringify({{type: "approve_code", approved: false}}), "*");
        }}
    </script>
    </body>
    </html>
    """
    return full_html


def main():
    st.set_page_config(
        page_title="Hackathon Copilot",
        page_icon="🚀",
        layout="wide",
        initial_sidebar_state="collapsed"
    )

    # Full-screen CSS
    st.markdown("""
        <style>
            /* Full screen layout */
            .stApp { max-width: 100%; }
            .main .block-container { padding: 0 !important; max-width: 100% !important; }
            header, #MainMenu, footer { visibility: hidden !important; display: none !important; }
            [data-testid="stSidebar"] { display: none; }
            
            /* Header */
            .app-header {
                background: linear-gradient(135deg, #FF6B00, #FF8F00);
                color: white;
                padding: 12px 20px;
                display: flex;
                align-items: center;
                justify-content: space-between;
            }
            .app-header h1 { font-size: 1.3em; margin: 0; }
            .app-header .subtitle { font-size: 0.8em; opacity: 0.9; }
            
            /* Progress bar */
            .progress-container { background: #FFF3E0; padding: 8px 20px; }
            .stProgress > div > div { background: linear-gradient(90deg, #FF6B00, #FFB300); }
            
            /* Controls bar */
            .controls-bar {
                background: white;
                border-top: 2px solid #FFF3E0;
                padding: 8px 20px;
                display: flex;
                align-items: center;
                gap: 10px;
            }
            
            /* Buttons */
            .stButton > button {
                background: linear-gradient(135deg, #FF6B00, #FF8F00) !important;
                border: none !important;
                color: white !important;
                border-radius: 8px !important;
            }
            
            /* Hide all streamlit elements except HTML */
            element {{ visibility: hidden; }}
        </style>
    """, unsafe_allow_html=True)

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
    if "theme" not in st.session_state:
        st.session_state.theme = ""

    # Handle messages from iframe
    from streamlit import runtime
    # We'll use session state for interaction

    if not st.session_state.session_id:
        show_create_session_fullscreen()
    else:
        show_fullscreen_chat()


def show_create_session_fullscreen():
    """Show full-screen creation form."""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: white;
            display: flex;
            align-items: center;
            justify-content: center;
            min-height: 100vh;
        }
        .container {
            max-width: 600px;
            width: 90%;
            text-align: center;
        }
        .logo { font-size: 4em; margin-bottom: 20px; }
        h1 { color: #FF6B00; font-size: 2.5em; margin-bottom: 10px; }
        .subtitle { color: #888; font-size: 1.1em; margin-bottom: 40px; }
        .form-group { text-align: left; margin-bottom: 20px; }
        label { color: #FF6B00; font-weight: bold; margin-bottom: 8px; display: block; }
        input, textarea {
            width: 100%;
            padding: 14px;
            border: 2px solid #FFD180;
            border-radius: 12px;
            font-size: 1em;
        }
        input:focus, textarea:focus { border-color: #FF6B00; outline: none; }
        textarea { min-height: 80px; resize: vertical; }
        .btn-start {
            width: 100%;
            padding: 16px;
            background: linear-gradient(135deg, #FF6B00, #FF8F00);
            color: white;
            border: none;
            border-radius: 12px;
            font-size: 1.2em;
            font-weight: bold;
            cursor: pointer;
            margin-top: 20px;
        }
        .btn-start:disabled { opacity: 0.5; cursor: not-allowed; }
        .status { margin-top: 20px; padding: 12px; border-radius: 8px; display: none; }
        .status.error { background: #FFEBEE; color: #D32F2F; display: block; }
        .status.success { background: #E8F5E9; color: #2E7D32; display: block; }
    </style>
    </head>
    <body>
    <div class="container">
        <div class="logo">🚀</div>
        <h1>Hackathon Copilot</h1>
        <p class="subtitle">AI-Powered Multi-Agent Team for Hackathon Success</p>
        <form id="createForm" onsubmit="return createSession(event)">
            <div class="form-group">
                <label>🎯 Hackathon Theme</label>
                <input type="text" id="theme" placeholder="e.g., AI for Education, Sustainable Living" required>
            </div>
            <div class="form-group">
                <label>📏 Constraints (optional)</label>
                <textarea id="constraints" placeholder="e.g., 48 hours, solo developer, no external APIs">48-hour hackathon, solo developer</textarea>
            </div>
            <button type="submit" class="btn-start" id="startBtn">🚀 Start Session</button>
        </form>
        <div id="status" class="status"></div>
    </div>
    <script>
        function createSession(e) {
            e.preventDefault();
            const theme = document.getElementById('theme').value;
            const constraints = document.getElementById('constraints').value;
            const btn = document.getElementById('startBtn');
            const status = document.getElementById('status');
            
            btn.disabled = true;
            btn.textContent = 'Creating session...';
            
            fetch('/api/sessions', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({theme, constraints})
            })
            .then(r => r.json())
            .then(data => {
                status.className = 'status success';
                status.textContent = 'Session created! Redirecting...';
                window.parent.postMessage(JSON.stringify({type: 'session_created', session_id: data.session_id}), '*');
            })
            .catch(err => {
                status.className = 'status error';
                status.textContent = 'Error: ' + err.message;
                btn.disabled = false;
                btn.textContent = '🚀 Start Session';
            });
            return false;
        }
    </script>
    </body>
    </html>
    """
    st.components.v1.html(html, height=800, scrolling=False)


def show_fullscreen_chat():
    """Show full-screen chat interface."""
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
    current_layer = state.get("current_layer", "")
    
    # Progress
    progress_value = get_progress_value(current_layer)
    status_text = get_status_text(current_layer)

    # Determine modals to show
    show_idea_modal = (current_layer == "hitl_1" and not state.get("selected_idea"))
    ideas = state.get("ideas", []) if show_idea_modal else None
    show_review_modal = (current_layer == "hitl_2")

    # Header + progress bar
    st.markdown(f"""
        <div style="background: linear-gradient(135deg, #FF6B00, #FF8F00); color: white; padding: 10px 16px; display: flex; justify-content: space-between; align-items: center;">
            <div>
                <div style="font-size: 1.1em; font-weight: bold;">🚀 Hackathon Copilot</div>
                <div style="font-size: 0.75em; opacity: 0.9;">{status_text}</div>
            </div>
            <div style="display: flex; gap: 8px;">
                <button onclick="window.parent.location.reload()" style="background: rgba(255,255,255,0.2); border: none; color: white; padding: 6px 12px; border-radius: 6px; cursor: pointer;">🔄</button>
                <button onclick="window.parent.postMessage(JSON.stringify({{type:'new_session'}}), '*')" style="background: rgba(255,255,255,0.2); border: none; color: white; padding: 6px 12px; border-radius: 6px; cursor: pointer;">➕</button>
            </div>
        </div>
        <div style="background: #FFF3E0; padding: 4px 16px;">
            <div style="background: #E0E0E0; border-radius: 4px; overflow: hidden;">
                <div style="background: linear-gradient(90deg, #FF6B00, #FFB300); width: {progress_value}%; height: 6px; transition: width 0.5s;"></div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    # Chat area
    chat_html = render_full_chat(
        st.session_state.stream_messages,
        show_idea_modal=show_idea_modal,
        ideas=ideas,
        show_review_modal=show_review_modal
    )
    st.components.v1.html(chat_html, height=550, scrolling=True)

    # Bottom controls
    col1, col2, col3, col4 = st.columns([1, 1, 1, 1])
    with col1:
        if st.button("🆕 New Session"):
            st.session_state.session_id = None
            st.session_state.stream_messages = []
            st.rerun()
    with col2:
        if st.button("🔄 Refresh"):
            st.rerun()
    with col3:
        if st.button("📥 Export"):
            pass

    # Handle auto-start
    if not state.get("is_paused") and not st.session_state.workflow_started:
        st.session_state.workflow_started = True
        api_request("POST", f"/sessions/{session_id}/start")

    # Auto-refresh when working
    if not state.get("is_paused") and st.session_state.workflow_started:
        time.sleep(0.5)
        st.rerun()


def poll_events(session_id: str, since_index: int = 0):
    try:
        url = f"{API_BASE_URL}/sessions/{session_id}/events"
        params = {"since_index": since_index}
        response = requests.get(url, params=params, timeout=3)
        if response.status_code == 200:
            return response.json()
    except Exception:
        pass
    return {"events": [], "total": since_index}


def get_status_text(layer: str) -> str:
    return {
        "idle": "🟡 Ready to start",
        "ideation": "🧠 Max is brainstorming...",
        "judging": "⚖️ Sarah is evaluating...",
        "hitl_1": "⏸️ เลือกไอเดียที่ต้องการ",
        "planning": "📋 Dave is planning...",
        "architecting": "🏗️ Luna is designing...",
        "building": "🔨 Kai is coding...",
        "critiquing": "🔍 Rex is reviewing...",
        "hitl_2": "⏸️ ตรวจสอบโค้ด",
        "pitching": "🎤 Nova is preparing pitch...",
        "complete": "✅ เสร็จสมบูรณ์!",
        "error": "❌ เกิดข้อผิดพลาด",
    }.get(layer, layer)


def get_progress_value(layer: str) -> float:
    layers = ["idle", "ideation", "judging", "hitl_1", "planning", "architecting", "building", "critiquing", "hitl_2", "pitching", "complete"]
    try:
        idx = layers.index(layer)
        return (idx + 1) / len(layers) * 100
    except ValueError:
        return 0.0


if __name__ == "__main__":
    main()