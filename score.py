"""Explainable, STRICT matching. Three independent signals, transparently combined.

The old system's failure was scoring everyone high. Fixes here:
  - LLM judge uses a hard, anchored rubric and must cite a paper or say 'NO DIRECT EVIDENCE'.
  - Out-of-scope areas (interpretability/fairness/policy/...) are detected and capped.
  - Final TIER is rule-based (not a soft average), so it's auditable:
        OUT_OF_SCOPE  -> excluded regardless of skill
        STRONG        -> LLM>=70 AND recent direct evidence AND keyword/dense corroboration
        POSSIBLE      -> LLM 40-69 with some evidence
        WEAK          -> everything else
  - Trustworthy-AI alignment is treated as NICHE: generic 'AI/ML' does NOT earn points.
"""
import re, math
import config, utils
from agenda import SUBTHEMES, agenda_for_prompt

# ---------- corpus per professor ----------
def build_corpus(row, academic):
    parts = [
        utils.clean(row.get("research_interests", "")),
        academic.get("recent_titles_text", ""),
        academic.get("recent_abstracts_text", ""),
        academic.get("all_titles_text", ""),
        " ".join(academic.get("concepts", []) or []),
    ]
    # research_interests is sometimes mis-scraped (e.g. an advisor's name) -> rely mostly on pubs
    return " . ".join(p for p in parts if p)[:12000]


_tok = re.compile(r"[a-z0-9\-]+")
def toks(s): return _tok.findall((s or "").lower())


# ---------- signal 1: BM25 ----------
def bm25_scores(corpus):
    from rank_bm25 import BM25Okapi
    theme_docs = [toks(t["title"] + " " + t["objective"] + " " + " ".join(t["keywords"])) for t in SUBTHEMES]
    bm = BM25Okapi(theme_docs)
    raw = bm.get_scores(toks(corpus))
    mx = float(max(raw)) if len(raw) and max(raw) > 0 else 1.0
    return {SUBTHEMES[i]["id"]: float(round(float(raw[i]) / mx, 3)) for i in range(len(SUBTHEMES))}


# ---------- signal 2: dense semantic (small fast model; degrades gracefully) ----------
_embedder = None
def _get_embedder():
    global _embedder
    if _embedder == "FAILED":
        return None
    if _embedder is None:
        try:
            from sentence_transformers import SentenceTransformer
            _embedder = SentenceTransformer(config.EMBED_MODEL)
        except Exception:
            _embedder = "FAILED"
            return None
    return _embedder


def dense_scores(corpus):
    emb = _get_embedder()
    if emb is None or not corpus.strip():
        return {t["id"]: None for t in SUBTHEMES}
    theme_texts = [t["title"] + ". " + t["objective"] for t in SUBTHEMES]
    vecs = emb.encode([corpus] + theme_texts, normalize_embeddings=True)
    cv, tv = vecs[0], vecs[1:]
    return {SUBTHEMES[i]["id"]: round(float((cv * tv[i]).sum()), 3) for i in range(len(SUBTHEMES))}


# ---------- signal 3: strict LLM judge ----------
JUDGE_SYS = (
    "You are a STRICT grant-matching reviewer for the Schmidt Sciences 'Science of Trustworthy AI' "
    "2026 RFP. Trustworthy-AI / AI-alignment / AI-safety is a NICHE field. Most computer scientists "
    "(networks, databases, vision, systems, generic ML) are NOT a fit and must score LOW. Do not "
    "reward generic 'AI/ML' or keyword overlap. Award high scores ONLY when the professor's own RECENT "
    "(last ~5 years) work directly addresses a sub-theme's core scientific question, and cite the "
    "specific paper title as evidence. If you cannot cite concrete evidence, the score MUST be < 30. "
    "Detect OUT-OF-SCOPE core areas and flag them. Output JSON only."
)

RUBRIC = (
    "SCORING RUBRIC (0-100 per sub-theme):\n"
    "  80-100: recent first-author/PI work DIRECTLY on the sub-theme's core question (cite the paper).\n"
    "  50-79 : adjacent/contributing recent work clearly relevant to the sub-theme.\n"
    "  20-49 : tangential or keyword-level overlap only.\n"
    "  0-19  : unrelated.\n"
)


