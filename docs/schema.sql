PRAGMA journal_mode = WAL;

CREATE TABLE IF NOT EXISTS captures (
  id           INTEGER PRIMARY KEY,
  timestamp    DATETIME NOT NULL,
  app_name     TEXT NOT NULL,
  window_title TEXT,
  content      TEXT NOT NULL,
  source_type  TEXT NOT NULL CHECK (
    source_type IN ('accessibility', 'browser', 'file', 'screenshot')
  ),
  url          TEXT,
  file_path    TEXT,
  is_noise     INTEGER DEFAULT NULL CHECK (
    is_noise IS NULL OR is_noise IN (0, 1)
  ),
  is_pinned    INTEGER NOT NULL DEFAULT 0 CHECK (
    is_pinned IN (0, 1)
  ),
  embedding    BLOB
);

CREATE TABLE IF NOT EXISTS sessions (
  id          INTEGER PRIMARY KEY,
  app_name    TEXT NOT NULL,
  start_time  DATETIME NOT NULL,
  end_time    DATETIME,
  duration_s  INTEGER
);

CREATE TABLE IF NOT EXISTS search_clicks (
  id          INTEGER PRIMARY KEY,
  query       TEXT NOT NULL,
  capture_id  INTEGER NOT NULL,
  rank        INTEGER,
  dwell_ms    INTEGER,
  clicked_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY(capture_id) REFERENCES captures(id)
);

CREATE TABLE IF NOT EXISTS todos (
  id          INTEGER PRIMARY KEY,
  title       TEXT NOT NULL,
  notes       TEXT,
  status      TEXT NOT NULL DEFAULT 'open' CHECK (
    status IN ('open', 'done')
  ),
  priority    INTEGER NOT NULL DEFAULT 2,
  due_at      DATETIME,
  source_capture_id INTEGER,
  created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY(source_capture_id) REFERENCES captures(id)
);

