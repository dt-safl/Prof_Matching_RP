"""Researcher → Proposal Match dashboard (v2).  Run:  streamlit run app.py

Design goals (from feedback):
  - Two axes: RFP FIT (strict, evidence-based) and STANDING & AGENCY (descriptive).
  - Every score has a LEGEND and the rubric is one click away.
  - Cohort-relative bars: each signal shows the cohort average + this prof's percentile,
    so a raw number like 0.27 becomes 'top 15% of the cohort'.
  - Strongest evidence and biggest gaps boxed and highlighted.
  - Out-of-scope is NARROW (only true RFP exclusions, e.g. interpretability).
"""
import json, os, statistics
import streamlit as st
import config
from agenda import SUBTHEMES, OUT_OF_SCOPE

st.set_page_config(page_title="Researcher–Proposal Match", layout="wide")

TIER = {
    "DIRECT":    ("#1f8a4c", "Direct fit",   "Recent first-hand work on a sub-theme's core question."),
    "ADJACENT":  ("#2f6fb0", "Adjacent",     "Transferable methods/topics applicable to the agenda."),
    "UNRELATED": ("#8a8f98", "Unrelated",    "Capable researcher, but work doesn't address the agenda."),
    "EXCLUDED":  ("#b3382f", "Out of scope", "Core area is explicitly excluded by this RFP (e.g. interpretability)."),
}
ST_TITLE = {t["id"]: t["title"] for t in SUBTHEMES}

st.markdown("""
<style>
 /* ============ DARK MODE THEME ============ */
 .stApp { background-color: #0B1020; color: #F5F7FA; }
 .block-container {
   padding-top: 2rem;
   max-width: 1400px;
   margin: auto;
   padding-left: 32px;
   padding-right: 32px;
 }

 /* ============ TYPOGRAPHY SCALE ============ */
 .main-title { font-size: 32px; font-weight: 700; color: #F5F7FA; margin-bottom: 8px; }
 .section-title { font-size: 22px; font-weight: 650; color: #F5F7FA; margin-top: 32px; margin-bottom: 16px; }
 .card-title { font-size: 18px; font-weight: 600; color: #F5F7FA; margin-bottom: 12px; }
 .body-text { font-size: 15px; line-height: 1.6; color: #F5F7FA; }
 .secondary-text { color: #B8C0CC; }
 .muted-text { color: #7E8794; font-size: 13px; }

 /* ============ EXECUTIVE HERO SECTION ============ */
 .executive-hero {
   background: linear-gradient(135deg, #111827 0%, #172033 100%);
   border-radius: 16px;
   padding: 32px;
   margin-bottom: 32px;
   border: 1px solid rgba(255,255,255,0.08);
 }

 .verdict-large {
   font-size: 48px;
   font-weight: 800;
   text-align: center;
   margin-bottom: 16px;
   line-height: 1.1;
 }

 .verdict-large.direct { color: #22C55E; }
 .verdict-large.adjacent { color: #3B82F6; }
 .verdict-large.unrelated { color: #F59E0B; }
 .verdict-large.excluded { color: #EF4444; }

 .executive-summary {
   font-size: 18px;
   font-style: italic;
   text-align: center;
   color: #B8C0CC;
   margin-bottom: 24px;
   line-height: 1.5;
 }

 /* ============ FIT SCORE MEGA DISPLAY ============ */
 .fit-score-mega {
   text-align: center;
   padding: 24px;
   background: rgba(239,68,68,0.1);
   border-radius: 12px;
   border: 1px solid rgba(239,68,68,0.3);
   margin-bottom: 24px;
 }

 .fit-number {
   font-size: 72px;
   font-weight: 900;
   color: #EF4444;
   line-height: 0.8;
   margin-bottom: 8px;
 }

 .fit-number.good { color: #22C55E; }
 .fit-number.medium { color: #F59E0B; }
 .fit-number.bad { color: #EF4444; }

 .fit-label {
   font-size: 16px;
   font-weight: 600;
   color: #B8C0CC;
   text-transform: uppercase;
   letter-spacing: 1px;
 }

 /* ============ SEMANTIC CARD SYSTEM ============ */
 .card {
   background: #111827;
   border-radius: 12px;
   padding: 24px;
   margin-bottom: 24px;
   border: 1px solid rgba(255,255,255,0.08);
 }

 .card-positive {
   border-left: 4px solid #22C55E;
   background: rgba(34,197,94,0.08);
 }

 .card-warning {
   border-left: 4px solid #F59E0B;
   background: rgba(245,158,11,0.08);
 }

 .card-critical {
   border-left: 4px solid #EF4444;
   background: rgba(239,68,68,0.08);
 }

 .card-neutral {
   border-left: 4px solid #3B82F6;
   background: rgba(59,130,246,0.05);
 }

 /* ============ IMPROVED CONTRAST ============ */
 .card h3, .card h4 { color: #F5F7FA !important; font-weight: 600; }
 .card p, .card div { color: rgba(255,255,255,0.92) !important; }
 .card .muted { color: #B8C0CC !important; }

 /* ============ LISTS & BULLETS ============ */
 .bullet-list {
   list-style: none;
   padding-left: 0;
   margin: 16px 0;
 }

 .bullet-list li {
   padding: 8px 0;
   padding-left: 24px;
   position: relative;
   color: #F5F7FA;
   line-height: 1.5;
 }

 .bullet-list li::before {
   content: '•';
   position: absolute;
   left: 0;
   color: #3B82F6;
   font-weight: bold;
   font-size: 18px;
 }

 .bullet-list.positive li::before { color: #22C55E; }
 .bullet-list.warning li::before { color: #F59E0B; }
 .bullet-list.critical li::before { color: #EF4444; }

 /* ============ METRICS ROW ============ */
 .metrics-row {
   display: flex;
   gap: 16px;
   margin: 24px 0;
   flex-wrap: wrap;
 }

 .metric-card {
   background: #172033;
   border-radius: 12px;
   padding: 20px;
   text-align: center;
   flex: 1;
   min-width: 140px;
   border: 1px solid rgba(255,255,255,0.05);
 }

 .metric-value {
   font-size: 32px;
   font-weight: 700;
   color: #F5F7FA;
   line-height: 1;
   margin-bottom: 8px;
 }

 .metric-label {
   font-size: 12px;
   color: #B8C0CC;
   text-transform: uppercase;
   letter-spacing: 0.5px;
 }

 /* ============ BARS & PROGRESS ============ */
 .progress-bar {
   height: 12px;
   background: rgba(255,255,255,0.1);
   border-radius: 6px;
   position: relative;
   margin: 8px 0;
 }

 .progress-fill {
   height: 100%;
   border-radius: 6px;
   position: absolute;
   left: 0;
   top: 0;
 }

 .progress-fill.high { background: linear-gradient(90deg, #22C55E, #16A34A); }
 .progress-fill.medium { background: linear-gradient(90deg, #F59E0B, #D97706); }
 .progress-fill.low { background: linear-gradient(90deg, #6B7280, #4B5563); }

 /* ============ BADGES & CHIPS ============ */
 .badge {
   display: inline-block;
   padding: 4px 12px;
   border-radius: 20px;
   font-size: 12px;
   font-weight: 600;
   text-transform: uppercase;
   letter-spacing: 0.5px;
 }

 .badge.direct { background: #22C55E; color: white; }
 .badge.adjacent { background: #3B82F6; color: white; }
 .badge.unrelated { background: #F59E0B; color: white; }
 .badge.excluded { background: #EF4444; color: white; }

 .chip {
   display: inline-block;
   padding: 4px 10px;
   margin: 2px 4px 2px 0;
   border-radius: 8px;
   font-size: 11px;
   background: rgba(59,130,246,0.15);
   color: #93C5FD;
   border: 1px solid rgba(59,130,246,0.3);
 }

 /* ============ 2-COLUMN LAYOUT ============ */
 .two-column {
   display: grid;
   grid-template-columns: 1fr 1fr;
   gap: 32px;
   margin-top: 32px;
 }

 @media (max-width: 768px) {
   .two-column {
     grid-template-columns: 1fr;
   }
   .metrics-row {
     flex-direction: column;
   }
 }

 /* ============ STREAMLIT OVERRIDES ============ */
 .stMarkdown, .stText { color: #F5F7FA !important; }
 .stExpander { background-color: #111827; border: 1px solid rgba(255,255,255,0.08); }
 .stButton button { background: #3B82F6; color: white; border: none; }
 .stSelectbox { background: #111827; }

/* ============ STAT BOXES (Profile Header) ============ */
.statbox {
  background: #172033;
  border-radius: 8px;
  padding: 12px;
  text-align: center;
  border: 1px solid rgba(255,255,255,0.05);
  margin-bottom: 8px;
}

.statbox b {
  display: block;
  font-size: 20px;
  font-weight: 700;
  color: #3B82F6;
  line-height: 1;
  margin-bottom: 4px;
}

.statbox span {
  display: block;
  font-size: 10px;
  color: #B8C0CC;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  line-height: 1.2;
}

</style>
""", unsafe_allow_html=True)


