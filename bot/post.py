"""Автопостинг: утро — новость, день — польза, вечер — рубрика дня."""
import json
from datetime import datetime, timedelta, timezone

import requests

from . import config, content, gigachat, news, vk

MSK = timezone(timedelta(hours=3))

IMAGE_QUERIES = {
    "texts": "laptop writing",
    "images": "digital art design",
    "video": "video editing",
    "bots": "robot technology",
    "news": "artificial intelligence",
}


def load_state() -> dict:
    return json.loads(config.STATE_FILE.read_text(encoding="utf-8"))


def save_state(state: dict) -> None:
    state["posted_links"] = state["posted_links"][-300:]
    state["recent_topics"] = state["recent_topics"][-30:]
    config.STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def pixabay_image(query: str) -> bytes | None:
    if not config.PIXABAY_KEY:
        return None
    try:
        resp = requests.get("https://pixabay.com/api/", params={
            "key": config.PIXABAY_KEY, "q": query, "image_type": "photo",
            "orientation": "horizontal", "safesearch": "true", "per_page": 30,
        }, timeout=30).json()
        hits = resp.get("hits", [])
        if not hits:
            return None
        hit = hits[datetime.now(MSK).timetuple().tm_yday % len(hits)]
        return requests.get(hit["largeImageURL"], timeout=60).content
    except Exception as exc:
        print(f"[image] без картинки: {exc}")
        return None


def tidy(text: str) -> str:
    """Убирает markdown, пробелы в концах строк и лишние пустые строки."""
    lines = [line.rstrip() for line in content.strip_markdown(text).splitlines()]
    out = []
    for line in lines:
        if line or (out and out[-1]):
            out.append(line)
    return "\n".join(out).strip()


def publish(text: str, image_query: str | None = None, extra: list[str] | None = None) -> None:
    if config.DRY_RUN:
        print("----- DRY RUN -----\n" + text + "\n-------------------")
        return
    attachments = list(extra or [])
    # Загрузка фото на стену работает только с ключом пользователя.
    if image_query and config.VK_USER_TOKEN:
        img = pixabay_image(image_query)
        if img:
            attachments.append(vk.upload_wall_photo(img))
    post_id = vk.wall_post(text, attachments)
    print(f"Опубликован пост {post_id}")


def morning(state: dict) -> None:
    items = news.fresh_items(set(state["posted_links"]))
    for item in items[:5]:
        text = gigachat.ask(
            content.SYSTEM_PROMPT,
            "Ниже новость. Если она не про нейросети или искусственный интеллект, ответь одним словом SKIP.\n"
            "Иначе напиши пост: первой строкой короткий заголовок, затем 2–3 коротких абзаца — "
            "что произошло и кому это может пригодиться. "
            "Используй только факты из текста ниже. Не делай выводов шире, чем в тексте, "
            "не обещай выгод, которых там нет. Без подписей вроде «Что произошло:».\n\n"
            f"Заголовок: {item['title']}\nТекст: {item['summary']}",
            temperature=0.3,
        )
        state["posted_links"].append(item["link"])  # не возвращаемся к ней, даже если SKIP
        if text.strip().upper().startswith("SKIP"):
            print(f"[news] не по теме, пропускаю: {item['title']}")
            continue
        post = f"{tidy(text)}\n\nИсточник: {item['link']}"
        publish(post, IMAGE_QUERIES["news"])
        state["week_news"].append(item["title"])
        return
    print("Подходящих новостей нет — утренний пост пропущен")


def day(state: dict, today) -> None:
    key, label = content.week_theme(today)
    recent = "; ".join(state["recent_topics"][-15:]) or "нет"
    text = gigachat.ask(
        content.SYSTEM_PROMPT,
        f"Тема недели: {label}. Напиши практичный совет: одну конкретную рабочую задачу "
        f"и как решить её нейросетью по шагам. Не повторяй темы: {recent}.\n"
        f"Сервисы, которые можно упоминать:\n{content.catalog_text(key)}",
    )
    text = tidy(text)
    state["recent_topics"].append(text.splitlines()[0][:80])
    publish(text, IMAGE_QUERIES[key])


def evening(state: dict, today) -> None:
    key, label = content.week_theme(today)
    name, ad_allowed, task = content.RUBRICS[today.weekday()]

    if name == "Опрос":
        question = "Чем вы пользуетесь для задач по теме «" + label + "»?"
        options = [s["name"] for s in content.load_catalog().get(key, [])][:4] + ["Пока ничем"]
        extra = [vk.create_poll(question, options)] if (config.VK_USER_TOKEN and not config.DRY_RUN) else []
        if not extra:  # без ключа пользователя опрос не создать — просим ответить в комментариях
            question += "\nОтветь в комментариях: " + " / ".join(options)
        publish(f"📊 Опрос недели\n\n{question}\nПо ответам выберем, о чём сделать следующие обзоры.",
                extra=extra)
        return

    if name == "Итоги недели":
        titles = "\n".join(f"- {t}" for t in state["week_news"][-7:]) or "- новостей не было"
        text = gigachat.ask(
            content.SYSTEM_PROMPT,
            "Сделай пост «Итоги недели»: коротко перескажи главное из списка новостей, "
            f"по одной строке на новость, без новых фактов.\n{titles}",
            temperature=0.4,
        )
        publish(f"{tidy(text)}\n\n{content.GUIDE_CTA}", IMAGE_QUERIES["news"])
        state["week_news"] = []
        return

    offer = content.pick_offer(key, state) if ad_allowed else None
    extra_info = ""
    if offer:
        extra_info = (f"\nВ конце поста органично подведи к сервису «{offer['name']}»: "
                      f"{offer.get('pitch', '')}. Ссылку не пиши — её добавят отдельно.")
    text = gigachat.ask(
        content.SYSTEM_PROMPT,
        f"Рубрика «{name}». Тема недели: {label}. {task}{extra_info}\n"
        f"Сервисы, которые можно упоминать:\n{content.catalog_text(key)}",
    )
    post = f"{content.HASHTAGS[name]}\n{tidy(text)}"
    if offer:
        subid = f"{today:%Y%m%d}_{name.replace(' ', '')}"
        post += "\n\n" + content.ad_block(offer, subid)
    else:
        post += "\n\n" + content.GUIDE_CTA
    publish(post, IMAGE_QUERIES[key])


def run(slot: str) -> None:
    today = datetime.now(MSK).date()
    state = load_state()
    if slot == "morning":
        morning(state)
    elif slot == "day":
        day(state, today)
    elif slot == "evening":
        evening(state, today)
    else:
        raise SystemExit(f"Неизвестный слот: {slot}")
    if not config.DRY_RUN:
        save_state(state)
