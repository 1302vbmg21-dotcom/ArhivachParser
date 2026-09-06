from __future__ import annotations

import argparse
import logging
from pathlib import Path
from wsgiref.simple_server import make_server

from .config import load_rules
from .crawler import Crawler
from .database import connect, initialise
from .web import application


def main() -> None:
    parser = argparse.ArgumentParser(prog="arhivach-archive")
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("init", "serve", "crawl"):
        item = sub.add_parser(name); item.add_argument("--database", default="data/archive.sqlite3")
    crawl = sub.choices["crawl"]
    crawl.add_argument("--tail-page", type=int, required=True)
    crawl.add_argument("--pages", type=int, default=1); crawl.add_argument("--mode", choices=("tail", "head"), default="tail")
    crawl.add_argument("--delay", type=float, default=1); crawl.add_argument("--media-rules")
    serve = sub.choices["serve"]; serve.add_argument("--host", default="127.0.0.1"); serve.add_argument("--port", type=int, default=8080)
    args = parser.parse_args(); initialise(args.database)
    if args.command == "init": return
    if args.command == "crawl":
        logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
        Crawler(connect(args.database), Path(args.database).parent / "media", load_rules(args.media_rules), args.delay).crawl(args.tail_page, args.pages, args.mode)
    else:
        print(f"Serving http://{args.host}:{args.port}")
        make_server(args.host, args.port, application(connect(args.database))).serve_forever()