@st.cache_data
def load():
    if not os.path.exists(config.OUT_JSON):
        return []
    # Include file modification time in cache key to auto-invalidate when data updates
    file_mtime = os.path.getmtime(config.OUT_JSON)
    return _load_data_with_mtime(file_mtime)

def _load_data_with_mtime(mtime):
    """Helper function that includes file modification time for proper cache invalidation."""
    return json.load(open(config.OUT_JSON))


def badge(t):
    tier_classes = {
        "DIRECT": "direct",
        "ADJACENT": "adjacent",
        "UNRELATED": "unrelated",
        "EXCLUDED": "excluded"
    }
    _, lbl, _ = TIER.get(t, ("", t, ""))
    css_class = tier_classes.get(t, "unrelated")
    return f'<span class="badge {css_class}">{lbl}</span>'

def impact_standing(seniority, h_index=None):
    """Convert generic seniority labels to impact-based standing"""
    if not seniority or seniority == "?":
        return "Emerging"

    seniority_str = str(seniority).lower()

    # Map based on common academic seniority labels
    if any(term in seniority_str for term in ["early", "junior", "assistant", "lecturer"]):
        return "Emerging"
    elif any(term in seniority_str for term in ["mid", "associate", "senior lecturer"]):
        return "Established"
    elif any(term in seniority_str for term in ["senior", "full", "professor", "chair", "distinguished"]):
        return "Leading"
    else:
        # Fallback to h-index if available
        if h_index and str(h_index).isdigit():
            h_val = int(h_index)
            if h_val >= 40:
                return "Leading"
            elif h_val >= 15:
                return "Established"
            else:
                return "Emerging"
        return "Emerging"

def executive_verdict(tier, fit_score):
    """Generate the big executive summary verdict"""
    tier_messages = {
        "DIRECT": "EXCELLENT FIT",
        "ADJACENT": "PARTIAL FIT",
        "UNRELATED": "POOR FIT",
        "EXCLUDED": "NOT ELIGIBLE"
    }
    verdict = tier_messages.get(tier, "UNRELATED")
    tier_class = tier.lower()

    # Fit score styling
    if fit_score >= 75:
        fit_class = "good"
    elif fit_score >= 45:
        fit_class = "medium"
    else:
        fit_class = "bad"

    return verdict, tier_class, fit_class


def cohort_stats(data):
    """Per-sub-theme mean for bm25 and dense across all profiles, for relative bars."""
    bm, dn = {t["id"]: [] for t in SUBTHEMES}, {t["id"]: [] for t in SUBTHEMES}
    for d in data:
        sc = d.get("scores", {})
        for tid in bm:
            b = sc.get("bm25", {}).get(tid)
            if b is not None: bm[tid].append(b)
            v = sc.get("dense", {}).get(tid)
            if v is not None: dn[tid].append(v)
    mean = lambda xs: round(statistics.mean(xs), 3) if xs else 0
    return ({k: mean(v) for k, v in bm.items()}, {k: mean(v) for k, v in dn.items()})


def format_bullet_list(items, list_type="neutral"):
    """Format items as a styled bullet list"""
    if not items:
        return ""

    list_class = f"bullet-list {list_type}"
    items_html = "".join([f'<li>{item}</li>' for item in items])
    return f'<ul class="{list_class}">{items_html}</ul>'

