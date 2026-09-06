from __future__ import annotations

from html import escape
from urllib.parse import parse_qs


STYLE = "body{margin:3em auto;max-width:1000px;background:#eee;font:14px Arial;color:#222}a{color:#268bd2}.post{background:#fff;border:1px solid #ccc;margin:12px 0;padding:12px}.meta{color:#666}.tag{background:#ddd;padding:2px 5px;margin-right:4px}input{width:70%;padding:8px}"


def page(title: str, content: str) -> bytes:
    return f"<!doctype html><meta charset=utf-8><title>{escape(title)}</title><style>{STYLE}</style><h1><a href='/'>Локальный Архивач</a></h1>{content}".encode()


def application(db):
    def app(environ, start_response):
        path, query = environ["PATH_INFO"], parse_qs(environ.get("QUERY_STRING", ""))
        if path == "/":
            q = query.get("q", [""])[0].strip()
            content = "<form><input name=q value='%s' placeholder='Поиск по сообщениям'><button>Искать</button></form>" % escape(q)
            if q:
                try:
                    rows = db.execute("SELECT t.id,t.title,t.tags, snippet(posts_fts,0,'<mark>','</mark>','…',16) excerpt FROM posts_fts JOIN posts p ON p.id=posts_fts.rowid JOIN threads t ON t.id=p.thread_id WHERE posts_fts MATCH ? GROUP BY t.id ORDER BY rank LIMIT 100", (q,)).fetchall()
                    content += "<h2>Результаты</h2>" + "".join(f"<div class=post><a href='/thread/{r['id']}'><b>{escape(r['title'])}</b></a><p>{r['excerpt']}</p><small>{escape(r['tags'])}</small></div>" for r in rows)
                except Exception as error:
                    content += f"<p>Некорректный FTS-запрос: {escape(str(error))}</p>"
            body = page("Локальный Архивач", content)
        elif path.startswith("/thread/") and path[8:].isdigit():
            ident = int(path[8:]); thread = db.execute("SELECT * FROM threads WHERE id=?", (ident,)).fetchone()
            if not thread:
                start_response("404 Not Found", [("Content-Type", "text/plain; charset=utf-8")]); return [b"Not found"]
            posts = db.execute("SELECT p.*, group_concat(m.local_path) media_paths FROM posts p LEFT JOIN media m ON m.post_id=p.id WHERE p.thread_id=? GROUP BY p.id ORDER BY p.number", (ident,)).fetchall()
            tags = "".join(f"<span class=tag>{escape(tag)}</span>" for tag in thread["tags"].split(", ") if tag)
            content = f"<h2>{escape(thread['title'])}</h2><p>{tags}</p>" + "".join(f"<article class=post><div class=meta>#{p['number'] or '?'} {escape(p['author'] or '')} {escape(p['posted_at'] or '')}</div><b>{escape(p['subject'] or '')}</b><div>{p['body_html']}</div></article>" for p in posts)
            body = page(thread["title"], content)
        else:
            start_response("404 Not Found", [("Content-Type", "text/plain; charset=utf-8")]); return [b"Not found"]
        start_response("200 OK", [("Content-Type", "text/html; charset=utf-8"), ("Content-Length", str(len(body)))])
        return [body]
    return app
