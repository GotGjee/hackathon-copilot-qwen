"""
Hackathon Copilot - Streamlit Frontend
Card-style design that works beautifully within Streamlit's natural padding.
"""

import streamlit as st
import requests
import time
import os
from datetime import datetime

API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8000")

AGENTS = {
    "สุรเดช": {"icon": "🧠", "color": "#FF6B00", "bg": "#FFF3E0"},
    "วันเพ็ญ": {"icon": "⚖️", "color": "#E65100", "bg": "#FFF8E1"},
    "สมศักดิ์": {"icon": "📋", "color": "#F57C00", "bg": "#FFFDE7"},
    "พิมพ์ใจ": {"icon": "🏗️", "color": "#FF8F00", "bg": "#FFF3E0"},
    "ธนภัทร": {"icon": "🔨", "color": "#EF6C00", "bg": "#FBE9E7"},
    "วิชัย": {"icon": "🔍", "color": "#BF360C", "bg": "#FFCCBC"},
    "อรุณี": {"icon": "🎤", "color": "#FF6B00", "bg": "#FFF3E0"},
    "อรุณี (Slides)": {"icon": "📊", "color": "#E65100", "bg": "#FFF8E1"},
    "อรุณี (Script)": {"icon": "🎙️", "color": "#FF8F00", "bg": "#FFF3E0"},
    "System": {"icon": "🚀", "color": "#999", "bg": "#F5F5F5"},
}

