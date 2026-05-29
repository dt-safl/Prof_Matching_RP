"""Schmidt Sciences 2026 'Science of Trustworthy AI' agenda, decomposed for matching.

Source: https://www.schmidtsciences.org/trustworthy-ai-research-agenda/ (modified 2026-02-19)
Objectives are paraphrased (not copied). Keywords drive BM25; objective text drives dense + LLM.
3 sections, 7 sub-themes.
"""

SUBTHEMES = [
    {
        "id": "1.1",
        "section": "S1: Characterizing & Forecasting Misalignment",
        "title": "What is misalignment, and how much do we see today?",
        "objective": ("Operationalize and quantify misalignment in decision-relevant terms; study "
                      "specification gaming, goal misgeneralization, distribution shift, emergent "
                      "misalignment, and how extended human-model interaction shapes behavior."),
        "keywords": ["misalignment", "specification gaming", "reward hacking", "goal misgeneralization",
                     "distribution shift", "emergent misalignment", "sycophancy", "deception",
                     "alignment", "out-of-distribution", "RLHF"],
    },
    {
        "id": "1.2",
        "section": "S1: Characterizing & Forecasting Misalignment",
        "title": "Mechanisms of generalization and representation",
        "objective": ("Understand why models generalize as they do: inductive biases, how training "
                      "shapes internal representations of beliefs/goals/values, mesa-optimization, "
                      "causal world models, and proxy collapse."),
        "keywords": ["inductive bias", "internal representations", "mechanistic", "world model",
                     "mesa-optimization", "generalization", "representation learning", "circuits",
                     "features", "probing", "causal"],
    },
    {
        "id": "1.3",
        "section": "S1: Characterizing & Forecasting Misalignment",
        "title": "Scaling, emergence, and forecasting risk",
        "objective": ("Forecast risk-relevant properties: safety scaling laws, emergence and phase "
                      "transitions, ex-ante prediction of deployment failures, and safety cases for "
                      "evaluations that must generalize."),
        "keywords": ["scaling laws", "emergence", "phase transition", "forecasting", "capability",
                     "autonomy", "time horizon", "safety case", "early warning", "prediction"],
    },
    {
        "id": "2.1",
        "section": "S2: Generalizable Measurements & Interventions",
        "title": "Building a science of evaluation",
        "objective": ("Develop evaluations with construct validity and predictive validity that stay "
                      "informative under optimization pressure: strategy-proof evals, chain-of-thought "
                      "monitorability, model organisms, tail-risk and uncertainty quantification."),
        "keywords": ["evaluation", "benchmark", "construct validity", "predictive validity",
                     "chain-of-thought", "monitorability", "model organisms", "red team",
                     "uncertainty quantification", "tail risk", "auditing", "measurement"],
    },
    {
        "id": "2.2",
        "section": "S2: Generalizable Measurements & Interventions",
        "title": "Interventions that generalize",
        "objective": ("Interventions that change what systems learn (effective goals), not just surface "
                      "behavior: deliberative/myopic/process supervision generalization, improving "
                      "specifications/constitutions, value uncertainty, preserving human agency."),
        "keywords": ["alignment training", "process supervision", "deliberative", "constitutional",
                     "model spec", "value alignment", "human agency", "fine-tuning", "robust training",
                     "intervention", "steering"],
    },
    {
        "id": "3.1",
        "section": "S3: Oversight Under Capability Gaps & Multi-Agent Risks",
        "title": "Amplified oversight for superhuman performance",
        "objective": ("Enable weaker supervisors to reliably oversee stronger models (scalable/amplified "
                      "oversight, superalignment): weak-to-strong generalization, debate, recursive reward "
                      "modeling, task decomposition; verification under capability gaps and control evals."),
        "keywords": ["scalable oversight", "amplified oversight", "superalignment", "weak-to-strong",
                     "debate", "recursive reward modeling", "task decomposition", "control evaluation",
                     "verification", "human feedback", "oversight"],
    },
    {
        "id": "3.2",
        "section": "S3: Oversight Under Capability Gaps & Multi-Agent Risks",
        "title": "Multi-agent risks and collective dynamics",
        "objective": ("Risks emerging from interacting AI agents: collusion, coercion and other "
                      "interaction-specific properties, multi-agent misgeneralization, emergent collective "
                      "failures, and infrastructure for trustworthy multi-agent interaction."),
        "keywords": ["multi-agent", "agents", "collusion", "cooperation", "game theory", "emergent",
                     "collective", "coordination", "negotiation", "agent infrastructure", "reputation"],
    },
]

# Explicitly OUT OF SCOPE for THIS RFP (per the agenda's 'Out of Scope' section).
# A professor whose CORE area is one of these is a non-fit even if technically excellent.
OUT_OF_SCOPE = [
    ("interpretability", "Projects exclusively focused on interpretability (separate Interpretability pilot program)."),
    ("fairness / bias", "Fairness, accountability, and bias research not tied to the agenda."),
    ("policy / governance", "Policy and AI governance."),
    ("watermarking / content authenticity", "Epistemic integrity, content authenticity, watermarking."),
    ("jailbreak discovery", "Jailbreak discovery / ad hoc adversarial probing without robustness science."),
    ("generic capability evals", "Generic capability evaluations without a safety-relevant link."),
    ("near-term product engineering", "Near-term product engineering / shipping immediate applications."),
    ("CBRN / ARA evals", "Direct CBRN or ARA dangerous-capability evaluations."),
    ("model safeguards", "I/O filtering, constitutional classifiers, and similar safeguards."),
]


def agenda_for_prompt() -> str:
    """Compact agenda text for the LLM judge."""
    lines = ["SCHMIDT SCIENCES 2026 — SCIENCE OF TRUSTWORTHY AI (matching targets):"]
    cur = None
    for t in SUBTHEMES:
        if t["section"] != cur:
            cur = t["section"]
            lines.append(f"\n{cur}")
        lines.append(f"  [{t['id']}] {t['title']}: {t['objective']}")
    lines.append("\nEXPLICITLY OUT OF SCOPE for this RFP (core work here = NOT a fit):")
    for name, desc in OUT_OF_SCOPE:
        lines.append(f"  - {name}: {desc}")
    return "\n".join(lines)


if __name__ == "__main__":
    print(agenda_for_prompt())
    print(f"\n{len(SUBTHEMES)} sub-themes, {len(OUT_OF_SCOPE)} out-of-scope categories.")
