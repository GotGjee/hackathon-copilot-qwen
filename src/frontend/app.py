"""
Hackathon Copilot - Streamlit Frontend
LINE-style chat - pure HTML rendering, no Streamlit containers around messages.
"""

import streamlit as st
import requests
import time
import os
from datetime import datetime

API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8000")

AGENTS = {
    "Max": {"icon": "🧠", "color": "#FF6B00", "bg": "#FFF3E0"},
    "Sarah": {"icon": "⚖️", "color": "#E65100", "bg": "#FFF8E1"},
    "Dave": {"icon": "📋", "color": "#F57C00", "bg": "#FFFDE7"},
    "Luna": {"icon": "🏗️", "color": "#FF8F00", "bg": "#FFF3E0"},
    "Kai": {"icon": "🔨", "color": "#EF6C00", "bg": "#FBE9E7"},
    "Rex": {"icon": "🔍", "color": "#BF360C", "bg": "#FFCCBC"},
    "Nova": {"icon": "🎤", "color": "#FF6B00", "bg": "#FFF3E0"},
    "Nova (Slides)": {"icon": "📊", "color": "#E65100", "bg": "#FFF8E1"},
    "Nova (Script)": {"icon": "🎙️", "color": "#FF8F00", "bg": "#FFF3E0"},
    "System": {"icon": "🚀", "color": "#999", "bg": "#F5F5F5"},
}

CSS = """
<style>
[data-testid="stHeader"], [data-testid="stSidebar"], footer { display: none !important; }
.main .block-container { max-width: 100% !important; padding: 0 !important; }
.stButton > button {
    background: linear-gradient(135deg, #FF6B00, #FF8F00) !important;
    color: white !important; border: none !important; border-radius: 20px !important;
    padding: 8px 16px !important; font-weight: 600 !important; font-size: 0.85rem !important;
}
.stButton > button:hover { opacity: 0.9 !important; }
.stTextInput > div > div > input { border-radius: 20px !important; }
.stTextArea > div > div > textarea { border-radius: 16px !important; }
</style>
"""

CHAT_HTML = """
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }

.hdr {
    background: linear-gradient(135deg, #FF6B00, #FF8F00);
    color: white; padding: 12px 16px;
    display: flex; align-items: center; justify-content: space-between;
    position: sticky; top: 0; z-index: 10;
    box-shadow: 0 2px 8px rgba(255,107,0,0.2);
}
.hdr-title { font-weight: 700; font-size: 0.95rem; }
.hdr-sub { font-size: 0.7rem; opacity: 0.85; margin-top: 2px; }

.pbar { background: #FFF3E0; }
.ptrack { background: #E8E0D8; height: 3px; }
.pfill { background: linear-gradient(90deg, #FF6B00, #FFB300); height: 100%; transition: width 0.3s; }

.chat {
    padding: 10px 10px 10px 6px;
    background: #FAFAFA;
    min-height: 60vh;
    overflow-y: auto;
}

.msg {
    display: flex;
    gap: 8px;
    margin-bottom: 14px;
    align-items: flex-start;
}
.ava {
    width: 32px; height: 32px; border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-size: 14px; flex-shrink: 0; margin-top: 2px;
}
.body { flex: 1; min-width: 0; }
.name { font-size: 0.68rem; font-weight: 600; margin-bottom: 2px; }
.bub {
    padding: 8px 12px;
    border-radius: 16px;
    border-top-left-radius: 4px;
    font-size: 0.82rem;
    line-height: 1.5;
    word-wrap: break-word;
    white-space: pre-wrap;
}
.time { font-size: 0.58rem; color: #BBB; margin-top: 2px; }

.sys {
    text-align: center; padding: 4px 10px;
    margin: 8px auto; font-size: 0.7rem;
    color: #AAA; background: none;
}

.bot {
    display: flex; gap: 6px; padding: 8px 12px;
    border-top: 1px solid #EEE; background: white;
    position: sticky; bottom: 0;
}
.bot button {
    flex: 1; padding: 8px; border: none; border-radius: 16px;
    background: linear-gradient(135deg, #FF6B00, #FF8F00);
    color: white; font-weight: 600; font-size: 0.8rem; cursor: pointer;
}
</style>
</head>
<body>
<div class="hdr">
    <div><div class="hdr-title">🚀 {theme}</div><div class="hdr-sub">{status}</div></div>
    <div style="font-size:0.6rem;opacity:0.7">{sid}</div>
</div>
<div class="pbar"><div class="ptrack"><div class="pfill" style="width:{progress}%"></div></div></div>
<div class="chat">{messages}</div>
<div class="bot">
    <button onclick="window.parent.postMessage('new','*')">🆕 New</button>
    <button onclick="window.parent.postMessage('refresh','*')">🔄 Refresh</button>
</div>
</body>
</html>
"""


