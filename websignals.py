"""Non-academic 'agency' signal discovery — BL's priority.

For each professor, run targeted web searches (startup / founder / advisor / board /
VC / patent / keynote / talk), collect result snippets WITH their source URLs, then ask
the LLM to extract ONLY claims supported by those snippets, each tagged with its source URL.
Nothing is asserted without a source the dashboard can show.

Free path: DuckDuckGo via the `ddgs` package. It rate-limits aggressively; SERP API
(paid) is the robust upgrade — see README.
"""
import time, json
import config, utils

QUERY_TEMPLATES = [
    '{name} {inst} startup OR founder OR co-founder',
    '{name} {inst} advisor OR "advisory board" OR board member',
    '{name} {inst} venture OR "raised funding" OR investor OR CEO',
    '{name} {inst} patent',
    '{name} {inst} keynote OR invited talk OR panel',
    '{name} {inst} LinkedIn',
    '{name} interview OR podcast {inst}',
    '{name} {inst} consultant OR industry collaboration',
]


def _ddg(query, k):
    try:
        from ddgs import DDGS
    except Exception:
        try:
            from duckduckgo_search import DDGS  # older package name
        except Exception:
            return {"error": "Install `ddgs` (pip install ddgs) for web discovery."}
    try:
        with DDGS() as d:
            return list(d.text(query, max_results=k))
    except Exception as e:
        return {"error": str(e)}


def gather_snippets(row):
    name = utils.clean(row.get("name", ""))
    inst = utils.clean(row.get("institute", "")) or "IIT Hyderabad"
    snippets, errors = [], []
    for tmpl in QUERY_TEMPLATES[:config.WEB_QUERIES_PER_PROF]:
        q = tmpl.format(name=name, inst=inst)
        ck = f"ddg:{q}"
        res = utils.cache_get(ck)
        if res is None:
            res = _ddg(q, config.WEB_RESULTS_PER_QUERY)
            utils.cache_set(ck, res)
            time.sleep(config.WEB_DELAY_SEC)
        if isinstance(res, dict) and res.get("error"):
            errors.append(res["error"]); continue
        for r in res:
            snippets.append({
                "query": q,
                "title": r.get("title", ""),
                "body": r.get("body", ""),
                "url": r.get("href") or r.get("url", ""),
            })
    return snippets, errors


SIGNAL_SCHEMA = {
    "startup_founder": "founded / co-founded a company or spinout",
    "advisory_board": "advisor, scientific advisor, or board member",
    "vc_funding": "raised venture capital / investor / CEO role",
    "patents": "named inventor on patents",
    "industry_collab": "consulting or named industry collaboration",
    "talks_keynotes": "keynotes, invited talks, panels, podcasts, interviews",
    "standards_gov": "government projects, standards bodies, committees",
    "social_presence": "active LinkedIn / X(Twitter) / GitHub presence",
}


def extract_signals(row, snippets):
    """LLM extracts only snippet-supported agency signals, each with a source URL."""
    if not snippets:
        return {"signals": {}, "note": "No web snippets gathered."}
    name = utils.clean(row.get("name", ""))
    corpus = "\n".join(
        f"[{i}] {s['title']} | {s['body'][:240]} | URL: {s['url']}"
        for i, s in enumerate(snippets[:40]))
    sys_p = (
        "You extract NON-ACADEMIC 'agency' signals about a professor strictly from provided web "
        "snippets. RULES: (1) Only state something if a snippet supports it; (2) attach the exact "
        "source URL for each claim; (3) if a snippet is clearly about a different person (wrong field/"
        "affiliation), ignore it; (4) if nothing supports a category, omit it. Never invent. "
        "Output JSON only.")
    cats = "\n".join(f"- {k}: {v}" for k, v in SIGNAL_SCHEMA.items())
    usr_p = (
        f"PROFESSOR: {name} ({row.get('institute','IIT Hyderabad')}, "
        f"{row.get('department','Computer Science')}).\n\n"
        f"CATEGORIES:\n{cats}\n\nSNIPPETS:\n{corpus}\n\n"
        'Return JSON: {"signals": {"<category>": [{"claim": "...", "url": "...", '
        '"confidence": "high|medium|low"}]}, "identity_caveats": "..."}. '
        "Include only categories with real evidence.")
    try:
        return utils.groq_json(
            [{"role": "system", "content": sys_p}, {"role": "user", "content": usr_p}],
            model=config.GROQ_MODEL_EXTRACT, max_tokens=1500)
    except Exception as e:
        return {"signals": {}, "error": str(e)}


def enrich_web(row):
    snippets, errors = gather_snippets(row)
    extracted = extract_signals(row, snippets)
    extracted["_n_snippets"] = len(snippets)
    if errors:
        extracted["_search_errors"] = list(set(errors))[:3]
    # Also fold in the social URLs already in the CSV (free, high-precision):
    socials = {}
    for col, label in [("linkedin_url", "LinkedIn"), ("twitter_url", "X/Twitter"),
                       ("github_url", "GitHub"), ("researchgate_url", "ResearchGate")]:
        if utils.clean(row.get(col, "")):
            socials[label] = row[col]
    extracted["socials_from_csv"] = socials
    return extracted
