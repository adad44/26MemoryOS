# Web UI Guide

This guide explains every tab and setting in the MemoryOS web UI.

Default local URL:

```text
http://127.0.0.1:5173
```

If Vite chooses another port, use the URL printed by `npm run dev`.

## Home

The Home tab is the main dashboard.

- **Backend**: shows whether the local FastAPI backend is reachable.
- **Captures**: total memories currently stored in SQLite.
- **Protected**: captures that cleanup should preserve, usually clicked search results or rows marked Keep.
- **Storage**: estimated local disk usage across the database, index, and logs.
- **Search Memory**: jumps to the Search tab.
- **Recent**: jumps to the Recent tab.
- **Refresh**: reloads backend health and stats.
- **Today**: summarizes Keep, Noise, and Unlabeled capture counts.
- **System**: shows index readiness, latest capture time, disk usage, and protected capture count.

## Search

Use Search for natural-language memory retrieval.

- **Search your memory**: type a query like `that transformer paper I read last week`.
- **Index backend**: shows the active search backend, such as `tfidf` or `faiss`.
- **Reranker**: shows whether results were reranked by the heuristic or trained reranker.
- **Candidates**: number of initial candidates retrieved before the top results are returned.
- **Latency**: measured backend search time in milliseconds.
- **Open**: opens a captured URL or file through the local backend using macOS `open`.
- **Similarity**: raw retrieval similarity score.
- **Rank**: final rerank score.

When you open a result, MemoryOS logs the click and dwell time as a positive signal for future reranker training.

## Recent

Use Recent to inspect what MemoryOS is collecting.

- **App**: filters captures by app name.
- **Source**: filters by capture source:
  - `accessibility`: macOS active-window text capture.
  - `browser`: Chrome extension captures.
  - `file`: FSEvents file watcher captures.
  - `screenshot`: reserved fallback source.
- **Refresh**: reloads the latest captures.
- **Open**: opens the original URL or file when available.

Recent is the fastest way to verify whether browser, file, or native macOS capture is working.

## Label

Use Label to train MemoryOS on what is useful versus junk.

- **Unlabeled**: shows captures that still need review.
- **All captures**: shows everything.
- **Keep**: shows captures marked useful.
- **Noise**: shows captures marked not useful.
- **All apps**: filters by app.
- **All sources**: filters by source type.
- **Select**: picks individual captures for batch action.
- **Keep visible / Keep selected**: marks captures as useful.
- **Noise visible / Noise selected**: marks captures as junk.
- **Clear visible / Clear selected**: removes the current label.

Captures marked Noise are excluded from indexing. Captures marked Keep are protected by cleanup by default.

## Stats

Use Stats to inspect the current local database and index state.

- **Refresh**: reloads stats.
- **Reindex**: rebuilds the search index from non-noise captures.
- **Captures**: total captured rows.
- **Indexed**: whether a search index artifact exists.
- **Keep**: count of useful captures.
- **Storage**: estimated disk usage.
- **Apps**: capture counts by app.
- **Sources**: capture counts by source type.
- **Labels**: Keep, Noise, and Unlabeled counts.
- **Protected**: captures cleanup should preserve.
- **Database**: local SQLite path.
- **Latest**: latest capture timestamp.

Run Reindex after adding many captures, cleaning storage, or changing labels.

## Settings

Settings controls backend connection, privacy lists, storage policy, export, and deletion.

### Backend

- **URL**: backend API URL. Default is:

```text
http://127.0.0.1:8765
```

If another backend is running, set this to that port, such as:

```text
http://127.0.0.1:8766
```

- **API Key**: optional key sent as `X-MemoryOS-API-Key`.
  - Leave blank for the normal local setup.
  - Fill it only if the backend was started with `MEMORYOS_API_KEY`.
- **Check**: tests backend connectivity.

### Privacy

Privacy settings tell MemoryOS what to avoid.

- **Blocked Apps**: app names that native capture should skip.
  - Good defaults include `1Password`, `Keychain Access`, and `System Settings`.
- **Blocked Domains**: browser domains that should not be captured.
  - Good defaults include banking, payments, and other sensitive sites.
- **Excluded Paths**: file path fragments that file capture should skip.
  - Good defaults include `/.ssh/`, `/.gnupg/`, and `/.Trash/`.
- **Save**: writes the privacy file.
- **Reload**: reloads privacy settings from disk.

Privacy config is stored locally at:

```text
~/Library/Application Support/MemoryOS/privacy.json
```

### Storage

Storage settings keep the local database from growing forever.

- **Total**: total capture count.
- **Noise**: captures marked noise.
- **Protected**: captures cleanup should not delete.
- **Disk**: estimated total MemoryOS storage.
- **Database**: SQLite database size.
- **Index**: search index/model artifact size.
- **Logs**: local log size.

#### Mode

- **Light**: shorter retention for minimal disk use.
- **Balanced**: default; keeps useful data while trimming junk.
- **Deep memory**: longer retention for heavier users.
- **Archive**: long retention for users who want to keep almost everything.

#### Retention Days

How long unprotected captures are kept.

Default:

```text
30 days
```

Clicked captures and Keep-labeled captures are protected by default.

#### Noise Hours

How long noise captures are kept before cleanup deletes them.

Default:

```text
24 hours
```

#### Max DB MB

Maximum database size target before cleanup starts pruning old unprotected captures.

Default:

```text
1024 MB
```

#### Noise Apps

Apps that should be treated as low-value by default, such as:

```text
Netflix
Spotify
TV
Music
Steam
Games
```

#### Noise Domains

Domains that should be treated as low-value by default, such as:

```text
netflix.com
youtube.com
youtu.be
tiktok.com
instagram.com
spotify.com
```

#### Auto-Noise

When enabled, MemoryOS can mark obvious junk as noise automatically based on app, domain, text length, and text density.

#### Protect Clicked

When enabled, captures opened from search results are protected from cleanup.

#### Protect Keep Labels

When enabled, captures marked Keep are protected from cleanup.

#### Save Policy

Saves the current storage policy.

#### Refresh Storage

Reloads the latest disk/capture counts.

#### Clean Up

Runs storage cleanup without rebuilding the index.

Cleanup can:

- Delete old noise.
- Delete exact duplicates.
- Delete old unprotected captures.
- Rotate oversized logs.
- Remove stale index artifacts if captures were deleted.

#### Clean + Reindex

Runs cleanup and then rebuilds the index.

Use this after larger cleanup jobs.

### Data Controls

- **Export JSON**: downloads a JSON export of captures and sessions.
- **Forget hours**: number of recent hours to delete.
- **Source dropdown**: optionally limits deletion to Accessibility, Browser, File, or Screenshot captures.
- **Forget Hours**: deletes matching captures.

Use Export JSON before destructive cleanup if you want a backup.

## Recommended Routine

For normal use:

1. Leave storage mode on Balanced.
2. Use Search and open useful results.
3. Mark important captures as Keep.
4. Mark obvious junk as Noise.
5. Run Clean Up occasionally.
6. Run Clean + Reindex after large cleanup jobs.

## Local Data Paths

SQLite database:

```text
~/Library/Application Support/MemoryOS/memoryos.db
```

Privacy config:

```text
~/Library/Application Support/MemoryOS/privacy.json
```

Storage policy:

```text
~/Library/Application Support/MemoryOS/storage_policy.json
```

Backend/index artifacts:

```text
ml/models/
```

Logs:

```text
.logs/
```
