from __future__ import annotations

import sqlite3
from pathlib import Path

SCHEMA = """
PRAGMA journal_mode=WAL;
CREATE TABLE IF NOT EXISTS threads (
  id INTEGER PRIMARY KEY, url TEXT NOT NULL UNIQUE, title TEXT NOT NULL,
  tags TEXT NOT NULL DEFAULT '', fetched_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  status TEXT NOT NULL CHECK(status IN ('discovered','fetched','failed')),
  error TEXT
);
CREATE TABLE IF NOT EXISTS posts (
  id INTEGER PRIMARY KEY, thread_id INTEGER NOT NULL REFERENCES threads(id),
  number INTEGER, author TEXT, posted_at TEXT, subject TEXT, body_html TEXT NOT NULL, body_text TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS media (
  id INTEGER PRIMARY KEY, post_id INTEGER NOT NULL REFERENCES posts(id), remote_url TEXT NOT NULL,
  local_path TEXT, kind TEXT NOT NULL CHECK(kind IN ('thumbnail','full'))
);
CREATE TABLE IF NOT EXISTS progress (name TEXT PRIMARY KEY, value INTEGER NOT NULL);
CREATE VIRTUAL TABLE IF NOT EXISTS posts_fts USING fts5(body_text, subject, author, content='posts', content_rowid='id');
CREATE TRIGGER IF NOT EXISTS posts_ai AFTER INSERT ON posts BEGIN
  INSERT INTO posts_fts(rowid, body_text, subject, author) VALUES (new.id,new.body_text,new.subject,new.author);
END;
CREATE TRIGGER IF NOT EXISTS posts_ad AFTER DELETE ON posts BEGIN
  INSERT INTO posts_fts(posts_fts, rowid, body_text, subject, author) VALUES ('delete',old.id,old.body_text,old.subject,old.author);
END;
"""


def connect(path: str) -> sqlite3.Connection:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys=ON")
    return db


def initialise(path: str) -> None:
    with connect(path) as db:
        db.executescript(SCHEMA)


def get_progress(db: sqlite3.Connection, name: str) -> int:
    row = db.execute("SELECT value FROM progress WHERE name=?", (name,)).fetchone()
    return row["value"] if row else 0


def set_progress(db: sqlite3.Connection, name: str, value: int) -> None:
    db.execute("INSERT INTO progress(name,value) VALUES (?,?) ON CONFLICT(name) DO UPDATE SET value=excluded.value", (name, value))