def llm_judge(row, academic, bm25, dense):
    name = utils.clean(row.get("name", ""))
    # give the judge the strongest cheap signals to focus on, plus evidence text
    top_hint = sorted(SUBTHEMES, key=lambda t: (dense.get(t["id"]) or 0) + bm25.get(t["id"], 0), reverse=True)[:4]
    hint = ", ".join(f'{t["id"]} {t["title"]}' for t in top_hint)
    evidence = (
        f"RESEARCH INTERESTS (scraped, may be noisy): {utils.clean(row.get('research_interests',''))[:600]}\n"
        f"OPENALEX CONCEPTS: {', '.join(academic.get('concepts', []) or [])}\n"
        f"RECENT PAPER TITLES (last {config.RECENT_YEARS}y): {academic.get('recent_titles_text','')[:2500]}\n"
        f"TOP-CITED TITLES: {' . '.join(w['title'] for w in academic.get('top_cited', []))[:1200]}\n"
        f"h-index: {academic.get('h_index_openalex')}, total citations: {academic.get('cited_by_total')}"
    )
    usr = (
        f"{agenda_for_prompt()}\n\n{RUBRIC}\n\nPROFESSOR: {name} "
        f"({row.get('department','CS')}, {row.get('institute','IIT Hyderabad')}).\n"
        f"Cheap-signal top sub-themes to scrutinize first: {hint}\n\nEVIDENCE:\n{evidence}\n\n"
        'Return JSON: {'
        '"overall_fit": 0-100, '
        '"verdict": "one strict sentence", '
        '"best_subthemes": [{"id":"x.y","score":0-100,"evidence":"paper title or NO DIRECT EVIDENCE","recency":"current|past|none"}], '
        '"out_of_scope": {"flag": true|false, "area": "", "reason": ""}, '
        '"strengths": ["..."], "gaps": ["..."], "deal_breakers": ["..."], '
        '"confidence": "HIGH|MEDIUM|LOW", "confidence_reason": "based on data coverage"'
        "}. Be strict: if evidence is generic ML or unrelated CS, overall_fit must be low (<30)."
    )
    try:
        return utils.groq_json([{"role": "system", "content": JUDGE_SYS},
                                {"role": "user", "content": usr}], max_tokens=1800)
    except Exception as e:
        return {"overall_fit": 0, "verdict": f"LLM error: {e}", "best_subthemes": [],
                "out_of_scope": {"flag": False}, "confidence": "LOW", "error": str(e)}


# ---------- combine into an auditable tier ----------
def decide_tier(bm25, dense, judge):
    if judge.get("out_of_scope", {}).get("flag"):
        return "OUT_OF_SCOPE"
    llm = judge.get("overall_fit", 0) or 0
    best = judge.get("best_subthemes", []) or []
    has_recent_direct = any((b.get("score", 0) >= 60 and b.get("recency") == "current"
                             and "NO DIRECT EVIDENCE" not in (b.get("evidence", "")).upper())
                            for b in best)
    # corroboration from cheap signals on any flagged sub-theme
    corroborated = False
    for b in best:
        sid = b.get("id")
        d = dense.get(sid)
        if (bm25.get(sid, 0) >= 0.5) or (d is not None and d >= 0.35):
            corroborated = True
    if llm >= config.TIER_STRONG_LLM and has_recent_direct and corroborated:
        return "STRONG"
    if llm >= config.TIER_POSSIBLE_LLM and best and any("NO DIRECT EVIDENCE" not in
                                                        (b.get("evidence", "")).upper() for b in best):
        return "POSSIBLE"
    return "WEAK"


def score_profile(row, academic):
    corpus = build_corpus(row, academic)
    bm25 = bm25_scores(corpus)
    dense = dense_scores(corpus)
    judge = llm_judge(row, academic, bm25, dense)
    tier = decide_tier(bm25, dense, judge)
    # rank key: tier first, then LLM fit, then citations
    tier_rank = {"STRONG": 3, "POSSIBLE": 2, "WEAK": 1, "OUT_OF_SCOPE": 0}[tier]
    return {
        "bm25": bm25, "dense": dense, "llm": judge, "tier": tier,
        "rank_key": (tier_rank, judge.get("overall_fit", 0), academic.get("cited_by_total") or 0),
        "corpus_chars": len(corpus),
    }