def metric_card(value, label, is_primary=False):
    """Generate a metric card"""
    if is_primary:
        return f'''
        <div class="metric-card" style="border: 2px solid #3B82F6;">
            <div class="metric-value" style="color: #3B82F6; font-size: 42px;">{value}</div>
            <div class="metric-label">{label}</div>
        </div>
        '''
    return f'''
    <div class="metric-card">
        <div class="metric-value">{value}</div>
        <div class="metric-label">{label}</div>
    </div>
    '''

def relbar(label, val, avg, color, lo=0.0, hi=1.0):
    if val is None:
        st.markdown(f'<div class="muted-text">{label}: n/a</div>', unsafe_allow_html=True); return
    span = (hi - lo) or 1
    pct = int(max(0, min(1, (val - lo) / span)) * 100)
    # Enhanced bar with better styling
    level = "high" if val > avg else ("medium" if val > avg * 0.7 else "low")
    rel = "above avg" if val > avg + 1e-6 else ("below avg" if val < avg - 1e-6 else "≈ avg")

    st.markdown(f'''
    <div class="secondary-text">{label}: <strong style="color: #F5F7FA;">{val:.2f}</strong>
    <span class="muted-text">(cohort avg {avg:.2f} · {rel})</span></div>
    <div class="progress-bar">
        <div class="progress-fill {level}" style="width: {pct}%;"></div>
    </div>
    ''', unsafe_allow_html=True)


data = load()
BM_AVG, DN_AVG = cohort_stats(data) if data else ({}, {})
if "sel_data" not in st.session_state:
    st.session_state.sel_data = None
if "page" not in st.session_state:
    st.session_state.page = 0
PAGE_SIZE = 20


# ============================== legend / rubric (shared) ==============================
def rubric_expander():
    with st.expander("📐 How scoring works (rubric & legends)"):
        st.markdown("""
**Two separate axes — we never collapse them into one number.**

**Axis A · RFP fit (0–100)** — strict, evidence-based mapping to the 7 Schmidt sub-themes.
Most computer scientists score low here, and that is *correct* — trustworthy-AI is a niche.

| Band | Score | Meaning |
|---|---|---|
| **Direct** | 75–100 | recent first-hand work on a sub-theme's core question (a paper is cited) |
| **Adjacent** | 45–74 | transferable methods (evaluation science, robustness, causal, uncertainty, multi-agent) |
| **Unrelated** | 15–44 | capable researcher, but the work doesn't address the agenda |
| **None / Out of scope** | 0–14 | no connection — *or* core area is an explicit RFP exclusion |

Fit is judged from **four angles**, all shown on the profile: *recent-direct work, transferable
methods, stated-interest alignment, and trajectory* (are they moving toward this).

**Out of scope is NARROW.** It fires **only** when the professor's *core* area is one of the RFP's
official exclusions (interpretability, fairness/bias, policy, watermarking, jailbreak-only,
generic capability evals, near-term product, CBRN, model safeguards). NLP, computer vision,
generic ML, systems, and networks are **Unrelated (low fit)** — never "out of scope".

**Axis B · Standing & agency** — *descriptive, not a grade*: seniority (by h-index), citation
trajectory, and non-academic agency (founder / advisor / VC / patents / grants / leadership /
talks / network). This answers "how strong are they, and *for what*", independent of RFP fit.

**The three signals** (shown on each profile, with cohort context):
- **Keyword Match** — direct text overlap with the agenda. *Noisy* (common ML words collide), so it's shown
  for transparency only and is **not** a tier driver.
- **Semantic Match** — conceptual similarity using AI understanding. Bars show the **cohort average**
  (the dark tick) so you can read "above/below average for these professors".
- **LLM judge** — the strict reviewer above; drives the fit band, with cited evidence.
""")


