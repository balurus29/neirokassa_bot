"""Автопостинг.

08:40 — «Новинки ИИ» из новостных лент (с превью ссылки на источник).
12:40 и 19:40 — рубрики по расписанию content.SCHEDULE (с картинкой от GigaChat).
"""
import json
from datetime import datetime, timedelta, timezone

import requests

from . import config, content, gigachat, news, vk

MSK = timezone(timedelta(hours=3))


def load_state() -> dict:
    state = json.loads(config.STATE_FILE.read_text(encoding="utf-8"))
    state.setdefault("posted_links", [])
    state.setdefault("week_news", [])
    state.setdefault("recent_topics", [])
    state.setdefault("topic_index", {})
    state.setdefault("offer_index", 0)
    return state


def save_state(state: dict) -> None:
    state["posted_links"] = state["posted_links"][-400:]
    state["recent_topics"] = state["recent_topics"][-30:]
    config.STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def tidy(text: str) -> str:
    """Убирает markdown, пробелы в концах строк и лишние пустые строки."""
    lines = [line.rstrip() for line in content.strip_markdown(text).splitlines()]
    out = []
    for line in lines:
        if line or (out and out[-1]):
            out.append(line)
    return "\n".join(out).strip()


# ---------- картинки ----------

def pixabay_image(query: str) -> bytes | None:
    if not config.PIXABAY_KEY:
        return None
    try:
        resp = requests.get("https://pixabay.com/api/", params={
            "key": config.PIXABAY_KEY, "q": query, "image_type": "illustration",
            "orientation": "horizontal", "safesearch": "true", "per_page": 30,
        }, timeout=30).json()
        hits = resp.get("hits", [])
        if not hits:
            return None
        hit = hits[datetime.now(MSK).timetuple().tm_yday % len(hits)]
        return requests.get(hit["largeImageURL"], timeout=60).content
    except Exception as exc:
        print(f"[image] Pixabay не ответил: {exc}")
        return None


def make_image(topic: str) -> bytes | None:
    """Сначала рисует GigaChat, если не вышло — тематическая иллюстрация с Pixabay."""
    if not config.IMAGES:
        return None
    img = gigachat.draw(content.IMAGE_PROMPT.format(topic=topic))
    return img or pixabay_image("artificial intelligence technology")


def publish(text: str, image: bytes | None = None, link: str | None = None,
            extra: list[str] | None = None) -> None:
    if config.DRY_RUN:
        note = f"[картинка {len(image)} байт]" if image else ("[превью ссылки]" if link else "[без картинки]")
        print(f"----- DRY RUN {note} -----\n{text}\n-------------------")
        return
    attachments = list(extra or [])
    if image:
        try:
            attachments.append(vk.upload_wall_photo(image))
        except Exception as exc:  # без картинки пост всё равно выходит
            print(f"[image] не удалось загрузить фото: {exc}")
    if link and not image:
        attachments.append(link)  # ВК сам сделает карточку с картинкой из статьи
    post_id = vk.wall_post(text, attachments)
    print(f"Опубликован пост {post_id}")


# ---------- утро: новинки ----------

def morning(state: dict) -> None:
    items = news.fresh_items(set(state["posted_links"]))
    for item in items[:6]:
        text = gigachat.ask(
            content.SYSTEM_PROMPT,
            content.NEWS_PROMPT.format(title=item["title"], summary=item["summary"]),
            temperature=0.3,
        )
        state["posted_links"].append(item["link"])  # не возвращаемся к ней, даже если SKIP
        if text.strip().upper().startswith("SKIP"):
            print(f"[news] не по теме, пропускаю: {item['title']}")
            continue
        post = f"#НовинкиИИ\n{tidy(text)}\n\nИсточник: {item['link']}"
        publish(post, link=item["link"])
        state["week_news"].append(item["title"])
        return
    print("Подходящих новостей нет — утренний пост пропущен")


# ---------- рубрики ----------

def rubric_post(state: dict, key: str, today) -> None:
    rubric = content.RUBRICS[key]
    topic = content.next_topic(rubric["bank"], state)
    task = rubric["task"].format(topic=topic)

    offer = content.pick_offer("any", state) if rubric["ad"] else None
    if offer:
        task += (f"\nВ конце поста органично подведи к сервису «{offer['name']}»: "
                 f"{offer.get('pitch', '')}. Ссылку не пиши — её добавят отдельно.")
    text = gigachat.ask(
        content.SYSTEM_PROMPT,
        f"{task}\n\nСервисы, которые можно упоминать:\n{content.catalog_text()}",
    )
    post = f"{rubric['tag']}\n{tidy(text)}"
    if offer:
        post += "\n\n" + content.ad_block(offer, f"{today:%Y%m%d}_{key}")
    state["recent_topics"].append(topic[:80])
    publish(post, image=make_image(topic))


def poll_post(state: dict) -> None:
    question = "Для чего вы чаще всего используете нейросети?"
    options = ["Тексты и письма", "Картинки и дизайн", "Учёба и поиск информации",
               "Зарабатываю с их помощью", "Пока присматриваюсь"]
    extra = []
    if not config.DRY_RUN:
        try:
            extra = [vk.create_poll(question, options)]
        except Exception as exc:
            print(f"[poll] опрос не создан: {exc}")
    text = f"📊 Опрос недели\n\n{question}"
    if not extra:
        text += "\n\nОтветь в комментариях:\n" + "\n".join(f"— {o}" for o in options)
    text += "\n\nПо ответам решим, о чём делать следующие разборы."
    publish(text)


def digest_post(state: dict) -> None:
    titles = "\n".join(f"- {t}" for t in state["week_news"][-7:])
    if not titles:
        print("За неделю не было новостей — итоги пропущены")
        return
    text = gigachat.ask(
        content.SYSTEM_PROMPT,
        "Сделай пост «Главное в мире ИИ за неделю»: цепляющий заголовок и по одной строке на каждую "
        f"новость из списка, своими словами, без новых фактов.\n{titles}",
        temperature=0.4,
    )
    publish(f"#ИтогиНедели\n{tidy(text)}\n\n{content.GUIDE_CTA}",
            image=make_image("главные новости искусственного интеллекта за неделю"))
    state["week_news"] = []


def scheduled(state: dict, today, slot_index: int) -> None:
    key = content.SCHEDULE[today.weekday()][slot_index]
    if key == "poll":
        poll_post(state)
    elif key == "digest":
        digest_post(state)
    else:
        rubric_post(state, key, today)


def run(slot: str) -> None:
    today = datetime.now(MSK).date()
    state = load_state()
    if slot == "morning":
        morning(state)
    elif slot == "day":
        scheduled(state, today, 0)
    elif slot == "evening":
        scheduled(state, today, 1)
    else:
        raise SystemExit(f"Неизвестный слот: {slot}")
    if not config.DRY_RUN:
        save_state(state)
