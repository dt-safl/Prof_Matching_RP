"""
MAAS RFP Groq-based scorer.
Scores each professor on:
  - 4 research clusters (S1-S4): 0-100 each
  - 7 selection criteria (SC1-SC7): 0-100 each
  - Identifies best cluster, provides key evidence notes
  - axis_a = best cluster score (researchers specialize; max one cluster counts)

Uses Groq with 5-key rotation. Falls back to Claude if all keys exhausted.
Results cached to scores_maas/<slug>.json.
"""

import json, os, re, time, random
from dotenv import load_dotenv

HERE = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(HERE, "..", "profmatchf", ".env"))

GROQ_KEYS = [
    os.environ.get(k, "")
    for k in ["GROQ_API_KEY", "GROQ_API_KEY_2", "GROQ_API_KEY_3", "GROQ_API_KEY_4", "GROQ_API_KEY_5"]
]
GROQ_KEYS = [k for k in GROQ_KEYS if k]
GROQ_MODEL = "llama-3.3-70b-versatile"
SCORES_DIR = os.path.join(HERE, "scores_maas")
os.makedirs(SCORES_DIR, exist_ok=True)

# Cluster descriptions (condensed for prompt)
CLUSTER_PROMPTS = {
    "S1": "Sandboxes & Testbeds: Building realistic, scalable, reproducible multi-agent environments for frontier AI agents (not toy games). Includes LLM agent frameworks, evaluation infrastructure, distilled proxy agents, logging tools.",
    "S2": "Science of Agent Networks: System-level safety science — game theory, mechanism design, MARL, emergent collective behaviours, cascading failures, collective agency, agent network analysis, population dynamics of AI agents.",
    "S3": "Agent Infrastructure: Identity, authentication, reputation, accountability, provenance, commitment protocols for AI agents. Zero-knowledge proofs, cryptographic trust, formal verification of agent protocols, Sybil resistance, watermarking.",
    "S4": "Multi-Agent Oversight & Control: Detecting/attributing/controlling unsafe behaviours in deployed multi-agent systems — collusion detection, steganography/covert comms detection, circuit breakers, red-teaming agent collectives, scalable oversight extensions.",
}

SC_PROMPTS = {
    "SC1": "Research Agenda Fit — how directly does their work engage with MAAS themes (multi-agent, NOT single-agent alignment/capabilities)?",
    "SC2": "Scientific Quality & Rigour — publication venues, methodological depth, generalisability of contributions.",
    "SC3": "Potential Impact — if funded for MAAS work, how much could they advance multi-agent AI safety science?",
    "SC4": "Philanthropic Fit — is this work that commercial AI labs won't fund? (public-good, precompetitive, foundational)",
    "SC5": "Feasibility & Scope — does their track record suggest they can deliver focused outputs in 1-2 years?",
    "SC6": "Team Expertise — specific technical background match (MAS, game theory, crypto, formal methods, distributed AI)?",
    "SC7": "Cost Appropriateness — would their work scope reasonably fit Tier 1 ($300K) or Tier 2 ($1M) budget?",
}

OUT_OF_SCOPE = """OUT OF SCOPE for this RFP (score 0 for clusters if this is their primary focus):
- Single-agent alignment/interpretability only
- Capability advancement (making agents better, not safer)
- AI for human cooperation (democratic institutions, negotiation mediation)
- Naive blockchain identity applied to agents without AI-specific challenges
- Toy/classical game theory without frontier-model extension
- Non-technical policy work
- Individual model robustness/adversarial attacks without multi-agent evaluation"""


def _slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


def _load_cached(slug: str) -> dict | None:
    p = os.path.join(SCORES_DIR, f"{slug}.json")
    return json.load(open(p)) if os.path.exists(p) else None


def _save(slug: str, result: dict) -> None:
    json.dump(result, open(os.path.join(SCORES_DIR, f"{slug}.json"), "w"), indent=2)