# ============================== HOME ==============================
def home():
    st.markdown('<h1 class="main-title">Researcher → Proposal Match</h1>', unsafe_allow_html=True)
    st.markdown('<p class="secondary-text">Schmidt Sciences · Science of Trustworthy AI (2026) — evidence-based fit analysis</p>', unsafe_allow_html=True)

    if not data:
        st.warning("No data yet. Run `python3 pipeline.py --one` (or `--all`), then refresh.")
        return

    rubric_expander()

    # Summary stats with better styling
    tiers = [d.get("scores", {}).get("tier", "UNRELATED") for d in data if "scores" in d]

    st.markdown('<h2 class="section-title">Portfolio Overview</h2>', unsafe_allow_html=True)
    cols = st.columns(4)
    for col, t in zip(cols, ["DIRECT", "ADJACENT", "UNRELATED", "EXCLUDED"]):
        count = tiers.count(t)
        col.markdown(f"""
        <div class="card card-neutral" style="text-align: center; padding: 16px;">
            {badge(t)}<br>
            <div class="metric-value" style="font-size: 24px; margin: 8px 0;">{count}</div>
            <div class="muted-text" style="font-size: 11px;">{TIER[t][2][:40]}...</div>
        </div>
        """, unsafe_allow_html=True)

    # Enhanced Filters and Sorting section
    st.markdown('<h2 class="section-title">Filters & Sorting</h2>', unsafe_allow_html=True)

    filter_col1, filter_col2, filter_col3 = st.columns([1, 1, 1])

    with filter_col1:
        show = st.multiselect("Filter by tier", list(TIER), default=list(TIER), format_func=lambda t: TIER[t][1])

    with filter_col2:
        # Get unique institutions from data
        institutions = list(set(d.get("institute", "Unknown") for d in data if d.get("institute")))
        institutions.sort()
        show_institutions = st.multiselect("Filter by institution", institutions, default=institutions)

    with filter_col3:
        # Sorting options
        sort_options = {
            "Overall Fit (High to Low)": ("overall_fit", True),
            "Overall Fit (Low to High)": ("overall_fit", False),
            "H-Index (High to Low)": ("h_index", True),
            "H-Index (Low to High)": ("h_index", False),
            "Theme 1.1 Score": ("1.1", True),
            "Theme 1.2 Score": ("1.2", True),
            "Theme 1.3 Score": ("1.3", True),
            "Theme 2.1 Score": ("2.1", True),
            "Theme 2.2 Score": ("2.2", True),
            "Theme 3.1 Score": ("3.1", True),
            "Theme 3.2 Score": ("3.2", True),
            "Institute Name": ("institute", False),
            "Professor Name": ("name", False)
        }

        sort_by = st.selectbox("Sort by", list(sort_options.keys()), index=0)
        sort_key, sort_desc = sort_options[sort_by]

    # Advanced filters
    adv_col1, adv_col2, adv_col3 = st.columns([1, 1, 1])

    with adv_col1:
        min_fit = st.slider("Minimum Overall Fit Score", 0, 100, 0)

    with adv_col2:
        min_h_index = st.slider("Minimum H-Index", 0, 100, 0)

    with adv_col3:
        theme_filter = st.selectbox("Filter by Theme Score",
                                  ["All Themes", "1.1 (AI Alignment)", "1.2 (Deception)", "1.3 (Power-Seeking)",
                                   "2.1 (Evaluation)", "2.2 (Red Teaming)", "3.1 (Governance)", "3.2 (Multi-Agent)"])

        if theme_filter != "All Themes":
            theme_id = theme_filter.split()[0]
            min_theme_score = st.slider(f"Minimum {theme_filter} Score", 0, 100, 0)

    # Text search and apply button
    search_col1, search_col2, search_col3 = st.columns([2, 1, 1])

    with search_col1:
        search_text = st.text_input("🔍 Search by name, institute, or research interests", placeholder="e.g. machine learning, neural networks, IIT Delhi...")

    with search_col2:
        apply_filters = st.button("🎯 Apply Filters", type="primary")

    with search_col3:
        clear_filters = st.button("🗑️ Clear All")

    # Handle clear filters
    if clear_filters:
        st.rerun()

    st.markdown('<h2 class="section-title">Ranked Candidates</h2>', unsafe_allow_html=True)

    # Apply filtering and sorting
    filtered_data = []
    for d in data:
        sc = d.get("scores", {})
        tier = sc.get("tier", "UNRELATED")
        institute = d.get("institute", "Unknown")
        llm = sc.get("llm", {})
        standing_raw = sc.get("standing")
        # Handle None, float, or other non-dict cases
        if isinstance(standing_raw, dict):
            standing = standing_raw
        else:
            standing = {}  # Default for None, float, or any other type

        # Apply basic filters
        if tier not in show:
            continue
        if institute not in show_institutions:
            continue

        # Apply advanced filters
        fit_score = llm.get("overall_fit", 0)
        h_index = standing.get("h_index", 0) or 0

        if fit_score < min_fit:
            continue
        if h_index < min_h_index:
            continue

        # Apply theme-specific filter
        if theme_filter != "All Themes":
            theme_id = theme_filter.split()[0]
            themes = {theme.get("id"): theme.get("score", 0) for theme in llm.get("best_subthemes", [])}
            theme_score = themes.get(theme_id, 0)
            if theme_score < min_theme_score:
                continue

        # Apply text search filter
        if search_text:
            search_lower = search_text.lower()
            searchable_text = " ".join([
                d.get("name", "").lower(),
                d.get("institute", "").lower(),
                d.get("research_interests", "").lower(),
                d.get("designation", "").lower(),
                llm.get("verdict", "").lower()
            ])
            if search_lower not in searchable_text:
                continue

        filtered_data.append(d)

    # Sort the filtered data
    def get_sort_value(prof):
        sc = prof.get("scores", {})
        if sort_key == "overall_fit":
            return sc.get("llm", {}).get("overall_fit", 0)
        elif sort_key == "h_index":
            standing_raw = sc.get("standing")
            standing = standing_raw if isinstance(standing_raw, dict) else {}
            return standing.get("h_index", 0) or 0
        elif sort_key in ["1.1", "1.2", "1.3", "2.1", "2.2", "3.1", "3.2"]:
            themes = {theme.get("id"): theme.get("score", 0) for theme in sc.get("llm", {}).get("best_subthemes", [])}
            return themes.get(sort_key, 0)
        elif sort_key == "institute":
            return prof.get("institute", "")
        elif sort_key == "name":
            return prof.get("name", "")
        return 0

    sorted_data = sorted(filtered_data, key=get_sort_value, reverse=sort_desc)

    # Pagination
    total = len(sorted_data)
    total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
    if st.session_state.page >= total_pages:
        st.session_state.page = 0
    page_start = st.session_state.page * PAGE_SIZE
    page_data = sorted_data[page_start:page_start + PAGE_SIZE]

    pg_l, pg_c, pg_r = st.columns([1, 3, 1])
    with pg_l:
        if st.button("◀ Prev", disabled=(st.session_state.page == 0)):
            st.session_state.page -= 1; st.rerun()
    with pg_c:
        st.markdown(
            f"<p style='text-align:center;color:#B8C0CC;margin:6px 0;'>"
            f"Page {st.session_state.page + 1} of {total_pages} &nbsp;·&nbsp; {total} results</p>",
            unsafe_allow_html=True)
    with pg_r:
        if st.button("Next ▶", disabled=(st.session_state.page >= total_pages - 1)):
            st.session_state.page += 1; st.rerun()

    st.markdown(f"<p class='secondary-text'>Showing {page_start + 1}–{min(page_start + PAGE_SIZE, total)} of {total} professors</p>", unsafe_allow_html=True)

    for i, d in enumerate(page_data):
        sc = d.get("scores", {})
        tier = sc.get("tier", "UNRELATED")
        llm = sc.get("llm", {})
        standing_raw = sc.get("standing")
        stand = standing_raw if isinstance(standing_raw, dict) else {}
        fit_score = llm.get("overall_fit", 0)

        # Determine card type based on fit score and tier
        if tier == "DIRECT":
            card_class = "card-positive"
        elif tier == "ADJACENT":
            card_class = "card-neutral"
        elif tier == "EXCLUDED":
            card_class = "card-critical"
        else:
            card_class = "card-warning"

        st.markdown(f"""
        <div class="card {card_class}">
            <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                <div style="flex: 1;">
                    <h3 style="color: #F5F7FA; margin-bottom: 8px;">{d.get('name','?')} · {d.get('designation','')} {badge(tier)}</h3>
                    <p style="color: #B8C0CC; font-style: italic; margin-bottom: 16px;">{llm.get('verdict','—')[:120]}...</p>

        """, unsafe_allow_html=True)

        # Show top themes as chips
        best = [b for b in (llm.get("best_subthemes") or []) if b.get("score", 0) >= 40][:3]
        if best:
            chips = " ".join([f'<span class="chip">{b["id"]} ({b.get("score","?")}/100)</span>' for b in best])
            st.markdown(f'<div style="margin-bottom: 12px;">{chips}</div>', unsafe_allow_html=True)

        # Agency signals
        sig = (d.get("web_signals", {}) or {}).get("signals", {}) or {}
        if sig:
            agency_chips = " ".join([f'<span class="chip" style="background: rgba(34,197,94,0.15); color: #22C55E; border-color: rgba(34,197,94,0.3);">{k.replace("_"," ")}</span>' for k in list(sig)[:4]])
            st.markdown(f'<div>{agency_chips}</div>', unsafe_allow_html=True)

        # Metrics row - render each card properly
        st.markdown('<div class="metrics-row" style="margin-top: 16px;">', unsafe_allow_html=True)

        # Create columns for proper layout
        metric_cols = st.columns(4)

        with metric_cols[0]:
            st.markdown(metric_card(fit_score, "RFP Fit", True), unsafe_allow_html=True)
        with metric_cols[1]:
            st.markdown(metric_card(stand.get("h_index", "N/A"), "H-Index"), unsafe_allow_html=True)
        with metric_cols[2]:
            st.markdown(metric_card(stand.get("citations", "N/A"), "Citations"), unsafe_allow_html=True)
        with metric_cols[3]:
            st.markdown(metric_card(impact_standing(stand.get("seniority"), stand.get("h_index")), "Impact"), unsafe_allow_html=True)

        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown('</div></div></div>', unsafe_allow_html=True)

        if st.button(f"View Full Profile →", key=f"o{page_start + i}"):
            st.session_state.sel_data = d; st.rerun()

    # Bottom pagination
    st.markdown("---")
    bot_l, bot_c, bot_r = st.columns([1, 3, 1])
    with bot_l:
        if st.button("◀ Prev", key="prev_bot", disabled=(st.session_state.page == 0)):
            st.session_state.page -= 1; st.rerun()
    with bot_c:
        st.markdown(
            f"<p style='text-align:center;color:#B8C0CC;margin:6px 0;'>"
            f"Page {st.session_state.page + 1} of {total_pages}</p>",
            unsafe_allow_html=True)
    with bot_r:
        if st.button("Next ▶", key="next_bot", disabled=(st.session_state.page >= total_pages - 1)):
            st.session_state.page += 1; st.rerun()


