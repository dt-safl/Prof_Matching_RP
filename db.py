"""SQLite layer: schema, connection, and small upsert/query helpers."""
import sqlite3
import json
from contextlib import contextmanager
from config import settings

SCHEMA = """
CREATE TABLE IF NOT EXISTS profs (
    prof_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    name_variants TEXT,
    institute TEXT,
    department TEXT,
    designation TEXT,
    email TEXT,
    homepage_url TEXT,
    openalex_id TEXT,
    scholar_id TEXT,
    orcid TEXT,
    h_index INT, i10_index INT,
    citations_total INT, citations_5y INT,
    works_count INT, works_count_5y INT,
    first_pub_year INT, last_pub_year INT,
    is_bhatnagar INT DEFAULT 0, is_jc_bose INT DEFAULT 0,
    is_insa_fellow INT DEFAULT 0, is_padma INT DEFAULT 0, is_infosys_prize INT DEFAULT 0,
    other_awards TEXT,
    interests_career TEXT,
    interests_recent TEXT,
    web_snippets TEXT,
    linkedin_manual TEXT,
    abstract_coverage REAL,
    enrich_quality REAL,
    last_enriched TEXT,
    sources TEXT
);
CREATE TABLE IF NOT EXISTS publications (
    pub_id TEXT PRIMARY KEY,
    prof_id TEXT,
    title TEXT NOT NULL,
    year INT,
    venue TEXT,
    venue_tier TEXT,
    citations INT,
    author_position TEXT,
    co_authors TEXT,
    abstract TEXT,
    concepts TEXT,
    source TEXT,
    url TEXT
);
CREATE TABLE IF NOT EXISTS sub_themes (
    sub_theme_id TEXT PRIMARY KEY,
    pillar INT, title TEXT,
    detailed_description TEXT,
    key_concepts TEXT, representative_methods TEXT,
    in_scope_examples TEXT, out_of_scope TEXT,
    indian_expertise_signals TEXT
);
CREATE TABLE IF NOT EXISTS scores (
    score_id INTEGER PRIMARY KEY AUTOINCREMENT,
    prof_id TEXT, sub_theme_id TEXT, run_id TEXT,
    bm25_score REAL, embedding_score REAL,
    topical_alignment INT, methodological_fit INT, recency_focus INT,
    depth_competence INT, out_of_scope_risk INT,
    composite REAL,
    fit_verdict TEXT, confidence TEXT,
    strong_points TEXT, weak_points TEXT, debatable_points TEXT, standout_facts TEXT,
    one_line_summary TEXT,
    llm_model TEXT, prompt_version TEXT, scored_at TEXT,
    UNIQUE(prof_id, sub_theme_id, run_id)
);
CREATE TABLE IF NOT EXISTS annotations (
    annotation_id INTEGER PRIMARY KEY AUTOINCREMENT,
    prof_id TEXT, sub_theme_id TEXT,
    status TEXT, note TEXT, created_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_pub_prof ON publications(prof_id);
CREATE INDEX IF NOT EXISTS idx_score_prof ON scores(prof_id);
CREATE INDEX IF NOT EXISTS idx_score_theme ON scores(sub_theme_id);
"""


