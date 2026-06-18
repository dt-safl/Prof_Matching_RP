"""
MAAS (Multi-Agent AI Safety) RFP keyword config.
Joint call: Schmidt Sciences, Google DeepMind, ARIA, Cooperative AI Foundation, Google.org

4 research clusters — keywords cover: exact RFP terms, adjacent methods, paper title patterns.
Pre-filter threshold: keyword_max >= 0.1 (1 hit in ANY cluster passes first pass).
"""

CLUSTER_KEYWORDS = {
    "S1_sandbox": [
        # Direct multi-agent testbed terms (specific to MAS evaluation)
        "multi-agent testbed", "multi-agent sandbox", "multi-agent environment",
        "multi-agent simulation", "multi-agent benchmark", "multi-agent platform",
        "multi-principal", "agent population simulation",
        "scalable multi-agent", "realistic multi-agent",
        "environment-agnostic agent", "multi-agent interoperation",
        "distilled model proxy", "agent proxy",
        # LLM agent infrastructure (specific compounds)
        "llm agent", "llm agents", "language model agent",
        "agentic framework", "agent orchestration framework",
        "tool-using agent", "multi-agent framework",
        "agent memory", "agent tool use",
        "frontier agent", "autonomous agent deployment",
        # Evaluation infra for MAS specifically
        "multi-agent evaluation infrastructure", "agent testbed",
        "agent simulation environment", "agent sandbox",
        "agent benchmark", "agent platform",
    ],
    "S2_science": [
        # Emergent collective (must be agent-specific)
        "emergent collective", "collective behavior agent",
        "collective capability agent", "collective agency",
        "collective agent", "agent network",
        "agent population dynamics", "population-level safety",
        "emergent multi-agent", "emergent coordination",
        "cascading failure agent", "adversarial sub-population",
        "phase transition agent", "emergent communication agent",
        "collective failure", "agent interaction dynamics",
        # Game theory / mechanism design (core S2)
        "game theory", "game theoretic",
        "mechanism design", "mechanism designer",
        "nash equilibrium", "nash equilibria",
        "cooperative game", "non-cooperative game",
        "social choice", "social welfare function",
        "auction mechanism", "voting mechanism",
        "incentive compatible", "incentive design",
        "stackelberg", "bargaining theory", "repeated game",
        "dominant strategy", "pareto optimal",
        "cooperative game theory", "algorithmic game theory",
        # Multi-agent RL (specific)
        "multi-agent reinforcement", "multi-agent rl", "marl",
        "cooperative multi-agent", "competitive multi-agent",
        "multiagent reinforcement", "multi-agent learning",
        "agent coordination", "agent cooperation dynamics",
        # Collective / distributed AI (specific)
        "multi-agent system", "multiagent system",
        "swarm intelligence", "swarm robotics",
        "collective ai", "cooperative ai",
        "distributed ai", "distributed multi-agent",
        "principal-agent", "agent competition",
    ],
    "S3_infra": [
        # Agent identity/auth specifics
        "agent identity", "agent authentication", "agent admission control",
        "agent authorization", "proof of agent", "proof of human credential",
        "agent credential", "agent revocation", "agent id",
        "verifiable agent", "agent provenance", "agent accountability",
        "reputation system ai", "agent reputation", "ai reputation mechanism",
        "dispute resolution agent", "commitment protocol",
        "agent commitment", "delegation protocol",
        "sybil attack", "sybil resistance", "malicious delegate",
        "agent delegation", "scope attenuation", "multi-principal support",
        "watermarking ai output", "proof of inference",
        "agent access control", "cross-principal trust",
        # Cryptographic infrastructure (for AI agents)
        "zero-knowledge proof", "zero knowledge proof", "zkp",
        "secure multi-party computation", "homomorphic encryption",
        "smart contract agent", "blockchain agent",
        "protocol verification", "verified computation",
        "verifiable computation", "attestation protocol",
        "trusted execution environment", "tee agent",
        # Agent protocol / trust standards
        "a2a protocol", "agent communication protocol",
        "inter-agent communication", "agent interoperability",
        "agent specification language", "agent contract",
        "provenance tracking", "audit trail ai",
        "decentralized identity agent", "verifiable credential agent",
        # Formal verification (specific to protocols)
        "formal verification protocol", "formal methods agent",
        "protocol formal verification",
    ],
    "S4_oversight": [
        # Collusion / covert communication detection (specific)
        "collusion detection", "agent collusion", "multi-agent collusion",
        "emergent communication detection", "steganography detection ai",
        "covert communication ai", "hidden communication agent",
        "covert channel agent",
        # Attribution (multi-agent specific)
        "attribution multi-agent", "trace attribution agent",
        "failure attribution agent", "delegation chain attribution",
        # Multi-agent oversight / control (specific compounds)
        "multi-agent oversight", "oversight multi-agent",
        "multi-agent control", "multi-agent monitoring",
        "population-level control", "population monitoring agent",
        "collective monitoring", "collective oversight",
        "agent population oversight", "deployed agent monitoring",
        # Circuit breakers / mechanisms
        "circuit breaker ai", "agent circuit breaker",
        "agent rate limiting", "agent desynchronization",
        "mechanism design collusion", "information design agent",
        # Red/blue teaming (multi-agent specific)
        "red team multi-agent", "blue team multi-agent",
        "multi-agent red teaming", "red-teaming agent collective",
        "agent red team", "collusion red team",
        # Scalable oversight for MAS
        "scalable oversight multi-agent", "oversight agent collective",
        "multi-agent safety", "agent safety multi",
        "unsafe multi-agent", "multi-agent risk",
        "cross-principal oversight",
    ],
}

