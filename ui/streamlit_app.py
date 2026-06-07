"""HERMES Streamlit UI — multi-page progressive disclosure interface."""

import json
import time
from datetime import datetime

import requests
import streamlit as st

API_BASE = "http://localhost:8000"
DEFAULT_USER = "demo-user"
DEFAULT_SESSION = "demo-session"

st.set_page_config(
    page_title="HERMES — Enterprise Assistant",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Sidebar navigation ────────────────────────────────────────────────────────
st.sidebar.title("HERMES")
st.sidebar.caption("Hybrid Enterprise Retrieval, Monitoring and Execution System")
st.sidebar.divider()

page = st.sidebar.radio(
    "Navigate",
    ["Ask HERMES", "Sources", "Monitors", "Actions", "Runs", "Memory"],
    index=0,
)
st.sidebar.divider()
st.sidebar.caption(f"API: `{API_BASE}`")
st.sidebar.caption(f"User: `{DEFAULT_USER}`")


# ── Helpers ───────────────────────────────────────────────────────────────────
def api_get(path: str, params: dict | None = None) -> dict | list | None:
    try:
        r = requests.get(f"{API_BASE}{path}", params=params, timeout=30)
        r.raise_for_status()
        return r.json()
    except requests.exceptions.ConnectionError:
        st.error("Cannot reach HERMES API. Is the server running? (`make api`)")
        return None
    except Exception as exc:
        st.error(f"API error: {exc}")
        return None


def api_post(path: str, body: dict, timeout: int = 120) -> dict | None:
    try:
        r = requests.post(f"{API_BASE}{path}", json=body, timeout=timeout)
        if r.status_code == 429:
            detail = r.json().get("detail", {})
            retry = detail.get("retry_after", "a few minutes")
            st.warning(f"⏳ Groq API rate limit reached. Please try again in **{retry}**.")
            return None
        r.raise_for_status()
        return r.json()
    except requests.exceptions.ConnectionError:
        st.error("Cannot reach HERMES API. Is the server running? (`make api`)")
        return None
    except Exception as exc:
        st.error(f"API error: {exc}")
        return None


def api_delete(path: str) -> bool:
    try:
        r = requests.delete(f"{API_BASE}{path}", timeout=10)
        return r.status_code in (200, 204)
    except Exception:
        return False


def confidence_badge(score: float) -> str:
    if score >= 0.8:
        return f"🟢 {score:.0%}"
    if score >= 0.5:
        return f"🟡 {score:.0%}"
    return f"🔴 {score:.0%}"


def source_icon(source_type: str) -> str:
    icons = {
        "confluence": "📄", "jira": "🎯", "slack": "💬", "gmail": "📧",
        "github": "🐙", "google_drive": "☁️", "hubspot": "🤝",
        "fireflies": "🎙️", "linear": "📊",
    }
    return icons.get(source_type, "📁")


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: ASK HERMES
# ═══════════════════════════════════════════════════════════════════════════════
if page == "Ask HERMES":
    st.title("Ask HERMES")
    st.caption("Search and synthesise enterprise knowledge from Rocket's internal systems.")

    with st.form("query_form"):
        question = st.text_area(
            "Your question",
            placeholder="What are the acceptance checks for a zero-trust private deployment?",
            height=100,
        )
        col1, col2 = st.columns([3, 1])
        with col1:
            source_filter = st.multiselect(
                "Filter by source (optional)",
                ["confluence", "jira", "slack", "gmail", "github", "google_drive", "hubspot", "fireflies", "linear"],
            )
        with col2:
            mode = st.selectbox("Mode", ["detailed", "concise"])
        submitted = st.form_submit_button("Ask HERMES", type="primary", use_container_width=True)

    if submitted and question.strip():
        with st.spinner("HERMES is thinking…"):
            result = api_post(
                "/v1/query",
                {
                    "user_id": DEFAULT_USER,
                    "session_id": DEFAULT_SESSION,
                    "question": question,
                    "source_types": source_filter,
                    "response_mode": mode,
                },
                timeout=180,
            )

        if result:
            st.session_state["last_result"] = result

    result = st.session_state.get("last_result")
    if result:
        # ── Primary answer view ───────────────────────────────────────────────
        col1, col2, col3 = st.columns([6, 2, 2])
        with col1:
            st.subheader(result.get("topic", "Answer")[:80])
        with col2:
            st.metric("Confidence", confidence_badge(result.get("confidence", 0)))
        with col3:
            st.metric("Latency", f"{result.get('latency_ms', 0):,} ms")

        if result.get("information_not_found"):
            st.warning("The requested information was not found in the knowledge base.")

        if result.get("conflicts"):
            with st.expander("⚠️ Conflicts detected", expanded=True):
                for c in result["conflicts"]:
                    st.warning(c)

        st.markdown(result.get("summary", ""))

        # ── Sources (always visible) ──────────────────────────────────────────
        sources = result.get("sources", [])
        if sources:
            st.subheader(f"Sources ({len(sources)})")
            for src in sources:
                icon = source_icon(src.get("source_type", ""))
                with st.container():
                    st.markdown(
                        f"{icon} **{src.get('title', 'Untitled')}** "
                        f"`{src.get('source_type', '')}` · "
                        f"doc_id: `{src.get('doc_id', '')}` · "
                        f"score: `{src.get('relevance_score', 0):.3f}`"
                    )

        # ── Progressive disclosure ────────────────────────────────────────────
        with st.expander("Workflow details"):
            st.json(
                {
                    "run_id": result.get("run_id"),
                    "workflow": result.get("workflow"),
                    "tools_used": result.get("tools_used"),
                }
            )


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: SOURCES
# ═══════════════════════════════════════════════════════════════════════════════
elif page == "Sources":
    st.title("Sources")
    st.caption("Inspect retrieved documents from the last query.")
    result = st.session_state.get("last_result")
    if not result:
        st.info("Run a query on the **Ask HERMES** page first.")
    else:
        sources = result.get("sources", [])
        if not sources:
            st.info("No sources were retrieved.")
        for src in sources:
            icon = source_icon(src.get("source_type", ""))
            with st.expander(f"{icon} {src.get('title', 'Untitled')} — `{src.get('doc_id', '')}`"):
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**Source type:** {src.get('source_type', '')}")
                    st.write(f"**Relevance score:** {src.get('relevance_score', 0):.4f}")
                with col2:
                    st.write(f"**doc_id:** `{src.get('doc_id', '')}`")


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: MONITORS
# ═══════════════════════════════════════════════════════════════════════════════
elif page == "Monitors":
    st.title("Monitors")
    st.caption("Create and manage topic monitors. HERMES will alert you to material changes.")

    with st.form("monitor_form"):
        m_name = st.text_input("Monitor name", placeholder="GPU burst SLO changes")
        m_query = st.text_area("Query to monitor", placeholder="Cross-account GPU burst SLO limits and thresholds")
        m_sources = st.multiselect("Source types", ["confluence", "jira", "slack", "github"])
        m_cron = st.text_input("Schedule (cron)", value="0 * * * *")
        m_submit = st.form_submit_button("Save Monitor", type="primary")

    if m_submit and m_name and m_query:
        r = api_post(
            "/v1/monitors",
            {
                "user_id": DEFAULT_USER,
                "name": m_name,
                "query": m_query,
                "source_types": m_sources,
                "schedule_cron": m_cron,
            },
        )
        if r:
            st.success(f"Monitor saved: {r.get('id')}")

    st.divider()
    monitors = api_get("/v1/monitors", {"user_id": DEFAULT_USER})
    if monitors:
        st.subheader(f"Active monitors ({len(monitors)})")
        for m in monitors:
            with st.expander(f"📡 {m['name']}"):
                st.write(f"**Query:** {m['query']}")
                st.write(f"**Sources:** {', '.join(m.get('source_types', [])) or 'all'}")
                st.write(f"**Schedule:** `{m.get('schedule_cron', '')}`")
                st.write(f"**Last run:** {m.get('last_run_at') or 'never'}")
                if st.button(f"Delete {m['id'][:8]}", key=f"del_{m['id']}"):
                    if api_delete(f"/v1/monitors/{m['id']}"):
                        st.success("Deleted.")
                        st.rerun()


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: ACTIONS
# ═══════════════════════════════════════════════════════════════════════════════
elif page == "Actions":
    st.title("Actions")
    st.caption("Review and approve or reject proposed enterprise actions.")

    actions = api_get("/v1/actions", {"user_id": DEFAULT_USER})
    if not actions:
        st.info("No pending actions. HERMES will propose actions when you ask it to create Jira tickets, emails, etc.")
    else:
        for a in actions:
            status_icon = {"pending": "🕐", "approved": "✅", "rejected": "❌"}.get(a["status"], "❓")
            with st.expander(f"{status_icon} {a['tool_name']} — `{a['id'][:12]}`"):
                st.json(a["tool_input"])
                if a["status"] == "pending":
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("✅ Approve", key=f"approve_{a['id']}", type="primary"):
                            r = api_post(
                                f"/v1/actions/{a['id']}/approve",
                                {"user_id": DEFAULT_USER, "decision": "approve"},
                            )
                            if r:
                                st.success("Action approved.")
                                st.rerun()
                    with col2:
                        if st.button("❌ Reject", key=f"reject_{a['id']}"):
                            r = api_post(
                                f"/v1/actions/{a['id']}/approve",
                                {"user_id": DEFAULT_USER, "decision": "reject"},
                            )
                            if r:
                                st.warning("Action rejected.")
                                st.rerun()


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: RUNS
# ═══════════════════════════════════════════════════════════════════════════════
elif page == "Runs":
    st.title("Runs")
    st.caption("Inspect agent run history, traces, and performance metrics.")

    run_id = st.text_input("Fetch a specific run by ID", placeholder="paste run_id here")
    if run_id:
        run = api_get(f"/v1/runs/{run_id}")
        if run:
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Status", run.get("status", ""))
            with col2:
                st.metric("Workflow", run.get("workflow", ""))
            with col3:
                st.metric("Latency", f"{run.get('latency_ms', 0):,} ms")
            st.write(f"**Question:** {run.get('question', '')}")
            if run.get("error"):
                st.error(f"Error: {run['error']}")
            with st.expander("Full result"):
                st.json(run.get("result") or {})

    st.info("Full run history is available in `storage/logs/traces.jsonl` and the Langfuse dashboard.")


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: MEMORY
# ═══════════════════════════════════════════════════════════════════════════════
elif page == "Memory":
    st.title("Memory")
    st.caption("View, add, or remove durable knowledge retained by HERMES.")

    memory_type_filter = st.selectbox("Filter by type", ["all", "episodic", "semantic", "procedural"])
    params = {"user_id": DEFAULT_USER}
    if memory_type_filter != "all":
        params["memory_type"] = memory_type_filter

    entries = api_get("/v1/memory", params)

    with st.form("add_memory"):
        m_content = st.text_area("New memory entry", placeholder="The user prefers concise executive summaries.")
        m_type = st.selectbox("Type", ["episodic", "semantic", "procedural"])
        m_tags = st.text_input("Tags (comma-separated)", placeholder="preference, format")
        m_save = st.form_submit_button("Save Memory", type="primary")

    if m_save and m_content.strip():
        tags = [t.strip() for t in m_tags.split(",") if t.strip()]
        r = api_post("/v1/memory", {"user_id": DEFAULT_USER, "content": m_content, "memory_type": m_type, "tags": tags})
        if r:
            st.success("Memory saved.")
            st.rerun()

    st.divider()
    if entries:
        st.subheader(f"Stored memories ({len(entries)})")
        for e in entries:
            type_icon = {"episodic": "📚", "semantic": "🧠", "procedural": "⚙️"}.get(e.get("memory_type", ""), "📝")
            with st.expander(f"{type_icon} [{e.get('memory_type', '')}] {e.get('content', '')[:80]}…"):
                st.write(e.get("content", ""))
                st.caption(f"id: `{e.get('id', '')}` · created: {e.get('created_at', '')}")
                if e.get("tags"):
                    st.write(f"Tags: {', '.join(e['tags'])}")
                if st.button("Delete", key=f"del_mem_{e['id']}"):
                    if api_delete(f"/v1/memory/{e['id']}?user_id={DEFAULT_USER}"):
                        st.success("Deleted.")
                        st.rerun()