def _build_prompt(prof: dict, oa_facts: dict | None) -> str:
    name = prof.get("name", "Unknown")
    institute = prof.get("institute", "")
    dept = prof.get("department", "")
    focus = prof.get("focus", {}) or {}
    research_summary = focus.get("research_summary", "") or ""
    expertise = focus.get("expertise", "") or ""
    llm = (prof.get("scores", {}) or {}).get("llm", {}) or {}
    prior_verdict = llm.get("verdict", "") or ""
    ac = prof.get("academic", {}) or {}

    # Build paper list: prefer OA enrichment (all papers), fall back to academic.recent_works
    papers_block = ""
    if oa_facts and oa_facts.get("all_papers"):
        papers = oa_facts["all_papers"]
        papers_block = "\n".join(
            f"  [{p['year']}] {p['title']}" for p in papers[:50] if p.get("title")
        )
        papers_block = f"RECENT PAPERS (from OpenAlex, up to 50):\n{papers_block}"
    else:
        recent = ac.get("recent_works", []) or []
        if recent:
            papers_block = "RECENT PAPERS:\n" + "\n".join(
                f"  [{w.get('year', '?')}] {w.get('title', '')}" for w in recent[:10]
            )
        else:
            papers_block = "RECENT PAPERS: (none available)"

    # Funding signals
    funders_block = ""
    if oa_facts and oa_facts.get("industry_funders"):
        flist = "; ".join(
            f"{f['funder']} ({f['year']})" for f in oa_facts["industry_funders"][:5]
        )
        funders_block = f"\nFUNDING SIGNALS: {flist}"

    # Cluster descriptions
    cluster_block = "\n".join(f"  {k}: {v}" for k, v in CLUSTER_PROMPTS.items())
    sc_block = "\n".join(f"  {k}: {v}" for k, v in SC_PROMPTS.items())

    prompt = f"""You are a rigorous evaluator for the "Scaling AI Safety for a Multi-Agent World" RFP (Schmidt Sciences + Google DeepMind + ARIA + Cooperative AI Foundation + Google.org).

PROFESSOR: {name}
INSTITUTION: {institute} | DEPARTMENT: {dept}

RESEARCH SUMMARY: {research_summary[:600]}

EXPERTISE KEYWORDS: {expertise[:400]}

{papers_block}
{funders_block}

PRIOR ASSESSMENT (from a separate AI safety RFP — may be partially relevant): {prior_verdict[:400]}

=== RESEARCH CLUSTERS ===
{cluster_block}

{OUT_OF_SCOPE}

=== SELECTION CRITERIA ===
{sc_block}

=== INSTRUCTIONS ===
Score each cluster and selection criterion from 0–100:
- 0–20: no evidence, completely off-topic, or actively out-of-scope
- 21–40: marginal signal only, very indirect connection
- 41–60: some relevant work but not central to the cluster
- 61–80: clear relevant work, strong fit to this cluster
- 81–100: direct, deep expertise — this is exactly what the cluster asks for

For axis_a use the BEST single cluster score (researchers specialize in one area).

Return ONLY valid JSON with this exact structure:
{{
  "cluster_scores": {{"S1": 0, "S2": 0, "S3": 0, "S4": 0}},
  "cluster_notes": {{
    "S1": "one sentence why/why-not",
    "S2": "one sentence why/why-not",
    "S3": "one sentence why/why-not",
    "S4": "one sentence why/why-not"
  }},
  "best_cluster": "S1 or S2 or S3 or S4",
  "selection_criteria": {{"SC1": 0, "SC2": 0, "SC3": 0, "SC4": 0, "SC5": 0, "SC6": 0, "SC7": 0}},
  "axis_a": 0,
  "key_evidence": "1-2 sentences on the most relevant papers, projects, or collaborations",
  "out_of_scope_risk": "none or low or medium or high",
  "out_of_scope_reason": "brief reason if medium/high, else empty string"
}}"""
    return prompt