def api(method, ep, data=None):
    try:
        url = f"{API_BASE_URL}{ep}"
        r = requests.get(url, timeout=6) if method == "GET" else requests.post(url, json=data or {}, timeout=6)
        r.raise_for_status()
        return r.json()
    except Exception:
        return None


def ftime():
    return datetime.now().strftime("%H:%M")


def render_msgs(msgs):
    parts = []
    for m in msgs:
        et = m.get("event_type", "message")
        an = m.get("agent_name", "System")
        txt = m.get("message", "").replace("{", "&#123;").replace("}", "&#125;")
        if et == "thinking":
            continue
        ag = AGENTS.get(an, {"icon": "🤖", "color": "#999", "bg": "#F5F5F5"})
        ic, co, bg = ag["icon"], ag["color"], ag["bg"]
        if et in ("phase_start", "phase_complete"):
            parts.append(f'<div class="sys">{txt}</div>')
        elif et == "error":
            parts.append(f'<div class="sys" style="color:#D32F2F">{txt}</div>')
        elif et == "message":
            parts.append(
                f'<div class="msg">'
                f'<div class="ava" style="background:{bg}">{ic}</div>'
                f'<div class="body">'
                f'<div class="name" style="color:{co}">{an}</div>'
                f'<div class="bub" style="background:{bg}">{txt}</div>'
                f'<div class="time">{ftime()}</div>'
                f'</div></div>'
            )
    return "\n".join(parts)


def main():
    st.set_page_config(page_title="Hackathon Copilot", page_icon="🚀", layout="wide", initial_sidebar_state="collapsed")

    if "session_id" not in st.session_state:
        st.session_state.session_id = None
    if "msgs" not in st.session_state:
        st.session_state.msgs = []
    if "eidx" not in st.session_state:
        st.session_state.eidx = 0
    if "started" not in st.session_state:
        st.session_state.started = False

    st.markdown(CSS, unsafe_allow_html=True)

    if not st.session_state.session_id:
        render_create()
    else:
        render_chat()


def render_create():
    st.markdown("""
    <div style="display:flex;align-items:center;justify-content:center;min-height:90vh;background:linear-gradient(180deg,#FFF8F0,#FFFFFF)">
    <div style="text-align:center;padding:2rem">
        <div style="font-size:4rem;margin-bottom:0.5rem">🚀</div>
        <div style="font-size:1.8rem;font-weight:800;color:#FF6B00;margin-bottom:0.3rem">Hackathon Copilot</div>
        <div style="color:#999;font-size:0.9rem;margin-bottom:2rem">AI-Powered Multi-Agent Team</div>
    </div></div>
    """, unsafe_allow_html=True)

    theme = st.text_input("🎯 Theme", placeholder="e.g., AI for Education", key="c_theme")
    const = st.text_area("📏 Constraints", value="48-hour hackathon, solo developer", key="c_const")

    if st.button("🚀 Start", type="primary", disabled=not theme, use_container_width=True):
        with st.spinner("Creating..."):
            res = api("POST", "/sessions", {"theme": theme, "constraints": const})
        if res:
            st.session_state.session_id = res["session_id"]
            st.session_state.msgs = []
            st.session_state.eidx = 0
            st.session_state.started = False
            st.rerun()
        else:
            st.error("Cannot reach API server.")


