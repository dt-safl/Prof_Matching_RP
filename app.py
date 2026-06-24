"""
Interpretability RFP Dashboard
Schmidt Sciences — AI Interpretability, March 2026
Detecting and mitigating deceptive behaviors in LLMs.
"""

import json, os, math, re
import html as _html
import streamlit as st

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(HERE, "data", "interp_profiles.json")

st.set_page_config(
    page_title="Interpretability RFP · Schmidt Sciences 2026",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
  html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
  .main { background: #0d1117; color: #e6edf3; }

  .prof-card {
    background: #161b22; border: 1px solid #30363d; border-radius: 10px;
    padding: 14px 18px; margin-bottom: 10px;
    transition: border-color .15s;
    content-visibility: auto; contain-intrinsic-size: 0 120px;
  }
  .prof-card:hover { border-color: #58a6ff; }
  .card-top { display: flex; align-items: flex-start; justify-content: space-between; }
  .card-name { font-size: 1.05rem; font-weight: 700; color: #e6edf3; }
  .card-meta { font-size: 0.78rem; color: #8b949e; margin-top: 2px; }

  .score-box {
    text-align: center; min-width: 68px;
    background: #0d1117; border-radius: 8px; padding: 6px 12px; margin-left: 14px;
    flex-shrink: 0;
  }
  .score-val { font-size: 1.6rem; font-weight: 800; line-height: 1; }
  .score-sub { font-size: 0.65rem; color: #6e7681; margin-top: 2px; }
  .score-high { color: #3fb950; }
  .score-mid  { color: #d29922; }
  .score-low  { color: #f85149; }
  .score-none { color: #30363d; }

  /* Cluster badges */
  .cluster-I1 { background:#0d2137; color:#58a6ff; border:1px solid #1f4a77; }
  .cluster-I2 { background:#0d2d1a; color:#3fb950; border:1px solid #1f5c34; }
  .cluster-I3 { background:#2a1a2e; color:#bc8cff; border:1px solid #5e3a8a; }
  .cluster-I4 { background:#2d2211; color:#e3b341; border:1px solid #7a5c22; }
  .cluster-badge {
    font-size: 0.70rem; font-weight: 600; border-radius: 5px;
    padding: 2px 8px; display: inline-block; margin-right: 6px;
  }

  .oos-none   { color: #3fb950; }
  .oos-low    { color: #d29922; }
  .oos-medium { color: #e3672a; }
  .oos-high   { color: #f85149; }

  .chip {
    display: inline-block; font-size: 0.68rem; border-radius: 4px;
    padding: 2px 7px; margin: 2px 3px 2px 0;
  }
  .chip-industry_funder { background:#0d2d1a; color:#3fb950; border:1px solid #1f5c34; }
  .chip-collaborator    { background:#0d1e37; color:#58a6ff; border:1px solid #1f4a77; }

  /* Cluster mini-bars */
  .bar-row { display: flex; align-items: center; gap: 8px; margin: 3px 0; }
  .bar-label { font-size: 0.68rem; color: #6e7681; width: 22px; flex-shrink: 0; }
  .bar-track { height: 6px; background: #21262d; border-radius: 3px; flex: 1; }
  .bar-fill  { height: 6px; border-radius: 3px; }

  hr { border-color: #21262d; }

  section[data-testid="stSidebar"] { background: #161b22; }
</style>
""", unsafe_allow_html=True)


# ───────────────────────────── Data ─────────────────────────────────────────

@st.cache_data(ttl=300)
def load_data():
    if not os.path.exists(DATA_PATH):
        return []
    return json.load(open(DATA_PATH))


data = load_data()
PAGE_SIZE = 25

CLUSTER_LABELS = {
    "I1": "🔍 Monitoring & Detection",
    "I2": "🎛️ Steering & Mitigation",
    "I3": "⚙️ Mechanistic Understanding",
    "I4": "📊 Applications & Evaluation",
}

SC_LABELS = {
    "SC1": "Agenda Fit",
    "SC2": "Scientific Quality",
    "SC3": "Potential Impact",
    "SC4": "Feasibility & Scope",
    "SC5": "Team Expertise",
    "SC6": "Cost Effectiveness",
}

BAR_COLORS = {
    "I1": "#58a6ff",
    "I2": "#3fb950",
    "I3": "#bc8cff",
    "I4": "#e3b341",
}


def score_color_class(s: int) -> str:
    if s >= 60:  return "score-high"
    if s >= 35:  return "score-mid"
    if s > 0:    return "score-low"
    return "score-none"


# ───────────────────────────── Header ───────────────────────────────────────

st.markdown("""
<h1 style="color:#e6edf3;font-size:1.6rem;font-weight:800;margin-bottom:2px;">
  🔍 AI Interpretability RFP — Schmidt Sciences 2026
</h1>
<p style="color:#6e7681;font-size:0.85rem;margin-top:0">
  <b>Focus:</b> Detecting &amp; mitigating deceptive behaviors in LLMs &nbsp;|&nbsp;
  Deadline: <b>May 26, 2026</b> &nbsp;|&nbsp;
  Budget: <b>$300K–$1M (1–3 years)</b>
</p>
<p style="color:#8b949e;font-size:0.8rem;max-width:960px">
  <b>Axis A</b> = best single cluster score (0–100). Four clusters:
  🔍 Monitoring/Detection &nbsp;·&nbsp; 🎛️ Steering/Mitigation &nbsp;·&nbsp;
  ⚙️ Mechanistic Understanding &nbsp;·&nbsp; 📊 Applications/Evaluation.
  Scores via Groq LLaMA-3.3-70B with full OpenAlex paper context + Claude fallback.
</p>
<hr style="margin:10px 0 16px 0">
""", unsafe_allow_html=True)

if not data:
    st.error("No data found. Run `python prep_interp.py` first to generate interp_profiles.json.")
    st.stop()


# ───────────────────────────── Sidebar ──────────────────────────────────────

with st.sidebar:
    st.markdown("### Filters")

    cluster_filter = st.multiselect(
        "Best-fit cluster",
        options=["I1", "I2", "I3", "I4"],
        format_func=lambda c: CLUSTER_LABELS.get(c, c),
        default=[],
        placeholder="All clusters",
    )

    all_insts = sorted({e.get("institute", "") for e in data if e.get("institute")})
    inst_filter = st.multiselect("Institution", all_insts, default=[], placeholder="All institutions")

    min_score = st.slider("Min Axis A score", 0, 100, 0, 5)

    oos_filter = st.multiselect(
        "Out-of-scope risk",
        ["none", "low", "medium", "high"],
        default=[],
        placeholder="Any",
    )

    only_scored = st.checkbox("Show only LLM-scored", value=True)

    sort_by = st.selectbox(
        "Sort by",
        [
            "Axis A (best cluster)",
            "I1 (Monitoring)", "I2 (Steering)", "I3 (Mechanistic)", "I4 (Applications)",
            "SC1 (Agenda Fit)", "SC2 (Sci. Quality)", "SC5 (Team Expertise)",
            "Evidence chips",
        ],
    )

    st.markdown("---")

    total    = len(data)
    scored_n = sum(1 for e in data if e.get("scored"))
    high_fit = sum(1 for e in data if e.get("axis_a", 0) >= 60)

    st.markdown(f"""
**Dataset stats**
Total candidates: **{total}**
LLM-scored: **{scored_n}**
High fit (≥60): **{high_fit}**

**Best-fit cluster**""")
    for c, label in CLUSTER_LABELS.items():
        n = sum(1 for e in data if e.get("best_cluster") == c)
        st.markdown(f"- {label}: **{n}**")

    st.markdown("---")
    st.markdown("""
**Cluster guide**
🔍 **I1** Detecting deceptive LLM behaviors (probing, whitebox)
🎛️ **I2** Steering models for truthfulness (activation patching)
⚙️ **I3** Mechanistic understanding (circuits, SAEs, causal tracing)
📊 **I4** Applications & evaluation frameworks
""")


# ───────────────────────────── Filter + Sort ────────────────────────────────

def sort_key(e):
    if sort_by == "Axis A (best cluster)":
        return e.get("axis_a", 0)
    if sort_by == "I1 (Monitoring)":
        return (e.get("cluster_scores") or {}).get("I1", 0)
    if sort_by == "I2 (Steering)":
        return (e.get("cluster_scores") or {}).get("I2", 0)
    if sort_by == "I3 (Mechanistic)":
        return (e.get("cluster_scores") or {}).get("I3", 0)
    if sort_by == "I4 (Applications)":
        return (e.get("cluster_scores") or {}).get("I4", 0)
    if sort_by == "SC1 (Agenda Fit)":
        return (e.get("selection_criteria") or {}).get("SC1", 0)
    if sort_by == "SC2 (Sci. Quality)":
        return (e.get("selection_criteria") or {}).get("SC2", 0)
    if sort_by == "SC5 (Team Expertise)":
        return (e.get("selection_criteria") or {}).get("SC5", 0)
    if sort_by == "Evidence chips":
        return len(e.get("axis_b_chips") or [])
    return e.get("axis_a", 0)


filtered = data
if only_scored:
    filtered = [e for e in filtered if e.get("scored")]
if cluster_filter:
    filtered = [e for e in filtered if e.get("best_cluster") in cluster_filter]
if inst_filter:
    filtered = [e for e in filtered if e.get("institute") in inst_filter]
if min_score > 0:
    filtered = [e for e in filtered if e.get("axis_a", 0) >= min_score]
if oos_filter:
    filtered = [e for e in filtered if e.get("out_of_scope_risk", "none") in oos_filter]

filtered = sorted(filtered, key=sort_key, reverse=True)

n_pages = max(1, math.ceil(len(filtered) / PAGE_SIZE))
if "page" not in st.session_state:
    st.session_state["page"] = 1

filter_sig = (
    tuple(sorted(cluster_filter)), tuple(sorted(inst_filter)),
    min_score, tuple(sorted(oos_filter)), only_scored, sort_by,
)
if st.session_state.get("_filter_sig") != filter_sig:
    st.session_state["_filter_sig"] = filter_sig
    st.session_state["page"] = 1

page     = st.session_state["page"]
start    = (page - 1) * PAGE_SIZE
page_data = filtered[start: start + PAGE_SIZE]

st.markdown(
    f'<p style="color:#6e7681;font-size:0.82rem;margin-bottom:8px">'
    f'Showing <b>{len(filtered)}</b> of <b>{total}</b> candidates'
    f'{"  ·  page " + str(page) + "/" + str(n_pages) if n_pages > 1 else ""}'
    f'</p>',
    unsafe_allow_html=True,
)


# ───────────────────────────── Card renderer ────────────────────────────────

def _e(s: str) -> str:
    """HTML-escape a string so dynamic content never breaks the card markup."""
    return _html.escape(str(s or ""), quote=True)


def render_card(e: dict, idx: int):
    name         = _e(e.get("name", "Unknown"))
    institute    = _e(e.get("institute", ""))
    dept         = _e(e.get("department", "") or e.get("designation", ""))
    axis_a       = e.get("axis_a", 0)
    best_cluster = e.get("best_cluster", "")
    cs           = e.get("cluster_scores") or {}
    chips        = e.get("axis_b_chips") or []
    oos_risk     = e.get("out_of_scope_risk", "none")
    ctx_flag     = e.get("context_flag")
    scored       = e.get("scored", False)
    key_ev_raw   = e.get("key_evidence", "") or ""
    industry_raw = e.get("industry_connections", "") or ""

    col_cls     = score_color_class(axis_a)
    best_label  = _e(CLUSTER_LABELS.get(best_cluster, ""))
    cluster_cls = f"cluster-{best_cluster}" if best_cluster else ""

    # Cluster mini-bars (all values are numeric/hex — safe, no escaping needed)
    bars = ""
    for c in ["I1", "I2", "I3", "I4"]:
        s   = cs.get(c, 0)
        pct = min(100, s)
        col = BAR_COLORS.get(c, "#6e7681")
        bars += (f'<div class="bar-row"><span class="bar-label">{c}</span>'
                 f'<div class="bar-track"><div class="bar-fill" style="width:{pct}%;background:{col}"></div></div>'
                 f'<span style="font-size:0.65rem;color:#6e7681;width:28px;text-align:right">{s}</span></div>')

    # Evidence chips
    chips_html = ""
    for chip in chips[:8]:
        ct     = chip.get("type", "")
        detail = _e(chip.get("detail", ""))
        label  = _e(chip.get("label", ""))
        chips_html += f'<span class="chip chip-{ct}" title="{detail}">{label}</span>'

    # OOS badge
    oos_badge = ""
    if oos_risk not in ("none", ""):
        oos_badge = f'<span class="oos-{oos_risk}" style="font-size:0.68rem">&#9888; OOS:{_e(oos_risk)}</span>'

    # Context flag
    ctx_badge = ""
    if ctx_flag:
        ctx_badge = f'<span style="font-size:0.7rem;color:#8b949e;margin-left:6px">&#9888; {_e(ctx_flag)}</span>'

    # Industry tag
    ind_badge = ""
    if industry_raw and industry_raw.lower() not in ("none found", "none", ""):
        ind_badge = f'<span style="font-size:0.68rem;color:#e3b341;margin-left:6px">&#127981; {_e(industry_raw[:70])}</span>'

    # Key evidence snippet
    kev_html = ""
    if key_ev_raw:
        snippet = _e(key_ev_raw[:150])
        kev_html = f'<div style="margin-top:4px;font-size:0.72rem;color:#8b949e;font-style:italic">{snippet}&#8230;</div>'

    score_display = str(axis_a) if scored else "&#8212;"
    score_sub     = "/ 100 &middot; best cluster" if scored else "not scored"
    paper_count   = e.get("paper_count", 0)
    paper_note    = f" &middot; {paper_count} OA papers" if paper_count > 0 else ""

    cluster_badge = (f'<span class="cluster-badge {cluster_cls}">{best_label}</span>'
                     if best_cluster else "")
    chips_div     = f'<div style="margin-top:6px">{chips_html}</div>' if chips_html else ""

    # Single-line card to avoid Streamlit markdown parser splitting the HTML block
    card_html = (
        f'<div class="prof-card">'
        f'<div class="card-top">'
        f'<div style="flex:1">'
        f'<div class="card-name">{name}</div>'
        f'<div class="card-meta">{institute} &nbsp;&middot;&nbsp; {dept}{paper_note}</div>'
        f'<div style="margin-top:6px">{cluster_badge}{oos_badge}{ctx_badge}{ind_badge}</div>'
        f'<div style="margin-top:8px">{bars}</div>'
        f'{kev_html}'
        f'{chips_div}'
        f'</div>'
        f'<div class="score-box">'
        f'<div class="score-val {col_cls}">{score_display}</div>'
        f'<div class="score-sub">{score_sub}</div>'
        f'</div>'
        f'</div>'
        f'</div>'
    )
    return card_html


# ───────────────────────────── Render loop ──────────────────────────────────
# Batch all card HTML into one st.markdown call (25→1 delta messages = faster load)
_all_cards_html = "".join(render_card(entry, idx) for idx, entry in enumerate(page_data))
st.markdown(_all_cards_html, unsafe_allow_html=True)

st.markdown('<p style="color:#30363d;font-size:0.75rem;margin:8px 0 4px 0">&#9660; Expand a row below to see detailed scores, papers &amp; funding signals</p>', unsafe_allow_html=True)

for idx, entry in enumerate(page_data):
    exp_label = f"{entry.get('name','?')[:45]}  ·  score {entry.get('axis_a',0)}"
    with st.expander(exp_label, expanded=False):
        tab_fit, tab_sc, tab_research, tab_funding, tab_raw = st.tabs(
            ["🎯 Cluster Fit", "📋 Selection Criteria", "📚 Research", "💰 Funding & Network", "🔢 Raw"]
        )

        # ── Tab: Cluster Fit ────────────────────────────────────────────
        with tab_fit:
            cs     = entry.get("cluster_scores") or {}
            cnotes = entry.get("cluster_notes") or {}
            key_ev = entry.get("key_evidence", "")
            oos_risk   = entry.get("out_of_scope_risk", "none")
            oos_reason = entry.get("out_of_scope_reason", "")

            if entry.get("scored"):
                for c, label in CLUSTER_LABELS.items():
                    score = cs.get(c, 0)
                    note  = cnotes.get(c, "")
                    col_a, col_b = st.columns([1, 4])
                    with col_a:
                        st.metric(label=label, value=f"{score}/100")
                    with col_b:
                        st.progress(score / 100)
                        if note:
                            st.caption(note)
                    st.divider()

                if key_ev:
                    st.markdown(f"**Key evidence:** {key_ev}")
                ind = entry.get("industry_connections", "")
                if ind and ind.lower() not in ("none found", ""):
                    st.info(f"**Industry connections:** {ind}")
                if oos_risk not in ("none", "") and oos_reason:
                    st.warning(f"**Out-of-scope risk ({oos_risk}):** {oos_reason}")
            else:
                st.info("This candidate hasn't been LLM-scored yet. Run `python prep_interp.py`.")

        # ── Tab: Selection Criteria ─────────────────────────────────────
        with tab_sc:
            sc     = entry.get("selection_criteria") or {}
            sc_nts = entry.get("sc_notes") or {}

            if sc:
                h1, h2, h3, h4 = st.columns([4, 1, 1, 4])
                h1.markdown("**Criterion**")
                h2.markdown("**Score**")
                h3.markdown("**Level**")
                h4.markdown("**Evidence**")
                st.divider()
                for k, label in SC_LABELS.items():
                    s     = sc.get(k, 0)
                    level = "Strong" if s >= 65 else "Moderate" if s >= 40 else "Weak" if s > 0 else "N/A"
                    note  = sc_nts.get(k, "")
                    c1, c2, c3, c4 = st.columns([4, 1, 1, 4])
                    c1.markdown(label)
                    c2.markdown(f"**{s}**")
                    c3.markdown(level)
                    c4.caption(note)
            else:
                st.info("Selection criteria not yet scored.")

        # ── Tab: Research ───────────────────────────────────────────────
        with tab_research:
            summary  = entry.get("research_summary", "")
            expertise = entry.get("expertise", "")
            verdict  = entry.get("original_verdict", "")
            oa       = entry.get("oa_enrichment") or {}
            papers   = oa.get("all_papers", []) or []
            ac       = entry.get("academic_context") or {}

            if summary:
                st.markdown(f"**Research Summary**\n\n{summary}")
            if expertise:
                st.markdown(f"**Expertise keywords:** {expertise}")

            if verdict:
                with st.expander("Prior Schmidt 2026 pipeline assessment", expanded=False):
                    st.caption(verdict)

            if papers:
                st.markdown(f"**Recent papers ({len(papers)} from OpenAlex 2020+):**")
                for p in papers[:20]:
                    yr    = p.get("year", "?")
                    title = p.get("title", "") or ""
                    st.markdown(f"- **{yr}** — {title}")
            else:
                works = (ac.get("recent_works") or [])
                if works:
                    st.markdown("**Recent papers (from profile):**")
                    for w in works:
                        title = w.get("title", "") or ""
                        yr    = w.get("year", w.get("publication_year", "?"))
                        st.markdown(f"- **{yr}** — {title}")

            h   = ac.get("h_index")
            wc  = ac.get("works_count")
            cb  = ac.get("cited_by_total")
            if any([h, wc, cb]):
                st.caption(f"h-index: {h or '?'} · works: {wc or '?'} · citations: {cb or '?'}")

        # ── Tab: Funding & Network ──────────────────────────────────────
        with tab_funding:
            oa        = entry.get("oa_enrichment") or {}
            funders   = oa.get("industry_funders") or []
            coauthors = oa.get("coauthors") or []
            ind_conn  = entry.get("industry_connections", "")

            if ind_conn and ind_conn.lower() not in ("none found", ""):
                st.info(f"**LLM-extracted industry signals:** {ind_conn}")

            if funders:
                st.markdown("**Industry / notable funders (OpenAlex):**")
                for f in funders:
                    yr    = f.get("year", "")
                    paper = (f.get("paper_title", "") or "").replace("_", r"\_").replace("*", r"\*")
                    fname = (f.get("funder", "") or "").replace("_", r"\_")
                    st.markdown(f"- **{fname}** ({yr}) — {paper}")
            else:
                st.markdown("*No industry funder signals found in OpenAlex papers.*")

            if coauthors:
                st.markdown("**Notable co-authors (joint papers since 2020):**")
                for c in coauthors[:6]:
                    insts = ", ".join(c.get("institutions", []))
                    n     = c.get("papers_together", 1)
                    cname = (c.get("name", "") or "").replace("_", r"\_")
                    st.markdown(f"- **{cname}** ({n} papers) — {insts}")

            links = entry.get("links") or {}
            if any(links.values()):
                st.markdown("**Profile links:**")
                for k, url in links.items():
                    if url:
                        st.markdown(f"- [{k}]({url})")

        # ── Tab: Raw ────────────────────────────────────────────────────
        with tab_raw:
            cs = entry.get("cluster_scores") or {}
            sc = entry.get("selection_criteria") or {}
            cn = entry.get("cluster_notes") or {}
            sn = entry.get("sc_notes") or {}

            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**Cluster scores & notes**")
                for c in ["I1", "I2", "I3", "I4"]:
                    note = cn.get(c, "")
                    st.markdown(f"`{c}` **{cs.get(c, 0)}** — {CLUSTER_LABELS.get(c,'')}")
                    if note:
                        st.caption(f"  {note}")
            with col2:
                st.markdown("**Selection criteria & notes**")
                for k, label in SC_LABELS.items():
                    note = sn.get(k, "")
                    st.markdown(f"`{k}` **{sc.get(k, 0)}** — {label}")
                    if note:
                        st.caption(f"  {note}")

            st.markdown(f"""
**Metadata:**
- Best cluster: `{entry.get('best_cluster', '')}`  ({CLUSTER_LABELS.get(entry.get('best_cluster',''), '')})
- Axis A: **{entry.get('axis_a', 0)}** / 100
- OOS risk: `{entry.get('out_of_scope_risk', 'none')}`
- Papers (OA): {(entry.get('oa_enrichment') or {}).get('total_works_fetched', 0)}
- Context flag: `{entry.get('context_flag') or 'none'}`
- Original Schmidt fit: {entry.get('original_fit', 0):.1f}
""")
            email = entry.get("email", "")
            if email:
                st.markdown(f"**Email:** {email}")



# ───────────────────────────── Pagination ───────────────────────────────────

if n_pages > 1:
    st.markdown("---")
    cols = st.columns([1, 2, 1])
    with cols[0]:
        if page > 1:
            if st.button("← Previous"):
                st.session_state["page"] = page - 1
                st.rerun()
    with cols[1]:
        st.markdown(
            f'<p style="text-align:center;color:#6e7681;font-size:0.82rem">Page {page} / {n_pages}</p>',
            unsafe_allow_html=True,
        )
    with cols[2]:
        if page < n_pages:
            if st.button("Next →"):
                st.session_state["page"] = page + 1
                st.rerun()
