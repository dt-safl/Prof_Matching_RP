"""Shared utilities: CSV loading, Groq LLM calls, HTTP, JSON helpers."""
import csv, sys, json, time, os, urllib.request, urllib.parse, hashlib
import config

# ---- CSV: fix the 'field larger than field limit' crash (photo_url ~5600 chars, big JSON cols) ----
csv.field_size_limit(min(sys.maxsize, 2**31 - 1))


def load_csv(path):
    """Read the scraped faculty CSV into a list of dicts, trying common encodings."""
    for enc in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            with open(path, encoding=enc, newline="") as f:
                return [dict(row) for row in csv.DictReader(f)]
        except UnicodeDecodeError:
            continue
    raise RuntimeError(f"Could not read {path} with utf-8/latin-1")


def clean(s):
    return (s or "").strip()


def orcid_id(url):
    """Extract bare ORCID from a URL or return '' ."""
    if not url:
        return ""
    m = url.rstrip("/").split("/")[-1]
    return m if m.count("-") == 3 else ""


# ---- HTTP ----
def http_get_json(url, headers=None):
    req = urllib.request.Request(url, headers=headers or {"User-Agent": "profmatch/1.0"})
    with urllib.request.urlopen(req, timeout=config.HTTP_TIMEOUT) as r:
        return json.load(r)


def http_get_text(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 profmatch/1.0"})
    with urllib.request.urlopen(req, timeout=config.HTTP_TIMEOUT) as r:
        raw = r.read()
    try:
        return raw.decode("utf-8", errors="ignore")
    except Exception:
        return raw.decode("latin-1", errors="ignore")


# ---- simple disk cache (so re-runs don't re-hit APIs) ----
def cache_path(key):
    os.makedirs(config.CACHE_DIR, exist_ok=True)
    h = hashlib.md5(key.encode()).hexdigest()
    return os.path.join(config.CACHE_DIR, h + ".json")


def cache_get(key):
    p = cache_path(key)
    if os.path.exists(p):
        try:
            return json.load(open(p))
        except Exception:
            return None
    return None


def cache_set(key, value):
    try:
        json.dump(value, open(cache_path(key), "w"))
    except Exception:
        pass


# ---- Groq (OpenAI-compatible chat) ----
def groq_chat(messages, model=None, temperature=0.1, max_tokens=1500, json_mode=False):
    """Call Groq. Returns assistant text, or raises with a clear message."""
    if not config.GROQ_API_KEY:
        raise RuntimeError("GROQ_API_KEY not set. `export GROQ_API_KEY=...`")
    body = {
        "model": model or config.GROQ_MODEL_JUDGE,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if json_mode:
        body["response_format"] = {"type": "json_object"}
    data = json.dumps(body).encode()
    req = urllib.request.Request(
        config.GROQ_BASE, data=data,
        headers={"Authorization": f"Bearer {config.GROQ_API_KEY}",
                 "Content-Type": "application/json",
                 "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"},
    )
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=90) as r:
                out = json.load(r)
            return out["choices"][0]["message"]["content"]
        except urllib.error.HTTPError as e:
            if e.code == 429:  # rate limit -> back off
                time.sleep(5 * (attempt + 1))
                continue
            raise RuntimeError(f"Groq HTTP {e.code}: {e.read().decode()[:300]}")
    raise RuntimeError("Groq rate-limited after retries.")


def groq_json(messages, model=None, max_tokens=1800):
    """Call Groq in JSON mode and parse. Falls back to brace-extraction if needed."""
    txt = groq_chat(messages, model=model, json_mode=True, max_tokens=max_tokens)
    try:
        return json.loads(txt)
    except Exception:
        a, b = txt.find("{"), txt.rfind("}")
        if a >= 0 and b > a:
            return json.loads(txt[a:b + 1])
        raise


def src(value, source, url=""):
    """Wrap a value with provenance so the dashboard can cite where it came from."""
    return {"value": value, "source": source, "url": url}
