"""
OpenAlex enrichment for MAAS RFP.
Saves ALL recent paper titles (not just grant-bearing ones) so the LLM scorer
can use full publication context when evaluating MAAS cluster fit.

Cache dir: prof_facts_maas/<slug>.json  (separate from Schmidt pipeline)
"""

import json, os, re, time
import urllib.request
import urllib.parse

MAILTO = "dhruv@secureaifutureslab.com"
OA_BASE = "https://api.openalex.org"

INDUSTRY_FUNDER_KEYWORDS = [
    "google", "deepmind", "openai", "microsoft", "meta", "anthropic",
    "amazon", "apple", "samsung", "intel", "qualcomm", "ibm",
    "tata", "infosys", "wipro", "huawei", "baidu", "adobe",
    "cisco", "nvidia", "salesforce", "siemens", "bosch",
    "schmidt", "aria", "darpa", "iarpa", "nsf", "epsrc",
]

HERE = os.path.dirname(os.path.abspath(__file__))
FACTS_DIR = os.path.join(HERE, "prof_facts_maas")
# Also look at Schmidt pipeline facts for re-usable OA author IDs
SCHMIDT_FACTS_DIR = os.path.join(HERE, "..", "profmatch", "prof_facts")
os.makedirs(FACTS_DIR, exist_ok=True)


def _slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


def _get(url: str) -> dict:
    try:
        sep = "&" if "?" in url else "?"
        full = f"{url}{sep}mailto={MAILTO}"
        req = urllib.request.Request(full, headers={"User-Agent": "profmatch-maas/1.0"})
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read())
    except Exception as e:
        return {"error": str(e)}


def _author_id_from_profile(prof: dict) -> str | None:
    """Extract OA author ID from existing enriched profile fields."""
    ac = prof.get("academic", {}) or {}
    raw_id = ac.get("id") or ac.get("openalex_id") or ac.get("openalex_url") or ""
    if raw_id and "openalex.org/A" in str(raw_id):
        return str(raw_id).split("/")[-1]
    return None


def _author_id_from_schmidt_cache(slug: str) -> str | None:
    """Check if Schmidt pipeline already resolved OA author ID for this prof."""
    path = os.path.join(SCHMIDT_FACTS_DIR, f"{slug}.json")
    if os.path.exists(path):
        cached = json.load(open(path))
        return cached.get("oa_author_id")
    return None


def _search_author_oa(name: str, institution: str) -> str | None:
    """Search OpenAlex for author by name+affiliation."""
    q = urllib.parse.quote(name)
    url = f"{OA_BASE}/authors?search={q}&per-page=3&select=id,display_name,last_known_institutions"
    data = _get(url)
    results = data.get("results", [])
    if not results:
        return None
    inst_lower = institution.lower()
    inst_tokens = {t for t in inst_lower.split() if len(t) > 3}

    def match_score(a):
        insts = " ".join(
            (i.get("display_name") or "") for i in (a.get("last_known_institutions") or [])
        ).lower()
        return sum(1 for t in inst_tokens if t in insts)

    best = max(results, key=match_score)
    aid = best.get("id", "").split("/")[-1]
    return aid if aid.startswith("A") else None


def _fetch_works(author_id: str) -> list:
    """Fetch up to 50 recent works from OA (2020+)."""
    full_id = author_id if author_id.startswith("http") else f"https://openalex.org/{author_id}"
    url = (
        f"{OA_BASE}/works"
        f"?filter=authorships.author.id:{full_id}"
        f"&sort=publication_year:desc&per-page=50"
    )
    data = _get(url)
    works = data.get("results", [])
    # Filter 2020+ client-side (combining year filter with https:// URL causes 400)
    return [w for w in works if (w.get("publication_year") or 0) >= 2020]


def _extract_industry_funders(works: list) -> list:
    funders = []
    seen = set()
    for w in works:
        # Check awards field
        for a in (w.get("awards") or []):
            name = a.get("funder_display_name", "")
            key = name.lower()
            if any(kw in key for kw in INDUSTRY_FUNDER_KEYWORDS) and key not in seen:
                seen.add(key)
                funders.append({
                    "funder": name,
                    "year": w.get("publication_year"),
                    "paper_title": (w.get("title") or "")[:80],
                })
        # Check funders field
        for f in (w.get("funders") or []):
            name = f.get("display_name", "")
            key = name.lower()
            if any(kw in key for kw in INDUSTRY_FUNDER_KEYWORDS) and key not in seen:
                seen.add(key)
                funders.append({
                    "funder": name,
                    "year": w.get("publication_year"),
                    "paper_title": (w.get("title") or "")[:80],
                })
    return funders


def _extract_coauthors(works: list, self_id: str) -> list:
    counts: dict = {}
    for w in works:
        for auth in w.get("authorships", []) or []:
            a = auth.get("author", {}) or {}
            aid = (a.get("id") or "").split("/")[-1]
            if aid == self_id or not aid:
                continue
            if aid not in counts:
                counts[aid] = {"name": a.get("display_name", ""), "count": 0, "insts": set()}
            counts[aid]["count"] += 1
            for inst in auth.get("institutions", []) or []:
                if inst.get("display_name"):
                    counts[aid]["insts"].add(inst["display_name"])
    top = sorted(counts.values(), key=lambda x: x["count"], reverse=True)[:8]
    return [
        {"name": c["name"], "papers_together": c["count"], "institutions": list(c["insts"])[:2]}
        for c in top
    ]


def enrich_professor(prof: dict, force: bool = False) -> dict:
    """
    Fetch OpenAlex data for a professor, caching to prof_facts_maas/<slug>.json.
    Saves ALL paper titles (up to 50, 2020+) for full MAAS scoring context.
    """
    name = prof.get("name", "unknown")
    slug = _slug(name)
    cache_path = os.path.join(FACTS_DIR, f"{slug}.json")
    if os.path.exists(cache_path) and not force:
        return json.load(open(cache_path))

    print(f"  [OA] {name} ({prof.get('institute', '')})")

    # Try to find OA author ID (3 sources in priority order)
    author_id = (
        _author_id_from_profile(prof)
        or _author_id_from_schmidt_cache(slug)
    )
    if not author_id:
        author_id = _search_author_oa(name, prof.get("institute", ""))
        time.sleep(0.4)

    facts = {
        "name": name,
        "slug": slug,
        "oa_author_id": author_id,
        "total_works_fetched": 0,
        "all_papers": [],           # ALL titles+years — used for LLM context
        "industry_funders": [],
        "coauthors": [],
    }

    if author_id:
        works = _fetch_works(author_id)
        time.sleep(0.3)
        facts["total_works_fetched"] = len(works)
        # ALL papers (title + year) for full LLM context
        facts["all_papers"] = [
            {"title": (w.get("title") or "")[:120], "year": w.get("publication_year")}
            for w in works
        ]
        facts["industry_funders"] = _extract_industry_funders(works)
        facts["coauthors"] = _extract_coauthors(works, author_id)

    json.dump(facts, open(cache_path, "w"), indent=2)
    return facts
