"""
MAAS RFP data preparation pipeline.

Stages:
  1. Keyword pre-filter on all 1939 profs (fast, local)
     → keep any prof with keyword_max >= 0.05 OR broad_hit == True
  2. OA enrichment for all passing candidates (full paper list)
  3. LLM scoring (Groq rotation + Claude fallback) for all candidates
  4. Build maas_profiles.json with cluster scores, SC scores, evidence chips

Run from profmatch_maas/:
  python prep_maas.py [--no-enrich] [--no-llm] [--dry-run]

  --dry-run    : only run keyword filter and print stats, don't enrich or score
  --no-enrich  : skip OA enrichment (use cached or empty)
  --no-llm     : skip LLM scoring (use cached scores only)
"""

import json, os, re, sys, time, argparse

HERE = os.path.dirname(os.path.abspath(__file__))
FULL_DATA = os.path.join(HERE, "..", "profmatchf", "data", "enriched_profiles.json")
OUT_PATH = os.path.join(HERE, "data", "maas_profiles.json")
os.makedirs(os.path.join(HERE, "data"), exist_ok=True)

sys.path.insert(0, HERE)
import keyword_config_maas as kw_mod
import enrich_maas as enrich_mod
import fit_scorer_maas as scorer_mod


def _slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


def _original_fit(prof: dict) -> float:
    return (prof.get("scores", {}) or {}).get("llm", {}) or {}


def _original_fit_score(prof: dict) -> float:
    llm = (prof.get("scores", {}) or {}).get("llm", {}) or {}
    return float(llm.get("overall_fit", 0) or 0)


def _load_oa_facts(slug: str) -> dict | None:
    p = os.path.join(HERE, "prof_facts_maas", f"{slug}.json")
    return json.load(open(p)) if os.path.exists(p) else None


def _load_score(slug: str) -> dict | None:
    p = os.path.join(HERE, "scores_maas", f"{slug}.json")
    return json.load(open(p)) if os.path.exists(p) else None


def build_entry(prof: dict, score: dict | None, oa_facts: dict | None) -> dict:
    name = prof.get("name", "")
    ac = prof.get("academic", {}) or {}
    focus = prof.get("focus", {}) or {}
    llm = (prof.get("scores", {}) or {}).get("llm", {}) or {}

    # --- Axis A: best cluster score ---
    if score and not score.get("error"):
        cluster_scores = score.get("cluster_scores", {})
        best_cluster = score.get("best_cluster", "S2")
        axis_a = score.get("axis_a", 0)
        selection_criteria = score.get("selection_criteria", {})
        cluster_notes = score.get("cluster_notes", {})
        key_evidence = score.get("key_evidence", "")
        oos_risk = score.get("out_of_scope_risk", "none")
        oos_reason = score.get("out_of_scope_reason", "")
        scored = True
    else:
        cluster_scores = {"S1": 0, "S2": 0, "S3": 0, "S4": 0}
        best_cluster = ""
        axis_a = 0
        selection_criteria = {}
        cluster_notes = {}
        key_evidence = ""
        oos_risk = "none"
        oos_reason = ""
        scored = False

    # --- Evidence chips (Axis B) ---
    chips = []
    if oa_facts:
        for f in (oa_facts.get("industry_funders") or []):
            chips.append({"type": "industry_funder", "label": f["funder"], "detail": f.get("paper_title", "")})
        for c in (oa_facts.get("coauthors") or [])[:3]:
            chips.append({"type": "collaborator", "label": c["name"], "detail": ", ".join(c.get("institutions", []))})

    # Paper count as signal
    paper_count = 0
    if oa_facts:
        paper_count = oa_facts.get("total_works_fetched", 0)
    else:
        paper_count = len(ac.get("recent_works", []) or [])

    return {
        # Identity
        "name": name,
        "institute": prof.get("institute"),
        "department": prof.get("department"),
        "designation": prof.get("designation"),
        "email": prof.get("email"),
        "links": prof.get("links", {}),
        # MAAS scoring
        "scored": scored,
        "axis_a": axis_a,
        "best_cluster": best_cluster,
        "cluster_scores": cluster_scores,
        "cluster_notes": cluster_notes,
        "selection_criteria": selection_criteria,
        "key_evidence": key_evidence,
        "out_of_scope_risk": oos_risk,
        "out_of_scope_reason": oos_reason,
        # Context
        "research_summary": focus.get("research_summary", ""),
        "expertise": focus.get("expertise", ""),
        "original_verdict": llm.get("verdict", ""),
        "original_fit": _original_fit_score(prof),
        "context_flag": kw_mod.context_quality(prof),
        "paper_count": paper_count,
        # Academic display
        "academic_context": {
            "h_index": ac.get("h_index_openalex"),
            "works_count": ac.get("works_count"),
            "cited_by_total": ac.get("cited_by_total"),
            "recent_works": (ac.get("recent_works") or [])[:5],
        },
        # OA enrichment
        "oa_enrichment": {
            "author_id": (oa_facts or {}).get("oa_author_id"),
            "total_works_fetched": (oa_facts or {}).get("total_works_fetched", 0),
            "all_papers": (oa_facts or {}).get("all_papers", [])[:20],  # top 20 for display
            "industry_funders": (oa_facts or {}).get("industry_funders", []),
            "coauthors": (oa_facts or {}).get("coauthors", []),
        } if oa_facts else {},
        # Chips
        "axis_b_chips": chips,
    }


