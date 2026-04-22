"""
Hackathon Copilot - Streamlit Frontend
Business-grade LINE-style chat UI with Alibaba orange-white theme.
"""

import streamlit as st
import requests
import time
import os
from datetime import datetime

API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8000")

AGENTS = {
    "Max": {"icon": "🧠", "color": "#FF6B00", "bg": "#FFF3E0", "border": "#FF6B00"},
    "Sarah": {"icon": "⚖️", "color": "#E65100", "bg": "#FFF8E1", "border": "#E65100"},
    "Dave": {"icon": "📋", "color": "#F57C00", "bg": "#FFFDE7", "border": "#F57C00"},
    "Luna": {"icon": "🏗️", "color": "#FF8F00", "bg": "#FFF3E0", "border": "#FF8F00"},
    "Kai": {"icon": "🔨", "color": "#EF6C00", "bg": "#FBE9E7", "border": "#EF6C00"},
    "Rex": {"icon": "🔍", "color": "#BF360C", "bg": "#FFCCBC", "border": "#BF360C"},
    "Nova": {"icon": "🎤", "color": "#FF6B00", "bg": "#FFF3E0", "border": "#FF6B00"},
    "Nova (Slides)": {"icon": "📊", "color": "#E65100", "bg": "#FFF8E1", "border": "#E65100"},
    "Nova (Script)": {"icon": "🎙️", "color": "#FF8F00", "bg": "#FFF3E0", "border": "#FF8F00"},
    "System": {"icon": "🚀", "color": "#999", "bg": "#F5F5F5", "border": "#DDD"},
    "Human": {"icon": "👤", "color": "#2196F3", "bg": "#E3F2FD", "border": "#2196F3"},
}

# Global CSS - inject once
GLOBAL_CSS = """
<style>
/* Hide all Streamlit defaults */
[data-testid="stHeader"] { display: none !important; }
[data-testid="stSidebar"] { display: none !important; }
footer { display: none !important; }

/* Hide chat elements by default (only show when body has .chat-mode) */
.chat-page, .chat-header, .chat-messages, .chat-bottom-bar, .progress-bar { display: none !important; }
/* Hide create elements by default (only show when body has .create-mode) */
.create-page, .create-card { display: none !important; }

/* Chat mode styles */
body.chat-mode .chat-page {
    display: flex !important; flex-direction: column !important; height: 100vh !important;
    background: #F5F0EB !important; margin: 0 !important; padding: 0 !important;
}
body.chat-mode .chat-header {
    background: linear-gradient(135deg, #FF6B00 0%, #FF8F00 100%) !important;
    color: white !important; padding: 12px 24px !important; display: flex !important;
    align-items: center !important; justify-content: space-between !important;
    flex-shrink: 0 !important; box-shadow: 0 2px 12px rgba(255,107,0,0.3) !important;
}
body.chat-mode .chat-header-title { font-size: 1.1rem !important; font-weight: 700 !important; }
body.chat-mode .chat-header-sub { font-size: 0.75rem !important; opacity: 0.85 !important; }
body.chat-mode .progress-bar { background: #FFF3E0 !important; padding: 0 24px !important; flex-shrink: 0 !important; }
body.chat-mode .progress-track { background: #E0E0E0 !important; border-radius: 4px !important; height: 4px !important; overflow: hidden !important; }
body.chat-mode .progress-fill { background: linear-gradient(90deg, #FF6B00, #FFB300) !important; height: 100% !important; transition: width 0.5s !important; }
body.chat-mode .chat-messages { flex: 1 !important; overflow-y: auto !important; padding: 16px 20px !important; }
body.chat-mode .chat-bottom-bar {
    background: white !important; border-top: 1px solid #E8E0D8 !important;
    padding: 10px 20px !important; display: flex !important; gap: 10px !important;
    flex-shrink: 0 !important; flex-wrap: wrap !important;
}

/* Create mode styles */
body.create-mode .create-page {
    display: flex !important; flex-direction: column !important; align-items: center !important;
    justify-content: center !important; min-height: 100vh !important;
    background: linear-gradient(180deg, #FFF8F0 0%, #FFFFFF 40%) !important;
    padding: 2rem !important;
}
body.create-mode .create-card {
    display: block !important; background: white !important; border-radius: 24px !important;
    box-shadow: 0 8px 40px rgba(255,107,0,0.08), 0 2px 12px rgba(0,0,0,0.04) !important;
    padding: 3rem !important; max-width: 560px !important; width: 100% !important; text-align: center !important;
}

/* Message bubbles */
.msg { display: flex; gap: 10px; margin-bottom: 14px; align-items: flex-start; }
.msg-avatar {
    width: 36px; height: 36px; border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-size: 16px; flex-shrink: 0; box-shadow: 0 2px 6px rgba(0,0,0,0.12);
}
.msg-body { flex: 1; min-width: 0; }
.msg-name { font-size: 0.7rem; font-weight: 700; margin-bottom: 2px; }
.msg-bubble {
    padding: 10px 14px; border-radius: 12px; border-top-left-radius: 4px;
    font-size: 0.88rem; line-height: 1.55; box-shadow: 0 1px 4px rgba(0,0,0,0.06);
}
.msg-time { font-size: 0.6rem; color: #AAA; margin-top: 3px; }
.sys-badge {
    text-align: center; padding: 6px 14px; margin: 10px auto;
    font-size: 0.75rem; color: #888; background: rgba(255,255,255,0.8);
    border-radius: 16px; max-width: 70%; border: 1px solid #E8E0D8;
}
.sys-badge.error { background: #FFEBEE; color: #D32F2F; border-color: #FFCDD2; }

/* Buttons */
.stButton > button {
    background: linear-gradient(135deg, #FF6B00, #FF8F00) !important;
    color: white !important; border: none !important; border-radius: 12px !important;
    padding: 10px 20px !important; font-weight: 700 !important; font-size: 0.95rem !important;
    box-shadow: 0 2px 8px rgba(255,107,0,0.25) !important;
}
.stButton > button:hover { box-shadow: 0 4px 16px rgba(255,107,0,0.35) !important; }
.stTextInput > div > div > input, .stTextArea > div > div > textarea {
    border: 2px solid #FFD180 !important; border-radius: 12px !important;
}
.stTextInput > div > div > input:focus, .stTextArea > div > div > textarea:focus {
    border-color: #FF6B00 !important; box-shadow: 0 0 0 3px rgba(255,107,0,0.1) !important;
}

/* Hide Streamlit content area margins */
.main .block-container { max-width: 100% !important; padding: 0 !important; }
</style>
"""


