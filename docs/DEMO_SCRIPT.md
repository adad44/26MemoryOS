# Demo Script

Target length: 60-90 seconds.

## 1. Open

Show the menu bar app.

Say:

MemoryOS is a local-first personal knowledge engine for macOS. It captures useful work context, filters noise, and makes the history searchable.

## 2. Capture Status

Show the menu bar status and pause/resume control.

Say:

The capture daemon runs locally and writes to SQLite. I can pause capture at any time for privacy.

## 3. Search UI

Open the web UI from the menu bar.

Search for a recent topic.

Say:

The web UI calls a local FastAPI backend. Search uses the Phase 2 index, with a TF-IDF fallback and a sentence-transformer/FAISS path for the full ML version.

## 4. Recent and Labeling

Open Recent, then Label.

Say:

Recent captures help inspect what the system is collecting. The Label tab lets me mark captures as keep or noise, which becomes training data for the noise classifier.

## 5. Stats and Reindex

Open Stats and click Reindex.

Say:

Stats show capture volume, source breakdown, labels, and index status. Reindex rebuilds the local search index.

## 6. Privacy Controls

Open Settings.

Say:

Privacy controls include blocklisted apps, domains, excluded paths, JSON export, and filtered forget/delete.

## 7. Close

Show the architecture diagram or README.

Say:

The project covers native macOS capture, browser capture, local search, ML training hooks, a web operator console, and a menu bar app.