# Specific first-pass terms — ONLY genuine multi-agent/MAS signals.
# Deliberately tight to avoid pulling in general ML/security/distributed-systems researchers.
BROAD_ADJACENT = [
    # MAS compound phrases (specific enough to stand alone)
    "multi-agent system", "multiagent system",
    "multi-agent reinforcement", "marl",
    "multi-agent framework", "multi-agent learning",
    # Game theory / mechanism design — core S2 signals
    "game theory", "mechanism design",
    "nash equilibrium", "incentive compatibility",
    "social choice", "cooperative game theory",
    "algorithmic game theory",
    # Collective / emergent (agent-specific compounds)
    "collective agent", "collective agency",
    "emergent collective", "agent population",
    "agent network", "agent ecosystem",
    # Swarm
    "swarm intelligence", "swarm robotics",
    # Agent infrastructure specifics
    "agent identity", "agent authentication",
    "agent reputation", "agent commitment",
    "agent delegation",
    # Oversight / collusion (specific)
    "collusion detection", "multi-agent oversight",
    "multi-agent control", "multi-agent safety",
    "multi-agent monitoring",
    # LLM agent (specific compound)
    "llm agent", "llm agents",
    "language model agent",
    "autonomous agent deployment",
    "agentic deployment",
    # Principal-agent (economics/AI specific)
    "principal-agent problem",
    "principal agent problem",
    "cooperative ai",
]

# Out-of-scope dominant terms (if these dominate and no MAAS signal → exclude)
OUT_OF_SCOPE_DOMINANT = [
    "image classification", "object detection", "semantic segmentation",
    "speech recognition", "audio processing", "signal processing",
    "medical imaging", "radiology", "histopathology",
    "drug discovery", "genomics", "protein folding", "bioinformatics",
    "vlsi", "chip design", "semiconductor", "embedded systems",
    "compiler design", "operating systems", "database query",
    "remote sensing", "climate model", "weather prediction",
    "structural engineering", "civil engineering", "power systems",
    "renewable energy", "smart grid",
    "sentiment analysis", "opinion mining",
    "document classification", "information retrieval",
]

# General AI safety terms (prevent over-exclusion of safety-adjacent researchers)
SAFETY_ADJACENT = [
    "ai safety", "trustworthy ai", "responsible ai",
    "alignment", "robustness", "fairness",
    "interpretability", "explainability", "transparency",
    "adversarial", "uncertainty", "calibration",
]


def build_prof_text(prof: dict) -> str:
    """Build combined research text from all available fields."""
    parts = []
    focus = prof.get("focus", {}) or {}
    if focus.get("research_summary"):
        parts.append(str(focus["research_summary"]))
    if focus.get("expertise"):
        parts.append(str(focus["expertise"]))
    if prof.get("department"):
        parts.append(str(prof["department"]))
    llm = (prof.get("scores", {}) or {}).get("llm", {}) or {}
    if llm.get("verdict"):
        parts.append(str(llm["verdict"]))
    for sub in llm.get("best_subthemes", []) or []:
        if isinstance(sub, dict):
            parts.append(str(sub.get("angle", "")))
    ac = prof.get("academic", {}) or {}
    for w in (ac.get("recent_works", []) or [])[:10]:
        if w.get("title"):
            parts.append(w["title"])
    return " ".join(parts)


def score_text(text: str) -> dict:
    """Per-cluster keyword scores (normalized 0-1, 3 hits = max)."""
    tl = text.lower()
    scores = {}
    for cluster, kws in CLUSTER_KEYWORDS.items():
        hits = sum(1 for kw in kws if kw in tl)
        scores[cluster] = min(1.0, hits / 3)
    return scores


def broad_hit(text: str) -> bool:
    """True if ANY broad adjacent term appears (very loose first pass)."""
    tl = text.lower()
    return any(t in tl for t in BROAD_ADJACENT)


def max_cluster_score(scores: dict) -> float:
    return max(scores.values()) if scores else 0.0


def is_off_topic(text: str, kw_max: float, broad: bool) -> bool:
    """True only if clearly dominated by out-of-scope terms with zero MAAS signal."""
    if broad or kw_max >= 0.1:
        return False
    tl = text.lower()
    oos_hits = sum(1 for t in OUT_OF_SCOPE_DOMINANT if t in tl)
    safety_hits = sum(1 for t in SAFETY_ADJACENT if t in tl)
    return oos_hits >= 2 and safety_hits < 2


def context_quality(prof: dict) -> str | None:
    ac = prof.get("academic", {}) or {}
    recent_works = ac.get("recent_works", []) or []
    focus = prof.get("focus", {}) or {}
    llm = (prof.get("scores", {}) or {}).get("llm", {}) or {}
    has_verdict = len(llm.get("verdict", "") or "") > 50
    has_focus = bool(focus.get("research_summary") or focus.get("expertise"))
    n_papers = len(recent_works)
    if n_papers == 0 and not has_focus and not has_verdict:
        return "no_papers"
    if n_papers <= 1 and not has_focus:
        return "low_context"
    return None