def api_request(method, endpoint, data=None):
    try:
        url = f"{API_BASE_URL}{endpoint}"
        if method == "GET":
            r = requests.get(url, timeout=10)
        elif method == "POST":
            r = requests.post(url, json=data or {}, timeout=10)
        else:
            return None
        r.raise_for_status()
        return r.json()
    except Exception:
        return None


def format_time():
    return datetime.now().strftime("%H:%M")


def render_bubbles(messages):
    parts = []
    for msg in messages:
        et = msg.get("event_type", "message")
        an = msg.get("agent_name", "System")
        m = msg.get("message", "")
        if et == "thinking":
            continue
        ag = AGENTS.get(an, {"icon": "🤖", "color": "#95A5A6", "bg": "#F5F5F5", "border": "#CCC"})
        ic, co, bg, br = ag["icon"], ag["color"], ag["bg"], ag["border"]
        if et in ("phase_start", "phase_complete"):
            parts.append(f'<div class="sys-badge">{m}</div>')
        elif et == "error":
            parts.append(f'<div class="sys-badge error">{m}</div>')
        elif et == "message":
            parts.append(
                f'<div class="msg">'
                f'<div class="msg-avatar" style="background:linear-gradient(135deg,{co},{br})">{ic}</div>'
                f'<div class="msg-body">'
                f'<div class="msg-name" style="color:{co}">{an}</div>'
                f'<div class="msg-bubble" style="background:{bg};border-left:3px solid {co}">{m}</div>'
                f'<div class="msg-time">{format_time()}</div>'
                f'</div></div>'
            )
    return "\n".join(parts)


def main():
    st.set_page_config(page_title="Hackathon Copilot", page_icon="🚀", layout="wide", initial_sidebar_state="collapsed")

    # Initialize state
    if "session_id" not in st.session_state:
        st.session_state.session_id = None
    if "stream_messages" not in st.session_state:
        st.session_state.stream_messages = []
    if "event_index" not in st.session_state:
        st.session_state.event_index = 0
    if "workflow_started" not in st.session_state:
        st.session_state.workflow_started = False
    if "_mode" not in st.session_state:
        st.session_state._mode = "create"  # "create" or "chat"

    in_chat = st.session_state.session_id is not None

    # Inject global CSS
    st.markdown(GLOBAL_CSS, unsafe_allow_html=True)

    # Set body class via JS
    mode_class = "chat-mode" if in_chat else "create-mode"
    st.components.v1.html(
        f"""<script>
        document.body.className = '{mode_class}';
        </script>""",
        height=0
    )

    if in_chat:
        render_chat()
    else:
        render_create()


def render_create():
    # Create page container (hidden when body doesn't have .create-mode)
    st.markdown('<div class="create-page">', unsafe_allow_html=True)

    st.markdown("""
    <div class="create-card">
        <div class="create-logo">🚀</div>
        <div class="create-title">Hackathon Copilot</div>
        <div class="create-sub">AI-Powered Multi-Agent Team for Hackathon Success</div>
    </div>
    """, unsafe_allow_html=True)

    theme = st.text_input(
        "🎯 Hackathon Theme",
        placeholder="e.g., AI for Education",
        key="create_theme"
    )
    constraints = st.text_area(
        "📏 Constraints (optional)",
        value="48-hour hackathon, solo developer",
        key="create_constraints"
    )

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("🚀 Start Session", type="primary", disabled=not theme, use_container_width=True):
            with st.spinner("Creating session..."):
                result = api_request("POST", "/sessions", {"theme": theme, "constraints": constraints})
            if result:
                st.session_state.session_id = result["session_id"]
                st.session_state.stream_messages = []
                st.session_state.event_index = 0
                st.session_state.workflow_started = False
                st.rerun()
            else:
                st.error("Failed to create session. Make sure API server is running.")

    st.markdown("</div>", unsafe_allow_html=True)


