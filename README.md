# Researcher → Proposal Matcher (IIT-H CSE demo)

Matches professors to the **Schmidt Sciences 2026 "Science of Trustworthy AI"** agenda.
Goes deep on each professor (real publications + abstracts, anchored by ID), captures
**non-academic agency signals** (startup / advisor / VC / patents / talks / social),
scores fit with **three explainable signals**, and shows everything in a dashboard where
you can validate a fit in under a minute. Every shown claim carries its source.

---

## Quick start

```bash
cd profmatch
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# keys (Groq is free tier; OpenAlex needs no key, email is optional politeness)
export GROQ_API_KEY="your_groq_key"
export OPENALEX_MAILTO="you@email.com"        # optional
export PROF_CSV="/Users/dhruv/Desktop/India_prof_scraping_IA/Matching_RP/matching_rp3/iith_cse_faculty.csv"

# 1) SEE THE DASHBOARD IMMEDIATELY (ships with 3 mock profiles)
streamlit run app.py

# 2) RUN FOR REAL — start with one professor (fast smoke test)
python3 pipeline.py --name "Antony"          # or --one for the first row
#    then all 30:
python3 pipeline.py --all                     # full: academic + web + scoring
python3 pipeline.py --all --no-web            # faster: skip web discovery
# refresh the dashboard after each run (it reads data/enriched_profiles.json)
```

The pipeline **checkpoints after every professor**, so a long `--all` run is resumable
and the dashboard shows partial results as they land. API responses are cached in
`data/cache/`, so re-runs are cheap.

---

## How it works (and why)

**1. Identity anchoring (the part that makes it trustworthy).**
Name search is hopeless here — "Abhijit Das" returns a Harvard professor, an IIT-KGP
professor, and three others. So we anchor on the **ORCID / Scholar / Scopus IDs already in
your CSV**. ORCID present (67% of rows) → exact OpenAlex match. No ORCID → name + IIT-H
affiliation + CS-concept filter, marked lower confidence. A built-in **h-index sanity check**
flags likely wrong-person matches. Nothing non-academic is trusted unless it corroborates
the anchored identity.

**2. Going deep.** From the anchored identity we pull the real publication record from
OpenAlex — titles, abstracts, venues, citations, coauthors — and split **whole-career vs.
last-5-years** focus. The scraped `research_interests` field is treated as a *weak* signal
because it's sometimes mis-scraped (one row literally contains the advisor's name).

**3. Non-academic agency signals (BL's priority).** Targeted web searches
(startup / founder / advisor / board / VC / patent / keynote / talk / podcast) → snippets
with URLs → the LLM extracts **only snippet-supported claims, each tagged with its source
URL**, ignoring snippets about a different person. Plus the LinkedIn/X/GitHub links already
in the CSV.

**4. Strict, explainable scoring.** Your old system's failure was scoring everyone high.
Three independent signals, shown transparently:
- **BM25** (keywords) and **dense semantic** (small fast embedding model — *not* the heavy
  one that was slow) — both cheap, run on everyone, used to rank and to focus the LLM.
- **LLM judge (Groq)** with a hard anchored rubric: high scores only for *recent, direct*
  work on a sub-theme's core question, and it **must cite a paper or say "NO DIRECT
  EVIDENCE"**. Generic "AI/ML" earns nothing.
- **Out-of-scope detection** — interpretability, fairness/bias, policy, watermarking, etc.
  are excluded by this RFP, so a brilliant interpretability prof is correctly flagged
  **Out of scope** (this is exactly the insight that saves wasted outreach).
- Final **tier is rule-based, not a soft average** (STRONG / POSSIBLE / WEAK / OUT_OF_SCOPE),
  so every ranking is auditable.

**5. Dashboard.** Ranked home page → click → full profile: fit per sub-theme with evidence,
career-vs-recent focus, top contributions, agency signals with source links, strengths /
gaps / deal-breakers, confidence, key numbers, and the raw three-signal scores in an
expander. Source on everything.

---

## Where this is now, and how to level it up

**Current level (honest):**
- Identity anchoring, deep academic pull, strict scoring, out-of-scope flagging, and the
  dashboard are solid and demo-ready on the 30 IIT-H CSE profs.
- The **web/agency layer is the weakest link**: free DuckDuckGo search rate-limits and
  returns noisy results, so recall on startup/advisor/VC signals is partial. It's good
  enough to *demonstrate* the capability on a few profs; it is not yet comprehensive.
- Dense embeddings use a small model (MiniLM) — fast and fine for ranking, not the last
  word on semantic nuance.

**Next steps, in priority order:**
1. **Validation set:** hand-label ~10 of the 30 as fit / not-fit, then tune the tier
   thresholds in `config.py` against them. This turns "looks right" into a number.
2. **Harden agency discovery:** swap DuckDuckGo for a real search API (below), add
   OpenAlex coauthor-network → "influence" signals, and Google Patents / PatentsView for
   inventorship.
3. **Scale path to 1,700:** keep the cheap signals (BM25 + dense) on everyone, run the
   expensive LLM judge + web discovery only on those who clear a cheap-score threshold or
   trip a keyword (the funnel). Add a small backend if you want on-demand "fetch full
   profile" for the long tail instead of precomputing all.
4. **Knowledge graph (later):** once extraction is reliable, store coauthor / advisor /
   company edges so you can query "who bridges academia and industry on oversight" without
   re-running the pipeline. Don't build this until extraction is trustworthy.

---

## Paid tools worth getting (all optional; everything above runs free)

| Tool | Why | Rough cost |
|------|-----|-----------|
| **Serper.dev / SerpAPI** | Reliable Google results — fixes the DuckDuckGo noise/rate-limit, biggest single quality win for agency signals | ~$50/mo |
| **Proxycurl / People Data Labs** | Structured LinkedIn data (only ~17% of rows have a LinkedIn URL today) | usage-based |
| **Semantic Scholar API key** | Higher rate limits for publication enrichment at scale | free key, paid tiers |
| **Crunchbase API** | Authoritative startup / funding / founder data | paid |
| **A hosted LLM (Claude/OpenAI)** | If Groq's free-tier limits pinch at 1,700 scale, or for a stronger judge | usage-based |

Tell me which you can get and I'll wire them in.

---

## Files
```
config.py        settings, keys, model names, thresholds
agenda.py        Schmidt 2026 agenda → 7 sub-themes + out-of-scope list
utils.py         CSV loader (field-size fix), Groq client, HTTP, cache, provenance
enrich.py        identity anchoring + OpenAlex publications/abstracts/recent focus
websignals.py    non-academic discovery (DDG search + LLM extraction, cited)
score.py         BM25 + dense + strict LLM judge + rule-based tiering
pipeline.py      orchestrator (--one / --name / --all / --no-web)
app.py           Streamlit dashboard (ranking → detail)
data/enriched_profiles.json   output (ships with 3 mock profiles)
```
