# Phase 7 — User Model (Codex Agent Instructions)

> You are implementing Phase 7 of the MemoryOS project.
> MemoryOS is a local-first personal knowledge engine for macOS and web.
> The existing repo has: SQLite captures DB, FastAPI backend, React web UI, Swift daemon, Swift menu bar app, Chrome extension, and a TF-IDF/FAISS search pipeline.
> Phase 7 adds a **local LLM-powered user model** that builds a persistent, structured understanding of the user over time.
> All processing must stay 100% local. No data leaves the machine.

---

## What You Are Building

A belief extraction system that:

1. Reads recent captures from SQLite every 6 hours
2. Sends them to a local Ollama LLM (mistral:7b)
3. Extracts structured beliefs about the user (interests, knowledge depth, working patterns, knowledge gaps)
4. Stores beliefs in SQLite
5. Exposes beliefs via FastAPI
6. Displays the user model in a new React tab

---

## Prerequisites — Verify Before Starting

Run these checks first. If any fail, fix them before writing any code.

```bash
# 1. Verify Ollama is installed
which ollama

# 2. If not installed
curl -fsSL https://ollama.com/install.sh | sh

# 3. Pull the model (requires ~4.5GB disk)
ollama pull mistral

# 4. Verify it runs
ollama run mistral "respond with only the word: ready"

# 5. Verify Ollama API is accessible
curl http://localhost:11434/api/tags

# 6. Verify existing DB exists and has captures
sqlite3 ~/Library/Application\ Support/MemoryOS/memoryos.db \
  "SELECT COUNT(*) FROM captures WHERE is_noise = 0 OR is_noise IS NULL;"
```

If the capture count is under 200, note this in your output but continue — the system should work with whatever data exists.

---

## Step 1 — Database Schema

Add three new tables to the existing SQLite database.

**File to create:** `backend/db_phase7.py`

```python
import sqlite3
import os

DB_PATH = os.path.expanduser(
    "~/Library/Application Support/MemoryOS/memoryos.db"
)

PHASE7_SCHEMA = """
CREATE TABLE IF NOT EXISTS beliefs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    topic           TEXT NOT NULL,
    belief_type     TEXT NOT NULL CHECK(belief_type IN (
                        'interest', 'knowledge', 'gap', 'pattern', 'project'
                    )),
    summary         TEXT NOT NULL,
    confidence      REAL NOT NULL DEFAULT 0.5 CHECK(confidence BETWEEN 0 AND 1),
    depth           TEXT CHECK(depth IN ('surface', 'familiar', 'intermediate', 'deep')),
    evidence        TEXT,           -- JSON array of capture IDs that support this belief
    first_seen      DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_updated    DATETIME DEFAULT CURRENT_TIMESTAMP,
    times_reinforced INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS user_model (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    generated_at    DATETIME DEFAULT CURRENT_TIMESTAMP,
    summary         TEXT NOT NULL,  -- 2-3 sentence plain english summary of the user
    top_interests   TEXT NOT NULL,  -- JSON array of top 5 interest strings
    active_projects TEXT,           -- JSON array of detected active projects
    work_rhythm     TEXT,           -- e.g. "late night coder, heavy reading in afternoon"
    knowledge_gaps  TEXT,           -- JSON array of gap strings
    raw_json        TEXT NOT NULL   -- full model JSON for debugging
);

CREATE TABLE IF NOT EXISTS abstraction_runs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    finished_at     DATETIME,
    captures_read   INTEGER DEFAULT 0,
    beliefs_written INTEGER DEFAULT 0,
    beliefs_updated INTEGER DEFAULT 0,
    status          TEXT DEFAULT 'running' CHECK(status IN ('running', 'complete', 'failed')),
    error           TEXT
);

CREATE INDEX IF NOT EXISTS idx_beliefs_topic ON beliefs(topic);
CREATE INDEX IF NOT EXISTS idx_beliefs_type ON beliefs(belief_type);
CREATE INDEX IF NOT EXISTS idx_beliefs_confidence ON beliefs(confidence DESC);
"""

def run_migrations():
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(PHASE7_SCHEMA)
    conn.commit()
    conn.close()
    print(f"Phase 7 schema applied to {DB_PATH}")

if __name__ == "__main__":
    run_migrations()
```