def render_chat():
    session_id = st.session_state.session_id

    # Poll events
    try:
        r = requests.get(
            f"{API_BASE_URL}/sessions/{session_id}/events",
            params={"since_index": st.session_state.event_index},
            timeout=3
        )
        if r.status_code == 200:
            ed = r.json()
            for ev in ed.get("events", []):
                st.session_state.stream_messages.append(ev)
                st.session_state.event_index = ev.get("index", 0) + 1
    except Exception:
        pass

    state = api_request("GET", f"/sessions/{session_id}")
    if not state:
        st.error("Failed to load session")
        return

    current_layer = state.get("current_layer", "")
    progress = 0
    layers_order = [
        "idle", "ideation", "judging", "hitl_1", "planning",
        "architecting", "building", "critiquing", "hitl_2", "pitching", "complete"
    ]
    try:
        progress = (layers_order.index(current_layer) + 1) / len(layers_order) * 100
    except ValueError:
        pass

    status_map = {
        "idle": "🟡 Ready",
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
    }
    status = status_map.get(current_layer, current_layer)

    # Chat page container
    st.markdown(f"""
    <div class="chat-page">
        <div class="chat-header">
            <div>
                <div class="chat-header-title">🚀 {state.get('theme', 'Hackathon Copilot')}</div>
                <div class="chat-header-sub">{status}</div>
            </div>
            <div style="font-size:0.7rem;opacity:0.8">{session_id[:8]}</div>
        </div>
        <div class="progress-bar">
            <div class="progress-track">
                <div class="progress-fill" style="width:{progress}%"></div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Idea selection modal
    show_idea = (current_layer == "hitl_1" and not state.get("selected_idea"))
    ideas = state.get("ideas", []) if show_idea else None

    if show_idea and ideas:
        st.markdown("### 🎯 เลือกไอเดียที่ต้องการ")
        st.caption("คลิกที่การ์ดเพื่อเลือกไอเดีย แล้ว AI จะเริ่มพัฒนาต่อ")
        cols = st.columns(min(len(ideas), 3))
        for i, idea in enumerate(ideas):
            with cols[i % 3]:
                with st.container(border=True):
                    st.markdown(f"### {idea.get('title','')}")
                    st.markdown(idea.get("description",""))
                    if idea.get("key_features"):
                        for f in idea["key_features"][:3]:
                            st.markdown(f"• {f}")
                    st.markdown(f"**Tech:** {', '.join(idea.get('tech_stack',[]))}")
                    if st.button("📌 เลือกไอเดียนี้นะ", key=f"sel_{idea.get('id')}", use_container_width=True):
                        result = api_request("POST", f"/sessions/{session_id}/select-idea", {"idea_id": idea.get("id")})
                        if result:
                            st.session_state.stream_messages.append({
                                "event_type": "message",
                                "agent_name": "System",
                                "emoji": "✅",
                                "role": "HITL",
                                "message": f"เลือก idea #{idea.get('id')}: '{idea.get('title','')}' กำลังเริ่มพัฒนา..."
                            })
                            st.rerun()

    # Chat messages via HTML component
    st.components.v1.html(
        f'<div class="chat-messages">{render_bubbles(st.session_state.stream_messages)}</div>',
        height=420,
        scrolling=True
    )

    # Code review modal
    show_review = (current_layer == "hitl_2")
    if show_review:
        st.markdown("### 🔍 ตรวจสอบโค้ด")
        st.caption("โค้ดถูกสร้างเรียบร้อยแล้ว คุณต้องการอนุมัติหรือแก้ไข?")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("✅ อนุมัติ", type="primary", use_container_width=True):
                api_request("POST", f"/sessions/{session_id}/review-code", {"approved": True})
                st.rerun()
        with c2:
            fb = st.text_area("Change requests (optional)", key="review_fb")
            if st.button("❌ แก้ไข", use_container_width=True):
                api_request("POST", f"/sessions/{session_id}/review-code", {"approved": False, "feedback": fb})
                st.rerun()

    # Bottom bar
    st.markdown('<div class="chat-bottom-bar">', unsafe_allow_html=True)
    bc1, bc2 = st.columns([1, 1])
    with bc1:
        if st.button("🆕 New Session", use_container_width=True):
            st.session_state.session_id = None
            st.session_state.stream_messages = []
            st.session_state.workflow_started = False
            st.rerun()
    with bc2:
        if st.button("🔄 Refresh", use_container_width=True):
            st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

    # Auto-start workflow
    if not state.get("is_paused") and not st.session_state.workflow_started:
        st.session_state.workflow_started = True
        api_request("POST", f"/sessions/{session_id}/start")

    # Auto-refresh
    if not state.get("is_paused") and st.session_state.workflow_started:
        time.sleep(0.5)
        st.rerun()


if __name__ == "__main__":
    main()