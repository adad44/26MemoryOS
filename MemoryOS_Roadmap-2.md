# MemoryOS — Complete Project Roadmap

> Historical planning document. For current implemented behavior, use `README.md`, `docs/QUICKSTART.md`, and the phase docs under `docs/`.

ML-powered personal knowledge engine for macOS \+ Web  
Stack: Swift · Python · PyTorch · FAISS · FastAPI · React

---

## Overview

| Phase | Name | Est. Time | Output |
| :---- | :---- | :---- | :---- |
| 0 | Setup & Architecture | 3–5 days | Repo, schema, dev env |
| 1 | Data Capture Layer | 2–3 weeks | Mac daemon capturing structured text |
| 2 | ML Pipeline | 3–4 weeks | Trained noise classifier \+ embedding model |
| 3 | Search Backend | 1–2 weeks | FastAPI serving semantic search |
| 4 | Web Interface | 1–2 weeks | React search UI deployed on Netlify |
| 5 | Mac Menu Bar App | 1–2 weeks | SwiftUI app with settings \+ status |
| 6 | Polish & Deploy | 1 week | Packaged, documented, demo-ready |

**Total estimate: 10–14 weeks** (part-time, student pace)

---

## Phase 0 — Setup & Architecture (Days 1–5)

### Goals

Design the full system before writing a line of code. Bad architecture decisions here cost 10x later.

### 0.1 Repo Structure

memoryos/

├── daemon/          \# Swift — background capture process

├── extension/       \# Browser extension (Chrome/Safari)

├── ml/              \# Python — training \+ inference

│   ├── data/        \# Raw \+ processed data

│   ├── models/      \# Saved model weights

│   ├── train/       \# Training scripts

│   └── serve/       \# Inference code

├── backend/         \# FastAPI server

├── web/             \# React frontend

└── docs/            \# Architecture diagrams, notes

### 0.2 Database Schema (SQLite)

Design this carefully — everything is built on top of it.

\-- Every piece of content captured

CREATE TABLE captures (

  id          INTEGER PRIMARY KEY,

  timestamp   DATETIME NOT NULL,

  app\_name    TEXT NOT NULL,          \-- "VSCode", "Safari", "Notion"

  window\_title TEXT,

  content     TEXT NOT NULL,          \-- extracted text

  source\_type TEXT NOT NULL,          \-- 'accessibility', 'browser', 'file', 'screenshot'

  url         TEXT,                   \-- if from browser

  file\_path   TEXT,                   \-- if from file system

  is\_noise    INTEGER DEFAULT NULL,   \-- NULL=unlabeled, 0=keep, 1=noise

  embedding   BLOB                    \-- stored vector (after Phase 2\)

);

\-- App usage sessions

CREATE TABLE sessions (

  id          INTEGER PRIMARY KEY,

  app\_name    TEXT NOT NULL,

  start\_time  DATETIME NOT NULL,

  end\_time    DATETIME,

  duration\_s  INTEGER

);

### 0.3 Tech Stack Decisions

| Component | Choice | Why |
| :---- | :---- | :---- |
| Mac daemon | Swift | Native AX API access, low overhead |
| ML training | Python \+ PyTorch | Ecosystem, HuggingFace support |
| Embeddings | sentence-transformers | Easy fine-tuning, good base models |
| Vector search | FAISS | Free, fast, runs local |
| Backend | FastAPI | Fast, Python-native, async |
| Frontend | React \+ Vite \+ Tailwind | You've used this stack before |
| DB | SQLite | Zero config, local, sufficient for personal scale |

### 0.4 Deliverables

- [ ] GitHub repo created, README stub written  
- [ ] SQLite schema finalized  
- [ ] Architecture diagram drawn (even by hand)  
- [ ] All tools installed: Xcode, Python 3.11+, Node 18+

---

## Phase 1 — Data Capture Layer (Weeks 1–3)

This is the Mac daemon: a background Swift process that silently captures what you're doing.

### 1.1 Accessibility API Integration (Week 1\)

The **AXUIElement API** lets you read text from any accessible app without screenshots.

import Cocoa

