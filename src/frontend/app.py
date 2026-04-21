"""
Hackathon Copilot - Streamlit Frontend
Interactive UI for the hackathon copilot system.
"""

import streamlit as st
import requests
import time


# Configuration
try:
    API_BASE_URL = st.secrets.get("API_BASE_URL", "http://localhost:8000")
except Exception:
    API_BASE_URL = "http://localhost:8000"


def api_request(method: str, endpoint: str, data: dict = None):
    """Make API request with error handling."""
    try:
        url = f"{API_BASE_URL}{endpoint}"
        if method == "GET":
            response = requests.get(url)
        elif method == "POST":
            response = requests.post(url, json=data)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.ConnectionError:
        st.error("Cannot connect to API. Make sure the backend is running.")
        return None
    except requests.exceptions.HTTPError as e:
        st.error(f"API Error: {e}")
        return None


def main():
    st.set_page_config(
        page_title="Hackathon Copilot",
        page_icon="🚀",
        layout="wide",
    )

    st.title("🚀 Hackathon Copilot")
    st.caption("AI-Powered Multi-Agent System for Hackathon Success")

    # Initialize session state
    if "session_id" not in st.session_state:
        st.session_state.session_id = None
    if "workflow_started" not in st.session_state:
        st.session_state.workflow_started = False

    # Sidebar
    with st.sidebar:
        st.header("⚙️ Controls")

        if st.button("🆕 New Session"):
            st.session_state.session_id = None
            st.session_state.workflow_started = False
            st.rerun()

        if st.session_state.session_id:
            st.success(f"Session: `{st.session_state.session_id}`")

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
            st.success(f"Session created: `{result['session_id']}`")
            st.rerun()


def show_session_flow():
    """Show main workflow."""
    session_id = st.session_state.session_id

    # Get session state
    with st.spinner("Loading session..."):
        state = api_request("GET", f"/sessions/{session_id}")

    if not state:
        st.error("Failed to load session")
        return

    # Progress indicator
    st.progress(get_progress_value(state["current_layer"]))
    st.caption(f"Current Phase: **{state['current_layer'].replace('_', ' ').title()}**")

    # Agent messages
    if state.get("agent_log"):
        st.subheader("💬 Agent Messages")
        for msg in state["agent_log"][-10:]:
            st.chat_message(msg.get("agent", "system")).write(
                f"{msg.get('emoji', '')} **{msg.get('agent_name', '')}** ({msg.get('role', '')}): {msg.get('message', '')}"
            )

    # Phase-specific UI
    if state["current_layer"] in ["hitl_1", "judging"]:
        handle_idea_selection(state)
    elif state["current_layer"] == "hitl_2":
        handle_code_review(state)
    elif state["current_layer"] == "complete":
        handle_completion(state)
    elif not state["is_paused"] and not st.session_state.workflow_started:
        handle_auto_start(state)


def handle_auto_start(state):
    """Auto-start the workflow."""
    st.session_state.workflow_started = True
    with st.spinner("AI team is brainstorming..."):
        result = api_request("POST", f"/sessions/{st.session_state.session_id}/start")

    if result:
        st.rerun()


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
        time.sleep(2)
        st.rerun()


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

    # Export options
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

    # Summary
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