CREATE TABLE IF NOT EXISTS beliefs (
  id                INTEGER PRIMARY KEY AUTOINCREMENT,
  topic             TEXT NOT NULL,
  belief_type       TEXT NOT NULL CHECK (
    belief_type IN ('interest', 'knowledge', 'gap', 'pattern', 'project')
  ),
  summary           TEXT NOT NULL,
  confidence        REAL NOT NULL DEFAULT 0.5 CHECK (
    confidence BETWEEN 0 AND 1
  ),
  depth             TEXT CHECK (
    depth IN ('surface', 'familiar', 'intermediate', 'deep')
  ),
  evidence          TEXT,
  first_seen        DATETIME DEFAULT CURRENT_TIMESTAMP,
  last_updated      DATETIME DEFAULT CURRENT_TIMESTAMP,
  times_reinforced  INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS user_model (
  id              INTEGER PRIMARY KEY AUTOINCREMENT,
  generated_at    DATETIME DEFAULT CURRENT_TIMESTAMP,
  summary         TEXT NOT NULL,
  top_interests   TEXT NOT NULL,
  active_projects TEXT,
  work_rhythm     TEXT,
  knowledge_gaps  TEXT,
  raw_json        TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS abstraction_runs (
  id              INTEGER PRIMARY KEY AUTOINCREMENT,
  started_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
  finished_at     DATETIME,
  captures_read   INTEGER DEFAULT 0,
  beliefs_written INTEGER DEFAULT 0,
  beliefs_updated INTEGER DEFAULT 0,
  status          TEXT DEFAULT 'running' CHECK (
    status IN ('running', 'complete', 'failed')
  ),
  error           TEXT
);

CREATE TABLE IF NOT EXISTS organizations (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  name        TEXT NOT NULL,
  slug        TEXT NOT NULL UNIQUE,
  created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS users (
  id               INTEGER PRIMARY KEY AUTOINCREMENT,
  organization_id  INTEGER NOT NULL,
  email            TEXT NOT NULL,
  name             TEXT NOT NULL,
  role             TEXT NOT NULL DEFAULT 'member' CHECK (
    role IN ('org_admin', 'manager', 'member', 'auditor')
  ),
  created_at       DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(organization_id, email),
  FOREIGN KEY(organization_id) REFERENCES organizations(id)
);

CREATE TABLE IF NOT EXISTS devices (
  id               INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id          INTEGER NOT NULL,
  device_name      TEXT NOT NULL,
  trust_state      TEXT NOT NULL DEFAULT 'trusted' CHECK (
    trust_state IN ('trusted', 'pending', 'revoked')
  ),
  registered_at    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  last_seen_at     DATETIME,
  FOREIGN KEY(user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS teams (
  id               INTEGER PRIMARY KEY AUTOINCREMENT,
  organization_id  INTEGER NOT NULL,
  name             TEXT NOT NULL,
  description      TEXT,
  created_at       DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY(organization_id) REFERENCES organizations(id)
);

CREATE TABLE IF NOT EXISTS team_memberships (
  id       INTEGER PRIMARY KEY AUTOINCREMENT,
  team_id  INTEGER NOT NULL,
  user_id  INTEGER NOT NULL,
  role     TEXT NOT NULL DEFAULT 'member',
  UNIQUE(team_id, user_id),
  FOREIGN KEY(team_id) REFERENCES teams(id),
  FOREIGN KEY(user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS projects (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  team_id     INTEGER NOT NULL,
  name        TEXT NOT NULL,
  description TEXT,
  status      TEXT NOT NULL DEFAULT 'active',
  created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY(team_id) REFERENCES teams(id)
);

CREATE TABLE IF NOT EXISTS project_memberships (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  project_id  INTEGER NOT NULL,
  user_id     INTEGER NOT NULL,
  role        TEXT NOT NULL DEFAULT 'member',
  UNIQUE(project_id, user_id),
  FOREIGN KEY(project_id) REFERENCES projects(id),
  FOREIGN KEY(user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS enterprise_policies (
  id                      INTEGER PRIMARY KEY AUTOINCREMENT,
  organization_id         INTEGER NOT NULL UNIQUE,
  name                    TEXT NOT NULL,
  capture_sources         TEXT NOT NULL,
  blocked_apps            TEXT NOT NULL,
  blocked_domains         TEXT NOT NULL,
  excluded_path_fragments TEXT NOT NULL,
  redaction_terms         TEXT NOT NULL,
  retention_days          INTEGER NOT NULL DEFAULT 90,
  sync_enabled            INTEGER NOT NULL DEFAULT 1 CHECK (
    sync_enabled IN (0, 1)
  ),
  updated_at              DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY(organization_id) REFERENCES organizations(id)
);

CREATE TABLE IF NOT EXISTS memory_shares (
  id                  INTEGER PRIMARY KEY AUTOINCREMENT,
  capture_id          INTEGER NOT NULL,
  organization_id     INTEGER NOT NULL,
  team_id             INTEGER,
  project_id          INTEGER,
  shared_by_user_id   INTEGER,
  share_state         TEXT NOT NULL DEFAULT 'shared' CHECK (
    share_state IN ('shared', 'revoked')
  ),
  summary             TEXT NOT NULL,
  created_at          DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY(capture_id) REFERENCES captures(id),
  FOREIGN KEY(organization_id) REFERENCES organizations(id),
  FOREIGN KEY(team_id) REFERENCES teams(id),
  FOREIGN KEY(project_id) REFERENCES projects(id),
  FOREIGN KEY(shared_by_user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS agent_access_grants (
  id               INTEGER PRIMARY KEY AUTOINCREMENT,
  agent_name       TEXT NOT NULL,
  user_id          INTEGER,
  team_id          INTEGER,
  project_id       INTEGER,
  scope            TEXT NOT NULL DEFAULT 'project',
  can_read_private INTEGER NOT NULL DEFAULT 0 CHECK (
    can_read_private IN (0, 1)
  ),
  can_read_shared  INTEGER NOT NULL DEFAULT 1 CHECK (
    can_read_shared IN (0, 1)
  ),
  created_at       DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY(user_id) REFERENCES users(id),
  FOREIGN KEY(team_id) REFERENCES teams(id),
  FOREIGN KEY(project_id) REFERENCES projects(id)
);

CREATE TABLE IF NOT EXISTS audit_events (
  id             INTEGER PRIMARY KEY AUTOINCREMENT,
  actor_user_id  INTEGER,
  action         TEXT NOT NULL,
  resource_type  TEXT NOT NULL,
  resource_id    TEXT,
  details        TEXT,
  created_at     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY(actor_user_id) REFERENCES users(id)
);

CREATE INDEX IF NOT EXISTS idx_captures_timestamp ON captures(timestamp);
CREATE INDEX IF NOT EXISTS idx_captures_app ON captures(app_name);
CREATE INDEX IF NOT EXISTS idx_captures_source_type ON captures(source_type);
CREATE INDEX IF NOT EXISTS idx_captures_noise ON captures(is_noise);
CREATE INDEX IF NOT EXISTS idx_captures_pinned ON captures(is_pinned);
CREATE INDEX IF NOT EXISTS idx_sessions_app ON sessions(app_name);
CREATE INDEX IF NOT EXISTS idx_search_clicks_capture ON search_clicks(capture_id);
CREATE INDEX IF NOT EXISTS idx_todos_status ON todos(status);
CREATE INDEX IF NOT EXISTS idx_beliefs_topic ON beliefs(topic);
CREATE INDEX IF NOT EXISTS idx_beliefs_type ON beliefs(belief_type);
CREATE INDEX IF NOT EXISTS idx_beliefs_confidence ON beliefs(confidence DESC);
CREATE INDEX IF NOT EXISTS idx_users_org ON users(organization_id);
CREATE INDEX IF NOT EXISTS idx_teams_org ON teams(organization_id);
CREATE INDEX IF NOT EXISTS idx_projects_team ON projects(team_id);
CREATE INDEX IF NOT EXISTS idx_memory_shares_capture ON memory_shares(capture_id);
CREATE INDEX IF NOT EXISTS idx_memory_shares_team ON memory_shares(team_id);
CREATE INDEX IF NOT EXISTS idx_memory_shares_project ON memory_shares(project_id);
CREATE INDEX IF NOT EXISTS idx_audit_events_created ON audit_events(created_at DESC);
