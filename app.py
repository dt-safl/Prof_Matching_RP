"""Streamlit dashboard.  Run:  streamlit run app.py
Reads data/enriched_profiles.json (produced by pipeline.py). Ranking page -> click -> detail.
"""
import json, os
import streamlit as st
import config
from agenda import SUBTHEMES

st.set_page_config(page_title="Researcher–Proposal Match", layout="wide")

TIER_COLOR = {"STRONG": "#1f8a4c", "POSSIBLE": "#c98a00", "WEAK": "#8a8f98", "OUT_OF_SCOPE": "#b3382f"}
TIER_LABEL = {"STRONG": "Strong fit", "POSSIBLE": "Possible fit", "WEAK": "Weak / no fit",
              "OUT_OF_SCOPE": "Out of scope"}
SUBTHEME_TITLE = {t["id"]: t["title"] for t in SUBTHEMES}

st.markdown("""
<style>
  .block-container{padding-top:1.5rem;max-width:1200px;}
  .badge{display:inline-block;padding:2px 10px;border-radius:12px;color:#fff;font-size:12px;font-weight:600;}
  .chip{display:inline-block;padding:1px 8px;margin:2px 4px 2px 0;border-radius:10px;
        background:#eef1f5;color:#3a4250;font-size:11px;border:1px solid #dde2e9;}
  .src{font-size:11px;color:#6b7280;}
  .src a{color:#2563a8;text-decoration:none;}
  .metric{display:inline-block;margin-right:22px;}
  .metric b{font-size:20px;color:#1f4e79;} .metric span{font-size:12px;color:#6b7280;display:block;}
  .card{border:1px solid #e3e6ea;border-radius:10px;padding:14px 16px;margin-bottom:10px;background:#fff;}
  .verdict{font-size:15px;color:#23303f;font-style:italic;}
  h3{margin-top:1.1rem;}
  .bar{height:7px;border-radius:4px;background:#eceff3;position:relative;margin:3px 0 8px;}
  .bar>i{position:absolute;left:0;top:0;height:7px;border-radius:4px;}
</style>
""", unsafe_allow_html=True)


@st.cache_data
def load():
    if not os.path.exists(config.OUT_JSON):
        return []
    return json.load(open(config.OUT_JSON))


def badge(tier):
    return f'<span class="badge" style="background:{TIER_COLOR.get(tier,"#888")}">{TIER_LABEL.get(tier,tier)}</span>'


def bar(label, val, color="#2f6fb0"):
    pct = 0 if val is None else int(max(0, min(1, val)) * 100)
    txt = "n/a" if val is None else f"{val:.2f}"
    st.markdown(f'<div class="src">{label}: {txt}</div>'
                f'<div class="bar"><i style="width:{pct}%;background:{color}"></i></div>',
                unsafe_allow_html=True)


def srcline(source, url=""):
    if url:
        return f'<span class="src">source: <a href="{url}" target="_blank">{source or url}</a></span>'
    return f'<span class="src">source: {source}</span>'


data = load()
if "sel" not in st.session_state:
    st.session_state.sel = None

