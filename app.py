import streamlit as st
import time
from orchestrator import DebateOrchestrator, get_history_stats

# Page Configuration - Sidebar collapsed by default
st.set_page_config(
    page_title="Debatr | AI Debate Simulator",
    page_icon="⚔️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom Styling for Minimal Modern UI (Sidebar completely hidden)
st.markdown("""
<style>
    /* Completely hide sidebar and collapse toggle */
    [data-testid="stSidebar"], [data-testid="stSidebarCollapsedControl"], section[data-testid="stSidebar"] {
        display: none !important;
    }
    
    /* Global styling */
    .block-container {
        padding-top: 1.5rem;
        padding-bottom: 3rem;
        max-width: 1050px;
    }
    
    /* Header & Stats Banner */
    .hero-container {
        background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
        border: 1px solid #334155;
        border-radius: 16px;
        padding: 24px;
        margin-bottom: 20px;
        color: #f8fafc;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.25);
    }
    .hero-title {
        font-size: 28px;
        font-weight: 700;
        margin-bottom: 6px;
        display: flex;
        align-items: center;
        gap: 12px;
    }
    .hero-subtitle {
        color: #94a3b8;
        font-size: 14.5px;
        margin-bottom: 18px;
    }
    
    /* Stats Grid */
    .stat-card {
        background: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 12px;
        padding: 12px 16px;
        text-align: center;
    }
    .stat-value {
        font-size: 24px;
        font-weight: 800;
        color: #38bdf8;
    }
    .stat-label {
        font-size: 11.5px;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: #94a3b8;
        margin-top: 4px;
    }

    /* Setup Card (In-Page) */
    .setup-card {
        background: #111827;
        border: 1px solid #374151;
        border-radius: 16px;
        padding: 24px;
        margin-bottom: 24px;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.2);
    }
    .setup-header {
        font-size: 18px;
        font-weight: 600;
        color: #f3f4f6;
        margin-bottom: 16px;
        display: flex;
        align-items: center;
        gap: 8px;
    }

    /* Active Debate Top Bar */
    .active-topic-bar {
        background: #1e293b;
        border: 1px solid #334155;
        border-left: 5px solid #38bdf8;
        border-radius: 12px;
        padding: 16px 20px;
        margin-bottom: 24px;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    .active-topic-title {
        font-size: 16px;
        font-weight: 600;
        color: #f8fafc;
    }
    .active-topic-sub {
        font-size: 13px;
        color: #94a3b8;
        margin-top: 2px;
    }

    /* Chat Bubbles */
    .chat-bubble-container {
        display: flex;
        flex-direction: column;
        margin-bottom: 18px;
    }
    .bubble-a {
        align-self: flex-start;
        background: #0f172a;
        border: 1px solid #2563eb;
        border-left: 5px solid #3b82f6;
        border-radius: 14px;
        padding: 16px 20px;
        max-width: 85%;
        box-shadow: 0 4px 12px rgba(59, 130, 246, 0.08);
        margin-bottom: 12px;
    }
    .bubble-b {
        align-self: flex-end;
        background: #18181b;
        border: 1px solid #7c3aed;
        border-right: 5px solid #8b5cf6;
        border-radius: 14px;
        padding: 16px 20px;
        max-width: 85%;
        box-shadow: 0 4px 12px rgba(139, 92, 246, 0.08);
        margin-bottom: 12px;
    }
    .badge-a {
        display: inline-block;
        background: rgba(59, 130, 246, 0.2);
        color: #60a5fa;
        font-weight: 700;
        font-size: 12px;
        padding: 3px 10px;
        border-radius: 9999px;
        margin-bottom: 8px;
        text-transform: uppercase;
    }
    .badge-b {
        display: inline-block;
        background: rgba(139, 92, 246, 0.2);
        color: #c084fc;
        font-weight: 700;
        font-size: 12px;
        padding: 3px 10px;
        border-radius: 9999px;
        margin-bottom: 8px;
        text-transform: uppercase;
    }
    .bubble-text {
        font-size: 15px;
        line-height: 1.6;
        color: #e2e8f0;
    }

    /* Voting & Reveal Cards */
    .voting-container {
        background: #1e1b4b;
        border: 2px dashed #6366f1;
        border-radius: 16px;
        padding: 24px;
        text-align: center;
        margin-top: 24px;
        margin-bottom: 24px;
    }
    .reveal-card {
        background: #0f172a;
        border: 1px solid #334155;
        border-radius: 16px;
        padding: 28px;
        margin-top: 24px;
        box-shadow: 0 8px 30px rgba(0, 0, 0, 0.4);
    }
    .agreement-badge-agreed {
        background: #064e3b;
        color: #34d399;
        border: 1px solid #059669;
        padding: 8px 16px;
        border-radius: 9999px;
        font-weight: 700;
        font-size: 14px;
        display: inline-block;
        margin-bottom: 14px;
    }
    .agreement-badge-disagreed {
        background: #78350f;
        color: #fcd34d;
        border: 1px solid #d97706;
        padding: 8px 16px;
        border-radius: 9999px;
        font-weight: 700;
        font-size: 14px;
        display: inline-block;
        margin-bottom: 14px;
    }
</style>
""", unsafe_allow_html=True)

# Initialize Session State
if "orchestrator" not in st.session_state:
    st.session_state.orchestrator = None
if "debate_status" not in st.session_state:
    st.session_state.debate_status = "idle"  # "idle" | "debating" | "awaiting_vote" | "revealed"
if "topic" not in st.session_state:
    st.session_state.topic = ""
if "rounds" not in st.session_state:
    st.session_state.rounds = 3

# Fetch Stats
stats = get_history_stats()

# Header & Running Stats Banner
st.markdown(f"""
<div class="hero-container">
    <div class="hero-title">⚔️ Debatr Simulator</div>
    <div class="hero-subtitle">Two AI debaters duel in multi-round intellectual combat. Vote for the winner, then uncover whether you aligned with the silent AI Judge.</div>
    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 12px;">
        <div class="stat-card">
            <div class="stat-value">{stats['total_debates']}</div>
            <div class="stat-label">Total Debates</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">{stats['agreement_rate']}%</div>
            <div class="stat-label">AI-User Agreement</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">{stats['agreement_count']} / {stats['total_debates']}</div>
            <div class="stat-label">Matched Verdicts</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">A:{stats['judge_wins_a']} | B:{stats['judge_wins_b']}</div>
            <div class="stat-label">Judge Decisions</div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# Helper to render styled chat bubble
def render_bubble(speaker: str, round_num: int, text: str):
    if speaker == "A":
        st.markdown(f"""
        <div class="chat-bubble-container">
            <div class="bubble-a">
                <span class="badge-a">Debater A (FOR) • Round {round_num}</span>
                <div class="bubble-text">{text}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div class="chat-bubble-container">
            <div class="bubble-b">
                <span class="badge-b">Debater B (AGAINST) • Round {round_num}</span>
                <div class="bubble-text">{text}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

# --- IN-PAGE SETUP (When IDLE) ---
if st.session_state.debate_status == "idle":
    st.markdown("""
    <div class="setup-header">⚙️ Configure Your Debate</div>
    """, unsafe_allow_html=True)
    
    preset_topics = [
        "Remote work is more effective than in-office work",
        "Universal Basic Income is essential in the age of AI",
        "Social media does more net harm than good to society",
        "Nuclear energy is indispensable for fighting climate change",
        "Cats make superior household companions compared to dogs"
    ]
    
    col_preset, col_rounds = st.columns([3, 1])
    with col_preset:
        selected_preset = st.selectbox("Quick Presets (or type your own below)", ["Choose a topic or write your own..."] + preset_topics)
    with col_rounds:
        rounds_input = st.slider("Debate Rounds", min_value=1, max_value=5, value=3, help="Each round features one argument from Debater A and one from Debater B.")
    
    default_text = selected_preset if selected_preset != "Choose a topic or write your own..." else "Remote work is more effective than in-office work"
    topic_input = st.text_input("Proposition / Debate Topic", value=default_text, help="The proposition Debater A will support and Debater B will oppose.")
    
    col_btn, col_info = st.columns([1, 2])
    with col_btn:
        start_btn = st.button("🚀 Start Live Debate", type="primary", use_container_width=True)
    with col_info:
        st.caption("Engine: **OpenRouter (stealth/union-alpha)** • Silent Judge executes in background")
        
    if start_btn and topic_input.strip():
        st.session_state.topic = topic_input.strip()
        st.session_state.rounds = rounds_input
        st.session_state.orchestrator = DebateOrchestrator(topic=topic_input.strip(), total_rounds=rounds_input)
        st.session_state.debate_status = "debating"
        st.rerun()

# --- ACTIVE OR COMPLETED DEBATE ---
else:
    orch: DebateOrchestrator = st.session_state.orchestrator
    
    # Sleek Top Topic Banner with Reset Option
    col_banner, col_reset = st.columns([5, 1])
    with col_banner:
        st.markdown(f"""
        <div class="active-topic-bar">
            <div>
                <div class="active-topic-title">📌 Proposition: {orch.topic}</div>
                <div class="active-topic-sub">Rounds: {orch.total_rounds} • Model: stealth/union-alpha</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    with col_reset:
        if st.button("🔄 New Debate", use_container_width=True):
            st.session_state.orchestrator = None
            st.session_state.debate_status = "idle"
            st.rerun()

    # Debate execution loop
    if st.session_state.debate_status == "debating":
        # Render past transcript
        for item in orch.transcript:
            render_bubble(item["speaker"], item["round"], item["text"])
            
        current_round = (len(orch.transcript) // 2) + 1
        
        if current_round <= orch.total_rounds:
            if len(orch.transcript) % 2 == 0:
                speaker = "A"
                role_label = "Debater A (FOR)"
                badge_class = "badge-a"
                bubble_class = "bubble-a"
            else:
                speaker = "B"
                role_label = "Debater B (AGAINST)"
                badge_class = "badge-b"
                bubble_class = "bubble-b"
                
            placeholder = st.empty()
            accumulated_text = ""
            
            with st.spinner(f"Round {current_round} - {role_label} is crafting their argument..."):
                for token in orch.stream_turn(speaker, current_round):
                    accumulated_text += token
                    placeholder.markdown(f"""
                    <div class="chat-bubble-container">
                        <div class="{bubble_class}">
                            <span class="{badge_class}">{role_label} • Round {current_round}</span>
                            <div class="bubble-text">{accumulated_text}▌</div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                placeholder.markdown(f"""
                <div class="chat-bubble-container">
                    <div class="{bubble_class}">
                        <span class="{badge_class}">{role_label} • Round {current_round}</span>
                        <div class="bubble-text">{accumulated_text}</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
            time.sleep(0.3)
            st.rerun()
        else:
            # All rounds finished! Evaluate Judge silently
            with st.status("⚖️ All debate rounds concluded! The AI Judge is deliberating in silence...", expanded=True) as status:
                st.write("Evaluating Logical Consistency, Evidence & Substantiation, and Rebuttal Engagement...")
                orch.evaluate_judge_silently()
                status.update(label="⚖️ AI Judge has reached a silent verdict! Awaiting your vote.", state="complete")
                
            st.session_state.debate_status = "awaiting_vote"
            st.rerun()

    # Display Transcript and Voting / Verdict if awaiting_vote or revealed
    elif st.session_state.debate_status in ("awaiting_vote", "revealed"):
        # Display full debate transcript
        for item in orch.transcript:
            render_bubble(item["speaker"], item["round"], item["text"])
            
        # Voting Section
        if st.session_state.debate_status == "awaiting_vote":
            st.markdown("""
            <div class="voting-container">
                <h3 style="margin-bottom: 8px; color: #e0e7ff;">🗳️ Cast Your Vote</h3>
                <p style="color: #94a3b8; font-size: 15px; margin-bottom: 20px;">
                    The silent AI Judge has already locked in its secret verdict. Who presented the superior arguments?
                </p>
            </div>
            """, unsafe_allow_html=True)
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("🔵 Debater A Won (FOR)", type="primary", use_container_width=True):
                    orch.submit_user_vote("A")
                    st.session_state.debate_status = "revealed"
                    st.rerun()
            with col2:
                if st.button("🟣 Debater B Won (AGAINST)", type="primary", use_container_width=True):
                    orch.submit_user_vote("B")
                    st.session_state.debate_status = "revealed"
                    st.rerun()

        # Verdict Revealed Section
        elif st.session_state.debate_status == "revealed":
            verdict = orch.revealed_verdict
            user_vote = verdict.get("user_vote")
            judge_winner = verdict.get("winner")
            agreed = verdict.get("agreed_with_ai", False)
            scores = verdict.get("scores", {})
            reasoning = verdict.get("reasoning", "")
            
            st.markdown("---")
            
            badge_html = (
                '<div class="agreement-badge-agreed">🎉 YOU AGREED WITH THE AI JUDGE</div>'
                if agreed else
                '<div class="agreement-badge-disagreed">⚖️ YOU DISAGREED WITH THE AI JUDGE</div>'
            )
            
            st.markdown(f"""
            <div class="reveal-card">
                {badge_html}
                <h2 style="margin-top: 0; color: #f8fafc; font-size: 26px;">
                    Official Verdict: Debater {judge_winner} Won the Debate
                </h2>
                <div style="display: flex; gap: 24px; margin: 16px 0 24px 0; color: #cbd5e1; font-size: 15px;">
                    <div>Your Vote: <strong style="color: {'#60a5fa' if user_vote == 'A' else '#c084fc'};">Debater {user_vote}</strong></div>
                    <div>AI Judge Winner: <strong style="color: {'#60a5fa' if judge_winner == 'A' else '#c084fc'};">Debater {judge_winner}</strong></div>
                </div>
                <div style="background: rgba(255, 255, 255, 0.03); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 10px; padding: 18px; margin-bottom: 20px;">
                    <h4 style="margin-top: 0; color: #38bdf8; font-size: 14px; text-transform: uppercase;">Judge Analysis & Reasoning</h4>
                    <p style="color: #e2e8f0; font-size: 14.5px; line-height: 1.6; margin-bottom: 0;">{reasoning}</p>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            st.subheader("📊 Criteria Score Breakdown")
            score_a = scores.get("A", {})
            score_b = scores.get("B", {})
            
            col_s1, col_s2, col_s3, col_s4 = st.columns(4)
            with col_s1:
                st.metric(
                    "Logical Consistency",
                    f"A: {score_a.get('logical_consistency', '-')} vs B: {score_b.get('logical_consistency', '-')}"
                )
            with col_s2:
                st.metric(
                    "Evidence & Substantiation",
                    f"A: {score_a.get('evidence_use', '-')} vs B: {score_b.get('evidence_use', '-')}"
                )
            with col_s3:
                st.metric(
                    "Rebuttal Engagement",
                    f"A: {score_a.get('rebuttal_engagement', '-')} vs B: {score_b.get('rebuttal_engagement', '-')}"
                )
            with col_s4:
                total_a = score_a.get('total', sum([score_a.get('logical_consistency', 0), score_a.get('evidence_use', 0), score_a.get('rebuttal_engagement', 0)]))
                total_b = score_b.get('total', sum([score_b.get('logical_consistency', 0), score_b.get('evidence_use', 0), score_b.get('rebuttal_engagement', 0)]))
                st.metric(
                    "Total Score",
                    f"A: {total_a} vs B: {total_b}"
                )
                
            st.markdown("<br>", unsafe_allow_html=True)
            col_act1, col_act2 = st.columns(2)
            with col_act1:
                transcript_md = orch.export_transcript_markdown()
                st.download_button(
                    label="📥 Download Debate Transcript (.md)",
                    data=transcript_md,
                    file_name=f"debate_{orch.id[:8]}.md",
                    mime="text/markdown",
                    use_container_width=True
                )
            with col_act2:
                if st.button("⚔️ Start Another Debate", type="primary", use_container_width=True):
                    st.session_state.orchestrator = None
                    st.session_state.debate_status = "idle"
                    st.rerun()

