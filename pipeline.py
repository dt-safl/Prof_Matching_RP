"""Orchestrator. Run end-to-end and write data/enriched_profiles.json (checkpointed).

Examples:
  python3 pipeline.py --one            # first professor only (fast smoke test)
  python3 pipeline.py --name "Antony"  # a specific professor by name substring
  python3 pipeline.py --all            # all professors in the CSV
  python3 pipeline.py --all --no-web   # skip web discovery (academic + scoring only)
"""
import argparse, json, os, sys, time
import config, utils, enrich, websignals, score


def summarize_focus(row, academic):
    """One LLM call: career-vs-recent focus, in plain language, from real titles."""
    if not academic.get("resolved") or not config.GROQ_API_KEY:
        ri = utils.clean(row.get("research_interests", ""))
        return {"overall": ri[:300], "recent": "", "source": "scraped_interests"}
    sys_p = ("Summarize a professor's research focus from their paper titles. Two short labelled "
             "lines: 'Overall:' (whole career) and 'Recent:' (last ~5 years, where they are now). "
             "Be concrete and specific; no fluff. JSON only.")
    usr = (f"ALL TITLES: {academic.get('all_titles_text','')[:3000]}\n\n"
           f"RECENT TITLES: {academic.get('recent_titles_text','')[:2500]}\n\n"
           'Return {"overall":"...","recent":"..."}')
    try:
        out = utils.groq_json([{"role": "system", "content": sys_p}, {"role": "user", "content": usr}],
                              model=config.GROQ_MODEL_EXTRACT, max_tokens=500)
        out["source"] = "openalex_titles+llm"
        return out
    except Exception as e:
        return {"overall": "", "recent": "", "error": str(e)}


def process_one(row, do_web=True):
    name = utils.clean(row.get("name", ""))
    print(f"  · {name}: resolving identity…", flush=True)
    academic = enrich.enrich_academic(row)
    sanity = enrich.identity_sanity(row, academic)
    focus = summarize_focus(row, academic)

    print(f"    scoring (bm25 + dense + strict LLM)…", flush=True)
    scored = score.score_profile(row, academic)

    web = {}
    if do_web:
        print(f"    web discovery (non-academic signals)…", flush=True)
        web = websignals.enrich_web(row)

    return {
        "name": name,
        "designation": utils.clean(row.get("designation", "")),
        "department": utils.clean(row.get("department", "")),
        "institute": utils.clean(row.get("institute", "")),
        "email": utils.clean(row.get("email", "")),
        "photo_ok": utils.clean(row.get("irins_photo_url", "")),  # photo_url col is junk; irins is clean
        "links": {k: row.get(k, "") for k in
                  ["iith_profile_url", "google_scholar_url", "orcid_url", "dblp_url",
                   "scopus_url", "linkedin_url", "twitter_url", "github_url", "personal_website"]
                  if utils.clean(row.get(k, ""))},
        "scraped_metrics": {
            "scholar_citations": row.get("scholar_citations", ""),
            "scholar_h_index": row.get("scholar_h_index", ""),
            "scholar_h_index5y": row.get("scholar_h_index5y", ""),
            "scholar_citations5y": row.get("scholar_citations5y", ""),
            "pub_journals": row.get("pub_journals", ""),
            "pub_conferences": row.get("pub_conferences", ""),
        },
        "scraped_extras": {k: utils.clean(row.get(k, "")) for k in
                           ["honors", "projects", "phd_supervised", "experience", "education", "admin_positions"]
                           if utils.clean(row.get(k, ""))},
        "academic": academic,
        "identity_sanity": sanity,
        "focus": focus,
        "scores": scored,
        "web_signals": web,
        "_generated": time.strftime("%Y-%m-%d %H:%M"),
    }


def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--one", action="store_true", help="first professor only")
    g.add_argument("--all", action="store_true", help="all professors")
    g.add_argument("--name", type=str, help="professors whose name contains this substring")
    ap.add_argument("--no-web", action="store_true", help="skip non-academic web discovery")
    ap.add_argument("--csv", default=config.DEFAULT_CSV)
    ap.add_argument("--limit", type=int, default=0, help="cap number processed")
    args = ap.parse_args()

    if not os.path.exists(args.csv):
        sys.exit(f"CSV not found: {args.csv}\nPass --csv /path/to/file.csv")
    rows = utils.load_csv(args.csv)
    if args.name:
        rows = [r for r in rows if args.name.lower() in utils.clean(r.get("name", "")).lower()]
    elif args.one:
        rows = rows[:1]
    if args.limit:
        rows = rows[:args.limit]
    if not rows:
        sys.exit("No matching professors.")

    print(f"Processing {len(rows)} professor(s). Web discovery: {not args.no_web}")
    if not config.GROQ_API_KEY:
        print("  ⚠ GROQ_API_KEY not set — LLM judge/summaries will be skipped/empty.")

    os.makedirs(os.path.dirname(config.OUT_JSON), exist_ok=True)
    results = []
    for i, row in enumerate(rows, 1):
        print(f"[{i}/{len(rows)}]", flush=True)
        try:
            results.append(process_one(row, do_web=not args.no_web))
        except Exception as e:
            print(f"    ! error: {e}")
            results.append({"name": utils.clean(row.get("name", "")), "error": str(e)})
        results.sort(key=lambda r: r.get("scores", {}).get("rank_key", (0, 0, 0)), reverse=True)
        json.dump(results, open(config.OUT_JSON, "w"), indent=2, default=str)  # checkpoint each prof

    print(f"\n✓ Wrote {len(results)} profiles → {config.OUT_JSON}")
    print("  Launch dashboard:  streamlit run app.py")


if __name__ == "__main__":
    main()
