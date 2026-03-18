"""
app.py — Module 1: UI Layer
Run with: streamlit run app.py
"""

import streamlit as st
from scraper import save_snapshot
from restore import restore_session, load_sessions

st.set_page_config(
    page_title="Workspaces",   # ← change this
    page_icon="📸",
    layout="wide"
)

st.markdown("""
<style>
  .stButton > button {
    width: 100%;
    border-radius: 10px;
    font-weight: 600;
    padding: 0.65rem;
  }
  .window-row {
    font-size: 0.85rem;
    color: #888;
    padding: 3px 0;
    border-bottom: 1px solid #f0f0f0;
  }
  .app-badge {
    display: inline-block;
    background: #f0f0f5;
    color: #444;
    border-radius: 5px;
    padding: 1px 7px;
    font-size: 0.75rem;
    margin-right: 6px;
    font-weight: 500;
  }
</style>
""", unsafe_allow_html=True)

# ── Header
st.title("📸 Workspaces")                                    # ← change this
st.caption("Save every open app and window. Restore your exact state with one click.")
st.divider()

# ── Save row
col_name, col_btn, col_tip = st.columns([3, 2, 3])

with col_name:
    session_name = st.text_input(
        "name",
        placeholder="Session name — e.g. Deep Work Monday",
        label_visibility="collapsed"
    )

with col_btn:
    if st.button("📸  Save Workspace", type="primary"):
        with st.spinner("Scanning open windows..."):
            session = save_snapshot(session_name or None)
        st.success(f"Saved **{len(session['windows'])}** windows as **{session['name']}**")
        st.rerun()

with col_tip:
    st.info("Name your session (optional), then click Save.")

st.divider()

# ── Session list
sessions = load_sessions()

if not sessions:
    st.markdown("### No saved sessions yet")
    st.markdown("Click **Save Workspace** above to capture your first snapshot.")
else:
    st.markdown(f"### Saved Sessions &nbsp; `{len(sessions)}`")

    for i, session in enumerate(reversed(sessions)):
        real_idx = len(sessions) - 1 - i
        windows  = session.get("windows", [])
        ts       = session["timestamp"][:16].replace("T", " at ")

        with st.expander(
            f"**{session['name']}**  ·  {ts}  ·  {len(windows)} windows",
            expanded=(i == 0)
        ):
            btn_col, info_col = st.columns([1, 3])

            with btn_col:
                if st.button("▶  Restore this session",
                             key=f"restore_{real_idx}",
                             type="primary"):
                    with st.spinner("Restoring..."):
                        results = restore_session(session)
                    ok  = sum(1 for r in results if r["status"].startswith("ok"))
                    bad = len(results) - ok
                    if bad == 0:
                        st.success(f"All {ok} apps restored!")
                    else:
                        st.warning(f"Restored {ok} apps · {bad} could not be found")

            with info_col:
                st.markdown("**Windows captured in this snapshot:**")
                for w in windows:
                    badge = f'<span class="app-badge">{w["app_name"]}</span>'
                    title = w["window_title"] or "—"
                    st.markdown(
                        f'<div class="window-row">{badge}{title}</div>',
                        unsafe_allow_html=True
                    )

            with st.expander("View raw JSON"):
                st.json(session)