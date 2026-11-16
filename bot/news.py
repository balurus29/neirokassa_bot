"""Сбор свежих новостей из RSS без сторонних библиотек."""
import json
import re
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from datetime import datetime, timedelta, timezone

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
    dt = None
    if raw:
        try:
            dt = parsedate_to_datetime(raw)
        except (TypeError, ValueError):
            try:
                dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
            except ValueError:
                dt = None
    if dt is None:
        return datetime.min.replace(tzinfo=timezone.utc)
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


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


AI_ABBR = re.compile(r"\b(ИИ|AI|GPT|LLM|ML)\b")
AI_WORDS = ("нейросет", "нейронн", "искусственн", "машинн", "chatgpt", "gigachat", "deepseek",
            "qwen", "алиса ai", "kandinsky", "шедеврум", "генеративн", "языков", "промпт", "ии-",
            "openai", "anthropic", "gemini", "claude", "midjourney", "sora", "copilot", "mistral",
            "llama", "perplexity", "chatbot", "neural", "generative", "language model", "kling")


def is_about_ai(item: dict) -> bool:
    text = f"{item['title']} {item['summary']}"
    low = text.lower()
    return bool(AI_ABBR.search(text)) or any(w in low for w in AI_WORDS)


def clean_link(link: str) -> str:
    """Убирает из ссылки метки utm_ и прочий хвост после ?."""
    return link.split("?", 1)[0].split("#", 1)[0]


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
    for i in items:
        i["link"] = clean_link(i["link"])
    items = [i for i in items if i["link"] not in seen_links and is_about_ai(i)]
    # Не старше трёх дней: «новинки» должны быть новыми.
    fresh_after = datetime.now(timezone.utc) - timedelta(days=3)
    recent = [i for i in items if i["date"] >= fresh_after]
    items = recent or items
    items.sort(key=lambda i: i["date"], reverse=True)
    return items
