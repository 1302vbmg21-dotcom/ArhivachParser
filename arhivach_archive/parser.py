from __future__ import annotations

import re
from dataclasses import dataclass, field
from html import unescape
from html.parser import HTMLParser
from urllib.parse import urljoin


def text(value: str) -> str:
    return " ".join(unescape(re.sub(r"<[^>]+>", " ", value)).split())


@dataclass
class ThreadLink:
    id: int
    url: str


def index_links(html: str, base_url: str) -> list[ThreadLink]:
    found = re.findall(r'href=["\']([^"\']*/thread/(\d+)/[^"\']*)', html, re.I)
    return [ThreadLink(int(ident), urljoin(base_url, url)) for url, ident in dict.fromkeys(found)]


@dataclass
class Post:
    number: int | None
    author: str
    posted_at: str
    subject: str
    body_html: str
    body_text: str
    images: list[tuple[str, str]] = field(default_factory=list)


@dataclass
class Thread:
    title: str
    tags: list[str]
    posts: list[Post]


def parse_thread(html: str, base_url: str) -> Thread:
    title_match = re.search(r"<title[^>]*>(.*?)</title>", html, re.I | re.S)
    tags = [text(x) for x in re.findall(r'<span class=["\']taglabel["\']>(.*?)</span>', html, re.I | re.S)]
    chunks = re.split(r'(?=<div class=["\']post["\'][^>]*>)', html, flags=re.I)
    posts = []
    for chunk in chunks[1:]:
        head = re.search(r'<div class=["\']post_head["\']>(.*?)</div>', chunk, re.I | re.S)
        body = re.search(r'<div class=["\']post_comment_body["\']>(.*?)</div>', chunk, re.I | re.S)
        if not body:
            continue
        h = head.group(1) if head else ""
        def klass(name: str) -> str:
            match = re.search(rf'<[^>]*class=["\'][^"\']*{name}[^"\']*["\'][^>]*>(.*?)</', h, re.I | re.S)
            return text(match.group(1)) if match else ""
        number_match = re.search(r'class=["\']post_num["\'][^>]*>#(\d+)', h, re.I)
        images = [(urljoin(base_url, u), "thumbnail" if "/storage/t/" in u else "full") for u in re.findall(r'<img[^>]+src=["\']([^"\']+)', chunk, re.I)]
        posts.append(Post(int(number_match.group(1)) if number_match else None, klass("poster_name"), klass("post_time"), klass("post_subject"), body.group(1), text(body.group(1)), images))
    return Thread(text(title_match.group(1)) if title_match else "", tags, posts)