@contextmanager
def get_conn():
    conn = sqlite3.connect(settings.DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_conn() as c:
        c.executescript(SCHEMA)


def _upsert(conn, table, row: dict):
    cols = list(row.keys())
    placeholders = ",".join("?" for _ in cols)
    updates = ",".join(f"{col}=excluded.{col}" for col in cols if col != "prof_id" and col != "pub_id" and col != "sub_theme_id")
    pk = "prof_id" if table == "profs" else "pub_id" if table == "publications" else "sub_theme_id"
    sql = (f"INSERT INTO {table} ({','.join(cols)}) VALUES ({placeholders}) "
           f"ON CONFLICT({pk}) DO UPDATE SET {updates}")
    conn.execute(sql, [row[c] for c in cols])


def upsert_prof(conn, row):
    _upsert(conn, "profs", row)


def upsert_publication(conn, row):
    _upsert(conn, "publications", row)


def upsert_sub_theme(conn, row):
    _upsert(conn, "sub_themes", row)


def save_score(conn, row):
    cols = list(row.keys())
    placeholders = ",".join("?" for _ in cols)
    updates = ",".join(f"{c}=excluded.{c}" for c in cols
                       if c not in ("prof_id", "sub_theme_id", "run_id"))
    sql = (f"INSERT INTO scores ({','.join(cols)}) VALUES ({placeholders}) "
           f"ON CONFLICT(prof_id, sub_theme_id, run_id) DO UPDATE SET {updates}")
    conn.execute(sql, [row[c] for c in cols])


# ---- query helpers used by the dashboard ----
def J(v):
    """json.loads that tolerates None / already-parsed values."""
    if v is None:
        return None
    if isinstance(v, (list, dict)):
        return v
    try:
        return json.loads(v)
    except Exception:
        return v


def get_runs():
    with get_conn() as c:
        rows = c.execute("SELECT DISTINCT run_id FROM scores ORDER BY run_id DESC").fetchall()
        return [r["run_id"] for r in rows]


def get_ranked(run_id, sub_theme_id=None, pillar=None):
    """Ranked list. If a sub-theme is given, rank by that theme; else rank by a prof's
    best (max composite) within the pillar."""
    with get_conn() as c:
        themes = []
        if pillar is not None:
            themes = [r["sub_theme_id"] for r in c.execute(
                "SELECT sub_theme_id FROM sub_themes WHERE pillar=?", (pillar,)).fetchall()]
        if sub_theme_id and sub_theme_id != "ALL":
            rows = c.execute(
                """SELECT s.*, p.name, p.department, p.designation
                   FROM scores s JOIN profs p ON p.prof_id=s.prof_id
                   WHERE s.run_id=? AND s.sub_theme_id=?
                   ORDER BY s.composite DESC""", (run_id, sub_theme_id)).fetchall()
        else:
            # best score per prof within the pillar
            qmarks = ",".join("?" for _ in themes) or "''"
            rows = c.execute(
                f"""SELECT s.*, p.name, p.department, p.designation
                    FROM scores s JOIN profs p ON p.prof_id=s.prof_id
                    WHERE s.run_id=? AND s.sub_theme_id IN ({qmarks})
                    AND s.composite = (
                        SELECT MAX(s2.composite) FROM scores s2
                        WHERE s2.prof_id=s.prof_id AND s2.run_id=s.run_id
                        AND s2.sub_theme_id IN ({qmarks}))
                    GROUP BY s.prof_id
                    ORDER BY s.composite DESC""",
                (run_id, *themes, *themes)).fetchall()
        return [dict(r) for r in rows]


def get_prof(prof_id):
    with get_conn() as c:
        r = c.execute("SELECT * FROM profs WHERE prof_id=?", (prof_id,)).fetchone()
        return dict(r) if r else None


def get_publications(prof_id):
    with get_conn() as c:
        rows = c.execute(
            "SELECT * FROM publications WHERE prof_id=? ORDER BY year DESC, citations DESC",
            (prof_id,)).fetchall()
        return [dict(r) for r in rows]


def get_scores_for_prof(prof_id, run_id, pillar=None):
    with get_conn() as c:
        if pillar is not None:
            themes = [r["sub_theme_id"] for r in c.execute(
                "SELECT sub_theme_id FROM sub_themes WHERE pillar=?", (pillar,)).fetchall()]
            qmarks = ",".join("?" for _ in themes) or "''"
            rows = c.execute(
                f"SELECT * FROM scores WHERE prof_id=? AND run_id=? AND sub_theme_id IN ({qmarks})",
                (prof_id, run_id, *themes)).fetchall()
        else:
            rows = c.execute("SELECT * FROM scores WHERE prof_id=? AND run_id=?",
                             (prof_id, run_id)).fetchall()
        return [dict(r) for r in rows]


def get_sub_themes(pillar=None):
    with get_conn() as c:
        if pillar is not None:
            rows = c.execute("SELECT * FROM sub_themes WHERE pillar=? ORDER BY sub_theme_id",
                             (pillar,)).fetchall()
        else:
            rows = c.execute("SELECT * FROM sub_themes ORDER BY sub_theme_id").fetchall()
        return [dict(r) for r in rows]


def save_annotation(prof_id, sub_theme_id, status, note):
    import datetime
    with get_conn() as c:
        c.execute("INSERT INTO annotations (prof_id, sub_theme_id, status, note, created_at)"
                  " VALUES (?,?,?,?,?)",
                  (prof_id, sub_theme_id, status, note, datetime.datetime.now().isoformat()))


def get_annotation(prof_id, sub_theme_id):
    with get_conn() as c:
        r = c.execute("SELECT * FROM annotations WHERE prof_id=? AND sub_theme_id=?"
                      " ORDER BY created_at DESC LIMIT 1", (prof_id, sub_theme_id)).fetchone()
        return dict(r) if r else None
