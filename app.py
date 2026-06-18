"""
Multi-Agent AI Safety RFP Dashboard
Joint funding call: Schmidt Sciences · Google DeepMind · ARIA · Cooperative AI Foundation · Google.org
Deadline: August 8, 2026

Entirely separate from Schmidt 2026 dashboard. No shared scores.
"""

import json, os, math, re
import streamlit as st

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(HERE, "data", "maas_profiles.json")

st.set_page_config(
    page_title="MAAS RFP · Multi-Agent AI Safety",
    page_icon="🤝",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────── CSS ────────────────────────────────────────────────
st.markdown("""
<style>
  html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
  .main { background: #0f1117; color: #e8eaf0; }

  /* Card */
  .prof-card {
    background: #1a1e2e; border: 1px solid #2d3148; border-radius: 10px;
    padding: 14px 18px; margin-bottom: 10px; cursor: pointer;
    transition: border-color .15s;
  }
  .prof-card:hover { border-color: #5b6af0; }
  .card-top { display: flex; align-items: flex-start; justify-content: space-between; }
  .card-name { font-size: 1.05rem; font-weight: 700; color: #e8eaf0; }
  .card-meta { font-size: 0.78rem; color: #8b93b8; margin-top: 2px; }

  /* Axis A score box */
  .score-box {
    text-align: center; min-width: 68px;
    background: #111520; border-radius: 8px; padding: 6px 12px; margin-left: 14px;
    flex-shrink: 0;
  }
  .score-val { font-size: 1.6rem; font-weight: 800; line-height: 1; }
  .score-sub { font-size: 0.65rem; color: #6b7394; margin-top: 2px; }
  .score-high { color: #68d391; }
  .score-mid  { color: #f6e05e; }
  .score-low  { color: #fc8181; }
  .score-none { color: #4a5178; }

  /* Cluster badge */
  .cluster-S1 { background:#1a2a3a; color:#63b3ed; border:1px solid #2b4560; }
  .cluster-S2 { background:#1a2e1a; color:#68d391; border:1px solid #2b4d2b; }
  .cluster-S3 { background:#2a1a2e; color:#b794f4; border:1px solid #4d2b60; }
  .cluster-S4 { background:#2e2a1a; color:#f6ad55; border:1px solid #604d2b; }
  .cluster-badge {
    font-size: 0.70rem; font-weight: 600; border-radius: 5px;
    padding: 2px 8px; display: inline-block; margin-right: 6px;
  }

  /* OOS risk */
  .oos-none   { color: #68d391; }
  .oos-low    { color: #f6e05e; }
  .oos-medium { color: #f6ad55; }
  .oos-high   { color: #fc8181; }

  /* Evidence chips */
  .chip {
    display: inline-block; font-size: 0.68rem; border-radius: 4px;
    padding: 2px 7px; margin: 2px 3px 2px 0;
  }
  .chip-industry_funder { background:#1a2a1a; color:#68d391; border:1px solid #2d4d2d; }
  .chip-collaborator    { background:#1a1a2a; color:#63b3ed; border:1px solid #2d2d4d; }
  .chip-award           { background:#2a1a1a; color:#fc8181; border:1px solid #4d2d2d; }
  .chip-startup         { background:#2a2a1a; color:#f6e05e; border:1px solid #4d4d2d; }
  .chip-advisory        { background:#2a1a2a; color:#b794f4; border:1px solid #4d2d4d; }

  /* Cluster mini-bars */
  .bar-row { display: flex; align-items: center; gap: 8px; margin: 3px 0; }
  .bar-label { font-size: 0.68rem; color: #6b7394; width: 22px; flex-shrink: 0; }
  .bar-track { height: 6px; background: #1e2236; border-radius: 3px; flex: 1; }
  .bar-fill { height: 6px; border-radius: 3px; }

  /* SC table */
  .sc-table { font-size: 0.8rem; border-collapse: collapse; width: 100%; }
  .sc-table td, .sc-table th { padding: 4px 8px; }
  .sc-table th { color: #6b7394; font-weight: 500; border-bottom: 1px solid #2d3148; }
  .sc-table tr:nth-child(even) td { background: #141825; }

  /* Context flag */
  .ctx-flag { font-size: 0.7rem; color: #f6ad55; }

  /* Divider */
  hr { border-color: #2d3148; }

  /* Sidebar */
  section[data-testid="stSidebar"] { background: #141825; }
</style>
""", unsafe_allow_html=True)


# ─────────────────────── Data ────────────────────────────────────────────────
@st.cache_data(ttl=300)
def load_data():
    if not os.path.exists(DATA_PATH):
        return []
    return json.load(open(DATA_PATH))


data = load_data()
PAGE_SIZE = 25

CLUSTER_LABELS = {
    "S1": "🧪 Sandboxes & Testbeds",
    "S2": "🔬 Science of Agent Networks",
    "S3": "🔐 Agent Infrastructure",
    "S4": "🛡️ Oversight & Control",
}
CLUSTER_SHORT = {"S1": "S1", "S2": "S2", "S3": "S3", "S4": "S4"}

SC_LABELS = {
    "SC1": "Agenda Fit",
    "SC2": "Scientific Quality",
    "SC3": "Potential Impact",
    "SC4": "Philanthropic Fit",
    "SC5": "Feasibility",
    "SC6": "Team Expertise",
    "SC7": "Cost Appropriate",
}

BAR_COLORS = {"S1": "#63b3ed", "S2": "#68d391", "S3": "#b794f4", "S4": "#f6ad55"}


def score_color_class(s: int) -> str:
    if s >= 65:
        return "score-high"
    if s >= 40:
        return "score-mid"
    if s > 0:
        return "score-low"
    return "score-none"


def cluster_color(pct: float, cluster: str) -> str:
    base = {"S1": "63b3ed", "S2": "68d391", "S3": "b794f4", "S4": "f6ad55"}.get(cluster, "6b7394")
    return f"#{base}"


# ─────────────────────── Header ─────────────────────────────────────────────
st.markdown("""
<h1 style="color:#e8eaf0;font-size:1.6rem;font-weight:800;margin-bottom:2px;">
  🤝 Multi-Agent AI Safety RFP
</h1>
<p style="color:#6b7394;font-size:0.85rem;margin-top:0">
  <b>Schmidt Sciences · Google DeepMind · ARIA · Cooperative AI Foundation · Google.org</b> &nbsp;|&nbsp;
  Deadline: <b>August 8, 2026</b> &nbsp;|&nbsp;
  Tier 1: up to $300K · Tier 2: $300K–$1M
</p>
<p style="color:#8b93b8;font-size:0.8rem;max-width:900px">
  <b>Axis A</b> = best single cluster fit score (0–100). Researchers specialise —
  one strong cluster beats a mediocre spread. &nbsp;<b>Axis B</b> = evidence chips
  (industry funders, collaborators, awards). Scores from Groq LLaMA-3.3-70B with
  full OpenAlex paper context.
</p>
<hr style="margin:10px 0 16px 0">
""", unsafe_allow_html=True)

if not data:
    st.error("No data found. Run `python prep_maas.py` first to generate maas_profiles.json.")
    st.stop()

# ─────────────────────── Sidebar ────────────────────────────────────────────
with st.sidebar:
    st.markdown("### Filters")

    # Cluster filter
    all_clusters = ["S1", "S2", "S3", "S4"]
    cluster_filter = st.multiselect(
        "Best-fit cluster",
        options=all_clusters,
        format_func=lambda c: CLUSTER_LABELS.get(c, c),
        default=[],
        placeholder="All clusters",
    )

    # Institute filter
    all_insts = sorted({e.get("institute", "") for e in data if e.get("institute")})
    inst_filter = st.multiselect("Institution", all_insts, default=[], placeholder="All institutions")

    # Score range
    min_score = st.slider("Min Axis A score", 0, 100, 0, 5)

    # OOS risk filter
    oos_filter = st.multiselect(
        "Out-of-scope risk",
        ["none", "low", "medium", "high"],
        default=[],
        placeholder="Any",
    )

    # Show only scored
    only_scored = st.checkbox("Show only LLM-scored", value=True)

    # Sort
    sort_by = st.selectbox(
        "Sort by",
        ["Axis A (best cluster)", "S1 score", "S2 score", "S3 score", "S4 score",
         "SC1 (Agenda Fit)", "SC6 (Team Expertise)", "Evidence chips"],
    )

    st.markdown("---")

    # Stats
    total = len(data)
    scored_n = sum(1 for e in data if e.get("scored"))
    st.markdown(f"""
    **Dataset stats**
    Total candidates: **{total}**
    LLM-scored: **{scored_n}**

    **Clusters (best fit)**
    """)
    for c in ["S1", "S2", "S3", "S4"]:
        n = sum(1 for e in data if e.get("best_cluster") == c)
        label = CLUSTER_LABELS.get(c, c)
        st.markdown(f"- {label}: **{n}**")

    st.markdown("---")
    st.markdown("""
    **Cluster guide**
    🧪 **S1** Testbeds & Sandboxes
    🔬 **S2** Agent Network Science
    🔐 **S3** Agent Infrastructure
    🛡️ **S4** Oversight & Control
    """)


# ─────────────────────── Filter + Sort ─────────────────────────────────────
def sort_key(e):
    if sort_by == "Axis A (best cluster)":
        return e.get("axis_a", 0)
    if sort_by == "S1 score":
        return (e.get("cluster_scores") or {}).get("S1", 0)
    if sort_by == "S2 score":
        return (e.get("cluster_scores") or {}).get("S2", 0)
    if sort_by == "S3 score":
        return (e.get("cluster_scores") or {}).get("S3", 0)
    if sort_by == "S4 score":
        return (e.get("cluster_scores") or {}).get("S4", 0)
    if sort_by == "SC1 (Agenda Fit)":
        return (e.get("selection_criteria") or {}).get("SC1", 0)
    if sort_by == "SC6 (Team Expertise)":
        return (e.get("selection_criteria") or {}).get("SC6", 0)
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

# Pagination
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

page = st.session_state["page"]
start = (page - 1) * PAGE_SIZE
page_data = filtered[start: start + PAGE_SIZE]

# Results count header
st.markdown(
    f'<p style="color:#6b7394;font-size:0.82rem;margin-bottom:8px">'
    f'Showing <b>{len(filtered)}</b> of <b>{total}</b> candidates'
    f'{"  ·  page " + str(page) + "/" + str(n_pages) if n_pages > 1 else ""}'
    f'</p>',
    unsafe_allow_html=True,
)


# ─────────────────────── Card renderer ──────────────────────────────────────
def render_card(e: dict, idx: int):
    name = e.get("name", "Unknown")
    institute = e.get("institute", "")
    dept = e.get("department", "")
    designation = e.get("designation", "")
    axis_a = e.get("axis_a", 0)
    best_cluster = e.get("best_cluster", "")
    cluster_scores = e.get("cluster_scores") or {}
    sc = e.get("selection_criteria") or {}
    chips = e.get("axis_b_chips") or []
    oos_risk = e.get("out_of_scope_risk", "none")
    ctx_flag = e.get("context_flag")
    scored = e.get("scored", False)

    col_cls = score_color_class(axis_a)
    best_label = CLUSTER_LABELS.get(best_cluster, "")
    cluster_cls = f"cluster-{best_cluster}" if best_cluster else ""

    # Cluster mini-bars HTML
    bars_html = ""
    for c in ["S1", "S2", "S3", "S4"]:
        s = cluster_scores.get(c, 0)
        pct = min(100, s)
        col = BAR_COLORS.get(c, "#6b7394")
        bars_html += (
            f'<div class="bar-row">'
            f'<span class="bar-label">{c}</span>'
            f'<div class="bar-track"><div class="bar-fill" style="width:{pct}%;background:{col}"></div></div>'
            f'<span style="font-size:0.65rem;color:#6b7394;width:28px;text-align:right">{s}</span>'
            f'</div>'
        )

    # Evidence chips HTML
    chips_html = ""
    for chip in chips[:8]:
        ct = chip.get("type", "")
        chips_html += f'<span class="chip chip-{ct}" title="{chip.get("detail","")}">{chip.get("label","")}</span>'

    # OOS risk badge
    oos_cls = f"oos-{oos_risk}"
    oos_html = f'<span class="{oos_cls}" style="font-size:0.68rem">⚠ OOS:{oos_risk}</span>' if oos_risk not in ("none", "") else ""

    score_display = str(axis_a) if scored else "—"
    score_sub = "/ 100 · best cluster" if scored else "not scored"

    paper_count = e.get("paper_count", 0)
    paper_note = f" · {paper_count} OA papers" if paper_count > 0 else ""

    card_html = f"""
    <div class="prof-card">
      <div class="card-top">
        <div style="flex:1">
          <div class="card-name">{name}</div>
          <div class="card-meta">{institute} &nbsp;·&nbsp; {dept or designation}{paper_note}</div>
          <div style="margin-top:6px">
            {f'<span class="cluster-badge {cluster_cls}">{best_label}</span>' if best_cluster else ''}
            {oos_html}
            {f'<span class="ctx-flag" style="margin-left:6px">⚠ {ctx_flag}</span>' if ctx_flag else ''}
          </div>
          <div style="margin-top:8px">{bars_html}</div>
          {f'<div style="margin-top:6px">{chips_html}</div>' if chips_html else ''}
        </div>
        <div class="score-box">
          <div class="score-val {col_cls}">{score_display}</div>
          <div class="score-sub">{score_sub}</div>
        </div>
      </div>
    </div>
    """
    return card_html


# ─────────────────────── Render loop ────────────────────────────────────────
for idx, entry in enumerate(page_data):
    card_html = render_card(entry, idx)
    with st.expander(entry.get("name", "?"), expanded=False):
        st.markdown(card_html, unsafe_allow_html=True)

        # Detail tabs
        tab_fit, tab_sc, tab_research, tab_funding, tab_raw = st.tabs(
            ["🎯 Cluster Fit", "📋 Selection Criteria", "📚 Research", "💰 Funding & Network", "🔢 Raw"]
        )

        with tab_fit:
            cs = entry.get("cluster_scores") or {}
            notes = entry.get("cluster_notes") or {}
            key_ev = entry.get("key_evidence", "")
            oos_risk = entry.get("out_of_scope_risk", "none")
            oos_reason = entry.get("out_of_scope_reason", "")

            if entry.get("scored"):
                for c, label in CLUSTER_LABELS.items():
                    score = cs.get(c, 0)
                    note = notes.get(c, "")
                    col_a, col_b = st.columns([1, 4])
                    with col_a:
                        cls = score_color_class(score)
                        st.markdown(f'<span class="{cls}" style="font-size:1.4rem;font-weight:800">{score}</span><br><span style="color:#6b7394;font-size:0.7rem">{label}</span>', unsafe_allow_html=True)
                    with col_b:
                        st.progress(score / 100)
                        if note:
                            st.markdown(f'<span style="color:#8b93b8;font-size:0.82rem">{note}</span>', unsafe_allow_html=True)
                    st.markdown("---")

                if key_ev:
                    st.markdown(f"**Key evidence:** {key_ev}")
                if oos_risk not in ("none", "") and oos_reason:
                    st.warning(f"**Out-of-scope risk ({oos_risk}):** {oos_reason}")
            else:
                st.info("This candidate hasn't been LLM-scored yet. Run `prep_maas.py` to score.")

        with tab_sc:
            sc = entry.get("selection_criteria") or {}
            if sc:
                sc_data = []
                for k, label in SC_LABELS.items():
                    sc_data.append({"Criterion": label, "Score": sc.get(k, 0)})

                sc_html = '<table class="sc-table"><tr><th>Criterion</th><th>Score</th><th>Level</th></tr>'
                for row in sc_data:
                    s = row["Score"]
                    cls = score_color_class(s)
                    level = "Strong" if s >= 65 else "Moderate" if s >= 40 else "Weak" if s > 0 else "N/A"
                    sc_html += f'<tr><td>{row["Criterion"]}</td><td class="{cls}">{s}</td><td style="color:#6b7394">{level}</td></tr>'
                sc_html += "</table>"
                st.markdown(sc_html, unsafe_allow_html=True)
            else:
                st.info("Selection criteria not yet scored.")

        with tab_research:
            summary = entry.get("research_summary", "")
            expertise = entry.get("expertise", "")
            verdict = entry.get("original_verdict", "")
            oa = entry.get("oa_enrichment") or {}
            papers = oa.get("all_papers", []) or []

            if summary:
                st.markdown("**Research Summary**")
                st.markdown(f'<p style="color:#c4cbdf;font-size:0.85rem">{summary}</p>', unsafe_allow_html=True)
            if expertise:
                st.markdown(f'**Expertise:** <span style="color:#8b93b8;font-size:0.82rem">{expertise}</span>', unsafe_allow_html=True)
            if verdict:
                st.markdown("**Prior assessment (Schmidt 2026 pipeline):**")
                st.markdown(f'<p style="color:#6b7394;font-size:0.8rem;font-style:italic">{verdict}</p>', unsafe_allow_html=True)

            if papers:
                st.markdown(f"**Recent papers ({len(papers)} shown, from OpenAlex):**")
                for p in papers[:20]:
                    yr = p.get("year", "?")
                    title = p.get("title", "")
                    st.markdown(f'<p style="margin:2px 0;font-size:0.8rem;color:#c4cbdf">[{yr}] {title}</p>', unsafe_allow_html=True)
            else:
                # Fallback to academic context
                ac = entry.get("academic_context") or {}
                works = ac.get("recent_works") or []
                if works:
                    st.markdown("**Recent papers (from profile):**")
                    for w in works:
                        title = w.get("title", "")
                        yr = w.get("year", w.get("publication_year", "?"))
                        st.markdown(f'<p style="margin:2px 0;font-size:0.8rem;color:#c4cbdf">[{yr}] {title}</p>', unsafe_allow_html=True)

            # Academic metrics
            ac = entry.get("academic_context") or {}
            h = ac.get("h_index")
            wc = ac.get("works_count")
            cb = ac.get("cited_by_total")
            if any([h, wc, cb]):
                st.markdown(
                    f'<p style="color:#4a5178;font-size:0.75rem;margin-top:8px">'
                    f'h-index: {h or "?"} &nbsp;·&nbsp; works: {wc or "?"} &nbsp;·&nbsp; citations: {cb or "?"}'
                    f'</p>',
                    unsafe_allow_html=True,
                )

        with tab_funding:
            oa = entry.get("oa_enrichment") or {}
            funders = oa.get("industry_funders") or []
            coauthors = oa.get("coauthors") or []
            chips = entry.get("axis_b_chips") or []

            if funders:
                st.markdown("**Industry / notable funders (from OpenAlex):**")
                for f in funders:
                    yr = f.get("year", "")
                    paper = f.get("paper_title", "")
                    st.markdown(f'- **{f["funder"]}** ({yr}) — _{paper}_')
            else:
                st.markdown("*No industry funder signals found in OpenAlex.*")

            if coauthors:
                st.markdown("**Notable co-authors (by joint papers since 2020):**")
                for c in coauthors[:6]:
                    insts = ", ".join(c.get("institutions", []))
                    n = c.get("papers_together", 1)
                    st.markdown(f'- **{c["name"]}** ({n} papers) — _{insts}_')

            # Links
            links = entry.get("links") or {}
            if any(links.values()):
                st.markdown("**Profile links:**")
                for k, url in links.items():
                    if url:
                        st.markdown(f"- [{k}]({url})")

        with tab_raw:
            # Show raw cluster + SC scores as compact table
            cs = entry.get("cluster_scores") or {}
            sc = entry.get("selection_criteria") or {}
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**Cluster scores**")
                for c in ["S1", "S2", "S3", "S4"]:
                    st.markdown(f'`{c}`: {cs.get(c, 0)}')
            with col2:
                st.markdown("**Selection criteria**")
                for k, label in SC_LABELS.items():
                    st.markdown(f'`{k}` {label}: {sc.get(k, 0)}')

            st.markdown(f"""
**Metadata:**
- Best cluster: `{entry.get('best_cluster','')}`
- Axis A (best cluster score): **{entry.get('axis_a', 0)}**
- OOS risk: `{entry.get('out_of_scope_risk','none')}`
- Papers (OA): {(entry.get('oa_enrichment') or {}).get('total_works_fetched', 0)}
- Context flag: `{entry.get('context_flag') or 'none'}`
- Original Schmidt fit score: {entry.get('original_fit', 0)}
""")
            email = entry.get("email", "")
            if email:
                st.markdown(f"**Email:** {email}")

# ─────────────────────── Pagination ─────────────────────────────────────────
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
            f'<p style="text-align:center;color:#6b7394;font-size:0.82rem">Page {page} / {n_pages}</p>',
            unsafe_allow_html=True,
        )
    with cols[2]:
        if page < n_pages:
            if st.button("Next →"):
                st.session_state["page"] = page + 1
                st.rerun()