# ============================== DETAIL ==============================
def detail(prof_data):
    d = prof_data
    if st.button("← Back to ranking"):
        st.session_state.sel_data = None; st.rerun()
    ac = d.get("academic", {}); sc = d.get("scores", {}); llm = sc.get("llm", {})
    standing_raw = sc.get("standing")
    stand = standing_raw if isinstance(standing_raw, dict) else {}; tier = sc.get("tier", "UNRELATED")

    head = st.columns([0.13, 0.87])
    if d.get("photo_ok"):
        try: head[0].image(d["photo_ok"], width=96)
        except Exception: pass
    with head[1]:
        # Professor name and tier with better styling
        name = d.get('name', 'Unknown')
        designation = d.get('designation', 'N/A')
        department = d.get('department', 'N/A')
        institute = d.get('institute', 'N/A')

        st.markdown(f"""
        <div class="card card-neutral" style="margin-bottom: 16px;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                <h3 style="margin: 0; color: #F5F7FA;">{name}</h3>
                {badge(tier)}
            </div>
            <div style="margin-bottom: 8px;">
                <strong>{designation if designation != 'N/A' else 'Professor'}</strong> ·
                {department if department != 'N/A' else 'Department N/A'} ·
                {institute if institute != 'N/A' else 'Institute N/A'}
            </div>
        """, unsafe_allow_html=True)

        # Display verdict (all profiles have complete analysis)
        verdict = llm.get('verdict', '—')
        if not verdict or verdict == '—' or len(verdict.strip()) == 0:
            verdict = "Analysis complete - detailed assessment available below"

        st.markdown(f"""
            <div style="font-style: italic; color: #B8C0CC; margin-bottom: 8px;">
                {verdict if verdict != '—' else 'No analysis available'}
            </div>
        """, unsafe_allow_html=True)

        if llm.get("general_value"):
            st.markdown(f"""
            <div style="margin-bottom: 8px;">
                <strong>Overall Value:</strong> {llm['general_value']}
            </div>
            """, unsafe_allow_html=True)

        st.markdown("</div>", unsafe_allow_html=True)

        if d.get("identity_sanity"):
            st.warning(f"Identity check: {d['identity_sanity']}")

    # ---- Fit Summary (Prominent) ----
    fit_score = llm.get("overall_fit", 0)
    confidence = llm.get("confidence", "?").upper()
    confidence_reason = llm.get("confidence_reason", "")

    # Determine fit tier description
    if tier == "DIRECT":
        fit_description = "Direct"
        fit_detail = "Recent first-hand work on core agenda questions"
    elif tier == "ADJACENT":
        fit_description = "Adjacent"
        fit_detail = "Transferable methods and applicable expertise"
    elif tier == "EXCLUDED":
        fit_description = "Out of scope"
        fit_detail = "Core area explicitly excluded by RFP"
    else:
        fit_description = "Unrelated"
        fit_detail = "Capable researcher, limited agenda alignment"

    # Determine match method for reason
    match_method = ac.get('match_method', '')
    papers_analyzed = ac.get('n_works_pulled', 0)

    if match_method == "ORCID":
        reason_detail = f"ORCID verified profile | {papers_analyzed} papers analyzed"
    elif match_method:
        reason_detail = f"Identity matched via {match_method} | {papers_analyzed} papers analyzed"
    else:
        reason_detail = f"Web profile analysis | {papers_analyzed} papers reviewed"

    st.markdown(f"""
    <div class="card card-neutral" style="background: #1a2332; border: 2px solid #3B82F6;">
        <h4 style="margin-bottom: 16px;">🎯 Fit Summary</h4>
        <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 20px; margin-bottom: 12px;">
            <div>
                <div style="font-size: 11px; color: #B8C0CC; text-transform: uppercase; letter-spacing: 0.5px;">Fit Level</div>
                <div style="font-size: 18px; font-weight: 600; color: #F5F7FA;">{fit_description} ({fit_score}/100)</div>
            </div>
            <div>
                <div style="font-size: 11px; color: #B8C0CC; text-transform: uppercase; letter-spacing: 0.5px;">Confidence</div>
                <div style="font-size: 18px; font-weight: 600; color: #F5F7FA;">{confidence}</div>
            </div>
            <div>
                <div style="font-size: 11px; color: #B8C0CC; text-transform: uppercase; letter-spacing: 0.5px;">Impact Standing</div>
                <div style="font-size: 18px; font-weight: 600; color: #F5F7FA;">{impact_standing(stand.get("seniority"), stand.get("h_index"))}</div>
            </div>
        </div>
        <div style="margin-bottom: 8px;">
            <strong style="color: #F5F7FA;">Why matched:</strong> {fit_detail}
        </div>
        <div class="muted-text">
            <strong>Data source:</strong> {reason_detail}
            {f" | Confidence basis: {confidence_reason}" if confidence_reason else ""}
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ---- stat boxes ----
    cells = st.columns(6)
    boxes = [
        (stand.get("h_index", "N/A"), "h-index"),
        (stand.get("citations", "N/A"), "citations"),
        (stand.get("h_index_5y", "N/A"), "h-index (5y)"),
        (f'{ac.get("n_works_pulled","N/A")}', "papers pulled"),
        (f'{llm.get("overall_fit","N/A")}', "RFP fit /100"),
        (impact_standing(stand.get("seniority"), stand.get("h_index")), "impact"),
    ]
    for c, (v, lbl) in zip(cells, boxes):
        c.markdown(f'<div class="statbox"><b>{v}</b><span>{lbl}</span></div>', unsafe_allow_html=True)

    # Detailed metrics explanation
    with st.expander("📊 Metrics Explanation & Data Sources"):
        st.markdown(f"""
        **Academic Metrics:**
        - **H-Index**: Number of papers with at least h citations each (current: {stand.get("h_index", "N/A")})
        - **Citations**: Total citation count across all publications (current: {stand.get("citations", "N/A")})
        - **5-Year H-Index**: H-index calculated from last 5 years only (current: {stand.get("h_index_5y", "N/A")})

        **Data Collection:**
        - **Papers Analyzed**: {ac.get("n_works_pulled", "N/A")} papers were pulled and analyzed for this assessment
        - **RFP Fit Score**: {llm.get("overall_fit", "N/A")}/100 based on LLM analysis of research alignment

        **Identity Verification:**
        - Status: {("Verified via " + ac.get('match_method', 'Unknown method') + " (" + str(ac.get('academic_confidence', '?')) + " confidence)") if ac.get("resolved") else "NOT anchored — scraped data only"}
        - Analysis Confidence: {llm.get('confidence', 'Unknown')} - {llm.get('confidence_reason', 'No reason provided')}

        **Impact Standing Calculation:**
        - Current: {impact_standing(stand.get("seniority"), stand.get("h_index"))}
        - Based on: Academic position ({stand.get("seniority", "N/A")}) + H-index ({stand.get("h_index", "N/A")})
        - Categories: Emerging (early career/H<15), Established (mid career/H 15-39), Leading (senior/H≥40)
        """)

    st.caption(f"Data sources: OpenAlex, ORCID, institutional profiles | Last updated: Current session")

    C1, C2 = st.columns([0.55, 0.45])

    # ----- LEFT: fit + focus + papers -----
    with C1:
        st.markdown("#### Axis A · Fit to the agenda")

        # Angle scores in a card
        ang = llm.get("angles", {}) or {}
        if not isinstance(ang, dict):
            ang = {}
        if ang:
            st.markdown(f"""
            <div class="card card-neutral">
                <h4>📊 Fit Assessment Angles</h4>
                <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px; margin-bottom: 12px;">
            """, unsafe_allow_html=True)

            angle_labels = {
                "recent_direct": "Recent Direct Work",
                "transferable_methods": "Transferable Methods",
                "interest_alignment": "Interest Alignment",
                "trajectory": "Research Trajectory"
            }

            for k, v in ang.items():
                label = angle_labels.get(k, k.replace("_", " ").title())
                color = "#22C55E" if v >= 60 else "#3B82F6" if v >= 30 else "#F59E0B"
                st.markdown(f"""
                    <div style="padding: 8px; background: rgba(255,255,255,0.02); border-radius: 6px;">
                        <div style="font-size: 11px; color: #B8C0CC; text-transform: uppercase;">{label}</div>
                        <div style="font-size: 16px; font-weight: 600; color: {color};">{v}/100</div>
                        <div style="background: rgba(255,255,255,0.1); height: 4px; border-radius: 2px; margin-top: 4px;">
                            <div style="width: {v}%; height: 100%; background: {color}; border-radius: 2px;"></div>
                        </div>
                    </div>
                """, unsafe_allow_html=True)

            st.markdown("""
                </div>
                <div class="muted-text">
                    <strong>Methodology:</strong> Each angle assessed independently (0-100) based on publication analysis,
                    stated interests, and research trajectory over past 5 years.
                </div>
            </div>
            """, unsafe_allow_html=True)

        # Strongest interest in a card
        si = llm.get("strongest_interest", {}) or {}
        if si:
            mp = si.get("maps_to", "NONE")
            mapping_status = (f"maps to {mp} ({ST_TITLE.get(mp,'')})" if mp not in ("NONE", "", None)
                           else "*no clear agenda mapping*")
            note = si.get('note', '')

            st.markdown(f"""
            <div class="card card-neutral">
                <h4>🎯 Primary Research Interest</h4>
                <div style="margin-bottom: 12px;">
                    <strong style="color: #F5F7FA; font-size: 16px;">{si.get('interest','—')}</strong>
                </div>
                <div style="margin-bottom: 8px;">
                    <strong>Agenda Mapping:</strong> {mapping_status}
                </div>
                {f'<div class="muted-text"><strong>Analysis:</strong> {note}</div>' if note else ''}
            </div>
            """, unsafe_allow_html=True)
        # Research Proposal Alignment Scores with clear explanations
        best_subthemes = (llm.get("best_subthemes") or [])[:5]
        if best_subthemes:
            st.markdown("""
            <div class="card card-neutral">
                <h4>📋 Research Proposal Alignment Analysis</h4>
                <div class="muted-text" style="margin-bottom: 16px;">
                    <strong>Legend:</strong> Subtheme ID refers to research proposal categories in the Schmidt Sciences agenda.
                    Scores reflect evidence strength (0-100): 65+ = Direct fit, 40-64 = Adjacent relevance, &lt;40 = Limited connection
                </div>
            """, unsafe_allow_html=True)

            for b in best_subthemes:
                sid = b.get("id", "?")
                s = b.get("score", 0)
                title = ST_TITLE.get(sid, "Unknown category")
                recency = b.get("recency", "?")
                angle = b.get("angle", "")
                evidence = b.get("evidence", "No evidence cited")

                # Color coding for score levels
                if s >= 65:
                    col = "#22C55E"
                    level = "Direct Fit"
                elif s >= 40:
                    col = "#3B82F6"
                    level = "Adjacent"
                else:
                    col = "#8A8F98"
                    level = "Limited"

                st.markdown(f"""
                <div style="margin-bottom: 16px; padding: 12px; border-left: 3px solid {col}; background: rgba(255,255,255,0.02);">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                        <div>
                            <strong style="color: #F5F7FA;">Proposal {sid}: {title}</strong>
                            <span class="badge" style="background: {col}; margin-left: 8px;">{level}</span>
                        </div>
                        <div style="font-size: 18px; font-weight: bold; color: {col};">{s}/100</div>
                    </div>
                    <div style="background: rgba(255,255,255,0.1); height: 6px; border-radius: 3px; margin-bottom: 8px;">
                        <div style="width: {int(s)}%; height: 100%; background: {col}; border-radius: 3px;"></div>
                    </div>
                    <div class="muted-text">
                        <strong>Timeline:</strong> {recency} | <strong>Approach:</strong> {angle}<br>
                        <strong>Evidence:</strong> {evidence[:200]}{'...' if len(evidence) > 200 else ''}
                    </div>
                </div>
                """, unsafe_allow_html=True)

            st.markdown("</div>", unsafe_allow_html=True)
        if tier == "EXCLUDED" and llm.get("out_of_scope", {}).get("flag"):
            st.error(f"Out of scope — {llm['out_of_scope'].get('area','')}: {llm['out_of_scope'].get('reason','')}")

        # Decision Matrix - Combined Evidence/Gaps/Deal-breakers (Moved to top for reviewer priority)
        strengths = llm.get("strengths") or []; gaps = llm.get("gaps") or []; stops = llm.get("deal_breakers") or []

        if strengths or gaps or stops:
            st.markdown("""
            <div class="card card-neutral">
                <h4>🎯 Decision Matrix</h4>
            """, unsafe_allow_html=True)

            # Generate final recommendation based on evidence analysis
            total_evidence = len(strengths)
            total_gaps = len(gaps)
            total_stops = len(stops)

            if total_stops > 0:
                recommendation = "❌ Not Recommended"
                rec_color = "#EF4444"
                rec_reason = f"Has {total_stops} deal-breaker(s) that prevent funding consideration"
            elif total_evidence >= 3 and total_gaps <= 1:
                recommendation = "✅ Strongly Recommended"
                rec_color = "#22C55E"
                rec_reason = f"Strong evidence portfolio ({total_evidence} strengths, {total_gaps} minor gaps)"
            elif total_evidence >= 2 or (total_evidence >= 1 and total_gaps <= 2):
                recommendation = "⚠️ Consider with Conditions"
                rec_color = "#F59E0B"
                rec_reason = f"Mixed profile ({total_evidence} strengths, {total_gaps} gaps) - review alignment carefully"
            else:
                recommendation = "❌ Limited Fit"
                rec_color = "#EF4444"
                rec_reason = f"Insufficient evidence ({total_evidence} strengths, {total_gaps} gaps)"

            # Final Recommendation Box
            st.markdown(f"""
            <div style="background: linear-gradient(135deg, {rec_color}15, {rec_color}08); border: 1px solid {rec_color}40; border-radius: 8px; padding: 16px; margin-bottom: 16px;">
                <div style="display: flex; align-items: center; margin-bottom: 8px;">
                    <h4 style="color: {rec_color}; margin: 0; margin-right: 12px;">{recommendation}</h4>
                    <span style="background: {rec_color}; color: white; padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 600;">
                        FIT SCORE: {fit_score}/100
                    </span>
                </div>
                <div style="color: #F5F7FA; margin-bottom: 8px;">{rec_reason}</div>
                <div style="color: #B8C0CC; font-size: 12px;">
                    Analysis based on {total_evidence + total_gaps + total_stops} decision factors from LLM assessment
                </div>
            </div>
            """, unsafe_allow_html=True)

            if strengths:
                strength_items = format_bullet_list(strengths, "positive")
                st.markdown(f"""
                <div style="margin-bottom: 16px;">
                    <h5 style="color: #22C55E; margin-bottom: 8px;">✅ Strongest Evidence ({len(strengths)} factors)</h5>
                    {strength_items}
                    <div style="color: #B8C0CC; font-size: 11px; margin-top: 8px;">
                        These factors strongly support funding consideration
                    </div>
                </div>
                """, unsafe_allow_html=True)

            if gaps:
                gap_items = format_bullet_list(gaps, "warning")
                st.markdown(f"""
                <div style="margin-bottom: 16px;">
                    <h5 style="color: #F59E0B; margin-bottom: 8px;">⚠️ Gaps / Debatable ({len(gaps)} factors)</h5>
                    {gap_items}
                    <div style="color: #B8C0CC; font-size: 11px; margin-top: 8px;">
                        These areas need additional consideration or may limit application strength
                    </div>
                </div>
                """, unsafe_allow_html=True)

            if stops:
                stop_items = format_bullet_list(stops, "critical")
                st.markdown(f"""
                <div style="margin-bottom: 16px;">
                    <h5 style="color: #EF4444; margin-bottom: 8px;">🚫 Deal-breakers ({len(stops)} factors)</h5>
                    {stop_items}
                    <div style="color: #B8C0CC; font-size: 11px; margin-top: 8px;">
                        These factors prevent funding recommendation under current RFP criteria
                    </div>
                </div>
                """, unsafe_allow_html=True)

            st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("#### Research focus")
        fo = d.get("focus", {})

        # Overall career focus card
        st.markdown(f"""
        <div class="card card-neutral">
            <h4>Overall (career)</h4>
            <p>{fo.get('overall','—')}</p>
        </div>
        """, unsafe_allow_html=True)

        # Recent focus card
        st.markdown(f"""
        <div class="card card-neutral">
            <h4>Recent (last 5y)</h4>
            <p>{fo.get('recent','—')}</p>
            <div class="muted-text">source: {fo.get('source','—')}</div>
        </div>
        """, unsafe_allow_html=True)

        # Top contributions section
        top_papers = (ac.get("top_cited") or [])[:config.TOP_PAPERS_SHOW]
        if top_papers:
            st.markdown("""
            <div class="card card-neutral">
                <h4>📄 Top Contributions</h4>
            """, unsafe_allow_html=True)
            for w in top_papers:
                title = w.get("title", "Title not available")
                year = w.get('year', 'N/A')
                citations = w.get('cited_by', 0)
                venue = w.get("venue", "")
                url = w.get("url", "")

                meta = f"{year}, {citations} citations"
                if venue:
                    meta += f", {venue}"

                # Only include link if URL exists and looks valid
                valid_link = ""
                if url and url.startswith(('http://', 'https://')):
                    valid_link = f' <a href="{url}" target="_blank" style="color: #3B82F6;">[view]</a>'

                st.markdown(f"""
                <div style="margin-bottom: 12px; padding-bottom: 8px; border-bottom: 1px solid rgba(255,255,255,0.1);">
                    <div style="font-weight: 500; color: #F5F7FA; margin-bottom: 4px;">{title}</div>
                    <div style="color: #B8C0CC; font-size: 13px;">{meta}{valid_link}</div>
                </div>
                """, unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.markdown("""
            <div class="card card-neutral">
                <h4>📄 Top Contributions</h4>
                <div class="muted-text">No publication data available</div>
            </div>
            """, unsafe_allow_html=True)

    # ----- RIGHT: standing + agency + win/gap panels -----
    with C2:
        st.markdown("#### Axis B · Standing & agency")
        traj = stand.get("activity_ratio")
        st.markdown(f'<span class="chip">{impact_standing(stand.get("seniority"), stand.get("h_index"))}</span>'
                    + (f'<span class="chip">5y activity {int(traj*100)}% of career h-index</span>' if traj else "")
                    + (f'<span class="chip agency">industry-active</span>' if stand.get("industry_active") else ""),
                    unsafe_allow_html=True)

        web = d.get("web_signals", {}) or {}
        if web.get("headline"):
            st.markdown(f"**Notable:** {web['headline']}")
        sigs = web.get("signals", {}) or {}
        if not sigs and not web.get("socials_from_csv"):
            st.markdown("<span class='src'>No non-academic signals found "
                        "(absence ≠ evidence of absence — see confidence).</span>", unsafe_allow_html=True)
        for cat, items in sigs.items():
            st.markdown(f"**{cat.replace('_',' ').title()}**")
            for it in (items if isinstance(items, list) else [items]):
                u = it.get("url", "")
                st.markdown(f"- {it.get('claim','')} "
                            f"<span class='src'>[{it.get('confidence','?')}]"
                            + (f" · <a href='{u}' target='_blank'>source</a>" if u else "") + "</span>",
                            unsafe_allow_html=True)
        # network / influence
        net = web.get("network", {}) or {}
        if net.get("frequent_coauthors") or net.get("funders"):
            with st.expander("Network & funding (from OpenAlex)"):
                if net.get("funders"):
                    st.markdown("**Funders on record:** " + ", ".join(net["funders"]))
                if net.get("frequent_coauthors"):
                    st.markdown("**Frequent collaborators:** " +
                                ", ".join(f'{c["name"]} ({c["papers_together"]})'
                                          for c in net["frequent_coauthors"]))
                st.markdown(f"<span class='src'>network size ≈ {net.get('network_size','?')} coauthors · "
                            "source: OpenAlex</span>", unsafe_allow_html=True)
        if web.get("socials_from_csv"):
            st.markdown(" ".join(f'<a class="chip agency" href="{u}" target="_blank">{k}</a>'
                                 for k, u in web["socials_from_csv"].items()), unsafe_allow_html=True)
        if web.get("identity_caveats"):
            st.markdown(f"<span class='src'>⚠ {web['identity_caveats']}</span>", unsafe_allow_html=True)

        with st.expander("Signal scores vs. cohort (Keyword / Semantic Match)"):
            st.markdown("<span class='leg'>Dark tick = cohort average across all loaded professors. "
                        "Keyword Match = exact text overlap; Semantic Match = conceptual overlap.</span>", unsafe_allow_html=True)
            bm, dn = sc.get("bm25", {}), sc.get("dense", {})
            ranked = sorted(SUBTHEMES, key=lambda t: (dn.get(t["id"]) or 0), reverse=True)
            for t in ranked:
                tid = t["id"]
                if (bm.get(tid, 0) > 0.1) or ((dn.get(tid) or 0) > 0.15):
                    st.markdown(f"**{tid}** {t['title'][:42]}")
                    relbar("Keyword Match", bm.get(tid), BM_AVG.get(tid, 0), "#2f6fb0")
                    relbar("Semantic Match", dn.get(tid), DN_AVG.get(tid, 0), "#7a5cc0",
                           lo=-0.1, hi=0.6)

        ex = d.get("scraped_extras", {})
        if ex:
            # Dynamic institute name from profile
            institute = d.get('institute', 'IIT')
            institute_short = institute.replace('IIT ', '').replace('Indian Institute of Technology ', '')

            # Get the appropriate profile URL
            profile_links = d.get('links', {})
            profile_url = (profile_links.get('iith_profile_url') or
                          profile_links.get('personal_website') or
                          profile_links.get('iitg_profile_url') or
                          list(profile_links.values())[0] if profile_links else '')

            with st.expander(f"From {institute_short} website (honors, projects, supervision)"):
                for k, v in ex.items():
                    st.markdown(f"**{k}:** {str(v)[:600]}")
                st.markdown(f"<span class='src'>source: {institute_short.lower()}_website · "
                            f"{profile_url}</span>", unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("**Profiles & links:** " + " · ".join(
        f"[{k.replace('_url','').replace('_',' ')}]({v})" for k, v in (d.get("links", {}) or {}).items()))


if not hasattr(st.session_state, 'sel_data') or st.session_state.sel_data is None:
    home()
else:
    detail(st.session_state.sel_data)