Run it immediately to verify:

```bash
cd backend
python db_phase7.py
sqlite3 ~/Library/Application\ Support/MemoryOS/memoryos.db ".tables"
# beliefs, user_model, abstraction_runs should appear
```

---

## Step 2 — Ollama Client

**File to create:** `backend/ollama_client.py`

```python
import requests
import json
import time
from typing import Optional

OLLAMA_BASE = "http://localhost:11434"
MODEL = "mistral"
TIMEOUT = 120  # seconds — local LLM can be slow on first call


def is_ollama_running() -> bool:
    try:
        r = requests.get(f"{OLLAMA_BASE}/api/tags", timeout=5)
        return r.status_code == 200
    except Exception:
        return False


def generate(prompt: str, system: str = "", temperature: float = 0.2) -> Optional[str]:
    """
    Send a prompt to local Ollama mistral model.
    Returns the response text or None on failure.
    temperature=0.2 keeps outputs consistent for JSON extraction.
    """
    if not is_ollama_running():
        raise RuntimeError(
            "Ollama is not running. Start it with: ollama serve"
        )

    payload = {
        "model": MODEL,
        "prompt": prompt,
        "system": system,
        "stream": False,
        "options": {
            "temperature": temperature,
            "num_predict": 2048,
        }
    }

    try:
        r = requests.post(
            f"{OLLAMA_BASE}/api/generate",
            json=payload,
            timeout=TIMEOUT
        )
        r.raise_for_status()
        return r.json().get("response", "").strip()
    except requests.exceptions.Timeout:
        raise RuntimeError(f"Ollama timed out after {TIMEOUT}s")
    except Exception as e:
        raise RuntimeError(f"Ollama request failed: {e}")


def extract_json(response: str) -> Optional[dict]:
    """
    Parse JSON from LLM response.
    Handles cases where the model wraps JSON in markdown code blocks.
    """
    text = response.strip()

    # Strip markdown code fences if present
    if text.startswith("```"):
        lines = text.split("\n")
        # Remove first and last fence lines
        text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Try to find JSON object within the text
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            try:
                return json.loads(text[start:end])
            except json.JSONDecodeError:
                return None
    return None
```

Test it:

```bash
python -c "
from ollama_client import generate, extract_json
resp = generate('Return this JSON exactly: {\"status\": \"ok\"}', system='You return only valid JSON.')
print('Response:', resp)
print('Parsed:', extract_json(resp))
"
```

---

## Step 3 — Belief Extraction Prompts

**File to create:** `backend/prompts.py`

These prompts are critical. Keep them exactly as written — they are tuned for mistral's JSON output behavior.

```python
BELIEF_EXTRACTION_SYSTEM = """You are a belief extraction system for a personal knowledge engine.
You analyze a person's recent computer activity (text they read, code they wrote, documents they opened) and extract structured beliefs about them.

RULES:
- Return ONLY valid JSON. No explanation, no preamble, no markdown.
- Be conservative with confidence scores. Default to 0.5 unless evidence is strong.
- Only extract beliefs that are clearly supported by the captures.
- Do not invent or infer beyond what the data shows.
- Keep all strings concise — under 100 characters each.
- belief_type must be exactly one of: interest, knowledge, gap, pattern, project"""


def build_extraction_prompt(captures: list[dict], existing_beliefs: list[dict]) -> str:
    captures_text = "\n---\n".join([
        f"App: {c['app_name']}\nWindow: {c.get('window_title', '')}\nContent: {c['content'][:400]}"
        for c in captures[:40]  # cap at 40 captures per run to stay within context
    ])

    existing_text = json.dumps(existing_beliefs[:20], indent=2) if existing_beliefs else "[]"

    return f"""Analyze these recent computer activity captures and extract or update beliefs about the user.

RECENT CAPTURES (last 6 hours):
{captures_text}

EXISTING BELIEFS (for context — update confidence if reinforced, do not duplicate):
{existing_text}

Return a JSON object with this exact structure:
{{
  "new_beliefs": [
    {{
      "topic": "string — the subject (e.g. FAISS vector indexing)",
      "belief_type": "interest|knowledge|gap|pattern|project",
      "summary": "string — one sentence describing the belief",
      "confidence": 0.0-1.0,
      "depth": "surface|familiar|intermediate|deep",
      "evidence_summary": "string — what in the captures supports this"
    }}
  ],
  "reinforced_topics": [
    "topic string that already exists in beliefs and was seen again"
  ],
  "gaps_detected": [
    "topic the user keeps searching but shows no deep engagement with"
  ]
}}"""


