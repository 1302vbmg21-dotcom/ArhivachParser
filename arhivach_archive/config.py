from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class MediaRule:
    mode: str
    tags: tuple[str, ...] = ()
    keywords: tuple[str, ...] = ()

    def matches(self, tags: list[str], text: str) -> bool:
        tag_set = {tag.casefold() for tag in tags}
        content = text.casefold()
        return (not self.tags or bool(tag_set & {x.casefold() for x in self.tags})) and (
            not self.keywords or any(word.casefold() in content for word in self.keywords)
        )


def load_rules(path: str | None) -> list[MediaRule]:
    if not path:
        return [MediaRule("none")]
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    rules = [MediaRule(item["mode"], tuple(item.get("tags", ())), tuple(item.get("keywords", ()))) for item in raw]
    if not rules or any(rule.mode not in {"none", "thumbnail", "full"} for rule in rules):
        raise ValueError("media rules must contain mode: none, thumbnail, or full")
    return rules


def media_mode(rules: list[MediaRule], tags: list[str], text: str) -> str:
    return next((rule.mode for rule in rules if rule.matches(tags, text)), "none")