def _call_claude(prompt: str) -> str:
    """Primary scorer: Claude Haiku (fast + cheap)."""
    import anthropic
    key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not key:
        raise RuntimeError("ANTHROPIC_API_KEY not set in profmatchf/.env")
    client = anthropic.Anthropic(api_key=key)
    msg = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=900,
        messages=[{"role": "user", "content": prompt}],
    )
    return msg.content[0].text


def _call_groq(prompt: str, key: str) -> str:
    """Groq fallback (when Claude key not set, or as backup)."""
    from groq import Groq
    client = Groq(api_key=key)
    resp = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
        max_tokens=900,
    )
    return resp.choices[0].message.content


def _parse_result(raw: str, name: str) -> dict:
    """Parse and validate Groq/Claude JSON response."""
    try:
        # Strip markdown fences if present
        cleaned = re.sub(r"```(?:json)?", "", raw).strip().strip("`")
        data = json.loads(cleaned)
    except Exception:
        # Best-effort: extract first JSON object
        m = re.search(r"\{.*\}", raw, re.DOTALL)
        if not m:
            raise ValueError(f"No JSON found in response for {name}")
        data = json.loads(m.group())

    # Validate and clamp scores
    cs = data.get("cluster_scores", {})
    sc = data.get("selection_criteria", {})
    for k in ["S1", "S2", "S3", "S4"]:
        cs[k] = max(0, min(100, int(cs.get(k, 0) or 0)))
    for k in ["SC1", "SC2", "SC3", "SC4", "SC5", "SC6", "SC7"]:
        sc[k] = max(0, min(100, int(sc.get(k, 0) or 0)))

    best = data.get("best_cluster", max(cs, key=cs.get))
    axis_a = cs.get(best, 0)

    return {
        "cluster_scores": cs,
        "cluster_notes": data.get("cluster_notes", {}),
        "best_cluster": best,
        "selection_criteria": sc,
        "axis_a": axis_a,
        "key_evidence": data.get("key_evidence", ""),
        "out_of_scope_risk": data.get("out_of_scope_risk", "none"),
        "out_of_scope_reason": data.get("out_of_scope_reason", ""),
    }


def score_professor(prof: dict, oa_facts: dict | None, force: bool = False) -> dict:
    """
    Score a professor for the MAAS RFP.
    Returns scored result dict; caches to scores_maas/<slug>.json.
    """
    name = prof.get("name", "Unknown")
    slug = _slug(name)

    if not force:
        cached = _load_cached(slug)
        if cached:
            return cached

    prompt = _build_prompt(prof, oa_facts)
    raw = None
    last_err = None

    # 1. Try Claude first (primary when ANTHROPIC_API_KEY is set)
    if os.environ.get("ANTHROPIC_API_KEY"):
        try:
            raw = _call_claude(prompt)
        except Exception as e:
            last_err = e
            print(f"    Claude failed ({e}), trying Groq...")

    # 2. Try each Groq key (primary if no Claude key, fallback otherwise)
    if raw is None:
        keys = list(GROQ_KEYS)
        random.shuffle(keys)
        for key in keys:
            try:
                raw = _call_groq(prompt, key)
                break
            except Exception as e:
                last_err = e
                err_str = str(e)
                if "429" in err_str or "rate" in err_str.lower():
                    time.sleep(2)
                    continue
                time.sleep(1)

    if raw is None:
        result = {
            "cluster_scores": {"S1": 0, "S2": 0, "S3": 0, "S4": 0},
            "cluster_notes": {},
            "best_cluster": "S1",
            "selection_criteria": {"SC1": 0, "SC2": 0, "SC3": 0, "SC4": 0, "SC5": 0, "SC6": 0, "SC7": 0},
            "axis_a": 0,
            "key_evidence": "",
            "out_of_scope_risk": "none",
            "out_of_scope_reason": "",
            "error": f"All backends failed: {last_err}",
        }
        _save(slug, result)
        return result

    result = _parse_result(raw, name)
    _save(slug, result)
    return result
