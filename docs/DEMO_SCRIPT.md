# Demo Script

Target length: 60-90 seconds.

## 1. Open

Show the menu bar app.

Say:

MemoryOS is a local-first personal knowledge engine for macOS. It captures useful work context, filters noise, and makes the history searchable.

If this is a fresh machine, setup is one command: `scripts/install_memoryos.sh`.

## 2. Capture Status

Show the menu bar status and pause/resume control.

Say:

The capture daemon runs locally and writes to SQLite. I can pause capture at any time for privacy.

## 3. Search UI

Open the web UI from the menu bar.

Search for a recent topic.

Say:

The web UI calls a local FastAPI backend. Search works immediately with a TF-IDF index, with optional sentence-transformer/FAISS support for heavier semantic search.

## 4. Recent and Labeling

Open Recent, Label, and Todo.

Say:

Recent captures help inspect what the system is collecting. The Label tab lets me mark captures as keep or noise, and Todo tracks follow-ups without leaving the local database.

## 5. You Model, Stats, and Reindex

Open You, then Stats and click Reindex.

Say:

The You tab uses local Ollama and Mistral to build a private user model from non-noise captures. Stats show capture volume, source breakdown, labels, and index status. Reindex rebuilds the local search index.

## 6. Privacy Controls

Open Settings.

Say:

Privacy controls include blocklisted apps, domains, excluded paths, storage cleanup, JSON export, and filtered forget/delete.

## 7. Agent Memory

Say:

Agents can use MemoryOS through the localhost FastAPI endpoints for search, recent captures, todos, and the local user model.

## 8. Close

Show the architecture diagram or README.

Say:

The project covers one-command install, native macOS capture, browser capture, local search, storage controls, agent memory endpoints, a local user model, a web app, and a menu bar app.
