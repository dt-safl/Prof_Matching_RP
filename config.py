"""Central configuration. Keys come from environment variables (never hard-code)."""
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# ---- API keys (set these in your shell or a .env file) ----
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")           # required for LLM steps
OPENALEX_MAILTO = os.environ.get("OPENALEX_MAILTO", "")      # optional: polite pool, faster

# ---- Groq models (VERIFY current names at console.groq.com/docs/models) ----
GROQ_MODEL_JUDGE   = os.environ.get("GROQ_MODEL_JUDGE", "llama-3.3-70b-versatile")   # strict scoring
GROQ_MODEL_EXTRACT = os.environ.get("GROQ_MODEL_EXTRACT", "llama-3.1-8b-instant")    # fast extraction/summaries
GROQ_BASE = "https://api.groq.com/openai/v1/chat/completions"

# ---- Dense embeddings (small + fast on CPU; the heavy model was the old bottleneck) ----
EMBED_MODEL = os.environ.get("EMBED_MODEL", "sentence-transformers/all-MiniLM-L6-v2")

# ---- Paths ----
HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_CSV = os.environ.get(
    "PROF_CSV",
    os.path.join(HERE, "data", "iith_cse_faculty.csv"),  # Use relative path for deployment
)
OUT_JSON = os.path.join(HERE, "data", "enriched_profiles.json")
CACHE_DIR = os.path.join(HERE, "data", "cache")

# ---- Enrichment knobs ----
MAX_WORKS = 200            # cap OpenAlex works pulled per author
RECENT_YEARS = 5           # "last N years" window
TOP_PAPERS_SHOW = 6        # top contributions to surface
WEB_QUERIES_PER_PROF = 6   # non-academic discovery queries (keep modest: DDG rate-limits)
WEB_RESULTS_PER_QUERY = 4
HTTP_TIMEOUT = 30
WEB_DELAY_SEC = 2.5        # politeness between web searches

# ---- Scoring thresholds (tune after first validation pass) ----
TIER_STRONG_LLM = 70
TIER_POSSIBLE_LLM = 40
