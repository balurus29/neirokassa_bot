"""Рубрики, банк тем, офферы и промпты для GigaChat."""
import json
from urllib.parse import urlencode, urlsplit, urlunsplit, parse_qsl

from . import config

# Каждая рубрика: хэштег, ключ банка тем, можно ли рекламу, задание для нейросети.
RUBRICS = {
    "lifehack": dict(
        tag="#Лайфхак", bank="lifehack", ad=False,
        task=(
            "Рубрика «Лайфхак». Тема: {topic}.\n"
            "Структура: цепляющий заголовок; одна фраза — какую боль решает приём; "
            "сам приём по шагам; готовый пример запроса к нейросети в кавычках, который можно скопировать; "
            "коротко — что получится на выходе. Пиши так, чтобы человек захотел сохранить пост."
        ),
    ),
    "prompt": dict(
        tag="#СекретныйПромт", bank="prompt", ad=False,
        task=(
            "Рубрика «Секретный промт». Тема: {topic}.\n"
            "Структура: заголовок; для какой ситуации промт; САМ ПРОМТ целиком в кавычках — подробный, "
            "с ролью, задачей, форматом ответа и квадратными скобками для того, что человек подставит сам; "
            "1–2 совета, как усилить результат. Промт должен быть реально рабочим и длиннее одной строки."
        ),
    ),
    "task": dict(
        tag="#СложнаяЗадача", bank="task", ad=True,
        task=(
            "Рубрика «Решаем сложную задачу». Задача: {topic}.\n"
            "Структура: заголовок; почему задача обычно отнимает много сил; решение по шагам с нейросетью, "
            "где на каждом шаге — конкретный запрос в кавычках; на чём нейросеть может ошибиться и что "
            "обязательно проверить самому."
        ),
    ),
    "earn": dict(
        tag="#КакЗаработать", bank="earn", ad=True,
        task=(
            "Рубрика «Как заработать». Направление: {topic}.\n"
            "Структура: заголовок; кому нужна эта услуга; что входит в работу и где помогают нейросети; "
            "как собрать первое портфолио из 2–3 работ; где искать первых клиентов. "
            "Не называй суммы дохода и не обещай лёгких денег — честно скажи, где нужна ручная работа."
        ),
    ),
    "bug": dict(
        tag="#БагиНейросетей", bank="bug", ad=False,
        task=(
            "Рубрика «Баги нейросетей». Тема: {topic}.\n"
            "Структура: заголовок; как баг выглядит на практике — короткий пример; простыми словами, почему "
            "так происходит; 2–3 способа обойти его с примерами запросов в кавычках."
        ),
    ),
    "top": dict(
        tag="#Топ5", bank="top", ad=True,
        task=(
            "Рубрика «Топ нейросетей». Задача: {topic}.\n"
            "Сделай подборку до 5 сервисов только из списка ниже: по каждому — для чего он лучше всего и "
            "одна подсказка, как с ним работать. Если в списке меньше 5 подходящих, пиши столько, сколько есть."
        ),
    ),
}

# день недели (0 = пн) -> (рубрика 12:40, рубрика 19:40)
SCHEDULE = {
    0: ("lifehack", "earn"),
    1: ("prompt", "bug"),
    2: ("task", "earn"),
    3: ("lifehack", "top"),
    4: ("prompt", "task"),
    5: ("bug", "poll"),
    6: ("lifehack", "digest"),
}

SYSTEM_PROMPT = (
    "Ты автор сообщества ВКонтакте «Нейрокасса» про нейросети для работы и заработка. "
    "Аудитория — взрослые: специалисты, фрилансеры, предприниматели в России. Не пиши про школьные задания. "
    "Стиль: живо, уверенно, по делу, как опытный практик делится находкой с коллегами. "
    "Никакого канцелярита, хайпа и общих слов. Каждая фраза должна нести пользу. "
    "Объём 700–1200 знаков. Короткие абзацы, 3–5 уместных эмодзи. "
    "Без markdown: ни звёздочек, ни решёток. Заголовок — первой строкой, он должен цеплять. "
    "Сервисы упоминай только из переданного списка. "
    "Не придумывай цены, проценты, статистику, даты, исследования и мнения экспертов. "
    "Не заканчивай пост общими фразами вроде «теперь твои письма будут идеальными» или «удачи!». "
    "Последней строкой задай читателю короткий вопрос по теме поста, чтобы он ответил в комментариях."
)

NEWS_PROMPT = (
    "Ниже новость (может быть на английском). Если она не про нейросети, ИИ-сервисы или их новые функции, "
    "ответь одним словом SKIP.\n"
    "Иначе напиши пост на русском для рубрики «Новинки ИИ»: первой строкой цепляющий заголовок; "
    "затем что именно появилось или изменилось; затем чем это может пригодиться в работе — только если это "
    "следует из текста. Используй только факты из новости, ничего не добавляй. "
    "Если новость о сервисе, недоступном в России, так и скажи одной фразой. "
    "Без подписей вроде «Что произошло:». Последней строкой — короткий вопрос читателям.\n\n"
    "Заголовок: {title}\nТекст: {summary}"
)

IMAGE_PROMPT = (
    "Нарисуй иллюстрацию к посту на тему: {topic}. Стиль: тёмно-синий фон, светящиеся неоново-зелёные "
    "линии и элементы, минималистичная цифровая иллюстрация, современный технологичный вид. "
    "Без текста, без букв и без цифр на изображении."
)

GUIDE_CTA = "🎁 Подборка нейросетей для работы — напиши ГАЙД в сообщения сообщества."


def load_topics() -> dict:
    return json.loads((config.DATA / "topics.json").read_text(encoding="utf-8"))


def next_topic(bank: str, state: dict) -> str:
    """Берёт темы из банка по кругу, для каждой рубрики свой счётчик."""
    topics = load_topics()[bank]
    counters = state.setdefault("topic_index", {})
    idx = counters.get(bank, 0)
    counters[bank] = idx + 1
    return topics[idx % len(topics)]


def load_catalog() -> dict:
    data = json.loads((config.DATA / "catalog.json").read_text(encoding="utf-8"))
    data.pop("_comment", None)
    return data


def catalog_text(category: str | None = None) -> str:
    catalog = load_catalog()
    groups = [catalog.get(category, [])] if category else catalog.values()
    seen, lines = set(), []
    for group in groups:
        for s in group:
            if s["name"] not in seen:
                seen.add(s["name"])
                lines.append(f"- {s['name']} ({s['by']}): {s['what']}; {s['price']}")
    return "\n".join(lines)


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
