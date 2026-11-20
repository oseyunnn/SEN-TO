SCHEMA = """
CREATE TABLE IF NOT EXISTS posts (
 id INTEGER PRIMARY KEY, topic TEXT NOT NULL, display_name TEXT NOT NULL,
 title TEXT NOT NULL, content TEXT NOT NULL, session_id TEXT NOT NULL,
 is_demo INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);
CREATE TABLE IF NOT EXISTS comments (
 id INTEGER PRIMARY KEY, post_id INTEGER NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
 display_name TEXT NOT NULL, content TEXT NOT NULL, session_id TEXT NOT NULL,
 created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);
CREATE TABLE IF NOT EXISTS likes (
 post_id INTEGER NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
 session_id TEXT NOT NULL, PRIMARY KEY(post_id,session_id)
);
CREATE TABLE IF NOT EXISTS reports (
 id INTEGER PRIMARY KEY, post_id INTEGER NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
 session_id TEXT NOT NULL, reason TEXT NOT NULL,
 created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
 UNIQUE(post_id,session_id)
);
CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS posts_topic ON posts(topic);
"""