# ============================== HOME (ranking) ==============================
def home():
    st.title("Researcher → Proposal Match")
    st.caption("Schmidt Sciences · Science of Trustworthy AI (2026) — ranked by strict, evidence-based fit")
    if not data:
        st.warning("No data yet. Run:  `python3 pipeline.py --one`  (or `--all`), then refresh.")
        return

    tiers = [d.get("scores", {}).get("tier", "WEAK") for d in data if "scores" in d]
    c = st.columns(4)
    for col, t in zip(c, ["STRONG", "POSSIBLE", "WEAK", "OUT_OF_SCOPE"]):
        col.markdown(f"{badge(t)} &nbsp;**{tiers.count(t)}**", unsafe_allow_html=True)

    show = st.multiselect("Show tiers", list(TIER_LABEL), default=["STRONG", "POSSIBLE", "OUT_OF_SCOPE", "WEAK"],
                          format_func=lambda t: TIER_LABEL[t])
    st.markdown("---")

    for i, d in enumerate(data):
        sc = d.get("scores", {})
        tier = sc.get("tier", "WEAK")
        if tier not in show:
            continue
        llm = sc.get("llm", {})
        ac = d.get("academic", {})
        left, right = st.columns([0.74, 0.26])
        with left:
            st.markdown(f"**{d.get('name','?')}** · {d.get('designation','')}  {badge(tier)}",
                        unsafe_allow_html=True)
            st.markdown(f"<span class='verdict'>{llm.get('verdict','—')}</span>", unsafe_allow_html=True)
            best = [b for b in (llm.get("best_subthemes") or []) if b.get("score", 0) >= 40][:3]
            if best:
                chips = " ".join(f'<span class="chip">{b["id"]} · {SUBTHEME_TITLE.get(b["id"],"")[:34]} '
                                 f'({b.get("score","?")})</span>' for b in best)
                st.markdown(chips, unsafe_allow_html=True)
            # quick agency hint
            sig = (d.get("web_signals", {}) or {}).get("signals", {}) or {}
            if sig:
                st.markdown(" ".join(f'<span class="chip" style="background:#eaf4ff">{k.replace("_"," ")}</span>'
                                     for k in list(sig)[:5]), unsafe_allow_html=True)
        with right:
            st.markdown(
                f'<div class="src">fit {llm.get("overall_fit","?")}/100 · conf {llm.get("confidence","?")}<br>'
                f'h-index {ac.get("h_index_openalex") or d.get("scraped_metrics",{}).get("scholar_h_index","?")} · '
                f'cites {ac.get("cited_by_total") or d.get("scraped_metrics",{}).get("scholar_citations","?")}</div>',
                unsafe_allow_html=True)
            if st.button("Open profile →", key=f"open{i}"):
                st.session_state.sel = i
                st.rerun()
        st.markdown("<hr style='margin:8px 0;border:none;border-top:1px solid #eee'>", unsafe_allow_html=True)