def render_chat():
    sid = st.session_state.session_id

    # Initialize loading state
    if "_loading_judging" not in st.session_state:
        st.session_state._loading_judging = False
    if "_prev_layer" not in st.session_state:
        st.session_state._prev_layer = ""

    # Poll events
    try:
        r = requests.get(f"{API_BASE_URL}/sessions/{sid}/events", params={"since_index": st.session_state.eidx}, timeout=3)
        if r.status_code == 200:
            resp = r.json()
            new_events = resp.get("events", [])
            if new_events:
                for ev in new_events:
                    st.session_state.msgs.append(ev)
                    st.session_state.eidx = ev.get("index", 0) + 1
    except Exception:
        pass

    state = api("GET", f"/sessions/{sid}")
    if not state:
        st.error("No session"); return

    layer = state.get("current_layer", "")
    order = ["idle","ideation","judging","hitl_1","planning","architecting","building","critiquing","hitl_2","pitching","complete"]
    progress = 0
    try: progress = (order.index(layer)+1)/len(order)*100
    except: pass

    status = {
        "idle":"🟡 Ready","ideation":"🧠 Max brainstorming...","judging":"⚖️ Sarah evaluating...",
        "hitl_1":"⏸️ เลือกไอเดีย","planning":"📋 Dave planning...","architecting":"🏗️ Luna designing...",
        "building":"🔨 Kai coding...","critiquing":"🔍 Rex reviewing...","hitl_2":"⏸️ ตรวจโค้ด",
        "pitching":"🎤 Nova...","complete":"✅ เสร็จ!","error":"❌ Error",
    }.get(layer, layer)

    msgs_html = render_msgs(st.session_state.msgs)
    theme_val = (state.get("theme") or "Hackathon").replace("{","&#123;").replace("}","&#125;")
    status_safe = (status or "").replace("{","&#123;").replace("}","&#125;")

    full_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
    <meta charset="UTF-8">
    <style>
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }}
    .hdr {{
        background: linear-gradient(135deg, #FF6B00, #FF8F00);
        color: white; padding: 12px 16px;
        display: flex; align-items: center; justify-content: space-between;
        position: sticky; top: 0; z-index: 10;
        box-shadow: 0 2px 8px rgba(255,107,0,0.2);
    }}
    .hdr-title {{ font-weight: 700; font-size: 0.95rem; }}
    .hdr-sub {{ font-size: 0.7rem; opacity: 0.85; margin-top: 2px; }}
    .pbar {{ background: #FFF3E0; }}
    .ptrack {{ background: #E8E0D8; height: 3px; }}
    .pfill {{ background: linear-gradient(90deg, #FF6B00, #FFB300); height: 100%; transition: width 0.3s; }}
    .chat {{ padding: 10px 10px 10px 6px; background: #FAFAFA; min-height: 60vh; overflow-y: auto; }}
    .msg {{ display: flex; gap: 8px; margin-bottom: 14px; align-items: flex-start; }}
    .ava {{ width: 32px; height: 32px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 14px; flex-shrink: 0; margin-top: 2px; }}
    .body {{ flex: 1; min-width: 0; }}
    .name {{ font-size: 0.68rem; font-weight: 600; margin-bottom: 2px; }}
    .bub {{ padding: 8px 12px; border-radius: 16px; border-top-left-radius: 4px; font-size: 0.82rem; line-height: 1.5; word-wrap: break-word; white-space: pre-wrap; }}
    .time {{ font-size: 0.58rem; color: #BBB; margin-top: 2px; }}
    .sys {{ text-align: center; padding: 4px 10px; margin: 8px auto; font-size: 0.7rem; color: #AAA; background: none; }}
    .bot {{ display: flex; gap: 6px; padding: 8px 12px; border-top: 1px solid #EEE; background: white; position: sticky; bottom: 0; }}
    .bot button {{ flex: 1; padding: 8px; border: none; border-radius: 16px; background: linear-gradient(135deg, #FF6B00, #FF8F00); color: white; font-weight: 600; font-size: 0.8rem; cursor: pointer; }}
    </style>
    </head>
    <body>
    <div class="hdr">
        <div><div class="hdr-title">🚀 {theme_val}</div><div class="hdr-sub">{status_safe}</div></div>
        <div style="font-size:0.6rem;opacity:0.7">{sid[:8]}</div>
    </div>
    <div class="pbar"><div class="ptrack"><div class="pfill" style="width:{progress}%"></div></div></div>
    <div class="chat">{msgs_html}</div>
    <div class="bot">
        <button onclick="window.parent.postMessage('new','*')">🆕 New</button>
        <button onclick="window.parent.postMessage('refresh','*')">🔄 Refresh</button>
    </div>
    </body>
    </html>
    """

    st.components.v1.html(full_html, height=600, scrolling=True)

    # Idea selection - only show after Sarah's critique is loaded
    if layer == "hitl_1" and not state.get("selected_idea"):
        ideas = state.get("ideas", [])
        if ideas:
            # Check if Sarah's messages are loaded
            has_sarah = any(m.get("agent_name") == "Sarah" for m in st.session_state.msgs)
            has_max_response = any(
                m.get("agent_name") == "Max" and "ตอบกลับ" in m.get("message", "")
                for m in st.session_state.msgs
            )
            
            if has_sarah and has_max_response:
                # All events loaded, show idea selection
                st.markdown("### 🎯 เลือกไอเดีย")
                cols = st.columns(min(len(ideas), 3))
                for i, idea in enumerate(ideas):
                    with cols[i % 3]:
                        with st.container(border=True):
                            st.write(f"### {idea.get('title','')}")
                            st.write(idea.get("description","")[:100])
                            st.write(f"**Tech:** {', '.join(idea.get('tech_stack',[]))}")
                            if st.button("📌 เลือก", key=f"pi_{idea.get('id')}", use_container_width=True):
                                api("POST", f"/sessions/{sid}/select-idea", {"idea_id": idea.get("id")})
                                st.session_state.msgs.append({"event_type":"message","agent_name":"System","message":f"✅ เลือก: {idea.get('title','')}"})
                                st.rerun()
            else:
                # Still loading Sarah's critique
                st.markdown("""
                <div style="text-align:center;padding:20px;color:#FF6B00">
                    <div style="font-size:2rem;margin-bottom:8px">⚖️</div>
                    <div style="font-weight:600">กำลังรอความเห็นจาก Sarah...</div>
                    <div style="font-size:0.8rem;color:#999;margin-top:4px">Sarah กำลังวิเคราะห์และให้คะแนนไอเดียอยู่</div>
                </div>
                """, unsafe_allow_html=True)

    # Code review
    if layer == "hitl_2":
        c1, c2 = st.columns(2)
        with c1:
            if st.button("✅ อนุมัติ", use_container_width=True):
                api("POST", f"/sessions/{sid}/review-code", {"approved": True}); st.rerun()
        with c2:
            if st.button("❌ แก้ไข", use_container_width=True):
                fb = st.text_area("Feedback", key="rfb")
                api("POST", f"/sessions/{sid}/review-code", {"approved": False, "feedback": fb}); st.rerun()

    # Auto-start
    if not state.get("is_paused") and not st.session_state.started:
        st.session_state.started = True
        api("POST", f"/sessions/{sid}/start")

    # Auto-refresh logic:
    # - When paused (HITL): do NOT auto-refresh to prevent flicker
    # - When running: only refresh if new events arrived
    is_paused = state.get("is_paused", False)
    prev_count = st.session_state.get("_prev_msg_count", 0)
    curr_count = len(st.session_state.msgs)
    
    # Store current count
    st.session_state._prev_msg_count = curr_count
    
    if is_paused:
        # Paused at HITL - stop auto-refresh to prevent flicker
        # User needs to interact manually
        pass
    elif st.session_state.started:
        # Running - only rerun if we got new events
        if curr_count > prev_count:
            time.sleep(0.5)
            st.rerun()
        else:
            # No new events, wait before checking again
            time.sleep(1.5)
            st.rerun()


if __name__ == "__main__":
    main()