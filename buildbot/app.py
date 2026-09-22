"""
🔧 Jenkins Build Bot — Premium AI Chat Dashboard UI
Modern sidebar + full-height chat panel with glassy cards.

Run: streamlit run app.py
"""

import streamlit as st
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ── Page config (MUST be first Streamlit call) ────────────────────────────────
st.set_page_config(
    page_title="Jenkins Build Bot",
    page_icon="🔧",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Imports ───────────────────────────────────────────────────────────────────
from config import settings
from core.processor import RequestProcessor
from core.conversation import ConversationManager
from services.llm_service import LLMService
from services.jenkins_service import JenkinsService
from services.notification_service import NotificationService
from services.artifact_service import ArtifactService
from services.github_service import GitHubService


# ─────────────────────────────────────────────────────────────────────────────
#  DYNAMIC CSS  — injected after init_state() so session prefs are available
# ─────────────────────────────────────────────────────────────────────────────
def inject_css():
    p = st.session_state   # shorthand

    # ── Palette based on mode ────────────────────────────────────────────
    if p.theme_mode == "light":
        bg_deep   = "#f0f2f8"
        bg_panel  = "#ffffff"
        bg_card   = "#f8f9fc"
        bg_hover  = "#eef0f6"
        border    = "rgba(0,0,0,0.08)"
        text_1    = "#0f172a"
        text_2    = "#475569"
        text_3    = "#94a3b8"
        scrollbar = "rgba(0,0,0,0.15)"
        log_bg    = "#1e293b"
        log_color = "#4ade80"
    else:
        bg_deep   = "#080b14"
        bg_panel  = "#0e1422"
        bg_card   = "#141927"
        bg_hover  = "#1a2235"
        border    = "rgba(255,255,255,0.07)"
        text_1    = "#f1f5f9"
        text_2    = "#94a3b8"
        text_3    = "#475569"
        scrollbar = "rgba(255,255,255,0.12)"
        log_bg    = "#060a10"
        log_color = "#4ade80"

    a1  = p.accent_color
    a2  = p.accent2_color
    fs  = p.font_size
    cw  = p.chat_width
    pad = "0.5rem 0.75rem" if p.compact_mode else "0.75rem 1rem"

    # ── Bubble border-radius per style ───────────────────────────────────
    if p.bubble_style == "sharp":
        bot_br  = "2px 14px 14px 14px"
        usr_br  = "14px 2px 14px 14px"
    elif p.bubble_style == "pill":
        bot_br  = "20px 20px 20px 4px"
        usr_br  = "20px 20px 4px 20px"
    else:  # rounded (default)
        bot_br  = "4px 16px 16px 16px"
        usr_br  = "16px 4px 16px 16px"

    st.markdown(f"""
<style>
/* ── Reset & base ──────────────────────────────────────────────── */
#MainMenu, footer, header {{ visibility: hidden; }}
.block-container {{ padding: 0 !important; max-width: 100% !important; }}
[data-testid="stAppViewContainer"] {{ padding: 0; }}
[data-testid="stVerticalBlock"] {{ gap: 0 !important; }}

/* ── Root palette ──────────────────────────────────────────────── */
:root {{
  --bg-deep:   {bg_deep};
  --bg-panel:  {bg_panel};
  --bg-card:   {bg_card};
  --bg-hover:  {bg_hover};
  --border:    {border};
  --accent1:   {a1};
  --accent2:   {a2};
  --accent3:   #06b6d4;
  --success:   #22c55e;
  --failure:   #ef4444;
  --warning:   #f59e0b;
  --text-1:    {text_1};
  --text-2:    {text_2};
  --text-3:    {text_3};
  --fs-base:   {fs}px;
}}

.stApp {{
  background: var(--bg-deep) !important;
  font-family: 'Inter', 'Segoe UI', sans-serif;
  font-size: var(--fs-base);
}}

/* ── Sidebar ────────────────────────────────────────────────────── */
[data-testid="stSidebar"] {{
  background: var(--bg-panel) !important;
  border-right: 1px solid var(--border);
  padding: 0 !important;
}}
[data-testid="stSidebar"] > div:first-child {{ padding: 0 !important; }}

.sidebar-logo {{
  padding: 1.5rem 1.25rem 1rem;
  border-bottom: 1px solid var(--border);
}}
.sidebar-logo-icon {{
  width: 42px; height: 42px;
  background: linear-gradient(135deg, var(--accent1), var(--accent2));
  border-radius: 12px;
  display: flex; align-items: center; justify-content: center;
  font-size: 1.2rem; margin-bottom: 0.75rem;
  box-shadow: 0 0 20px color-mix(in srgb, {a1} 40%, transparent);
}}
.sidebar-logo-title {{ color: var(--text-1); font-size: 1rem; font-weight: 700; letter-spacing: -0.02em; }}
.sidebar-logo-sub   {{ color: var(--text-2); font-size: 0.72rem; margin-top: 0.15rem; }}

.status-pill {{
  display: inline-flex; align-items: center; gap: 0.35rem;
  padding: 0.2rem 0.65rem; border-radius: 20px;
  font-size: 0.7rem; font-weight: 600; margin-top: 0.5rem;
}}
.status-pill.ok  {{ background: rgba(34,197,94,0.15); color: var(--success); border: 1px solid rgba(34,197,94,0.3); }}
.status-pill.err {{ background: rgba(239,68,68,0.15);  color: var(--failure); border: 1px solid rgba(239,68,68,0.3); }}
.status-pill-dot {{ width: 6px; height: 6px; border-radius: 50%; background: currentColor; animation: pulse 2s infinite; }}
@keyframes pulse {{ 0%,100%{{opacity:1}} 50%{{opacity:0.4}} }}

.sidebar-section {{
  padding: 0.85rem 1rem 0.3rem;
  color: var(--text-3); font-size: 0.62rem; font-weight: 700;
  letter-spacing: 0.1em; text-transform: uppercase;
}}

/* ── Stats bar ──────────────────────────────────────────────────── */
.stats-bar {{ display: flex; gap: 0.75rem; padding: 1rem 1.25rem 0; }}
.stat-chip {{
  display: flex; flex-direction: column; align-items: center;
  background: var(--bg-card); border: 1px solid var(--border);
  border-radius: 10px; padding: 0.6rem 1rem; flex: 1;
}}
.stat-chip-val {{ font-size: 1.4rem; font-weight: 700; color: var(--text-1); line-height: 1; }}
.stat-chip-lbl {{ font-size: 0.65rem; color: var(--text-2); text-transform: uppercase; letter-spacing: 0.06em; margin-top: 0.2rem; }}
.stat-chip.s-ok  .stat-chip-val {{ color: var(--success); }}
.stat-chip.s-err .stat-chip-val {{ color: var(--failure); }}
.stat-chip.s-bld .stat-chip-val {{ color: var(--warning); }}

/* ── Job items ──────────────────────────────────────────────────── */
.job-item {{
  display: flex; align-items: center; gap: 0.65rem;
  padding: 0.55rem 1.25rem; cursor: pointer; transition: background 0.15s;
}}
.job-item:hover {{ background: var(--bg-hover); }}
.job-dot {{ width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }}
.job-dot.ok  {{ background: var(--success); box-shadow: 0 0 6px var(--success); }}
.job-dot.err {{ background: var(--failure); box-shadow: 0 0 6px var(--failure); }}
.job-dot.bld {{ background: var(--warning); animation: pulse 1s infinite; }}
.job-dot.unk {{ background: var(--text-3); }}
.job-item-name {{ font-size: 0.8rem; color: var(--text-1); flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}
.job-item-num  {{ font-size: 0.7rem; color: var(--text-3); flex-shrink: 0; }}

/* ── Top bar ────────────────────────────────────────────────────── */
.top-bar {{
  display: flex; align-items: center; justify-content: space-between;
  padding: 0.9rem 1.5rem; border-bottom: 1px solid var(--border);
  background: var(--bg-panel); flex-shrink: 0;
}}
.top-bar-title {{ color: var(--text-1); font-size: 1rem; font-weight: 600; }}
.top-bar-sub   {{ color: var(--text-2); font-size: 0.78rem; margin-top: 0.1rem; }}
.top-bar-right {{ display: flex; align-items: center; gap: 0.75rem; }}

/* ── Chat messages ──────────────────────────────────────────────── */
.chat-scroll {{
  flex: 1; overflow-y: auto;
  padding: 1.5rem 2rem; display: flex;
  flex-direction: column; gap: {('0.5rem' if p.compact_mode else '1rem')};
}}
.chat-scroll::-webkit-scrollbar {{ width: 4px; }}
.chat-scroll::-webkit-scrollbar-track {{ background: transparent; }}
.chat-scroll::-webkit-scrollbar-thumb {{ background: {scrollbar}; border-radius: 4px; }}

.msg-row {{ display: flex; gap: 0.75rem; max-width: {cw}%; }}
.msg-row.user {{ align-self: flex-end; flex-direction: row-reverse; }}
.msg-row.bot  {{ align-self: flex-start; }}

.msg-avatar {{
  width: 34px; height: 34px; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-size: 0.85rem; flex-shrink: 0; margin-top: 2px;
}}
.msg-avatar.bot-av  {{ background: linear-gradient(135deg, {a1}, {a2}); box-shadow: 0 0 12px color-mix(in srgb, {a1} 50%, transparent); }}
.msg-avatar.user-av {{ background: linear-gradient(135deg, #0ea5e9, #06b6d4); box-shadow: 0 0 12px rgba(6,182,212,0.4); }}

.msg-bubble {{ padding: {pad}; font-size: var(--fs-base); line-height: 1.6; max-width: 640px; }}
.msg-bubble.bot-bubble  {{
  background: var(--bg-card); border: 1px solid var(--border); color: var(--text-1);
  border-radius: {bot_br};
}}
.msg-bubble.user-bubble {{
  background: linear-gradient(135deg, {a1} 0%, {a2} 100%); color: #fff;
  border-radius: {usr_br};
  box-shadow: 0 4px 15px color-mix(in srgb, {a1} 35%, transparent);
}}
.msg-time {{ font-size: 0.65rem; color: var(--text-3); margin-top: 0.3rem; display: {'none' if not p.show_timestamps else 'block'}; }}
.msg-row.user .msg-time {{ text-align: right; }}

/* Welcome */
.chat-welcome {{
  display: flex; flex-direction: column; align-items: center;
  justify-content: center; flex: 1; gap: 1rem; padding: 3rem;
}}
.welcome-orb {{
  width: 72px; height: 72px;
  background: linear-gradient(135deg, {a1}, {a2}, #06b6d4);
  border-radius: 50%;
  display: flex; align-items: center; justify-content: center; font-size: 2rem;
  box-shadow: 0 0 40px color-mix(in srgb, {a1} 50%, transparent), 0 0 80px color-mix(in srgb, {a1} 20%, transparent);
  animation: glow 3s ease-in-out infinite;
}}
@keyframes glow {{
  0%,100%{{ box-shadow: 0 0 40px color-mix(in srgb, {a1} 50%, transparent); }}
  50%    {{ box-shadow: 0 0 60px color-mix(in srgb, {a2} 70%, transparent), 0 0 100px rgba(6,182,212,0.3); }}
}}
.welcome-title {{ color: var(--text-1); font-size: 1.3rem; font-weight: 700; }}
.welcome-sub   {{ color: var(--text-2); font-size: 0.85rem; text-align: center; max-width: 360px; }}
.welcome-chips {{ display: flex; flex-wrap: wrap; gap: 0.5rem; justify-content: center; margin-top: 0.5rem; }}
.welcome-chip {{
  background: var(--bg-card); border: 1px solid var(--border);
  border-radius: 20px; padding: 0.3rem 0.85rem;
  font-size: 0.78rem; color: var(--text-2); cursor: pointer; transition: all 0.15s;
}}
.welcome-chip:hover {{ border-color: {a1}; color: var(--text-1); }}

/* Input bar */
.input-bar {{
  padding: 1rem 1.5rem; border-top: 1px solid var(--border);
  background: var(--bg-panel); flex-shrink: 0;
}}

/* ── Sidebar nav — slim icon+label rows, NOT gradient blocks ────── */
[data-testid="stSidebar"] .stButton > button {{
  background: transparent !important;
  border: none !important;
  border-radius: 8px !important;
  color: var(--text-2) !important;
  text-align: left !important;
  padding: 0.45rem 1rem !important;
  font-size: 0.83rem !important;
  font-weight: 500 !important;
  width: 100% !important;
  box-shadow: none !important;
  transition: background 0.15s, color 0.15s !important;
  justify-content: flex-start !important;
}}
[data-testid="stSidebar"] .stButton > button:hover {{
  background: var(--bg-hover) !important;
  color: var(--text-1) !important;
  box-shadow: none !important;
  opacity: 1 !important;
}}
[data-testid="stSidebar"] .stButton > button:active {{
  background: color-mix(in srgb, var(--accent1) 18%, transparent) !important;
  color: var(--accent1) !important;
}}
[data-testid="stSidebar"] .stButton > button[kind="secondary"] {{
  color: var(--text-3) !important;
}}

/* Send button in MAIN area keeps the gradient */
[data-testid="stMain"] .stButton > button,
section.main .stButton > button {{
  background: linear-gradient(135deg, var(--accent1), var(--accent2)) !important;
  color: #fff !important;
  border-radius: 10px !important;
  font-weight: 600 !important;
}}
.stTextInput > div > div > input {{
  background: var(--bg-card) !important;
  border: 1.5px solid {border} !important;
  border-radius: 12px !important; color: var(--text-1) !important;
  font-size: var(--fs-base) !important; padding: 0.75rem 1rem !important;
  transition: border-color 0.2s, box-shadow 0.2s !important;
}}
.stTextInput > div > div > input:focus {{
  border-color: {a1} !important;
  box-shadow: 0 0 0 3px color-mix(in srgb, {a1} 20%, transparent) !important;
  outline: none !important;
}}
.stTextInput > div > div > input::placeholder {{ color: var(--text-3) !important; }}

.stButton > button {{
  background: linear-gradient(135deg, {a1}, {a2}) !important;
  color: #fff !important; border: none !important; border-radius: 10px !important;
  font-weight: 600 !important; font-size: 0.82rem !important;
  padding: 0.55rem 1.1rem !important; transition: opacity 0.2s, box-shadow 0.2s !important;
}}
.stButton > button:hover {{
  opacity: 0.9 !important;
  box-shadow: 0 4px 14px color-mix(in srgb, {a1} 45%, transparent) !important;
}}

/* Detail / cards */
.detail-card {{
  background: var(--bg-card); border: 1px solid var(--border);
  border-radius: 14px; padding: 1.25rem; margin-bottom: 0.75rem;
}}
.detail-card-title {{ color: var(--text-1); font-size: 1rem; font-weight: 600; margin-bottom: 0.75rem; }}

.badge {{
  display: inline-block; padding: 0.22rem 0.6rem; border-radius: 20px;
  font-size: 0.68rem; font-weight: 700; letter-spacing: 0.04em; text-transform: uppercase;
}}
.badge-ok  {{ background: rgba(34,197,94,0.15);  color: var(--success); }}
.badge-err {{ background: rgba(239,68,68,0.15);   color: var(--failure); }}
.badge-bld {{ background: rgba(245,158,11,0.15);  color: var(--warning); }}
.badge-unk {{ background: rgba(148,163,184,0.1);  color: var(--text-2); }}

.log-box {{
  background: {log_bg}; border: 1px solid var(--border); border-radius: 8px;
  padding: 0.75rem;
  font-family: 'JetBrains Mono', 'Fira Code', monospace;
  font-size: 0.72rem; color: {log_color}; max-height: 200px;
  overflow-y: auto; white-space: pre-wrap; line-height: 1.5;
}}
.log-box::-webkit-scrollbar {{ width: 3px; }}
.log-box::-webkit-scrollbar-thumb {{ background: rgba(74,222,128,0.3); border-radius: 3px; }}

.sug-item {{
  display: flex; align-items: flex-start; gap: 0.5rem;
  padding: 0.45rem 0.65rem;
  background: color-mix(in srgb, {a2} 8%, transparent);
  border-left: 2px solid {a2}; border-radius: 0 6px 6px 0;
  margin: 0.3rem 0; color: #a5b4fc; font-size: 0.8rem;
}}
.sec-lbl {{
  color: var(--text-3); font-size: 0.68rem; font-weight: 700;
  letter-spacing: 0.08em; text-transform: uppercase; margin: 0.85rem 0 0.4rem;
}}
.hist-row {{
  display: flex; align-items: center; gap: 0.65rem;
  padding: 0.4rem 0; border-bottom: 1px solid var(--border);
  font-size: 0.8rem; color: var(--text-2);
}}
.hist-row:last-child {{ border-bottom: none; }}
.divider {{ border: none; border-top: 1px solid var(--border); margin: 0.5rem 0; }}

[data-testid="stForm"] {{ background: transparent !important; border: none !important; padding: 0 !important; }}
[data-testid="stDecoration"] {{ display: none; }}

/* ── Hide Streamlit theme switcher ──────────────────────────────── */
[data-testid="stToolbar"], [data-testid="stToolbarActions"],
button[title="View app in fullscreen"],
button[aria-label="Toggle dark mode"], button[aria-label="Toggle light mode"],
[data-testid="baseButton-headerNoPadding"],
header[data-testid="stHeader"] {{ display: none !important; }}

/* ── Ensure sidebar is always visible ───────────────────────────── */
[data-testid="stSidebar"] {{
  display: flex !important;
  visibility: visible !important;
  opacity: 1 !important;
  transform: none !important;
  min-width: 280px !important;
}}
[data-testid="stSidebar"] > div {{
  display: flex !important;
  flex-direction: column !important;
  visibility: visible !important;
}}
[data-testid="stSidebarCollapsedControl"] {{
  display: none !important;
}}
section[data-testid="stSidebar"] {{
  width: 320px !important;
  min-width: 280px !important;
}}

/* ── History view ───────────────────────────────────────────────── */
.hist-page-card {{
  background: var(--bg-card); border: 1px solid var(--border);
  border-radius: 12px; padding: 1rem 1.25rem; margin-bottom: 0.6rem;
}}
.hist-page-card-title {{
  color: var(--text-1); font-size: 0.9rem; font-weight: 600; margin-bottom: 0.6rem;
  display: flex; align-items: center; gap: 0.5rem;
}}
.hist-table-row {{
  display: grid;
  grid-template-columns: 2rem 3.5rem 1fr 5rem 5rem 4.5rem;
  align-items: center; gap: 0.5rem; padding: 0.45rem 0;
  border-bottom: 1px solid var(--border); font-size: 0.8rem; color: var(--text-2);
}}
.hist-table-row.header {{
  color: var(--text-3); font-size: 0.65rem; font-weight: 700;
  text-transform: uppercase; letter-spacing: 0.06em;
  border-bottom: 1px solid var(--border);
}}
.hist-table-row:last-child {{ border-bottom: none; }}
.hist-dur {{ color: var(--text-3); font-size: 0.72rem; }}
.hist-date {{ color: var(--text-3); font-size: 0.72rem; }}

/* ── History build card rows ────────────────────────────────────── */
.hist-build-row {{
  display: flex; align-items: center; justify-content: space-between;
  gap: 1rem;
  padding: 0.65rem 0.85rem;
  border-radius: 8px;
  border-left: 3px solid transparent;
  background: var(--bg-deep);
  margin-bottom: 0.4rem;
  transition: background 0.15s;
}}
.hist-build-row:hover {{ background: var(--bg-hover); }}
.hist-build-main {{
  display: flex; align-items: center; gap: 0.75rem; flex: 1; min-width: 0;
}}
.hist-build-icon {{ font-size: 1.1rem; flex-shrink: 0; }}
.hist-build-info {{ flex: 1; min-width: 0; }}
.hist-build-title {{
  display: flex; align-items: center; gap: 0.4rem;
  font-size: 0.88rem; white-space: nowrap;
}}
.hist-build-meta {{
  display: flex; align-items: center; gap: 0.5rem;
  font-size: 0.75rem; color: var(--text-2); margin-top: 0.2rem;
}}
.hist-sep {{ color: var(--text-3); }}
.hist-build-links {{
  display: flex; gap: 0.4rem; flex-shrink: 0;
}}

/* ── Customize panel ────────────────────────────────────────────── */
.cust-section {{
  padding: 0.75rem 1.25rem 0.25rem;
  color: var(--text-3); font-size: 0.62rem; font-weight: 700;
  letter-spacing: 0.08em; text-transform: uppercase;
  border-top: 1px solid var(--border); margin-top: 0.5rem;
}}
.cust-row {{
  display: flex; align-items: center; justify-content: space-between;
  padding: 0.35rem 1.25rem; font-size: 0.8rem; color: var(--text-2);
}}
.theme-toggle {{
  display: flex; gap: 0.4rem; align-items: center;
}}
.theme-btn {{
  display: inline-flex; align-items: center; gap: 0.3rem;
  padding: 0.3rem 0.75rem; border-radius: 8px; cursor: pointer;
  font-size: 0.75rem; font-weight: 600; border: 1px solid var(--border);
  background: var(--bg-card); color: var(--text-2); transition: all 0.15s;
}}
.theme-btn.active {{
  background: linear-gradient(135deg, {a1}, {a2}); color: #fff; border-color: {a1};
}}

/* ── Jenkins links ──────────────────────────────────────────────── */
a.jk-link {{
  color: var(--accent3); text-decoration: none; font-weight: 500;
  border-bottom: 1px dashed rgba(6,182,212,0.4); transition: color 0.15s, border-color 0.15s;
}}
a.jk-link:hover {{ color: #67e8f9; border-bottom-color: #67e8f9; }}
a.jk-link-btn {{
  display: inline-flex; align-items: center; gap: 0.35rem;
  background: rgba(6,182,212,0.1); border: 1px solid rgba(6,182,212,0.3);
  border-radius: 6px; padding: 0.25rem 0.65rem;
  color: var(--accent3); font-size: 0.72rem; font-weight: 600;
  text-decoration: none; transition: background 0.15s; white-space: nowrap;
}}
a.jk-link-btn:hover {{ background: rgba(6,182,212,0.2); color: #67e8f9; }}
a.jk-link-pill {{
  display: inline-flex; align-items: center; gap: 0.3rem;
  padding: 0.18rem 0.55rem; border-radius: 12px;
  background: color-mix(in srgb, {a1} 15%, transparent);
  border: 1px solid color-mix(in srgb, {a1} 30%, transparent);
  color: #c4b5fd; font-size: 0.68rem; font-weight: 600; text-decoration: none;
  transition: background 0.15s;
}}
a.jk-link-pill:hover {{ background: color-mix(in srgb, {a1} 30%, transparent); }}

/* Streamlit select/slider labels in customize panel */
.stSelectbox label, .stSlider label, .stCheckbox label {{
  color: var(--text-2) !important; font-size: 0.78rem !important;
}}
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
#  SERVICES
# ─────────────────────────────────────────────────────────────────────────────
@st.cache_resource
def init_services():
    try:
        llm          = LLMService()
        jenkins      = JenkinsService()
        notifications = NotificationService()
        artifacts    = ArtifactService()
        github       = GitHubService()
        conversation = ConversationManager()
        processor    = RequestProcessor(
            llm_service=llm,
            jenkins_service=jenkins,
            notification_service=notifications,
            artifact_service=artifacts,
            conversation=conversation,
            github_service=github
        )
        return processor, jenkins
    except Exception as e:
        logger.error(f"Init error: {e}")
        return None, None


# ─────────────────────────────────────────────────────────────────────────────
#  HELPERS
# ─────────────────────────────────────────────────────────────────────────────
def _now() -> str:
    return datetime.now().strftime("%H:%M")


# ── Jenkins URL helpers ───────────────────────────────────────────────────────
def _jk_base() -> str:
    return settings.jenkins.url.rstrip("/")

def _jk_job_url(job_name: str) -> str:
    return f"{_jk_base()}/job/{job_name}"

def _jk_build_url(job_name: str, build_num) -> str:
    return f"{_jk_base()}/job/{job_name}/{build_num}"

def _jk_console_url(job_name: str, build_num) -> str:
    return f"{_jk_base()}/job/{job_name}/{build_num}/console"

def _jk_artifact_url(job_name: str, build_num, rel_path: str) -> str:
    return f"{_jk_base()}/job/{job_name}/{build_num}/artifact/{rel_path}"

def _link(href: str, label: str, cls: str = "jk-link") -> str:
    """Render a styled anchor that opens Jenkins in a new tab."""
    return f'<a href="{href}" target="_blank" class="{cls}">{label}</a>'


def _job_dot_class(color: str) -> str:
    if not color:
        return "unk"
    if "anime" in color:
        return "bld"
    if "blue" in color or "green" in color:
        return "ok"
    if "red" in color:
        return "err"
    return "unk"


def _badge(color: str) -> str:
    dc = _job_dot_class(color)
    labels = {"ok": "Success", "err": "Failed", "bld": "Building", "unk": "Unknown"}
    classes = {"ok": "badge-ok", "err": "badge-err", "bld": "badge-bld", "unk": "badge-unk"}
    return f'<span class="badge {classes[dc]}">{labels[dc]}</span>'


def _result_badge(result: str) -> str:
    r = (result or "UNKNOWN").upper()
    cls = "badge-ok" if r == "SUCCESS" else "badge-err" if r == "FAILURE" else "badge-bld" if r in ("BUILDING","QUEUED") else "badge-unk"
    return f'<span class="badge {cls}">{r}</span>'


def _enrich_response(text: str) -> str:
    """
    Post-process processor response text to inject clickable Jenkins links.
    Looks for patterns like:
      - **Build #N** → links to the build page
      - job names followed by #N → links to build
      - Artifact paths → links to artifact URL
    Works on the raw markdown-ish string that Streamlit renders as HTML via
    unsafe_allow_html, so we inject <a> tags directly.
    """
    import re

    base = _jk_base()

    # Pattern: "**Build #42**" or "Build #42" — we need a job context
    # We do a two-pass: first find job+build combos, then plain build refs
    # Pattern: job_name #N  (from list jobs output: **JobName** - ... (#N))
    def replace_job_build(m):
        job  = m.group(1)
        num  = m.group(2)
        url  = f"{base}/job/{job}/{num}"
        curl = f"{base}/job/{job}/{num}/console"
        return (
            f'<b><a href="{url}" target="_blank" class="jk-link">{job} #{num}</a></b>'
            f' <a href="{curl}" target="_blank" class="jk-link-btn">log</a>'
        )

    # Match "**JobName #N**" patterns
    text = re.sub(
        r'\*\*([A-Za-z0-9_\-\.]+)\s+#(\d+)\*\*',
        replace_job_build,
        text
    )

    # Pattern: standalone "**Build #N**" (detail view context — job stored in session)
    def replace_build_ref(m):
        num  = m.group(1)
        # We can't get job_name here reliably, so just link to Jenkins base + hint
        return f'<b>Build #{num}</b>'

    text = re.sub(r'\*\*Build #(\d+)\*\*', replace_build_ref, text)

    # Pattern: "• ✅ **#N** - SUCCESS" from history output
    # We need job context — skip deep replacement here, it's safe already in detail view

    # Pattern: http(s):// links already in text — make them clickable
    def replace_url(m):
        url = m.group(0)
        label = url.replace("http://", "").replace("https://", "")[:40]
        return f'<a href="{url}" target="_blank" class="jk-link">{label}</a>'

    text = re.sub(r'https?://[^\s<>"\']+', replace_url, text)

    # Pattern: job names in "• emoji **JobName**" list format from list_jobs
    def replace_job_name(m):
        emoji = m.group(1)
        job   = m.group(2)
        rest  = m.group(3)
        url   = f"{base}/job/{job}"
        return f'{emoji} <b><a href="{url}" target="_blank" class="jk-link">{job}</a></b>{rest}'

    text = re.sub(
        r'([\u2705\u274c\u26a0\ufe0f\u23f8\ufe0f\u23f9\ufe0f\U0001f534\U0001f7e0\u2753\u2757]+)\s+\*\*([A-Za-z0-9_\-\.]+)\*\*([^<\n]*)',
        replace_job_name,
        text
    )

    return text


def analyze_build(console: str, result: str) -> dict:
    out = console.lower()
    base = {
        "category": "Build Complete" if result == "SUCCESS" else "Build Issue",
        "icon": "✅" if result == "SUCCESS" else "❌" if result == "FAILURE" else "❓",
        "reason": "Completed successfully" if result == "SUCCESS" else "Build failed",
        "suggestions": [],
        "errors": []
    }
    if result == "SUCCESS":
        base["suggestions"] = ["View artifacts", "Deploy to staging"]
        return base
    # Extract error lines
    for line in console.split("\n"):
        if any(x in line.lower() for x in ["error", "fail", "exception", "fatal"]) and len(line.strip()) > 10:
            base["errors"].append(line.strip()[:120])
    base["errors"] = base["errors"][:5]
    # Categorise
    if any(x in out for x in ["compilation failed", "compile error", "syntax error"]):
        base.update({"category":"Compilation Error","icon":"🔴","reason":"Code failed to compile",
                     "suggestions":["Fix syntax errors","Check imports","Run local build"]})
    elif any(x in out for x in ["test failed","tests failed","assertionerror"]):
        base.update({"category":"Test Failure","icon":"🧪","reason":"Unit/integration tests failed",
                     "suggestions":["Review test output","Run tests locally","Check recent changes"]})
    elif any(x in out for x in ["dependency","module not found","package not found"]):
        base.update({"category":"Dependency Error","icon":"📦","reason":"Missing or broken dependency",
                     "suggestions":["Check requirements","Reinstall packages"]})
    elif any(x in out for x in ["timeout","timed out"]):
        base.update({"category":"Timeout","icon":"⏱️","reason":"Build exceeded time limit",
                     "suggestions":["Optimise build steps","Increase timeout setting"]})
    elif any(x in out for x in ["permission denied","access denied","403"]):
        base.update({"category":"Permission Error","icon":"🔒","reason":"Access denied",
                     "suggestions":["Check credentials","Verify repo permissions"]})
    else:
        base["suggestions"] = ["Review full console log","Check recent commits"]
    return base


# ─────────────────────────────────────────────────────────────────────────────
#  SESSION STATE
# ─────────────────────────────────────────────────────────────────────────────
def init_state():
    defaults = {
        "messages":    [],
        "pending_cmd": None,
        "selected_job": None,
        "view":        "chat",   # "chat" | "detail" | "history" | "customize"
        "jenkins_ok":  None,
        "llm_ok":      None,      # LLM connection status
        "llm_status_msg": "Not checked",
        # ── Theme / customize prefs ───────────────────────────────────────
        "theme_mode":     "dark",           # "dark" | "light"
        "accent_color":   "#7c3aed",        # hex
        "accent2_color":  "#4f46e5",
        "font_size":      14,               # px  (12–20)
        "bubble_style":   "rounded",        # "rounded" | "sharp" | "pill"
        "bot_avatar":     "🤖",
        "user_avatar":    "👤",
        "chat_width":     75,               # % of available width (40–100)
        "show_timestamps": True,
        "compact_mode":   False,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


# ─────────────────────────────────────────────────────────────────────────────
#  CUSTOMIZE PANEL
# ─────────────────────────────────────────────────────────────────────────────
def render_customize_panel():
    p = st.session_state

    col_back, col_title = st.columns([1, 7])
    with col_back:
        if st.button("← Back", key="cust_back"):
            p.view = "chat"
            st.rerun()
    with col_title:
        st.markdown("""
        <div class="top-bar" style="border-bottom:none; padding:0.5rem 0;">
          <div>
            <div class="top-bar-title">🎨 Customize</div>
            <div class="top-bar-sub">Theme, chat appearance, and display preferences</div>
          </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown('<hr class="divider">', unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    with col1:
        # ── Appearance ────────────────────────────────────────────────────
        st.markdown("### 🌗 Theme Mode")
        tm_cols = st.columns(2)
        with tm_cols[0]:
            if st.button(
                "🌙  Dark" + (" ✓" if p.theme_mode == "dark" else ""),
                key="btn_dark", use_container_width=True
            ):
                p.theme_mode = "dark"
                st.rerun()
        with tm_cols[1]:
            if st.button(
                "☀️  Light" + (" ✓" if p.theme_mode == "light" else ""),
                key="btn_light", use_container_width=True
            ):
                p.theme_mode = "light"
                st.rerun()

        st.markdown("---")
        st.markdown("### 🎨 Accent Color")

        # Preset swatches
        presets = [
            ("Violet",  "#7c3aed", "#4f46e5"),
            ("Blue",    "#2563eb", "#1d4ed8"),
            ("Teal",    "#0d9488", "#0891b2"),
            ("Rose",    "#e11d48", "#be123c"),
            ("Orange",  "#ea580c", "#c2410c"),
            ("Green",   "#16a34a", "#15803d"),
        ]
        sw_cols = st.columns(6)
        for i, (name, c1, c2) in enumerate(presets):
            with sw_cols[i]:
                active = "✓" if p.accent_color == c1 else ""
                st.markdown(
                    f'<div title="{name}" style="width:28px;height:28px;border-radius:50%;'
                    f'background:linear-gradient(135deg,{c1},{c2});margin:auto;'
                    f'border:2px solid {"white" if active else "transparent"};cursor:pointer;"></div>',
                    unsafe_allow_html=True
                )
                if st.button(active or "·", key=f"sw_{name}", use_container_width=True,
                             help=name):
                    p.accent_color  = c1
                    p.accent2_color = c2
                    st.rerun()

        # Custom hex
        custom_c = st.color_picker(
            "Custom primary color", value=p.accent_color, key="cust_color1"
        )
        if custom_c != p.accent_color:
            p.accent_color = custom_c
            st.rerun()

        st.markdown("---")
        st.markdown("### 🔤 Font Size")
        new_fs = st.slider(
            "Font size (px)", min_value=11, max_value=20,
            value=p.font_size, key="cust_fs"
        )
        if new_fs != p.font_size:
            p.font_size = new_fs
            st.rerun()

    with col2:
        # ── Chat options ──────────────────────────────────────────────────
        st.markdown("### 💬 Chat Bubbles")

        new_bs = st.selectbox(
            "Bubble style",
            options=["rounded", "sharp", "pill"],
            index=["rounded", "sharp", "pill"].index(p.bubble_style),
            key="cust_bubble"
        )
        if new_bs != p.bubble_style:
            p.bubble_style = new_bs
            st.rerun()

        new_cw = st.slider(
            "Max chat width (%)", min_value=40, max_value=100,
            value=p.chat_width, step=5, key="cust_cw"
        )
        if new_cw != p.chat_width:
            p.chat_width = new_cw
            st.rerun()

        st.markdown("---")
        st.markdown("### 🧑 Avatars")

        avatar_options_bot  = ["🤖","⚙️","🔧","🛠️","🦾","💡","🚀"]
        avatar_options_user = ["👤","🧑","👨‍💻","👩‍💻","🦊","🐱","🐼"]

        new_bot = st.selectbox(
            "Bot avatar", avatar_options_bot,
            index=avatar_options_bot.index(p.bot_avatar) if p.bot_avatar in avatar_options_bot else 0,
            key="cust_bot_av"
        )
        if new_bot != p.bot_avatar:
            p.bot_avatar = new_bot
            st.rerun()

        new_user = st.selectbox(
            "Your avatar", avatar_options_user,
            index=avatar_options_user.index(p.user_avatar) if p.user_avatar in avatar_options_user else 0,
            key="cust_user_av"
        )
        if new_user != p.user_avatar:
            p.user_avatar = new_user
            st.rerun()

        st.markdown("---")
        st.markdown("### ⚙️ Display")

        new_ts = st.checkbox(
            "Show message timestamps", value=p.show_timestamps, key="cust_ts"
        )
        if new_ts != p.show_timestamps:
            p.show_timestamps = new_ts
            st.rerun()

        new_cm = st.checkbox(
            "Compact mode (tighter spacing)", value=p.compact_mode, key="cust_cm"
        )
        if new_cm != p.compact_mode:
            p.compact_mode = new_cm
            st.rerun()

    st.markdown("---")
    # Reset button
    if st.button("↺  Reset to defaults", key="cust_reset"):
        for k in ["theme_mode","accent_color","accent2_color","font_size",
                  "bubble_style","bot_avatar","user_avatar","chat_width",
                  "show_timestamps","compact_mode"]:
            del st.session_state[k]
        st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
#  SIDEBAR
# ─────────────────────────────────────────────────────────────────────────────
def render_sidebar(jenkins):
    with st.sidebar:
        # ── Logo ──────────────────────────────────────────────────────────
        jenkins_ok = st.session_state.jenkins_ok
        llm_ok     = st.session_state.get("llm_ok", None)

        # Determine overall status
        if jenkins_ok and llm_ok:
            pill_cls = "ok"
            pill_txt = "All Systems Online"
        elif jenkins_ok is False or llm_ok is False:
            pill_cls = "err"
            pill_txt = "Service Issue"
        else:
            pill_cls = "ok" if jenkins_ok else "err"
            pill_txt = "Checking..."

        st.markdown(f"""
        <div class="sidebar-logo">
          <div class="sidebar-logo-icon">🔧</div>
          <div class="sidebar-logo-title">Jenkins Build Bot</div>
          <div class="sidebar-logo-sub">AI-Powered DevOps Assistant</div>
          <div class="status-pill {pill_cls}">
            <span class="status-pill-dot"></span>{pill_txt}
          </div>
        </div>
        """, unsafe_allow_html=True)

        # ── Connection Status Detail ──────────────────────────────────────
        jk_icon = "🟢" if jenkins_ok else "🔴" if jenkins_ok is False else "⏳"
        llm_icon = "🟢" if llm_ok else "🔴" if llm_ok is False else "⏳"
        llm_msg = st.session_state.get("llm_status_msg", "Not checked")
        
        st.markdown(f"""
        <div style="padding:0.5rem 1.25rem;font-size:0.72rem;color:var(--text-2);">
          <div style="display:flex;align-items:center;gap:0.4rem;margin-bottom:0.3rem;">
            {jk_icon} <span>Jenkins: {'Connected' if jenkins_ok else 'Offline' if jenkins_ok is False else 'Checking...'}</span>
          </div>
          <div style="display:flex;align-items:center;gap:0.4rem;">
            {llm_icon} <span>LLM: {llm_msg[:40]}</span>
          </div>
        </div>
        """, unsafe_allow_html=True)

        # ── Stats ─────────────────────────────────────────────────────────
        try:
            jobs     = jenkins.list_jobs()
            total    = len(jobs)
            success  = sum(1 for j in jobs if j.color and ("blue" in j.color or "green" in j.color) and "anime" not in j.color)
            failed   = sum(1 for j in jobs if j.color and "red" in j.color and "anime" not in j.color)
            building = sum(1 for j in jobs if j.color and "anime" in j.color)
            st.session_state.jenkins_ok = True
        except Exception:
            jobs = []
            total = success = failed = building = 0
            st.session_state.jenkins_ok = False

        st.markdown(f"""
        <div class="stats-bar">
          <div class="stat-chip">
            <div class="stat-chip-val">{total}</div>
            <div class="stat-chip-lbl">Total</div>
          </div>
          <div class="stat-chip s-ok">
            <div class="stat-chip-val">{success}</div>
            <div class="stat-chip-lbl">Passing</div>
          </div>
          <div class="stat-chip s-err">
            <div class="stat-chip-val">{failed}</div>
            <div class="stat-chip-lbl">Failed</div>
          </div>
          <div class="stat-chip s-bld">
            <div class="stat-chip-val">{building}</div>
            <div class="stat-chip-lbl">Building</div>
          </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("---")

        # ── Nav ───────────────────────────────────────────────────────────
        st.markdown('<div class="sidebar-section">Navigation</div>', unsafe_allow_html=True)
        if st.button("💬  Chat", key="nav_chat", use_container_width=True):
            st.session_state.view = "chat"
            st.session_state.selected_job = None
            st.rerun()
        if st.button("📋  All Jobs", key="nav_jobs", use_container_width=True):
            st.session_state.pending_cmd = "list jobs"
            st.session_state.view = "chat"
            st.rerun()
        if st.button("📊  Build History", key="nav_history", use_container_width=True):
            st.session_state.view = "history"
            st.session_state.selected_job = None
            st.rerun()
        if st.button("🔄  Rebuild Last", key="nav_rebuild", use_container_width=True):
            st.session_state.pending_cmd = "rebuild"
            st.session_state.view = "chat"
            st.rerun()
        if st.button("❓  Help", key="nav_help", use_container_width=True):
            st.session_state.pending_cmd = "help"
            st.session_state.view = "chat"
            st.rerun()

        # ── Settings / theme ──────────────────────────────────────────────
        st.markdown('<div class="sidebar-section">Settings</div>', unsafe_allow_html=True)

        # Dark / Light one-click toggle
        mode_label = "☀️  Light Mode" if st.session_state.theme_mode == "dark" else "🌙  Dark Mode"
        if st.button(mode_label, key="nav_toggle_theme", use_container_width=True):
            st.session_state.theme_mode = "light" if st.session_state.theme_mode == "dark" else "dark"
            st.rerun()

        if st.button("🎨  Customize", key="nav_customize", use_container_width=True):
            st.session_state.view = "customize"
            st.session_state.selected_job = None
            st.rerun()

        # ── Job list ──────────────────────────────────────────────────────
        if jobs:
            st.markdown('<div class="sidebar-section">Live Jobs</div>', unsafe_allow_html=True)
            for job in jobs[:15]:
                dc  = _job_dot_class(job.color or "")
                num = f"#{job.last_build_number}" if job.last_build_number else "—"
                job_url   = _jk_job_url(job.name)
                build_url = _jk_build_url(job.name, job.last_build_number) if job.last_build_number else job_url
                col_a, col_b = st.columns([5, 1])
                with col_a:
                    st.markdown(f"""
                    <div class="job-item">
                      <div class="job-dot {dc}"></div>
                      <a href="{job_url}" target="_blank" class="job-item-name" style="
                        color:var(--text-1);text-decoration:none;
                        border-bottom:1px dashed rgba(255,255,255,0.15);"
                        title="Open {job.name} in Jenkins"
                      >{job.name}</a>
                      <a href="{build_url}" target="_blank" class="job-item-num" style="
                        color:var(--text-3);text-decoration:none;font-size:0.7rem;"
                        title="Open build {num} in Jenkins"
                      >{num}</a>
                    </div>
                    """, unsafe_allow_html=True)
                with col_b:
                    if st.button("▶", key=f"sel_{job.name}", help=f"View {job.name} details"):
                        st.session_state.selected_job = job.name
                        st.session_state.view = "detail"
                        st.rerun()

        # ── Bottom ────────────────────────────────────────────────────────
        st.markdown("---")
        
        # Check connections button
        if st.button("🔄  Check Connections", key="check_conn", use_container_width=True):
            # Check LLM
            try:
                from services.llm_service import LLMService
                llm = LLMService()
                llm_ok, llm_msg = llm.test_connection()
                st.session_state.llm_ok = llm_ok
                st.session_state.llm_status_msg = "Connected ✓" if llm_ok else llm_msg[:35]
            except Exception as e:
                st.session_state.llm_ok = False
                st.session_state.llm_status_msg = f"Error: {str(e)[:30]}"
            
            # Check Jenkins (already done above via list_jobs)
            try:
                jenkins.test_connection()
                st.session_state.jenkins_ok = True
            except Exception:
                st.session_state.jenkins_ok = False
            
            st.rerun()
        
        if st.button("🗑️  Clear Chat", key="clr", use_container_width=True):
            st.session_state.messages = []
            st.rerun()
        st.markdown(
            f'<div style="padding:0.75rem 1.25rem;font-size:0.7rem;">'
            f'<a href="{settings.jenkins.url}" target="_blank" class="jk-link">'
            f'🔗 {settings.jenkins.url}</a></div>',
            unsafe_allow_html=True
        )


# ─────────────────────────────────────────────────────────────────────────────
#  CHAT VIEW
# ─────────────────────────────────────────────────────────────────────────────
def render_chat_view(processor):
    # ── Top bar ───────────────────────────────────────────────────────────
    st.markdown("""
    <div class="top-bar">
      <div>
        <div class="top-bar-title">🤖 AI Build Assistant</div>
        <div class="top-bar-sub">Natural language • Jenkins control • Failure analysis</div>
      </div>
      <div class="top-bar-right">
        <span style="color:var(--text-3);font-size:0.75rem;">Powered by Exterro Qwen3</span>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Messages ──────────────────────────────────────────────────────────
    if not st.session_state.messages:
        # Welcome screen
        st.markdown(f"""
        <div class="chat-welcome">
          <div class="welcome-orb">{st.session_state.get('bot_avatar','🔧')}</div>
          <div class="welcome-title">Jenkins Build Bot</div>
          <div class="welcome-sub">
            Ask me anything about your Jenkins jobs — trigger builds,
            check status, analyse failures, view history.
          </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        # Message bubbles
        chat_html = '<div class="chat-scroll" id="chat-bottom">'
        bot_av  = st.session_state.get("bot_avatar",  "🤖")
        user_av = st.session_state.get("user_avatar", "👤")
        for msg in st.session_state.messages:
            role = msg["role"]
            content = str(msg["content"]).replace("\n", "<br>").replace("`", "&#96;")
            time_str = msg.get("time", "")
            if role == "user":
                chat_html += f"""
                <div class="msg-row user">
                  <div class="msg-avatar user-av">{user_av}</div>
                  <div>
                    <div class="msg-bubble user-bubble">{content}</div>
                    <div class="msg-time">{time_str}</div>
                  </div>
                </div>"""
            else:
                chat_html += f"""
                <div class="msg-row bot">
                  <div class="msg-avatar bot-av">{bot_av}</div>
                  <div>
                    <div class="msg-bubble bot-bubble">{content}</div>
                    <div class="msg-time">{time_str}</div>
                  </div>
                </div>"""
        chat_html += '</div>'
        st.markdown(chat_html, unsafe_allow_html=True)
        # Auto-scroll JS
        st.markdown("""
        <script>
          const el = document.getElementById('chat-bottom');
          if (el) el.scrollTop = el.scrollHeight;
        </script>
        """, unsafe_allow_html=True)

    # ── Input bar ─────────────────────────────────────────────────────────
    st.markdown('<div class="input-bar">', unsafe_allow_html=True)

    with st.form(key="chat_form", clear_on_submit=True):
        col_in, col_btn = st.columns([7, 1])
        with col_in:
            user_input = st.text_input(
                "msg",
                placeholder="Ask me anything… e.g. 'build HOT_fix_job from main'",
                label_visibility="collapsed",
                key="chat_input_field"
            )
        with col_btn:
            submitted = st.form_submit_button("Send ➤", use_container_width=True)

    # ── Handle pending / submitted ────────────────────────────────────────
    if st.session_state.pending_cmd:
        user_input = st.session_state.pending_cmd
        st.session_state.pending_cmd = None
        submitted = True

    if submitted and user_input and user_input.strip():
        cmd = user_input.strip()
        st.session_state.messages.append({"role": "user", "content": cmd, "time": _now()})
        status_holder = st.empty()
        try:
            def _status(t):
                status_holder.markdown(
                    f'<div style="color:var(--text-2);font-size:0.8rem;padding:0.25rem 0;">⏳ {t}</div>',
                    unsafe_allow_html=True
                )
            response = processor.process_message(cmd, status_callback=_status)
        except Exception as e:
            response = f"❌ Error: {e}\n\nTry `help` for available commands."
        status_holder.empty()
        # Enrich response with Jenkins hyperlinks
        response = _enrich_response(response)
        st.session_state.messages.append({"role": "assistant", "content": response, "time": _now()})
        st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
#  HISTORY VIEW  — all jobs × recent builds, each row links to Jenkins
# ─────────────────────────────────────────────────────────────────────────────
def render_history_view(jenkins):
    # Top bar
    col_back, col_title = st.columns([1, 7])
    with col_back:
        if st.button("← Back", key="hist_back"):
            st.session_state.view = "chat"
            st.rerun()
    with col_title:
        st.markdown("""
        <div class="top-bar" style="border-bottom:none; padding:0.5rem 0;">
          <div>
            <div class="top-bar-title">📊 Build History</div>
            <div class="top-bar-sub">Recent builds across all jobs — click any build to open in Jenkins</div>
          </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown('<hr class="divider">', unsafe_allow_html=True)

    # Job selector
    try:
        all_jobs = jenkins.list_jobs()
    except Exception as e:
        st.error(f"Could not load jobs: {e}")
        return

    if not all_jobs:
        st.info("No jobs found in Jenkins.")
        return

    job_names = [j.name for j in all_jobs]

    col_sel, col_lim, col_ref = st.columns([4, 2, 1])
    with col_sel:
        selected_jobs = st.multiselect(
            "Jobs to show",
            options=job_names,
            default=job_names[:5],          # show first 5 by default
            label_visibility="collapsed",
            placeholder="Select jobs…",
            key="hist_job_select"
        )
    with col_lim:
        limit = st.selectbox(
            "Builds per job",
            options=[5, 10, 20, 50],
            index=1,
            label_visibility="collapsed",
            key="hist_limit"
        )
    with col_ref:
        if st.button("🔄", key="hist_refresh", help="Refresh", use_container_width=True):
            st.rerun()

    if not selected_jobs:
        st.info("Select at least one job above.")
        return

    # Render one card per job
    for job_name in selected_jobs:
        job_url = _jk_job_url(job_name)

        # find color for the job dot
        dot_cls = "unk"
        for j in all_jobs:
            if j.name == job_name:
                dot_cls = _job_dot_class(j.color or "")
                break

        try:
            history = jenkins.get_build_history(job_name, limit=limit)
        except Exception as e:
            st.markdown(
                f'<div class="hist-page-card">'
                f'<div class="hist-page-card-title">'
                f'<div class="job-dot {dot_cls}" style="width:9px;height:9px;border-radius:50%;flex-shrink:0;"></div>'
                f'{_link(job_url, job_name, "jk-link")}'
                f'</div>'
                f'<span style="color:var(--failure);font-size:0.8rem;">Error: {e}</span>'
                f'</div>',
                unsafe_allow_html=True
            )
            continue

        # ── Pass rate (needed for header) ─────────────────────────────────
        total_done = len([b for b in history if b.get("result") in ("SUCCESS","FAILURE","UNSTABLE")])
        total_ok   = len([b for b in history if b.get("result") == "SUCCESS"])
        rate       = f"{round(total_ok/total_done*100)}%" if total_done else "—"
        rate_color = "var(--success)" if total_done and total_ok/total_done >= 0.8 else \
                     "var(--warning)" if total_done and total_ok/total_done >= 0.5 else \
                     "var(--failure)"

        # ── Render job header card ────────────────────────────────────────
        dot_bg  = 'var(--success)' if dot_cls=='ok' else 'var(--failure)' if dot_cls=='err' else 'var(--warning)' if dot_cls=='bld' else 'var(--text-3)'
        dot_sh  = '0 0 5px var(--success)' if dot_cls=='ok' else '0 0 5px var(--failure)' if dot_cls=='err' else 'none'

        st.markdown(f"""
        <div class="hist-page-card">
          <div class="hist-page-card-title">
            <div style="width:9px;height:9px;border-radius:50%;flex-shrink:0;
              background:{dot_bg};box-shadow:{dot_sh};"></div>
            {_link(job_url, job_name, 'jk-link')}
            <span style="margin-left:auto;font-size:0.72rem;color:var(--text-3);font-weight:400;">
              Pass rate: <span style="color:{rate_color};font-weight:700;">{rate}</span>
              &nbsp;({total_ok}/{total_done} builds)
            </span>
          </div>
        </div>
        """, unsafe_allow_html=True)

        # ── Render each build as its own st.markdown call ─────────────────
        if not history:
            st.markdown('<div style="color:var(--text-3);font-size:0.8rem;padding:0.4rem 1rem;">No builds found.</div>', unsafe_allow_html=True)
        for b in history:
            bn  = b.get("number", "?")
            br  = b.get("result") or "RUNNING"
            bd  = b.get("duration", 0)
            bdt = b.get("datetime")

            bi   = "✅" if br == "SUCCESS" else "❌" if br == "FAILURE" else "⚠️" if br == "UNSTABLE" else "🔄"
            bcls = "badge-ok" if br == "SUCCESS" else "badge-err" if br == "FAILURE" else "badge-bld"
            row_accent = "#22c55e" if br=="SUCCESS" else "#ef4444" if br=="FAILURE" else "#f59e0b"

            # Duration
            ts = (bd or 0) // 1000
            if ts <= 0:        dur_str = "—"
            elif ts < 60:      dur_str = f"{ts} sec"
            elif ts < 3600:    m,s = divmod(ts,60); dur_str = f"{m} min {s} sec" if s else f"{m} min"
            else:              h,r = divmod(ts,3600); m=r//60; dur_str = f"{h} hr {m} min" if m else f"{h} hr"

            # Time ago
            if bdt:
                secs_ago = int((datetime.now() - bdt).total_seconds())
                if   secs_ago < 60:      ago = "just now"
                elif secs_ago < 3600:    m2=secs_ago//60; ago = f"{m2} minutes ago" if m2>1 else "1 minute ago"
                elif secs_ago < 86400:   h2=secs_ago//3600; ago = f"{h2} hours ago" if h2>1 else "1 hour ago"
                elif secs_ago < 172800:  ago = f"Yesterday at {bdt.strftime('%H:%M')}"
                elif secs_ago < 604800:  ago = f"{secs_ago//86400} days ago"
                else:                    ago = bdt.strftime("%d %b %Y")
                exact = bdt.strftime("%A, %d %b %Y at %H:%M:%S")
            else:
                ago, exact = "—", ""

            burl = _jk_build_url(job_name, bn)
            curl = _jk_console_url(job_name, bn)

            st.markdown(f"""
<div style="
  display:flex; align-items:center; justify-content:space-between; gap:1rem;
  padding:0.7rem 1rem; margin:0.3rem 0;
  background:var(--bg-card); border-radius:10px;
  border-left:3px solid {row_accent};
  border:1px solid var(--border); border-left:3px solid {row_accent};
">
  <div style="display:flex; align-items:center; gap:0.75rem; flex:1; min-width:0;">
    <span style="font-size:1.2rem; flex-shrink:0;">{bi}</span>
    <div style="flex:1; min-width:0;">
      <div style="display:flex; align-items:center; gap:0.5rem; flex-wrap:wrap;">
        <a href="{burl}" target="_blank" class="jk-link"
           style="font-size:0.92rem; font-weight:700; text-decoration:none;">
          Build #{bn}
        </a>
        <span class="badge {bcls}">{br}</span>
      </div>
      <div style="display:flex; align-items:center; gap:0.5rem; margin-top:0.25rem;
                  font-size:0.78rem; color:var(--text-2);">
        <span title="{exact}" style="cursor:default;">🕐 {ago}</span>
        <span style="color:var(--text-3);">·</span>
        <span>⏱ {dur_str}</span>
      </div>
    </div>
  </div>
  <div style="display:flex; gap:0.4rem; flex-shrink:0;">
    <a href="{burl}" target="_blank" class="jk-link-btn">🔗 Build</a>
    <a href="{curl}" target="_blank" class="jk-link-btn">📋 Log</a>
  </div>
</div>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
#  JOB DETAIL VIEW
# ─────────────────────────────────────────────────────────────────────────────
def render_detail_view(jenkins, job_name: str):
    # ── Top bar ───────────────────────────────────────────────────────────
    col_back, col_title, col_act = st.columns([1, 5, 2])
    with col_back:
        if st.button("← Back", key="detail_back"):
            st.session_state.view = "chat"
            st.session_state.selected_job = None
            st.rerun()
    with col_title:
        st.markdown(f"""
        <div class="top-bar" style="border-bottom:none; padding: 0.5rem 0;">
          <div>
            <div class="top-bar-title">📋 {job_name}</div>
            <div class="top-bar-sub">Job details • Console logs • Build history</div>
          </div>
        </div>
        """, unsafe_allow_html=True)
    with col_act:
        if st.button("🔄 Trigger Build", key="detail_build"):
            st.session_state.pending_cmd = f"build {job_name} from main"
            st.session_state.view = "chat"
            st.rerun()

    st.markdown('<hr class="divider">', unsafe_allow_html=True)

    try:
        job_info  = jenkins.get_job_info(job_name)
        last_build = job_info.get("lastBuild")

        if not last_build:
            st.info("No builds found for this job.")
            return

        build_num    = last_build.get("number")
        build_status = jenkins.get_build_status(job_name, build_num)
        result       = build_status.status.name if build_status.status else "UNKNOWN"
        # Human-readable duration
        _ds = (build_status.duration or 0) // 1000
        if _ds <= 0:       duration_str = ""
        elif _ds < 60:     duration_str = f"{_ds}s"
        elif _ds < 3600:   duration_str = f"{_ds//60}m {_ds%60}s" if _ds%60 else f"{_ds//60}m"
        else:              duration_str = f"{_ds//3600}h {(_ds%3600)//60}m" if (_ds%3600)//60 else f"{_ds//3600}h"

        console_short = jenkins.get_console_output(job_name, build_num, last_n_lines=20)
        console_full  = jenkins.get_console_output(job_name, build_num, last_n_lines=100)
        analysis      = analyze_build(console_full, result)

        # ── Status card ───────────────────────────────────────────────────
        build_url   = _jk_build_url(job_name, build_num)
        console_url = _jk_console_url(job_name, build_num)
        job_url     = _jk_job_url(job_name)
        border_col  = "#22c55e" if result == "SUCCESS" else "#ef4444" if result == "FAILURE" else "#f59e0b"
        st.markdown(f"""
        <div class="detail-card" style="border-left: 3px solid {border_col};">
          <div style="display:flex; align-items:center; justify-content:space-between;">
            <div style="display:flex; align-items:center; gap:0.75rem;">
              <span style="font-size:1.75rem;">{analysis['icon']}</span>
              <div>
                <div style="color:var(--text-1);font-size:1rem;font-weight:700;">
                  {_link(build_url, f'Build #{build_num}', 'jk-link')}
                  &nbsp;
                  {_link(console_url, '📋 Console', 'jk-link-btn')}
                  &nbsp;
                  {_link(job_url, '🔗 Job Page', 'jk-link-btn')}
                </div>
                <div style="color:var(--text-2);font-size:0.78rem;margin-top:0.35rem;">
                  {analysis['category']} &bull; {analysis['reason']}
                  {'&bull; ⏱️ ' + duration_str if duration_str else ''}
                </div>
              </div>
            </div>
            {_result_badge(result)}
          </div>
        </div>
        """, unsafe_allow_html=True)

        # ── Two-column layout ─────────────────────────────────────────────
        col_l, col_r = st.columns([3, 2])

        with col_l:
            # Console header with link
            st.markdown(
                f'<div class="sec-lbl">📋 Last 20 Lines &nbsp;'
                f'{_link(console_url, "↗ Open in Jenkins", "jk-link-btn")}</div>',
                unsafe_allow_html=True
            )
            st.markdown(f'<div class="log-box">{console_short}</div>', unsafe_allow_html=True)

            # Full log expander with link
            with st.expander(f"📄 Full Console Log"):
                st.markdown(
                    f'{_link(console_url, "↗ Open full console in Jenkins", "jk-link-btn")}',
                    unsafe_allow_html=True
                )
                full_log = jenkins.get_console_output(job_name, build_num, last_n_lines=300)
                st.text_area("log", full_log, height=280, label_visibility="collapsed")

        with col_r:
            # Errors
            if analysis["errors"]:
                st.markdown('<div class="sec-lbl">🔴 Errors Detected</div>', unsafe_allow_html=True)
                for err in analysis["errors"]:
                    st.code(err, language=None)

            # Suggestions
            if analysis["suggestions"]:
                st.markdown('<div class="sec-lbl">💡 Suggestions</div>', unsafe_allow_html=True)
                for sug in analysis["suggestions"]:
                    st.markdown(f'<div class="sug-item">→ {sug}</div>', unsafe_allow_html=True)

            # Build history
            st.markdown('<div class="sec-lbl">📊 Recent Builds</div>', unsafe_allow_html=True)
            history = jenkins.get_build_history(job_name, limit=8)
            hist_html = ""
            for b in history:
                br   = b.get("result", "UNKNOWN")
                bi   = "✅" if br == "SUCCESS" else "❌" if br == "FAILURE" else "🔄"
                bn   = b.get("number", "?")
                burl = _jk_build_url(job_name, bn)
                curl = _jk_console_url(job_name, bn)
                hist_html += f"""
                <div class="hist-row">
                  <span>{bi}</span>
                  <a href="{burl}" target="_blank" class="jk-link" style="font-weight:600;">#{bn}</a>
                  <span style="flex:1;">{br}</span>
                  <a href="{curl}" target="_blank" class="jk-link-btn" style="font-size:0.65rem;">log</a>
                </div>"""
            st.markdown(
                f'<div class="detail-card" style="padding:0.75rem 1rem;">{hist_html}</div>',
                unsafe_allow_html=True
            )

    except Exception as e:
        st.error(f"Error loading job details: {e}")


# ─────────────────────────────────────────────────────────────────────────────
#  MAIN
# ─────────────────────────────────────────────────────────────────────────────
def main():
    init_state()
    inject_css()
    processor, jenkins = init_services()

    if not processor:
        st.error("❌ Failed to initialise services. Check your .env configuration.")
        st.code("JENKINS_URL, JENKINS_USER, JENKINS_API_TOKEN must be set in buildbot/.env")
        return

    # Sidebar always rendered
    render_sidebar(jenkins)

    # Main content based on view
    if st.session_state.view == "detail" and st.session_state.selected_job:
        render_detail_view(jenkins, st.session_state.selected_job)
    elif st.session_state.view == "history":
        render_history_view(jenkins)
    elif st.session_state.view == "customize":
        render_customize_panel()
    else:
        render_chat_view(processor)


if __name__ == "__main__":
    main()
