from __future__ import annotations

import logging
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .config import media_mode
from .database import get_progress, set_progress
from .parser import index_links, parse_thread

LOG = logging.getLogger(__name__)
BASE = "https://arhivach.vc"


class Crawler:
    def __init__(self, db, media_root: Path, rules, delay: float = 1.0):
        self.db, self.media_root, self.rules, self.delay = db, media_root, rules
        self.delay = delay

    def fetch(self, url: str) -> bytes:
        for attempt in range(5):
            try:
                with urlopen(Request(url, headers={"User-Agent": "LocalArchiveBot/1.0 (polite archival)"}), timeout=30) as response:
                    payload = response.read()
                time.sleep(self.delay)
                return payload
            except HTTPError as error:
                if error.code not in (429, 500, 502, 503, 504) or attempt == 4:
                    raise
            except URLError:
                if attempt == 4:
                    raise
            time.sleep(min(60, 2**attempt * self.delay))
        raise RuntimeError("unreachable")

    def save_thread(self, thread_id: int, url: str) -> bool:
        existing = self.db.execute("SELECT status FROM threads WHERE id=?", (thread_id,)).fetchone()
        if existing and existing["status"] == "fetched":
            return False
        try:
            parsed = parse_thread(self.fetch(url).decode("utf-8", errors="replace"), url)
            with self.db:
                self.db.execute("INSERT INTO threads(id,url,title,tags,status,error) VALUES (?,?,?,?, 'discovered',NULL) ON CONFLICT(id) DO UPDATE SET url=excluded.url,title=excluded.title,tags=excluded.tags,status='discovered',error=NULL", (thread_id, url, parsed.title, ", ".join(parsed.tags)))
                self.db.execute("DELETE FROM posts WHERE thread_id=?", (thread_id,))
                for post in parsed.posts:
                    cursor = self.db.execute("INSERT INTO posts(thread_id,number,author,posted_at,subject,body_html,body_text) VALUES (?,?,?,?,?,?,?)", (thread_id, post.number, post.author, post.posted_at, post.subject, post.body_html, post.body_text))
                    self._save_media(cursor.lastrowid, thread_id, parsed.tags, parsed.title + " " + post.body_text, post.images)
                self.db.execute("UPDATE threads SET status='fetched', fetched_at=CURRENT_TIMESTAMP WHERE id=?", (thread_id,))
            return True
        except Exception as error:
            LOG.warning("thread %s failed: %s", thread_id, error)
            with self.db:
                self.db.execute("INSERT INTO threads(id,url,title,status,error) VALUES (?,?,?,'failed',?) ON CONFLICT(id) DO UPDATE SET status='failed',error=excluded.error", (thread_id, url, "", str(error)))
            return False

    def _save_media(self, post_id, thread_id, tags, content, images):
        wanted = media_mode(self.rules, tags, content)
        for remote_url, guessed_kind in images:
            kind = "full" if wanted == "full" and guessed_kind == "full" else "thumbnail"
            if wanted == "none" or (wanted == "thumbnail" and guessed_kind != "thumbnail"):
                continue
            name = remote_url.rsplit("/", 1)[-1].split("?", 1)[0]
            destination = self.media_root / str(thread_id) / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            if not destination.exists():
                destination.write_bytes(self.fetch(remote_url))
            self.db.execute("INSERT INTO media(post_id,remote_url,local_path,kind) VALUES (?,?,?,?)", (post_id, remote_url, str(destination), kind))

    def crawl(self, tail_page: int, pages: int, mode: str) -> None:
        done = get_progress(self.db, "pages_done_from_tail") if mode == "tail" else 0
        for offset in range(done, done + pages):
            page = tail_page - offset if mode == "tail" else offset
            links = index_links(self.fetch(f"{BASE}/index/{page}/"), BASE)
            fresh = sum(self.save_thread(link.id, link.url) for link in links)
            with self.db:
                if mode == "tail":
                    set_progress(self.db, "pages_done_from_tail", offset + 1)
            LOG.info("page %s: %s links, %s fetched", page, len(links), fresh)
            if mode == "head" and links and fresh == 0:
                return