# ============================== DETAIL ==============================
def detail(idx):
    d = data[idx]
    if st.button("← Back to ranking"):
        st.session_state.sel = None
        st.rerun()
    ac = d.get("academic", {})
    sc = d.get("scores", {})
    llm = sc.get("llm", {})
    tier = sc.get("tier", "WEAK")

    head = st.columns([0.16, 0.84])
    if d.get("photo_ok"):
        head[0].image(d["photo_ok"], width=110)
    with head[1]:
        st.markdown(f"### {d.get('name','?')} &nbsp; {badge(tier)}", unsafe_allow_html=True)
        st.markdown(f"{d.get('designation','')} · {d.get('department','')} · {d.get('institute','')}")
        st.markdown(f"<span class='verdict'>{llm.get('verdict','—')}</span>", unsafe_allow_html=True)
        if d.get("identity_sanity"):
            st.warning(f"Identity check: {d['identity_sanity']}")

    # key numbers
    m = d.get("scraped_metrics", {})
    st.markdown(
        f'<div class="metric"><b>{ac.get("h_index_openalex") or m.get("scholar_h_index","?")}</b>'
        f'<span>h-index</span></div>'
        f'<div class="metric"><b>{ac.get("cited_by_total") or m.get("scholar_citations","?")}</b>'
        f'<span>citations</span></div>'
        f'<div class="metric"><b>{m.get("scholar_h_index5y","?")}</b><span>h-index (5y)</span></div>'
        f'<div class="metric"><b>{ac.get("n_works_pulled","?")}</b><span>papers pulled</span></div>'
        f'<div class="metric"><b>{llm.get("overall_fit","?")}/100</b><span>fit · conf {llm.get("confidence","?")}</span></div>',
        unsafe_allow_html=True)
    st.caption("Academic identity " + ("anchored via " + ac.get("match_method", "?") +
               f" ({ac.get('academic_confidence','?')})" if ac.get("resolved") else "NOT anchored — scraped data only"))

    c1, c2 = st.columns([0.55, 0.45])

    # ---- left: fit + research focus + top papers ----
    with c1:
        st.markdown("#### Fit to the agenda")
        for b in (llm.get("best_subthemes") or [])[:5]:
            sid = b.get("id", "?")
            ev = b.get("evidence", "")
            color = "#1f8a4c" if b.get("score", 0) >= 60 else ("#c98a00" if b.get("score", 0) >= 40 else "#8a8f98")
            st.markdown(f'**{sid} · {SUBTHEME_TITLE.get(sid,"")}** — {b.get("score","?")}/100 '
                        f'<span class="src">({b.get("recency","?")})</span>', unsafe_allow_html=True)
            st.markdown(f'<div class="bar"><i style="width:{int(b.get("score",0))}%;background:{color}"></i></div>'
                        f'<span class="src">evidence: {ev}</span>', unsafe_allow_html=True)
        if llm.get("out_of_scope", {}).get("flag"):
            st.error(f"Out of scope — {llm['out_of_scope'].get('area','')}: {llm['out_of_scope'].get('reason','')}")

        st.markdown("#### Research focus")
        fo = d.get("focus", {})
        st.markdown(f"**Overall (career):** {fo.get('overall','—')}")
        st.markdown(f"**Recent (last 5y):** {fo.get('recent','—')}")
        st.markdown(srcline(fo.get("source", "—")), unsafe_allow_html=True)

        st.markdown("#### Top contributions")
        for w in (ac.get("top_cited") or [])[:config.TOP_PAPERS_SHOW]:
            st.markdown(f"- {w.get('title','')} *({w.get('year','?')}, {w.get('cited_by',0)} cites"
                        f"{', '+w['venue'] if w.get('venue') else ''})* "
                        f"[link]({w.get('url','')})" if w.get("url") else f"- {w.get('title','')}")

    # ---- right: agency signals + scores + scraped extras ----
    with c2:
        st.markdown("#### Non-academic / agency signals")
        web = d.get("web_signals", {}) or {}
        sigs = web.get("signals", {}) or {}
        if not sigs and not web.get("socials_from_csv"):
            st.markdown("<span class='src'>No non-academic signals found "
                        "(absence ≠ evidence of absence — see confidence).</span>", unsafe_allow_html=True)
        for cat, items in sigs.items():
            st.markdown(f"**{cat.replace('_',' ').title()}**")
            for it in (items if isinstance(items, list) else [items]):
                st.markdown(f"- {it.get('claim','')} "
                            f"<span class='src'>[{it.get('confidence','?')}] "
                            f"<a href='{it.get('url','')}' target='_blank'>source</a></span>",
                            unsafe_allow_html=True)
        if web.get("socials_from_csv"):
            st.markdown(" ".join(f'<a class="chip" href="{u}" target="_blank">{k}</a>'
                                 for k, u in web["socials_from_csv"].items()), unsafe_allow_html=True)
        if web.get("identity_caveats"):
            st.markdown(f"<span class='src'>⚠ {web['identity_caveats']}</span>", unsafe_allow_html=True)

        st.markdown("#### Strengths · gaps · deal-breakers")
        for s in (llm.get("strengths") or []): st.markdown(f"- ✅ {s}")
        for s in (llm.get("gaps") or []): st.markdown(f"- ⚠️ {s}")
        for s in (llm.get("deal_breakers") or []): st.markdown(f"- ⛔ {s}")
        st.caption(f"Confidence {llm.get('confidence','?')}: {llm.get('confidence_reason','')}")

        with st.expander("Signal scores (BM25 / dense / LLM)"):
            bm, dn = sc.get("bm25", {}), sc.get("dense", {})
            for t in SUBTHEMES:
                if bm.get(t["id"], 0) > 0.15 or (dn.get(t["id"]) or 0) > 0.2:
                    st.markdown(f"**{t['id']}** {t['title'][:40]}")
                    bar("BM25", bm.get(t["id"]))
                    bar("Dense", dn.get(t["id"]), "#7a5cc0")

        ex = d.get("scraped_extras", {})
        if ex:
            with st.expander("From IIT-H website (honors, projects, supervision)"):
                for k, v in ex.items():
                    st.markdown(f"**{k}:** {v[:600]}")
                st.markdown(srcline("iith_website", d.get("links", {}).get("iith_profile_url", "")),
                            unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("**Profiles & links:** " + " · ".join(
        f"[{k.replace('_url','').replace('_',' ')}]({v})" for k, v in (d.get("links", {}) or {}).items()))


if st.session_state.sel is None:
    home()
else:
    detail(st.session_state.sel)
