"""Сбор свежих новостей из RSS без сторонних библиотек."""
import json
import re
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from datetime import datetime, timezone

import requests

from . import config

HEADERS = {"User-Agent": "Mozilla/5.0 (NeirokassaBot)"}


def _text(el, *names):
    for name in names:
        found = el.find(name)
        if found is not None:
            if found.text and found.text.strip():
                return found.text.strip()
            if found.get("href"):
                return found.get("href")
    return ""


def _date(raw: str):
    if not raw:
        return datetime.min.replace(tzinfo=timezone.utc)
    try:
        return parsedate_to_datetime(raw)
    except (TypeError, ValueError):
        pass
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return datetime.min.replace(tzinfo=timezone.utc)


def _clean(html: str) -> str:
    text = re.sub(r"<[^>]+>", " ", html or "")
    return re.sub(r"\s+", " ", text).strip()


def parse_feed(xml_text: str) -> list[dict]:
    root = ET.fromstring(xml_text)
    atom = "{http://www.w3.org/2005/Atom}"
    items = root.findall(".//item") or root.findall(f".//{atom}entry")
    result = []
    for it in items:
        title = _text(it, "title", f"{atom}title")
        link = _text(it, "link", f"{atom}link")
        summary = _text(it, "description", f"{atom}summary", f"{atom}content")
        date = _date(_text(it, "pubDate", f"{atom}published", f"{atom}updated"))
        if title and link:
            result.append({"title": _clean(title), "link": link,
                           "summary": _clean(summary)[:1500], "date": date})
    return result


def fresh_items(seen_links: set[str]) -> list[dict]:
    feeds = json.loads((config.DATA / "feeds.json").read_text(encoding="utf-8"))
    items = []
    for url in feeds:
        try:
            resp = requests.get(url, headers=HEADERS, timeout=30)
            resp.raise_for_status()
            items.extend(parse_feed(resp.text))
        except Exception as exc:  # одна сломанная лента не должна ронять бота
            print(f"[news] пропускаю {url}: {exc}")
    items = [i for i in items if i["link"] not in seen_links]
    items.sort(key=lambda i: i["date"], reverse=True)
    return items