func getCurrentWindowText() \-\> String? {

    let app \= NSWorkspace.shared.frontmostApplication

    guard let pid \= app?.processIdentifier else { return nil }

    

    let axApp \= AXUIElementCreateApplication(pid)

    var focusedWindow: CFTypeRef?

    AXUIElementCopyAttributeValue(axApp, kAXFocusedWindowAttribute as CFString, \&focusedWindow)

    

    // Walk the accessibility tree to extract all visible text

    return extractText(from: focusedWindow as\! AXUIElement)

}

**Tasks:**

- [ ] Request Accessibility permissions in app entitlements  
- [ ] Poll active window every 5–10 seconds (not too aggressive)  
- [ ] Extract app name, window title, visible text content  
- [ ] Handle apps that block AX API (flag for screenshot fallback)  
- [ ] Write captured text to SQLite `captures` table

**Edge cases to handle:**

- Password fields (never capture)  
- Apps with no AX support (Electron apps, games)  
- Duplicate captures (same window, same content — debounce)

### 1.2 NSWorkspace App Tracker (Week 1\)

Track which app is in focus and for how long.

NSWorkspace.shared.notificationCenter.addObserver(

    forName: NSWorkspace.didActivateApplicationNotification,

    object: nil, queue: .main

) { notification in

    let app \= notification.userInfo?\[NSWorkspace.applicationUserInfoKey\] as? NSRunningApplication

    logAppSession(app?.localizedName ?? "unknown")

}

**Tasks:**