def main(run_enrich: bool = True, run_llm: bool = True, dry_run: bool = False):
    print(f"Loading {FULL_DATA}")
    data = json.load(open(FULL_DATA))
    print(f"  {len(data)} total profiles")

    # === STAGE 1: Keyword pre-filter ===
    print("\n=== Stage 1: Keyword pre-filter ===")
    candidates = []
    excluded = []
    for prof in data:
        text = kw_mod.build_prof_text(prof)
        kw_scores = kw_mod.score_text(text)
        kw_max = kw_mod.max_cluster_score(kw_scores)
        broad = kw_mod.broad_hit(text)
        off_topic = kw_mod.is_off_topic(text, kw_max, broad)

        if off_topic:
            excluded.append(prof.get("name", ""))
        elif kw_max >= 0.05 or broad:
            prof["_kw_scores"] = kw_scores
            prof["_kw_max"] = kw_max
            prof["_broad_hit"] = broad
            candidates.append(prof)
        else:
            excluded.append(prof.get("name", ""))

    print(f"  Candidates (pass keyword filter): {len(candidates)}")
    print(f"  Excluded (no MAAS signal): {len(excluded)}")

    # Sort candidates by keyword relevance for priority ordering
    candidates.sort(key=lambda p: (p.get("_kw_max", 0), p.get("_broad_hit", False)), reverse=True)

    # Show top keyword-matched
    print("\n  Top 15 by keyword score:")
    for p in candidates[:15]:
        print(f"    {p.get('name','?')[:35]:35s} kw={p.get('_kw_max',0):.2f} broad={p.get('_broad_hit',False)}")

    if dry_run:
        print(f"\n[DRY RUN] Would enrich + score {len(candidates)} candidates.")
        return

    # === STAGE 2: OA enrichment ===
    if run_enrich:
        print(f"\n=== Stage 2: OA enrichment ({len(candidates)} candidates) ===")
        for i, prof in enumerate(candidates, 1):
            slug = _slug(prof.get("name", ""))
            if _load_oa_facts(slug):
                continue  # already cached
            print(f"  [{i}/{len(candidates)}] {prof.get('name','?')}")
            try:
                enrich_mod.enrich_professor(prof)
                time.sleep(0.5)
            except Exception as e:
                print(f"    Enrich error: {e}")
    else:
        print("\n=== Stage 2: Skipping OA enrichment (--no-enrich) ===")

    # === STAGE 3: LLM scoring ===
    if run_llm:
        need_score = [p for p in candidates if not _load_score(_slug(p.get("name", "")))]
        print(f"\n=== Stage 3: LLM scoring ({len(need_score)} to score, {len(candidates)-len(need_score)} cached) ===")
        for i, prof in enumerate(need_score, 1):
            name = prof.get("name", "?")
            slug = _slug(name)
            oa_facts = _load_oa_facts(slug)
            papers_note = f"{oa_facts.get('total_works_fetched',0)} OA papers" if oa_facts else "no OA"
            print(f"  [{i}/{len(need_score)}] {name[:40]} | {papers_note}")
            try:
                scorer_mod.score_professor(prof, oa_facts)
                time.sleep(2)
            except Exception as e:
                print(f"    Scoring error: {e}")
    else:
        print("\n=== Stage 3: Skipping LLM scoring (--no-llm) ===")

    # === STAGE 4: Build output ===
    print(f"\n=== Stage 4: Building maas_profiles.json ({len(candidates)} entries) ===")
    results = []
    for prof in candidates:
        slug = _slug(prof.get("name", ""))
        score = _load_score(slug)
        oa_facts = _load_oa_facts(slug)
        entry = build_entry(prof, score, oa_facts)
        results.append(entry)

    # Sort: scored first (by axis_a), then unscored
    results.sort(
        key=lambda e: (1 if e["scored"] else 0, e["axis_a"], len(e.get("axis_b_chips", []))),
        reverse=True,
    )

    # Stats
    scored_count = sum(1 for e in results if e["scored"])
    chips_total = sum(len(e.get("axis_b_chips", [])) for e in results)
    print(f"\nStats:")
    print(f"  Total candidates: {len(results)}")
    print(f"  LLM-scored: {scored_count}")
    print(f"  Evidence chips: {chips_total}")

    # Cluster breakdown
    cluster_counts = {"S1": 0, "S2": 0, "S3": 0, "S4": 0}
    for e in results:
        bc = e.get("best_cluster", "")
        if bc in cluster_counts:
            cluster_counts[bc] += 1
    print("  Best cluster distribution:")
    for c, n in sorted(cluster_counts.items()):
        print(f"    {c}: {n}")

    json.dump(results, open(OUT_PATH, "w"), indent=None, separators=(",", ":"))
    size_kb = os.path.getsize(OUT_PATH) / 1024
    print(f"\n✓ Saved {len(results)} profiles to {OUT_PATH} ({size_kb:.0f} KB)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-enrich", action="store_true")
    parser.add_argument("--no-llm", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    main(run_enrich=not args.no_enrich, run_llm=not args.no_llm, dry_run=args.dry_run)