import json


USER_MODEL_SYSTEM = """You are summarizing a person's user model for display in a personal dashboard.
Return ONLY valid JSON. Be concise and honest. Do not flatter."""


def build_user_model_prompt(beliefs: list[dict]) -> str:
    beliefs_text = json.dumps(beliefs, indent=2)

    return f"""Given these structured beliefs about a user, generate a user model summary.

BELIEFS:
{beliefs_text}

Return a JSON object with this exact structure:
{{
  "summary": "2-3 sentence plain English description of who this person is based on their computer activity",
  "top_interests": ["interest1", "interest2", "interest3", "interest4", "interest5"],
  "active_projects": ["project or focus area currently active"],
  "work_rhythm": "one sentence describing when and how they work",
  "knowledge_gaps": ["topic they engage with superficially but haven't internalized"]
}}"""
```

---

## Step 4 — Abstraction Engine

This is the core background job that reads captures, calls Ollama, and writes beliefs.

**File to create:** `backend/abstraction_engine.py`

```python
import sqlite3
import json
import os
import logging
from datetime import datetime, timedelta
from ollama_client import generate, extract_json
from prompts import (
    BELIEF_EXTRACTION_SYSTEM,
    USER_MODEL_SYSTEM,
    build_extraction_prompt,
    build_user_model_prompt
)

DB_PATH = os.path.expanduser(
    "~/Library/Application Support/MemoryOS/memoryos.db"
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("abstraction_engine")


def get_recent_captures(conn: sqlite3.Connection, hours: int = 6) -> list[dict]:
    """Fetch non-noise captures from the last N hours."""
    since = (datetime.now() - timedelta(hours=hours)).isoformat()
    cursor = conn.execute("""
        SELECT id, app_name, window_title, content, timestamp, source_type
        FROM captures
        WHERE (is_noise = 0 OR is_noise IS NULL)
          AND timestamp >= ?
          AND length(content) > 50
        ORDER BY timestamp DESC
        LIMIT 60
    """, (since,))
    cols = [d[0] for d in cursor.description]
    return [dict(zip(cols, row)) for row in cursor.fetchall()]


def get_existing_beliefs(conn: sqlite3.Connection) -> list[dict]:
    """Fetch current beliefs ordered by confidence."""
    cursor = conn.execute("""
        SELECT topic, belief_type, summary, confidence, depth, times_reinforced
        FROM beliefs
        ORDER BY confidence DESC, times_reinforced DESC
        LIMIT 30
    """)
    cols = [d[0] for d in cursor.description]
    return [dict(zip(cols, row)) for row in cursor.fetchall()]


def write_new_belief(conn: sqlite3.Connection, belief: dict, capture_ids: list[int]):
    """Insert a new belief, skipping if topic already exists."""
    existing = conn.execute(
        "SELECT id FROM beliefs WHERE topic = ?", (belief["topic"],)
    ).fetchone()

    if existing:
        log.info(f"Belief already exists for topic: {belief['topic']} — skipping")
        return False

    # Validate required fields
    required = ["topic", "belief_type", "summary", "confidence"]
    if not all(k in belief for k in required):
        log.warning(f"Belief missing required fields: {belief}")
        return False

    # Validate belief_type
    valid_types = {"interest", "knowledge", "gap", "pattern", "project"}
    if belief.get("belief_type") not in valid_types:
        log.warning(f"Invalid belief_type: {belief.get('belief_type')}")
        return False

    # Clamp confidence
    confidence = max(0.0, min(1.0, float(belief.get("confidence", 0.5))))

    conn.execute("""
        INSERT INTO beliefs (topic, belief_type, summary, confidence, depth, evidence)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        belief["topic"][:200],
        belief["belief_type"],
        belief["summary"][:500],
        confidence,
        belief.get("depth", "surface"),
        json.dumps(capture_ids[:10])  # store up to 10 evidence capture IDs
    ))
    return True


def reinforce_belief(conn: sqlite3.Connection, topic: str):
    """Increment reinforcement count and update confidence and timestamp."""
    conn.execute("""
        UPDATE beliefs
        SET times_reinforced = times_reinforced + 1,
            confidence = MIN(confidence + 0.05, 0.95),
            last_updated = CURRENT_TIMESTAMP
        WHERE topic = ?
    """, (topic,))


def generate_user_model(conn: sqlite3.Connection):
    """Roll up all beliefs into a user model summary."""
    beliefs = get_existing_beliefs(conn)
    if not beliefs:
        log.info("No beliefs yet — skipping user model generation")
        return

    prompt = build_user_model_prompt(beliefs)
    log.info("Generating user model summary...")

    response = generate(prompt, system=USER_MODEL_SYSTEM)
    if not response:
        log.error("Empty response from Ollama for user model")
        return

    parsed = extract_json(response)
    if not parsed:
        log.error(f"Failed to parse user model JSON: {response[:200]}")
        return

    conn.execute("""
        INSERT INTO user_model (summary, top_interests, active_projects, work_rhythm, knowledge_gaps, raw_json)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        parsed.get("summary", "")[:1000],
        json.dumps(parsed.get("top_interests", [])),
        json.dumps(parsed.get("active_projects", [])),
        parsed.get("work_rhythm", "")[:500],
        json.dumps(parsed.get("knowledge_gaps", [])),
        json.dumps(parsed)
    ))
    log.info("User model updated")