- [ ] Log app activation/deactivation events  
- [ ] Write session rows to `sessions` table  
- [ ] Track idle time (don't log when screen is locked/sleeping)

### 1.3 FSEvents File Watcher (Week 2\)

Capture files you open, edit, or save — not just what's on screen.

import FSEvents

let paths \= \["/Users/\\(NSUserName())/Documents", "/Users/\\(NSUserName())/Desktop"\]

// Set up FSEventStream watching these directories

// On event: log file\_path, modification time, extension

**Tasks:**

- [ ] Watch Documents, Desktop, Downloads folders  
- [ ] On file open/modify: read first 2000 chars, store in captures  
- [ ] Filter by extension: `.pdf`, `.md`, `.txt`, `.py`, `.js`, `.swift`  
- [ ] Skip binary files, system files, hidden files

### 1.4 Browser Extension (Week 2\)

Capture page title, URL, and visible text as you browse.

// content.js — runs on every page

chrome.runtime.sendMessage({

  type: 'page\_capture',

  url: window.location.href,

  title: document.title,

  content: document.body.innerText.substring(0, 3000),

  timestamp: Date.now()

});

**Tasks:**

- [ ] Build Chrome extension (manifest v3)  
- [ ] Send page data to local FastAPI endpoint on page visit  
- [ ] Only capture after 10+ seconds on page (not just passing through)  
- [ ] Respect private/incognito mode (don't capture)

### 1.5 Screenshot Fallback (Week 3\)

Only for apps that block everything else.

// Use ScreenCaptureKit (macOS 12.3+)

import ScreenCaptureKit

// Capture specific window, not full screen

// Pass to Tesseract for OCR

**Tasks:**

- [ ] Detect which apps have no AX API output  
- [ ] Capture those windows only (not full screen)  
- [ ] Run Tesseract OCR via Python subprocess  
- [ ] Store extracted text same as accessibility captures

### 1.6 Phase 1 Deliverable

A running Swift daemon that silently collects data into SQLite. After one week of use you should have thousands of rows — enough to label data for Phase 2\.

**Validation:**

sqlite3 memoryos.db "SELECT app\_name, COUNT(\*) FROM captures GROUP BY app\_name ORDER BY 2 DESC LIMIT 20;"

---

## Phase 2 — ML Pipeline (Weeks 4–7)

This is the core ML work. Three models, trained on your own captured data.

### 2.1 Noise Classifier (Week 4\)

**Problem:** Most screen captures are junk — menu bars, notifications, loading screens, YouTube. You need a classifier that says "keep this" vs "discard this."

**Data labeling:**

\# Label 500–1000 captures manually

\# 0 \= useful (article, code, document, email)

\# 1 \= noise (menu, notification, video player, settings)

import sqlite3, pandas as pd

conn \= sqlite3.connect('memoryos.db')

df \= pd.read\_sql("SELECT id, app\_name, window\_title, content FROM captures", conn)

\# Interactive labeling loop

for \_, row in df.sample(500).iterrows():

    print(f"App: {row\['app\_name'\]}")

    print(f"Content: {row\['content'\]\[:200\]}")

    label \= input("0=keep, 1=noise: ")

    \# store label...

**Model:**

from sklearn.pipeline import Pipeline

from sklearn.feature\_extraction.text import TfidfVectorizer

from sklearn.linear\_model import LogisticRegression

\# Features: TF-IDF on content \+ app\_name one-hot \+ content\_length

pipeline \= Pipeline(\[

    ('tfidf', TfidfVectorizer(max\_features=5000)),

    ('clf', LogisticRegression())

\])

pipeline.fit(X\_train, y\_train)

\# Target: \>90% precision on "keep" class (don't throw away good content)

**Tasks:**

- [ ] Label 500–1000 rows manually (this is your training data)  
- [ ] Feature engineering: text content, app name, window title, content length, time of day  
- [ ] Train LogisticRegression baseline, then try LightGBM  
- [ ] Evaluate: prioritize precision on "keep" class — false negatives (losing good content) are worse than false positives  
- [ ] Export model as `.pkl`, load in daemon to filter captures in real-time  
- [ ] Update daemon: set `is_noise = model.predict(capture)` on every new row

### 2.2 Embedding Model Fine-tuning (Weeks 5–6)

**Problem:** Generic sentence embeddings (like `all-MiniLM-L6-v2`) don't understand your personal context. "VSCode window" and "Python file" mean different things in your workflow than in a general corpus.

**Base model:** `sentence-transformers/all-MiniLM-L6-v2` (small, fast, good baseline)

**Fine-tuning approach — Contrastive Learning:**

You need positive pairs (semantically similar captures) and negative pairs (unrelated captures). Generate them automatically:

\# Positive pairs: same app \+ same day \+ similar window title

\# Negative pairs: different app \+ different content domain

from sentence\_transformers import SentenceTransformer, InputExample, losses

from torch.utils.data import DataLoader

\# Build training pairs from your captures

positive\_pairs \= \[\]  \# (capture\_a, capture\_b) — same context

negative\_pairs \= \[\]  \# (capture\_a, capture\_b) — different context

train\_examples \= \[

    InputExample(texts=\[a, b\], label=1.0) for a, b in positive\_pairs

\] \+ \[

    InputExample(texts=\[a, b\], label=0.0) for a, b in negative\_pairs

\]

model \= SentenceTransformer('all-MiniLM-L6-v2')

train\_loss \= losses.CosineSimilarityLoss(model)

train\_dataloader \= DataLoader(train\_examples, shuffle=True, batch\_size=16)

model.fit(

    train\_objectives=\[(train\_dataloader, train\_loss)\],

    epochs=3,

    warmup\_steps=100,

    output\_path='models/memoryos-embedder'

)

**Tasks:**

- [ ] Generate 2000+ training pairs from your captured data  
- [ ] Fine-tune on your personal corpus  
- [ ] Evaluate: does "Python debugging session" now score closer to "traceback error fix" than to "cooking recipe"?  
- [ ] Export model for inference

### 2.3 FAISS Vector Index (Week 6\)

import faiss

import numpy as np

from sentence\_transformers import SentenceTransformer

model \= SentenceTransformer('models/memoryos-embedder')

\# Load all non-noise captures

captures \= load\_captures\_from\_db()  \# list of (id, content, metadata)

texts \= \[c\['content'\] for c in captures\]

\# Encode

embeddings \= model.encode(texts, batch\_size=32, show\_progress\_bar=True)

embeddings \= np.array(embeddings).astype('float32')

\# Build index

d \= embeddings.shape\[1\]  \# embedding dimension

index \= faiss.IndexFlatIP(d)  \# Inner product \= cosine similarity (if normalized)

faiss.normalize\_L2(embeddings)

index.add(embeddings)

\# Save

faiss.write\_index(index, 'models/memoryos.faiss')

**Tasks:**

- [ ] Encode all non-noise captures  
- [ ] Build FAISS `IndexFlatIP` index  
- [ ] Store mapping: FAISS index position → SQLite capture ID  
- [ ] Write incremental update: add new captures to index without full rebuild  
- [ ] Benchmark: query latency should be \<50ms for 100K captures

### 2.4 Temporal Re-ranking Model (Week 7\)

**Problem:** Nearest neighbor by embedding alone ignores that you probably want *recent* content more than *old* content, and *frequently accessed* content more than *rarely seen* content.

Train a small re-ranker on top of FAISS results:

\# Features for each candidate result:

\# \- cosine\_similarity (from FAISS)

\# \- hours\_since\_capture

\# \- access\_frequency (how many times this content was captured/revisited)

\# \- app\_match (does query context match capture app?)

\# \- session\_duration (longer session \= more intentional engagement)

\# Label: did user click this result? (collect from web UI logs)

from sklearn.ensemble import GradientBoostingClassifier

reranker \= GradientBoostingClassifier(n\_estimators=100)

reranker.fit(X\_features, y\_clicked)

**Tasks:**

- [ ] Define re-ranking features (similarity \+ temporal \+ frequency)  
- [ ] Collect click data from search UI (Phase 4\) to get labels  
- [ ] Train GBM re-ranker  
- [ ] Integrate: FAISS returns top 50 → re-ranker scores → return top 10

### 2.5 Phase 2 Deliverable

- Noise classifier running in daemon, filtering captures in real-time  
- Fine-tuned embedding model saved to disk  
- FAISS index built and queryable  
- Python script that takes a query string and returns top-10 results with metadata

python search.py "that article about attention mechanisms I read last week"

\# → Returns: \[Safari, arxiv.org, "Attention Is All You Need", 3 days ago, sim=0.91\]

---

## Phase 3 — Search Backend (Weeks 8–9)

### 3.1 FastAPI Server

from fastapi import FastAPI

from pydantic import BaseModel

import faiss, sqlite3

from sentence\_transformers import SentenceTransformer

app \= FastAPI()

model \= SentenceTransformer('models/memoryos-embedder')

index \= faiss.read\_index('models/memoryos.faiss')

class SearchRequest(BaseModel):

    query: str

    top\_k: int \= 10

@app.post("/search")

async def search(req: SearchRequest):

    \# Encode query

    query\_vec \= model.encode(\[req.query\])

    faiss.normalize\_L2(query\_vec)

    

    \# FAISS search

    distances, indices \= index.search(query\_vec, 50\)

    

    \# Fetch metadata from SQLite

    results \= fetch\_captures\_by\_ids(indices\[0\])

    

    \# Re-rank

    ranked \= reranker.score\_and\_sort(results, distances\[0\])

    

    return {"results": ranked\[:req.top\_k\]}

@app.get("/stats")

async def stats():

    \# Return capture counts, index size, etc.

    ...

**Tasks:**

- [ ] `/search` endpoint — takes query, returns ranked results  
- [ ] `/stats` endpoint — dashboard data (capture count, app breakdown, index freshness)  
- [ ] `/recent` endpoint — last N captures, for browsing  
- [ ] Index refresh job — runs every 30 min, encodes new captures, updates FAISS  
- [ ] Run as local service: `uvicorn backend.main:app --host 127.0.0.1 --port 8765`

### 3.2 Security

Since this runs locally with your personal data:

- [ ] Bind only to localhost (never 0.0.0.0)  
- [ ] Add a local API key (stored in macOS Keychain, sent as header)  
- [ ] Exclude sensitive paths from capture (banking, passwords, private dirs)

---

## Phase 4 — Web Interface (Weeks 9–10)

### 4.1 Search UI (React \+ Vite \+ Tailwind)

Key screens:

**Search page:**

┌─────────────────────────────────────────────┐

│  🧠 MemoryOS                                │

│  ┌─────────────────────────────────────┐   │

│  │ Search your memory...               │   │

│  └─────────────────────────────────────┘   │

│                                             │

│  Results                                    │

│  ┌─────────────────────────────────────┐   │

│  │ 📄 Attention Is All You Need        │   │

│  │ Safari · arxiv.org · 3 days ago     │   │

│  │ "...the encoder maps an input       │   │

│  │ sequence of symbol representations" │   │

│  └─────────────────────────────────────┘   │

│  ┌─────────────────────────────────────┐   │

│  │ 🐍 train.py                         │   │

│  │ VSCode · \~/projects/ml · yesterday  │   │

│  └─────────────────────────────────────┘   │

└─────────────────────────────────────────────┘

**Tasks:**

- [ ] Search bar with debounced query (fires after 300ms of no typing)  
- [ ] Result cards: icon (by app), title, source, timestamp, text snippet  
- [ ] Click result → open original URL or file  
- [ ] Filter bar: by app, by date range, by source type  
- [ ] Stats dashboard: captures today, top apps, index size  
- [ ] Log clicks for re-ranker training data

### 4.2 Deploy on Netlify

Web UI deployed on Netlify, but it calls your local FastAPI backend:

// config.js

const API\_BASE \= process.env.VITE\_API\_URL || 'http://127.0.0.1:8765';

**Tasks:**

- [ ] Deploy React app to Netlify (free tier)  
- [ ] Configure to point to localhost backend when running locally  
- [ ] Handle "backend offline" state gracefully

---

## Phase 5 — Mac Menu Bar App (Weeks 10–11)

### 5.1 SwiftUI Menu Bar

@main

struct MemoryOSApp: App {

    var body: some Scene {

        MemoryOS menu bar item with the outline-only circuit-brain mark {

            MenuBarView()

        }

        .menuBarExtraStyle(.window)

    }

}

struct MenuBarView: View {

    var body: some View {

        VStack(alignment: .leading) {

            Text("MemoryOS").font(.headline)

            Divider()

            Button("Open Search") { openBrowser() }

            Button("Pause Capture") { toggleCapture() }

            Button("Stats") { showStats() }

            Divider()

            Button("Quit") { NSApp.terminate(nil) }

        }

        .padding()

        .frame(width: 200\)

    }

}

**Tasks:**

- [x] Menu bar icon using the outline-only MemoryOS circuit-brain mark
- [x] Show/hide: "Capturing" vs "Paused" state
- [x] Quick stats: capture count, index readiness, latest capture, and active/paused state
- [x] "Open Search" button opens the local web UI
- [x] "Pause" toggle for private moments
- [x] Launch at login through LaunchAgents

### 5.2 Daemon Packaging

- [ ] Package daemon as a macOS Launch Agent (`.plist` in `~/Library/LaunchAgents/`)  
- [ ] Auto-start on login  
- [ ] Crash recovery: launchd restarts it automatically

---

## Phase 6 — Polish & Launch (Week 12–14)

### 6.1 Performance

- [ ] Benchmark search latency: target \<100ms end-to-end  
- [ ] Measure daemon CPU/memory: should be \<2% CPU idle  
- [ ] FAISS index size at 10K, 50K, 100K captures — still fast?  
- [ ] Battery impact test: does it drain significantly?

### 6.2 Privacy Controls

- [ ] App blocklist (never capture from: 1Password, banking apps, etc.)  
- [ ] Manual "forget" button: delete captures from a time range  
- [ ] Data export: dump your entire index as JSON

### 6.3 Documentation

- [ ] README with architecture diagram, setup instructions, screenshots  
- [ ] Demo video: optional launch asset; not currently published on the Netlify landing page
- [ ] Blog post / write-up explaining the ML decisions (great for PM/AI roles)

### 6.4 Portfolio Packaging

- [ ] Repo is clean, well-commented, has proper `.gitignore`  
- [ ] `ARCHITECTURE.md` explaining every component  
- [ ] Training scripts are reproducible (requirements.txt, seed set)  
- [ ] Model cards for each trained model (what data, what metrics, what tradeoffs)

---

## Key Technical Risks & Mitigations

| Risk | Likelihood | Mitigation |
| :---- | :---- | :---- |
| AX API blocked by apps | High | Screenshot fallback, browser extension covers most gaps |
| Not enough training data for fine-tuning | Medium | Start with zero-shot embeddings, fine-tune later when you have 4+ weeks of data |
| FAISS index gets stale | Medium | Background refresh job every 30 min |
| macOS security (TCC permissions) | Medium | Request permissions gracefully on first launch, guide user through |
| Re-ranker has no click data yet | High | Ship without it first, collect data passively, train re-ranker in v2 |

---

## Milestone Checkpoints

| Week | Checkpoint | Success Criteria |
| :---- | :---- | :---- |
| 3 | Capture pipeline working | 500+ rows in SQLite after 1 week of use |
| 5 | Noise classifier done | \>90% precision, running in daemon |
| 7 | Search working in Python CLI | Top result is correct 7/10 times manually |
| 9 | Web UI live | Can search from browser, results load \<2s |
| 11 | Menu bar app done | App launches at login, pause/resume works |
| 14 | Portfolio ready | README, demo video, blog post complete |

---
