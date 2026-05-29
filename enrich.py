"""Academic enrichment: anchor identity by ORCID (or name+affiliation fallback),
then pull real publications, abstracts, recent focus, coauthors from OpenAlex.

Why anchored: name search is unreliable (the probe returned 5 'Abhijit Das' across
Harvard/IIT-KGP/etc). ORCID/Scholar IDs in the CSV give a clean 1:1 match.
"""
import time
import config, utils

OA = "https://api.openalex.org"


def _mailto():
    return f"&mailto={config.OPENALEX_MAILTO}" if config.OPENALEX_MAILTO else ""


def _abstract(inv):
    """Reconstruct text from OpenAlex abstract_inverted_index."""
    if not inv:
        return ""
    pos = {}
    for word, idxs in inv.items():
        for i in idxs:
            pos[i] = word
    return " ".join(pos[i] for i in sorted(pos))[:1200]


def resolve_author(row):
    """Return (openalex_author_dict, match_method, confidence) or (None, reason, 'LOW')."""
    orcid = utils.orcid_id(row.get("orcid_url", ""))
    if orcid:
        key = f"oa_author_orcid:{orcid}"
        cached = utils.cache_get(key)
        if cached:
            return cached, "orcid", "HIGH"
        try:
            a = utils.http_get_json(f"{OA}/authors/orcid:{orcid}?{_mailto()[1:]}")
            utils.cache_set(key, a)
            return a, "orcid", "HIGH"
        except Exception:
            pass  # fall through to name search

    # fallback: name search filtered to a Hyderabad/CS-ish candidate
    name = utils.clean(row.get("name", ""))
    if not name:
        return None, "no name", "LOW"
    key = f"oa_authsearch:{name}"
    cached = utils.cache_get(key)
    res = cached or utils.http_get_json(
        f"{OA}/authors?search={utils.urllib.parse.quote(name)}&per_page=5{_mailto()}").get("results", [])
    if not cached:
        utils.cache_set(key, res)

    def score(a):
        insts = " ".join(i.get("display_name", "") for i in (a.get("last_known_institutions") or [])).lower()
        concepts = " ".join(c.get("display_name", "") for c in a.get("x_concepts", [])[:5]).lower()
        s = 0
        if "hyderabad" in insts: s += 3
        if "indian institute of technology" in insts: s += 1
        if "computer science" in concepts: s += 1
        return s
    if not res:
        return None, "no match", "LOW"
    best = max(res, key=score)
    conf = "MEDIUM" if score(best) >= 3 else "LOW"
    return best, "name+affiliation", conf


def fetch_works(author_id):
    short = author_id.rstrip("/").split("/")[-1]
    key = f"oa_works:{short}"
    cached = utils.cache_get(key)
    if cached:
        return cached
    url = (f"{OA}/works?filter=author.id:{short}"
           f"&sort=publication_date:desc&per-page=100{_mailto()}")
    works = []
    try:
        page = utils.http_get_json(url)
        for w in page.get("results", [])[:config.MAX_WORKS]:
            works.append({
                "title": w.get("title") or "",
                "year": w.get("publication_year"),
                "cited_by": w.get("cited_by_count", 0),
                "venue": (((w.get("primary_location") or {}).get("source") or {}) or {}).get("display_name", ""),
                "abstract": _abstract(w.get("abstract_inverted_index")),
                "url": w.get("id", ""),
            })
    except Exception as e:
        return {"error": str(e), "works": []}
    utils.cache_set(key, works)
    return works


def enrich_academic(row):
    """Build the academic half of a profile, anchored and cited."""
    author, method, conf = resolve_author(row)
    out = {"resolved": bool(author), "match_method": method, "academic_confidence": conf}
    if not author:
        out["note"] = f"Could not anchor identity ({method}); academic signals rely on scraped CSV only."
        return out

    aid = author.get("id", "")
    out["openalex_id"] = aid
    out["openalex_url"] = aid
    ss = author.get("summary_stats", {}) or {}
    out["h_index_openalex"] = ss.get("h_index")
    out["works_count"] = author.get("works_count")
    out["cited_by_total"] = author.get("cited_by_count")
    out["concepts"] = [c.get("display_name") for c in author.get("x_concepts", [])[:8]]

    works = fetch_works(aid)
    if isinstance(works, dict) and works.get("error"):
        out["works_error"] = works["error"]; works = []
    out["n_works_pulled"] = len(works)

    recent = [w for w in works if (w.get("year") or 0) >= 2026 - config.RECENT_YEARS]
    out["recent_works"] = recent[:25]
    out["top_cited"] = sorted(works, key=lambda w: w.get("cited_by", 0), reverse=True)[:config.TOP_PAPERS_SHOW]
    out["recent_titles_text"] = " . ".join(w["title"] for w in recent if w["title"])[:4000]
    out["recent_abstracts_text"] = " ".join(w["abstract"] for w in recent if w["abstract"])[:6000]
    out["all_titles_text"] = " . ".join(w["title"] for w in works if w["title"])[:6000]
    return out


# ---- sanity cross-check: does OpenAlex h-index roughly match the scraped Scholar h-index? ----
def identity_sanity(row, academic):
    sch = row.get("scholar_h_index", "")
    oa_h = academic.get("h_index_openalex")
    try:
        sch = int(sch)
    except Exception:
        return None
    if oa_h is None:
        return None
    # large mismatch => possible wrong-person match
    if abs(oa_h - sch) > max(8, 0.6 * max(oa_h, sch)):
        return f"h-index mismatch (OpenAlex {oa_h} vs scraped Scholar {sch}) — verify identity"
    return None
