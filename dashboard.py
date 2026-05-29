"""Stage E — DASHBOARD (Streamlit).

Run:  streamlit run dashboard.py

Screen 1: ranked list for a pillar / sub-theme, sortable, with fit + confidence badges.
Screen 2: per-prof detail card — verdict, interests, cited strong/weak/debatable/standout
          points, metrics, signal chips, per-sub-theme bar, publications, notes.
"""
import json
import pandas as pd
import streamlit as st

import db

st.set_page_config(page_title="RFP Matcher", layout="wide", page_icon="🎯")

# ---------- styling ----------
st.markdown("""
<style>
.badge{display:inline-block;padding:2px 10px;border-radius:12px;font-size:12px;font-weight:600;margin-right:6px}
.STRONG_FIT{background:#1b5e20;color:#fff}.PLAUSIBLE_FIT{background:#2e7d32;color:#fff}
.WEAK_FIT{background:#f9a825;color:#000}.NOT_A_FIT{background:#9e9e9e;color:#fff}
.HIGH{background:#1565c0;color:#fff}.MEDIUM{background:#7e57c2;color:#fff}.LOW{background:#c62828;color:#fff}
.chip{display:inline-block;padding:2px 9px;border-radius:8px;font-size:12px;background:#eceff1;color:#263238;margin-right:6px}
.award{display:inline-block;padding:2px 9px;border-radius:8px;font-size:12px;background:#fff3e0;color:#e65100;margin-right:6px;border:1px solid #ffb74d}
.pt{margin:3px 0}.ev{color:#607d8b;font-size:12px}
</style>
""", unsafe_allow_html=True)

PILLARS = {1: "Characterizing Misalignment", 2: "Measurements & Interventions",
           3: "Oversight & Multi-agent"}


def badge(text, cls):
    return f"<span class='badge {cls}'>{text}</span>"


def J(v):
    return db.J(v) or []


# ---------- sidebar ----------
st.sidebar.title("🎯 RFP Matcher")
runs = db.get_runs()
if not runs:
    st.warning("No scored data yet. Run the pipeline first:\n\n"
               "`python run.py --csv <path> --pillar 1`")
    st.stop()
run_id = st.sidebar.selectbox("Run", runs)
pillar = st.sidebar.selectbox("Pillar", list(PILLARS), format_func=lambda p: f"Pillar {p}: {PILLARS[p]}")

themes = db.get_sub_themes(pillar)
theme_opts = ["ALL"] + [t["sub_theme_id"] for t in themes]
theme_labels = {t["sub_theme_id"]: f"{t['sub_theme_id']}: {t['title']}" for t in themes}
theme_labels["ALL"] = "All sub-themes (best per prof)"
sub_theme = st.sidebar.selectbox("Sub-theme", theme_opts, format_func=lambda s: theme_labels[s])

conf_filter = st.sidebar.multiselect("Confidence", ["HIGH", "MEDIUM", "LOW"],
                                     default=["HIGH", "MEDIUM", "LOW"])
verdict_filter = st.sidebar.multiselect(
    "Verdict", ["STRONG_FIT", "PLAUSIBLE_FIT", "WEAK_FIT", "NOT_A_FIT"],
    default=["STRONG_FIT", "PLAUSIBLE_FIT", "WEAK_FIT"])

# ---------- data ----------
rows = db.get_ranked(run_id, sub_theme_id=sub_theme, pillar=pillar)
rows = [r for r in rows if r["confidence"] in conf_filter and r["fit_verdict"] in verdict_filter]

st.title(f"Pillar {pillar} — {PILLARS[pillar]}")
st.caption(f"{len(rows)} professors · run `{run_id}` · "
           f"{'sub-theme ' + sub_theme if sub_theme != 'ALL' else 'ranked by best sub-theme fit'}")

if not rows:
    st.info("No professors match the current filters.")
    st.stop()

# ===== Screen 1: ranked list =====
df = pd.DataFrame([{
    "rank": i + 1, "name": r["name"], "dept": r.get("department") or "",
    "designation": r.get("designation") or "", "theme": r["sub_theme_id"],
    "composite": round(r["composite"], 1), "verdict": r["fit_verdict"],
    "confidence": r["confidence"], "summary": r.get("one_line_summary") or "",
} for i, r in enumerate(rows)])

st.dataframe(df, width="stretch", hide_index=True,
             column_config={"composite": st.column_config.NumberColumn("score", format="%.1f")})

# ===== Screen 2: detail card =====
st.divider()
name_to_pid = {f"{r['name']}  ({r['sub_theme_id']}, {r['composite']:.1f})": (r["prof_id"], r["sub_theme_id"])
               for r in rows}
pick = st.selectbox("🔍 Open detail card for:", list(name_to_pid))
prof_id, picked_theme = name_to_pid[pick]
prof = db.get_prof(prof_id)
all_scores = db.get_scores_for_prof(prof_id, run_id, pillar=pillar)
sc = next((s for s in all_scores if s["sub_theme_id"] == picked_theme), all_scores[0])
theme = next(t for t in themes if t["sub_theme_id"] == picked_theme)

# header
st.markdown(f"## {prof['name']}")
st.caption(f"{prof.get('designation') or ''} · {prof.get('department') or ''} · {prof.get('institute') or ''}")
st.markdown(
    f"**{picked_theme}: {theme['title']}** &nbsp; "
    + badge(sc["fit_verdict"].replace("_", " "), sc["fit_verdict"])
    + badge(f"confidence: {sc['confidence']}", sc["confidence"]),
    unsafe_allow_html=True)
