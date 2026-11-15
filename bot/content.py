"""Рубрики, темы недели, партнёрские офферы и промпты для GigaChat."""
import json
from datetime import date
from urllib.parse import urlencode, urlsplit, urlunsplit, parse_qsl

from . import config

THEMES = [
    ("texts", "тексты, письма и учёба"),
    ("images", "картинки и дизайн"),
    ("video", "видео и клипы"),
    ("bots", "свой бот и автоматизация"),
]

# день недели (0 = пн) -> (название рубрики, можно ли рекламу, задача для нейросети)
RUBRICS = {
    0: ("Нейросеть недели", True,
        "Сделай обзор одного сервиса из списка: что умеет, для кого, с чего начать, ограничения."),
    1: ("Промпт дня", False,
        "Дай один готовый промпт для рабочей задачи по теме недели: сам промпт в кавычках, "
        "когда он пригодится и как подправить под себя."),
    2: ("Как заработать", True,
        "Разбери одну фриланс-услугу по теме недели, которую можно делать с помощью нейросетей: "
        "кому она нужна, что входит в работу, как найти первого клиента. Не называй конкретных сумм дохода."),
    3: ("До и после", True,
        "Опиши одну рабочую задачу: как её делают вручную и как с нейросетью, по шагам. "
        "Не придумывай точных цифр экономии времени, пиши «заметно быстрее»."),
    4: ("Топ-5", True,
        "Сделай подборку до 5 сервисов из списка под одну задачу темы недели, по строке на каждый."),
    5: ("Опрос", False, None),
    6: ("Итоги недели", False, None),
}

SYSTEM_PROMPT = (
    "Ты пишешь посты для сообщества ВКонтакте «Нейрокасса» про нейросети для работы и заработка. "
    "Аудитория — обычные люди и фрилансеры в России. Пиши по-русски, просто, без канцелярита и хайпа, "
    "короткими абзацами, 2–4 уместных эмодзи. Объём 500–900 знаков. "
    "Упоминай только сервисы из переданного списка и только их свойства из списка. "
    "Не придумывай цены, цифры, проценты, даты и обещания заработка. "
    "Не используй markdown: ни звёздочек, ни решёток. Заголовок — первой строкой."
)

GUIDE_CTA = "🎁 Подборка нейросетей для работы — напиши ГАЙД в сообщения сообщества."


HASHTAGS = {
    "Нейросеть недели": "#НейросетьНедели",
    "Промпт дня": "#ПромптДня",
    "Как заработать": "#КакЗаработать",
    "До и после": "#ДоИПосле",
    "Топ-5": "#Топ5",
}

# Первая неделя (тема «тексты») начинается с понедельника 16.11.2026.
START = date(2026, 11, 16)


def week_theme(today: date) -> tuple[str, str]:
    return THEMES[((today - START).days // 7) % len(THEMES)]


def load_catalog() -> dict:
    data = json.loads((config.DATA / "catalog.json").read_text(encoding="utf-8"))
    data.pop("_comment", None)
    return data


def catalog_text(category: str) -> str:
    items = load_catalog().get(category, [])
    return "\n".join(f"- {s['name']} ({s['by']}): {s['what']}; {s['price']}" for s in items)


def load_offers() -> list[dict]:
    return json.loads((config.DATA / "offers.json").read_text(encoding="utf-8"))


def _with_params(url: str, **params) -> str:
    """Добавляет параметры в ссылку; erid всегда последним."""
    parts = urlsplit(url)
    query = [(k, v) for k, v in parse_qsl(parts.query) if k not in params]
    erid = params.pop("erid", None)
    query += [(k, v) for k, v in params.items() if v]
    if erid:
        query.append(("erid", erid))
    return urlunsplit(parts._replace(query=urlencode(query)))


def pick_offer(category: str, state: dict) -> dict | None:
    """Оффер для рекламного блока. Без erid оффер не используется никогда."""
    if not config.MONETIZATION:
        return None
    offers = [o for o in load_offers()
              if o.get("erid") and o.get("url") and o.get("advertiser")
              and o.get("category") in (category, "any")]
    if not offers:
        return None
    idx = state.get("offer_index", 0) % len(offers)
    state["offer_index"] = idx + 1
    return offers[idx]


def ad_block(offer: dict, subid: str) -> str:
    url = _with_params(offer["url"], subid=subid, erid=offer["erid"])
    lines = [f"Реклама. {offer['advertiser']}. erid: {offer['erid']}"]
    if offer.get("pitch"):
        lines.append(offer["pitch"])
    if offer.get("promo"):
        lines.append(f"Промокод: {offer['promo']}")
    lines.append(f"👉 {url}")
    return "\n".join(lines)


def strip_markdown(text: str) -> str:
    for ch in ("**", "__", "##", "#"):
        text = text.replace(ch, "")
    return text.strip()