def run_abstraction():
    """Main abstraction engine run. Call this every 6 hours."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    # Log the run start
    run_id = conn.execute(
        "INSERT INTO abstraction_runs (status) VALUES ('running')"
    ).lastrowid
    conn.commit()

    captures_read = 0
    beliefs_written = 0
    beliefs_updated = 0

    try:
        captures = get_recent_captures(conn)
        captures_read = len(captures)
        log.info(f"Read {captures_read} recent captures")

        if captures_read < 5:
            log.info("Too few captures for meaningful extraction — skipping")
            conn.execute("""
                UPDATE abstraction_runs
                SET status='complete', finished_at=CURRENT_TIMESTAMP, captures_read=?
                WHERE id=?
            """, (captures_read, run_id))
            conn.commit()
            conn.close()
            return

        existing_beliefs = get_existing_beliefs(conn)
        prompt = build_extraction_prompt(captures, existing_beliefs)

        log.info("Calling Ollama for belief extraction...")
        response = generate(prompt, system=BELIEF_EXTRACTION_SYSTEM)

        if not response:
            raise RuntimeError("Empty response from Ollama")

        parsed = extract_json(response)
        if not parsed:
            raise RuntimeError(f"Failed to parse JSON from response: {response[:300]}")

        capture_ids = [c["id"] for c in captures]

        # Write new beliefs
        for belief in parsed.get("new_beliefs", []):
            if write_new_belief(conn, belief, capture_ids):
                beliefs_written += 1

        # Reinforce existing beliefs
        for topic in parsed.get("reinforced_topics", []):
            reinforce_belief(conn, topic)
            beliefs_updated += 1

        # Write gap beliefs
        for gap in parsed.get("gaps_detected", []):
            gap_belief = {
                "topic": gap,
                "belief_type": "gap",
                "summary": f"User engages with '{gap}' but shows limited deep retention",
                "confidence": 0.55,
                "depth": "surface"
            }
            if write_new_belief(conn, gap_belief, capture_ids):
                beliefs_written += 1

        conn.commit()
        log.info(f"Beliefs written: {beliefs_written}, updated: {beliefs_updated}")

        # Regenerate user model every run
        generate_user_model(conn)
        conn.commit()

        conn.execute("""
            UPDATE abstraction_runs
            SET status='complete', finished_at=CURRENT_TIMESTAMP,
                captures_read=?, beliefs_written=?, beliefs_updated=?
            WHERE id=?
        """, (captures_read, beliefs_written, beliefs_updated, run_id))
        conn.commit()

    except Exception as e:
        log.error(f"Abstraction run failed: {e}")
        conn.execute("""
            UPDATE abstraction_runs
            SET status='failed', finished_at=CURRENT_TIMESTAMP, error=?
            WHERE id=?
        """, (str(e), run_id))
        conn.commit()
        raise

    finally:
        conn.close()


if __name__ == "__main__":
    run_abstraction()
```

Test it with a dry run:

```bash
cd backend
python abstraction_engine.py
# Should print: Read N captures, called Ollama, wrote beliefs
# Check results:
sqlite3 ~/Library/Application\ Support/MemoryOS/memoryos.db \
  "SELECT topic, belief_type, confidence FROM beliefs ORDER BY confidence DESC LIMIT 10;"
```

---

## Step 5 — Background Scheduler

**File to create:** `backend/scheduler.py`

```python
import schedule
import time
import logging
from abstraction_engine import run_abstraction

log = logging.getLogger("scheduler")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def safe_run():
    try:
        log.info("Starting abstraction run...")
        run_abstraction()
        log.info("Abstraction run complete")
    except Exception as e:
        log.error(f"Abstraction run failed: {e}")


if __name__ == "__main__":
    log.info("Scheduler started — running abstraction every 6 hours")

    # Run once immediately on startup
    safe_run()

    # Then every 6 hours
    schedule.every(6).hours.do(safe_run)

    while True:
        schedule.run_pending()
        time.sleep(60)
```

Add `schedule` to `backend/requirements.txt`:

```
schedule
```

Install it:

```bash
pip install schedule
```

---

## Step 6 — FastAPI Endpoints

Add these routes to the existing FastAPI backend. Find the main FastAPI app file (likely `backend/main.py` or `backend/app.py`) and add the following:

```python
import json
import sqlite3
import subprocess
import sys
from fastapi import HTTPException
from pydantic import BaseModel

# Add after existing imports — adjust DB_PATH import to match existing pattern


@app.get("/user-model")
async def get_user_model():
    """Return the most recent user model."""
    conn = sqlite3.connect(DB_PATH)
    row = conn.execute("""
        SELECT summary, top_interests, active_projects, work_rhythm, knowledge_gaps, generated_at
        FROM user_model
        ORDER BY generated_at DESC
        LIMIT 1
    """).fetchone()
    conn.close()

    if not row:
        return {"status": "no_model", "message": "Run abstraction engine first"}

    return {
        "summary": row[0],
        "top_interests": json.loads(row[1] or "[]"),
        "active_projects": json.loads(row[2] or "[]"),
        "work_rhythm": row[3],
        "knowledge_gaps": json.loads(row[4] or "[]"),
        "generated_at": row[5]
    }


@app.get("/beliefs")
async def get_beliefs(belief_type: str = None, min_confidence: float = 0.0, limit: int = 50):
    """Return beliefs, optionally filtered by type and confidence."""
    conn = sqlite3.connect(DB_PATH)

    query = """
        SELECT topic, belief_type, summary, confidence, depth, times_reinforced, last_updated
        FROM beliefs
        WHERE confidence >= ?
    """
    params = [min_confidence]

    if belief_type:
        valid = {"interest", "knowledge", "gap", "pattern", "project"}
        if belief_type not in valid:
            conn.close()
            raise HTTPException(status_code=400, detail=f"Invalid belief_type. Must be one of: {valid}")
        query += " AND belief_type = ?"
        params.append(belief_type)

    query += " ORDER BY confidence DESC, times_reinforced DESC LIMIT ?"
    params.append(limit)

    cursor = conn.execute(query, params)
    cols = [d[0] for d in cursor.description]
    rows = [dict(zip(cols, row)) for row in cursor.fetchall()]
    conn.close()

    return {"beliefs": rows, "count": len(rows)}


@app.delete("/beliefs/{topic}")
async def delete_belief(topic: str):
    """Delete a belief by topic. Allows user to correct mistakes."""
    conn = sqlite3.connect(DB_PATH)
    result = conn.execute("DELETE FROM beliefs WHERE topic = ?", (topic,))
    conn.commit()
    deleted = result.rowcount
    conn.close()

    if deleted == 0:
        raise HTTPException(status_code=404, detail="Belief not found")
    return {"deleted": topic}


@app.post("/run-abstraction")
async def trigger_abstraction():
    """Manually trigger the abstraction engine. Returns immediately — runs in background."""
    import threading
    from abstraction_engine import run_abstraction

    def run():
        try:
            run_abstraction()
        except Exception as e:
            pass  # logged inside run_abstraction

    thread = threading.Thread(target=run, daemon=True)
    thread.start()

    return {"status": "started", "message": "Abstraction engine running in background"}


@app.get("/abstraction-runs")
async def get_abstraction_runs(limit: int = 10):
    """Return recent abstraction run history."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.execute("""
        SELECT started_at, finished_at, captures_read, beliefs_written, beliefs_updated, status, error
        FROM abstraction_runs
        ORDER BY started_at DESC
        LIMIT ?
    """, (limit,))
    cols = [d[0] for d in cursor.description]
    rows = [dict(zip(cols, row)) for row in cursor.fetchall()]
    conn.close()
    return {"runs": rows}
```

Verify the endpoints are live:

```bash
# Start the backend (use existing start command for this repo)
# Then test:
curl http://127.0.0.1:8765/user-model
curl http://127.0.0.1:8765/beliefs
curl -X POST http://127.0.0.1:8765/run-abstraction
```

---

## Step 7 — React UI Tab

Add a new "You" tab to the existing React web app. Find where the existing tabs are defined (likely `web/src/App.tsx` or similar) and add this component.

**File to create:** `web/src/UserModel.tsx`

```tsx
import { useEffect, useState } from "react";

const API = import.meta.env.VITE_API_URL || "http://127.0.0.1:8765";

interface UserModelData {
  summary: string;
  top_interests: string[];
  active_projects: string[];
  work_rhythm: string;
  knowledge_gaps: string[];
  generated_at: string;
}

interface Belief {
  topic: string;
  belief_type: string;
  summary: string;
  confidence: number;
  depth: string;
  times_reinforced: number;
  last_updated: string;
}

const TYPE_COLORS: Record<string, string> = {
  interest: "#4f8ef7",
  knowledge: "#1d9e75",
  gap: "#d85a30",
  pattern: "#7f77dd",
  project: "#ba7517",
};

const DEPTH_ORDER = ["surface", "familiar", "intermediate", "deep"];

export default function UserModel() {
  const [model, setModel] = useState<UserModelData | null>(null);
  const [beliefs, setBeliefs] = useState<Belief[]>([]);
  const [filter, setFilter] = useState<string>("all");
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchData = async () => {
    try {
      const [modelRes, beliefsRes] = await Promise.all([
        fetch(`${API}/user-model`),
        fetch(`${API}/beliefs?limit=100`),
      ]);
      const modelData = await modelRes.json();
      const beliefsData = await beliefsRes.json();

      if (modelData.status !== "no_model") setModel(modelData);
      setBeliefs(beliefsData.beliefs || []);
      setError(null);
    } catch (e) {
      setError("Could not reach backend. Is it running?");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchData(); }, []);

  const triggerRun = async () => {
    setRunning(true);
    try {
      await fetch(`${API}/run-abstraction`, { method: "POST" });
      setTimeout(() => {
        fetchData();
        setRunning(false);
      }, 8000); // wait 8s then refresh
    } catch {
      setRunning(false);
    }
  };

  const deleteBelief = async (topic: string) => {
    await fetch(`${API}/beliefs/${encodeURIComponent(topic)}`, { method: "DELETE" });
    setBeliefs(prev => prev.filter(b => b.topic !== topic));
  };

  const filteredBeliefs = filter === "all"
    ? beliefs
    : beliefs.filter(b => b.belief_type === filter);

  if (loading) return <div style={{ padding: 24, color: "var(--color-text-secondary)" }}>Loading user model...</div>;
  if (error) return <div style={{ padding: 24, color: "var(--color-text-danger)" }}>{error}</div>;

  return (
    <div style={{ padding: 24, maxWidth: 800, margin: "0 auto" }}>

      {/* Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 24 }}>
        <h2 style={{ margin: 0, fontSize: 22, fontWeight: 500 }}>Your User Model</h2>
        <button
          onClick={triggerRun}
          disabled={running}
          style={{
            padding: "8px 16px",
            borderRadius: 8,
            border: "1px solid var(--color-border-secondary)",
            background: "var(--color-background-secondary)",
            color: "var(--color-text-primary)",
            cursor: running ? "default" : "pointer",
            opacity: running ? 0.5 : 1,
            fontSize: 13,
          }}
        >
          {running ? "Running..." : "Run Now"}
        </button>
      </div>

      {/* No model yet */}
      {!model && beliefs.length === 0 && (
        <div style={{
          padding: 32, textAlign: "center",
          border: "1px dashed var(--color-border-secondary)",
          borderRadius: 12, color: "var(--color-text-secondary)"
        }}>
          <p style={{ margin: "0 0 12px" }}>No user model yet.</p>
          <p style={{ margin: "0 0 16px", fontSize: 13 }}>
            Make sure Ollama is running and you have captures, then click Run Now.
          </p>
          <code style={{ fontSize: 12 }}>ollama serve</code>
        </div>
      )}

      {/* User model summary */}
      {model && (
        <div style={{
          background: "var(--color-background-secondary)",
          border: "1px solid var(--color-border-tertiary)",
          borderRadius: 12, padding: 20, marginBottom: 24
        }}>
          <p style={{ margin: "0 0 16px", lineHeight: 1.6, color: "var(--color-text-primary)" }}>
            {model.summary}
          </p>

          {model.top_interests.length > 0 && (
            <div style={{ marginBottom: 12 }}>
              <span style={{ fontSize: 12, color: "var(--color-text-tertiary)", display: "block", marginBottom: 6 }}>
                Top interests
              </span>
              <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
                {model.top_interests.map(i => (
                  <span key={i} style={{
                    padding: "3px 10px", borderRadius: 20,
                    background: "#E6F1FB", color: "#0C447C", fontSize: 12
                  }}>{i}</span>
                ))}
              </div>
            </div>
          )}

          {model.work_rhythm && (
            <p style={{ margin: "8px 0 0", fontSize: 13, color: "var(--color-text-secondary)", fontStyle: "italic" }}>
              {model.work_rhythm}
            </p>
          )}

          <p style={{ margin: "12px 0 0", fontSize: 11, color: "var(--color-text-tertiary)" }}>
            Updated {new Date(model.generated_at).toLocaleString()}
          </p>
        </div>
      )}

      {/* Beliefs */}
      {beliefs.length > 0 && (
        <>
          {/* Filter tabs */}
          <div style={{ display: "flex", gap: 8, marginBottom: 16, flexWrap: "wrap" }}>
            {["all", "interest", "knowledge", "gap", "pattern", "project"].map(t => (
              <button
                key={t}
                onClick={() => setFilter(t)}
                style={{
                  padding: "5px 12px", borderRadius: 20, fontSize: 12,
                  border: "1px solid var(--color-border-secondary)",
                  background: filter === t ? "var(--color-text-primary)" : "var(--color-background-secondary)",
                  color: filter === t ? "var(--color-background-primary)" : "var(--color-text-secondary)",
                  cursor: "pointer"
                }}
              >
                {t}
              </button>
            ))}
          </div>

          {/* Belief cards */}
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {filteredBeliefs.map(b => (
              <div key={b.topic} style={{
                background: "var(--color-background-secondary)",
                border: "1px solid var(--color-border-tertiary)",
                borderLeft: `3px solid ${TYPE_COLORS[b.belief_type] || "#888"}`,
                borderRadius: 8, padding: "12px 14px",
                display: "flex", alignItems: "flex-start", gap: 12
              }}>
                <div style={{ flex: 1 }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
                    <span style={{ fontWeight: 500, fontSize: 14, color: "var(--color-text-primary)" }}>
                      {b.topic}
                    </span>
                    <span style={{
                      fontSize: 10, padding: "1px 6px", borderRadius: 10,
                      background: "var(--color-background-tertiary)",
                      color: "var(--color-text-tertiary)"
                    }}>
                      {b.depth || "surface"}
                    </span>
                  </div>
                  <p style={{ margin: 0, fontSize: 13, color: "var(--color-text-secondary)", lineHeight: 1.5 }}>
                    {b.summary}
                  </p>
                  <div style={{ marginTop: 6, display: "flex", gap: 12, fontSize: 11, color: "var(--color-text-tertiary)" }}>
                    <span>confidence {Math.round(b.confidence * 100)}%</span>
                    <span>seen {b.times_reinforced}×</span>
                  </div>
                </div>
                <button
                  onClick={() => deleteBelief(b.topic)}
                  style={{
                    background: "none", border: "none", cursor: "pointer",
                    color: "var(--color-text-tertiary)", fontSize: 16, padding: "0 4px"
                  }}
                  title="Remove belief"
                >×</button>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
```

**Add the tab to App.tsx** — find the tab navigation and insert "You" tab that renders `<UserModel />`.

---

## Step 8 — Wire Up the Scheduler as a Launch Agent

**File to create:** `scripts/start_scheduler.sh`

```bash
#!/bin/bash
# Start the Phase 7 abstraction scheduler
# Run this alongside the backend

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/../backend"

cd "$BACKEND_DIR"
source ../.venv/bin/activate 2>/dev/null || true

echo "Starting abstraction scheduler..."
python scheduler.py
```

```bash
chmod +x scripts/start_scheduler.sh
```

---

## Step 9 — Verification Checklist

Run through each of these before marking Phase 7 complete.

```bash
# 1. Schema exists
sqlite3 ~/Library/Application\ Support/MemoryOS/memoryos.db \
  "SELECT name FROM sqlite_master WHERE type='table';" | grep -E "beliefs|user_model|abstraction_runs"

# 2. Ollama is running and responsive
curl http://localhost:11434/api/tags | python3 -m json.tool

# 3. Abstraction engine runs without error
cd backend && python abstraction_engine.py

# 4. Beliefs were written
sqlite3 ~/Library/Application\ Support/MemoryOS/memoryos.db \
  "SELECT COUNT(*) FROM beliefs;"

# 5. User model was generated
sqlite3 ~/Library/Application\ Support/MemoryOS/memoryos.db \
  "SELECT summary FROM user_model ORDER BY generated_at DESC LIMIT 1;"

# 6. FastAPI endpoints respond
curl http://127.0.0.1:8765/user-model | python3 -m json.tool
curl http://127.0.0.1:8765/beliefs | python3 -m json.tool

# 7. React UI compiles without errors
cd web && npm run build

# 8. Scheduler runs without error (ctrl+c after confirming first run)
cd backend && python scheduler.py
```

---

## Known Failure Modes — Fix These If They Occur

**Ollama times out**
Mistral 7B can take 30–60 seconds on first call (model loads into memory). Subsequent calls are faster. If it keeps timing out, switch to `llama3.2:3b`:
```python
# In ollama_client.py
MODEL = "llama3.2"
```
And pull it: `ollama pull llama3.2`

**JSON parse failures**
Mistral occasionally wraps JSON in markdown or adds preamble. The `extract_json()` function handles most cases. If you see persistent failures, add this to the system prompt in `BELIEF_EXTRACTION_SYSTEM`:
```
CRITICAL: Your entire response must be a single JSON object. Start with { and end with }. No other characters.
```

**Too few captures**
If you have under 200 captures the beliefs will be sparse. This is fine — the system improves automatically as the daemon collects more data. Do not artificially inflate captures.

**Duplicate beliefs**
The `write_new_belief` function checks for existing topics before inserting. If you see duplicates with slightly different topic strings (e.g. "FAISS" vs "FAISS indexing"), this is the LLM inconsistency — acceptable at this stage.

---

## Files Created in This Phase

```
backend/
├── db_phase7.py          # Schema migrations
├── ollama_client.py      # Local LLM interface
├── prompts.py            # Extraction prompt templates
├── abstraction_engine.py # Core belief extraction logic
├── scheduler.py          # 6-hour background job
web/
└── src/
    └── UserModel.tsx     # React UI tab
scripts/
└── start_scheduler.sh    # Scheduler startup script
```

---

## What This Phase Delivers

After Phase 7 is complete, MemoryOS can:

- Tell the user what topics they are actively learning
- Detect where they are struggling (knowledge gaps)
- Identify active projects from behavioral patterns
- Build a richer user profile over time as confidence scores accumulate
- Surface all of this in a clean UI tab

The model improves automatically — every 6 hours it reads new captures, reinforces existing beliefs, and regenerates the summary. No user action required after setup.