CSS = """
<style>
/* Hide defaults */
[data-testid="stHeader"], [data-testid="stSidebar"], footer { display: none !important; }
.main { background: #F5F0EB !important; }
.main .block-container { 
    max-width: 800px !important; 
    padding-top: 1rem !important;
    padding-bottom: 1rem !important;
    padding-left: 1rem !important;
    padding-right: 1rem !important;
}

/* Create page card */
.create-card {
    background: white;
    border-radius: 24px;
    box-shadow: 0 4px 24px rgba(255,107,0,0.08);
    padding: 2.5rem;
    text-align: center;
    margin: 2rem 0;
}

/* Chat container */
.chat-container {
    background: white;
    border-radius: 20px;
    box-shadow: 0 4px 20px rgba(0,0,0,0.06);
    overflow: hidden;
    margin-bottom: 1rem;
}

/* Header inside chat */
.chat-hdr {
    background: linear-gradient(135deg, #FF6B00, #FF8F00);
    color: white;
    padding: 16px 20px;
    display: flex;
    align-items: center;
    justify-content: space-between;
}

/* Progress */
.pbar-wrap {
    background: #FFF3E0;
    padding: 0;
}

/* Messages area */
.msgs {
    padding: 12px;
    background: #FAFAFA;
    max-height: 55vh;
    overflow-y: auto;
}

/* Bubble styles */
.msg {
    display: flex;
    gap: 10px;
    margin-bottom: 12px;
    align-items: flex-start;
}
.ava {
    width: 36px; height: 36px; border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-size: 16px; flex-shrink: 0; margin-top: 2px;
    box-shadow: 0 2px 6px rgba(0,0,0,0.1);
}
.bub-body { flex: 1; min-width: 0; }
.bub-name { font-size: 0.72rem; font-weight: 700; margin-bottom: 3px; }
.bub {
    padding: 10px 14px;
    border-radius: 18px;
    border-top-left-radius: 6px;
    font-size: 0.85rem;
    line-height: 1.55;
    word-wrap: break-word;
    white-space: pre-wrap;
    box-shadow: 0 1px 3px rgba(0,0,0,0.05);
}
.bub-time { font-size: 0.6rem; color: #BBB; margin-top: 3px; }

/* System messages */
.sys {
    text-align: center;
    padding: 6px 14px;
    margin: 10px auto;
    font-size: 0.72rem;
    color: #999;
    background: #F5F5F5;
    border-radius: 14px;
    max-width: 65%;
}

/* Buttons */
.stButton > button {
    background: linear-gradient(135deg, #FF6B00, #FF8F00) !important;
    color: white !important;
    border: none !important;
    border-radius: 14px !important;
    padding: 10px 20px !important;
    font-weight: 600 !important;
    font-size: 0.9rem !important;
    box-shadow: 0 2px 8px rgba(255,107,0,0.2) !important;
}
.stButton > button:hover {
    box-shadow: 0 4px 12px rgba(255,107,0,0.3) !important;
    transform: translateY(-1px) !important;
}

/* Inputs */
.stTextInput > div > div > input,
.stTextArea > div > div > textarea {
    border-radius: 14px !important;
    border: 2px solid #FFD180 !important;
}
.stTextInput > div > div > input:focus,
.stTextArea > div > div > textarea:focus {
    border-color: #FF6B00 !important;
    box-shadow: 0 0 0 3px rgba(255,107,0,0.1) !important;
}

/* Idea cards */
.idea-card {
    background: white;
    border-radius: 16px;
    border: 2px solid #FFE0B2;
    padding: 1rem;
    margin-bottom: 0.5rem;
}
.idea-card:hover {
    border-color: #FF6B00;
    box-shadow: 0 4px 12px rgba(255,107,0,0.1);
}

/* Bottom bar */
.bot-bar {
    display: flex;
    gap: 8px;
    padding: 12px 0;
}
</style>
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


def render_bubbles(msgs):
    parts = []
    for m in msgs:
        et = m.get("event_type", "message")
        an = m.get("agent_name", "System")
        txt = m.get("message", "")
        if et == "thinking":
            continue
        ag = AGENTS.get(an, {"icon": "🤖", "color": "#999", "bg": "#F5F5F5"})
        ic, co, bg = ag["icon"], ag["color"], ag["bg"]
        if et in ("phase_start", "phase_complete"):
            parts.append(f'<div class="sys">{txt}</div>')
        elif et == "error":
            parts.append(f'<div class="sys" style="color:#D32F2F;background:#FFEBEE">{txt}</div>')
        elif et == "message":
            txt_escaped = txt.replace("{", "&#123;").replace("}", "&#125;")
            parts.append(
                f'<div class="msg">'
                f'<div class="ava" style="background:{bg}">{ic}</div>'
                f'<div class="bub-body">'
                f'<div class="bub-name" style="color:{co}">{an}</div>'
                f'<div class="bub" style="background:{bg}">{txt_escaped}</div>'
                f'<div class="bub-time">{ftime()}</div>'
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
    if "export_code_path" not in st.session_state:
        st.session_state.export_code_path = None
    if "export_pitch_path" not in st.session_state:
        st.session_state.export_pitch_path = None

    st.markdown(CSS, unsafe_allow_html=True)

    if not st.session_state.session_id:
        render_create()
        st.stop()
    else:
        render_chat()
        st.stop()


def render_create():
    st.markdown("""
    <div class="create-card">
        <div style="font-size:4rem;margin-bottom:0.5rem">🚀</div>
        <div style="font-size:2rem;font-weight:800;color:#FF6B00;margin-bottom:0.3rem">Hackathon Copilot</div>
        <div style="color:#999;font-size:1rem;margin-bottom:2rem">AI-Powered Multi-Agent Team for Hackathon Success</div>
    </div>
    """, unsafe_allow_html=True)

    theme = st.text_input("🎯 Hackathon Theme", placeholder="e.g., AI for Education", key="c_theme")
    const = st.text_area("📏 Constraints", value="48-hour hackathon, solo developer", key="c_const", height=80)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("🚀 Start Session", type="primary", disabled=not theme, use_container_width=True):
            with st.spinner("Creating session..."):
                res = api("POST", "/sessions", {"theme": theme, "constraints": const})
            if res:
                st.session_state.session_id = res["session_id"]
                st.session_state.msgs = []
                st.session_state.eidx = 0
                st.session_state.started = False
                st.rerun()
            else:
                st.error("Cannot reach API server. Make sure it's running on port 8000.")


def render_chat():
    sid = st.session_state.session_id

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
        st.error("Session not found"); return

    layer = state.get("current_layer", "")
    order = ["idle","ideation","judging","hitl_1","planning","architecting","building","critiquing","hitl_2","pitching","complete"]
    progress = 0
    try: progress = (order.index(layer)+1)/len(order)*100
    except: pass

    status = {
        "idle":"🟡 พร้อมแล้ว","ideation":"🧠 สุรเดชกำลัง brainstorming...","judging":"⚖️ วันเพ็ญกำลัง evaluating...",
        "hitl_1":"⏸️ เลือกไอเดีย","planning":"📋 สมศักดิ์กำลัง planning...","architecting":"🏗️ พิมพ์ใจกำลัง designing...",
        "building":"🔨 ธนภัทรกำลัง coding...","critiquing":"🔍 วิชัยกำลัง reviewing...","hitl_2":"⏸️ ตรวจสอบโค้ด",
        "pitching":"🎤 อรุณีกำลัง preparing...","complete":"✅ เสร็จสมบูรณ์!","error":"❌ เกิดข้อผิดพลาด",
    }.get(layer, layer)

    theme_val = state.get("theme") or "Hackathon"

    # Chat header
    st.markdown(f"""
    <div class="chat-container">
        <div class="chat-hdr">
            <div>
                <div style="font-weight:700;font-size:1rem">🚀 {theme_val}</div>
                <div style="font-size:0.75rem;opacity:0.85;margin-top:2px">{status}</div>
            </div>
            <div style="font-size:0.65rem;opacity:0.7">{sid[:8]}</div>
        </div>
        <div class="pbar-wrap">
            <div style="background:#E8E0D8;height:4px;">
                <div style="background:linear-gradient(90deg,#FF6B00,#FFB300);height:100%;width:{progress}%;transition:width 0.3s;"></div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Messages
    if st.session_state.msgs:
        st.markdown(f'<div class="chat-container"><div class="msgs">{render_bubbles(st.session_state.msgs)}</div></div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="chat-container"><div style="text-align:center;padding:3rem;color:#CCC">⏳ กำลังรอการตอบสนองจาก AI...</div></div>', unsafe_allow_html=True)

    # Idea selection
    if layer == "hitl_1" and not state.get("selected_idea"):
        ideas = state.get("ideas", [])
        if ideas:
            has_wanphen = any(m.get("agent_name") == "วันเพ็ญ" for m in st.session_state.msgs)
            has_sudet_response = any(
                m.get("agent_name") == "สุรเดช" and ("ตอบกลับ" in m.get("message", "") or "ตอบกลับ" in m.get("message", ""))
                for m in st.session_state.msgs
            )
            
            if has_wanphen and has_sudet_response:
                st.markdown("### 🎯 เลือกไอเดียที่ต้องการ")
                st.caption("คลิกเลือกไอเดีย แล้ว AI จะเริ่มพัฒนาต่อ")
                cols = st.columns(min(len(ideas), 3))
                for i, idea in enumerate(ideas):
                    with cols[i % 3]:
                        with st.container(border=True):
                            st.markdown(f"### {idea.get('title','')}")
                            st.markdown(idea.get("description","")[:120] + "...")
                            st.markdown(f"** Tech:** {', '.join(idea.get('tech_stack',[]))}")
                            if st.button("📌 เลือกไอเดียนี้นะ", key=f"pi_{idea.get('id')}", use_container_width=True):
                                api("POST", f"/sessions/{sid}/select-idea", {"idea_id": idea.get("id")})
                                st.session_state.msgs.append({"event_type":"message","agent_name":"System","message":f"✅ เลือก: {idea.get('title','')}"})
                                st.rerun()
            else:
                st.markdown("""
                <div style="text-align:center;padding:1.5rem;background:white;border-radius:16px;box-shadow:0 2px 12px rgba(0,0,0,0.05)">
                    <div style="font-size:2.5rem;margin-bottom:0.5rem">⚖️</div>
                    <div style="font-weight:700;color:#FF6B00;margin-bottom:0.25rem">กำลังรอความเห็นจากวันเพ็ญ...</div>
                    <div style="font-size:0.85rem;color:#999">วันเพ็ญกำลังวิเคราะห์และให้คะแนนไอเดียอยู่ โปรดรอซักครู่</div>
                </div>
                """, unsafe_allow_html=True)

    # Export section (when complete)
    if layer == "complete":
        st.markdown("---")
        st.markdown("### 📦 ดาวน์โหลดไฟล์")
        st.caption("ดาวน์โหลดโค้ดและไฟล์พิตชิ่งสำหรับนำเสนอ")
        
        # Export code
        c1, c2 = st.columns(2)
        with c1:
            if st.button("📁 Export Code (ZIP)", type="primary", use_container_width=True):
                with st.spinner("กำลังเตรียมไฟล์โค้ด..."):
                    res = api("GET", f"/sessions/{sid}/export/code")
                    if res:
                        st.success(f"✅ สร้างไฟล์เรียบร้อย: `{res['filepath']}`")
                        st.info("💡 ไฟล์ถูกบันทึกในโฟลเดอร์ `data/exports/`")
                        # Store filepath for download
                        st.session_state.export_code_path = res['filepath']
                    else:
                        st.error("❌ ไม่สามารถสร้างไฟล์ได้")
        
        with c2:
            if st.button("📊 Export Pitch Materials (ZIP)", type="primary", use_container_width=True):
                with st.spinner("กำลังเตรียมไฟล์พิตชิ่ง..."):
                    res = api("GET", f"/sessions/{sid}/export/pitch")
                    if res:
                        st.success(f"✅ สร้างไฟล์เรียบร้อย: `{res['filepath']}`")
                        st.info("💡 ไฟล์ถูกบันทึกในโฟลเดอร์ `data/exports/`")
                        st.session_state.export_pitch_path = res['filepath']
                    else:
                        st.error("❌ ไม่สามารถสร้างไฟล์ได้")
        
        # Show download buttons if exports exist
        if hasattr(st.session_state, 'export_code_path') and st.session_state.export_code_path:
            with open(st.session_state.export_code_path, "rb") as f:
                st.download_button(
                    label="⬇️ ดาวน์โหลด Code ZIP",
                    data=f,
                    file_name=f"code_{sid}.zip",
                    mime="application/zip",
                    use_container_width=True,
                )
        
        if hasattr(st.session_state, 'export_pitch_path') and st.session_state.export_pitch_path:
            with open(st.session_state.export_pitch_path, "rb") as f:
                st.download_button(
                    label="⬇️ ดาวน์โหลด Pitch Materials ZIP",
                    data=f,
                    file_name=f"pitch_{sid}.zip",
                    mime="application/zip",
                    use_container_width=True,
                )

    # Code review
    if layer == "hitl_2":
        st.markdown("### 🔍 ตรวจสอบโค้ด")
        st.caption("โค้ดถูกสร้างเรียบร้อยแล้ว ต้องการอนุมัติหรือแก้ไข?")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("✅ อนุมัติ", type="primary", use_container_width=True):
                api("POST", f"/sessions/{sid}/review-code", {"approved": True})
                st.rerun()
        with c2:
            fb = st.text_area("💬 Feedback (ถ้าต้องการแก้ไข)", key="rfb", height=60)
            if st.button("❌ แก้ไข", use_container_width=True):
                api("POST", f"/sessions/{sid}/review-code", {"approved": False, "feedback": fb})
                st.rerun()

    # Bottom bar
    st.markdown('<div style="display:flex;gap:8px;padding:8px 0">', unsafe_allow_html=True)
    has_code = state.get("code_artifacts") or layer in ["hitl_2", "pitching", "complete"]
    has_pitch = state.get("narrative") or layer in ["pitching", "complete"]
    btn_count = 3 if (has_code and has_pitch) else (2 if (has_code or has_pitch) else 1)
    cols = st.columns([1, 1] + ([1] * btn_count))
    idx = 0
    with cols[idx]:
        idx += 1
        if st.button("🆕 New Session", use_container_width=True):
            st.session_state.session_id = None
            st.session_state.msgs = []
            st.session_state.started = False
            st.session_state.export_code_path = None
            st.session_state.export_pitch_path = None
            st.rerun()
    with cols[idx]:
        idx += 1
        if st.button("🔄 Refresh", use_container_width=True):
            st.rerun()
    if has_code:
        with cols[idx]:
            idx += 1
            if st.button("📁 Export Code", use_container_width=True):
                with st.spinner("กำลังเตรียมไฟล์โค้ด..."):
                    res = api("GET", f"/sessions/{sid}/export/code")
                    if res:
                        st.success(f"✅ สร้างไฟล์เรียบร้อย: `{res['filepath']}`")
                        st.info("💡 ไฟล์ถูกบันทึกในโฟลเดอร์ `data/exports/`")
                        st.session_state.export_code_path = res['filepath']
                    else:
                        st.error("❌ ไม่สามารถสร้างไฟล์ได้")
    if has_pitch:
        with cols[idx]:
            idx += 1
            if st.button("📊 Export Pitch", use_container_width=True):
                with st.spinner("กำลังเตรียมไฟล์พิตชิ่ง..."):
                    res = api("GET", f"/sessions/{sid}/export/pitch")
                    if res:
                        st.success(f"✅ สร้างไฟล์เรียบร้อย: `{res['filepath']}`")
                        st.info("💡 ไฟล์ถูกบันทึกในโฟลเดอร์ `data/exports/`")
                        st.session_state.export_pitch_path = res['filepath']
                    else:
                        st.error("❌ ไม่สามารถสร้างไฟล์ได้")
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Show download buttons if exports exist (always visible)
    if hasattr(st.session_state, 'export_code_path') and st.session_state.export_code_path:
        try:
            with open(st.session_state.export_code_path, "rb") as f:
                st.download_button(
                    label="⬇️ ดาวน์โหลด Code ZIP",
                    data=f,
                    file_name=f"code_{sid}.zip",
                    mime="application/zip",
                    use_container_width=True,
                    key="dl_code_btn",
                )
        except Exception:
            st.session_state.export_code_path = None
    
    if hasattr(st.session_state, 'export_pitch_path') and st.session_state.export_pitch_path:
        try:
            with open(st.session_state.export_pitch_path, "rb") as f:
                st.download_button(
                    label="⬇️ ดาวน์โหลด Pitch Materials ZIP",
                    data=f,
                    file_name=f"pitch_{sid}.zip",
                    mime="application/zip",
                    use_container_width=True,
                    key="dl_pitch_btn",
                )
        except Exception:
            st.session_state.export_pitch_path = None

    # Auto-start
    if not state.get("is_paused") and not st.session_state.started:
        st.session_state.started = True
        api("POST", f"/sessions/{sid}/start")

    # Auto-refresh: stop when paused, only refresh on new events when running
    is_paused = state.get("is_paused", False)
    prev_count = st.session_state.get("_prev_msg_count", 0)
    curr_count = len(st.session_state.msgs)
    st.session_state._prev_msg_count = curr_count
    
    if is_paused:
        pass
    elif st.session_state.started:
        if curr_count > prev_count:
            time.sleep(0.5)
            st.rerun()
        else:
            time.sleep(1.5)
            st.rerun()


if __name__ == "__main__":
    main()