st.markdown(f"> {sc.get('one_line_summary') or ''}")

# metrics boxes
m = st.columns(6)
m[0].metric("h-index", prof.get("h_index") or "—")
m[1].metric("citations", f"{prof.get('citations_total') or 0:,}")
m[2].metric("cites (5y)", f"{prof.get('citations_5y') or 0:,}")
m[3].metric("papers", prof.get("works_count") or 0)
m[4].metric("papers (5y)", prof.get("works_count_5y") or 0)
yrs = (prof.get("last_pub_year") or 0) - (prof.get("first_pub_year") or 0)
m[5].metric("years active", yrs if yrs > 0 else "—")

# award + signal chips
awards = [(prof.get(f), n) for f, n in (("is_bhatnagar", "Bhatnagar"), ("is_jc_bose", "JC Bose"),
          ("is_insa_fellow", "INSA"), ("is_padma", "Padma"), ("is_infosys_prize", "Infosys Prize"))]
award_html = "".join(f"<span class='award'>🏅 {n}</span>" for v, n in awards if v)
chips = (f"<span class='chip'>BM25 {sc.get('bm25_score')}</span>"
         f"<span class='chip'>embed {sc.get('embedding_score')}</span>"
         f"<span class='chip'>composite {sc.get('composite'):.1f}</span>"
         f"<span class='chip'>topical {sc.get('topical_alignment')}/3</span>"
         f"<span class='chip'>method {sc.get('methodological_fit')}/3</span>"
         f"<span class='chip'>recency {sc.get('recency_focus')}/3</span>"
         f"<span class='chip'>depth {sc.get('depth_competence')}/3</span>"
         f"<span class='chip'>OOS-risk {sc.get('out_of_scope_risk')}/3</span>")
st.markdown(award_html + chips, unsafe_allow_html=True)
st.caption(f"scored by `{sc.get('llm_model')}` · abstract coverage "
           f"{int((prof.get('abstract_coverage') or 0)*100)}% · enrich quality {prof.get('enrich_quality')}")

# interests
ci, ri = st.columns(2)
with ci:
    st.markdown("**Career interests**")
    for it in J(prof.get("interests_career")):
        ex = "; ".join(filter(None, it.get("example_papers", [])))[:90]
        st.markdown(f"<div class='pt'>• {it.get('phrase')}<br><span class='ev'>{ex}</span></div>",
                    unsafe_allow_html=True)
with ri:
    st.markdown("**Recent focus (last 5y)**")
    for it in J(prof.get("interests_recent")):
        ex = "; ".join(filter(None, it.get("example_papers", [])))[:90]
        st.markdown(f"<div class='pt'>• {it.get('phrase')}<br><span class='ev'>{ex}</span></div>",
                    unsafe_allow_html=True)

# points
def render_points(title, key, icon):
    pts = J(sc.get(key))
    if not pts:
        return
    st.markdown(f"**{icon} {title}**")
    for p in pts:
        st.markdown(f"<div class='pt'>• {p.get('point')}<br>"
                    f"<span class='ev'>↳ {p.get('evidence')}</span></div>", unsafe_allow_html=True)

c1, c2 = st.columns(2)
with c1:
    render_points("Strong points", "strong_points", "✅")
    render_points("Standout facts", "standout_facts", "⭐")
with c2:
    render_points("Gaps / weak points", "weak_points", "⚠️")
    render_points("Debatable / worth checking", "debatable_points", "❓")

# per-sub-theme bar across the pillar
st.markdown("**Fit across this pillar**")
bar = pd.DataFrame([{"sub_theme": s["sub_theme_id"], "composite": round(s["composite"], 1)}
                    for s in sorted(all_scores, key=lambda x: x["sub_theme_id"])]).set_index("sub_theme")
st.bar_chart(bar, height=180)

# publications (the raw evidence)
with st.expander(f"📚 Publications ({len(db.get_publications(prof_id))})"):
    pubs = db.get_publications(prof_id)
    pdf = pd.DataFrame([{"year": p["year"], "title": p["title"], "venue": p.get("venue"),
                         "cites": p.get("citations")} for p in pubs])
    st.dataframe(pdf, width="stretch", hide_index=True)

# external links
links = []
if prof.get("openalex_id"):
    links.append(f"[OpenAlex]({prof['openalex_id']})")
if prof.get("scholar_id"):
    links.append(f"[Scholar](https://scholar.google.com/citations?user={prof['scholar_id']})")
if prof.get("homepage_url"):
    links.append(f"[Homepage]({prof['homepage_url']})")
if prof.get("orcid"):
    links.append(f"[ORCID](https://orcid.org/{prof['orcid']})")
if links:
    st.markdown(" · ".join(links))

# LinkedIn manual paste + notes
with st.expander("✍️ Reviewer notes & manual context"):
    existing = db.get_annotation(prof_id, picked_theme)
    status = st.radio("Decision", ["relevant", "not_relevant", "look_closer", "contacted"],
                      horizontal=True,
                      index=["relevant", "not_relevant", "look_closer", "contacted"].index(
                          existing["status"]) if existing and existing.get("status") in
                      ["relevant", "not_relevant", "look_closer", "contacted"] else 2)
    note = st.text_area("Note", value=existing["note"] if existing else "")
    if st.button("Save note"):
        db.save_annotation(prof_id, picked_theme, status, note)
        st.success("Saved.")
