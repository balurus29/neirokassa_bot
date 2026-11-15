"""Бот в сообщениях: отвечает на ГАЙД, «Начать» и кнопки подборщика.

Запускается по расписанию (раз в 10–15 минут) и отвечает на все неотвеченные диалоги.
Сообщения, которые бот не понял, остаются неотвеченными — их видно админу в сообщениях сообщества.
"""
import json

from . import config, content, vk

CATEGORIES = {
    "texts": "✍️ Тексты",
    "images": "🖼 Картинки",
    "video": "🎬 Видео",
    "study": "📚 Учёба",
    "bots": "🤖 Свой бот",
}

GREETING = (
    "Привет! 👋 Это Нейрокасса.\n\n"
    "Напиши ГАЙД — пришлю подборку нейросетей для работы, которые доступны из России.\n"
    "Или выбери задачу кнопкой ниже — посоветую, с чего начать."
)


def keyboard() -> dict:
    buttons = [[{"action": {"type": "text", "label": label,
                            "payload": json.dumps({"pick": key})},
                 "color": "secondary"}] for key, label in CATEGORIES.items()]
    buttons.append([{"action": {"type": "text", "label": "🎁 ГАЙД",
                                "payload": json.dumps({"cmd": "guide"})},
                     "color": "positive"}])
    return {"one_time": False, "buttons": buttons}


def guide_text() -> str:
    if config.GUIDE_URL:
        return f"Держи гайд 🎁 «Нейросети для работы, доступные из России»\n👉 {config.GUIDE_URL}"
    return "Гайд скоро будет готов — напиши ГАЙД чуть позже 🙏"


def pick_text(key: str) -> str:
    services = content.load_catalog().get(key, [])[:2]
    lines = [f"Для задачи «{CATEGORIES[key]}» начни с этого:\n"]
    for s in services:
        lines.append(f"• {s['name']} ({s['by']}) — {s['what']}; {s['price']}\n{s['url']}")
    offer = content.pick_offer(key, {})
    if offer:
        lines.append("\n" + content.ad_block(offer, f"bot_{key}"))
    lines.append("\nХочешь полную подборку — напиши ГАЙД.")
    return "\n".join(lines)


def classify(message: dict) -> tuple[str, str | None]:
    payload = {}
    if message.get("payload"):
        try:
            payload = json.loads(message["payload"])
        except (TypeError, ValueError):
            payload = {}
    text = (message.get("text") or "").strip().lower()

    if payload.get("command") == "start" or text in ("начать", "start", "привет", "меню"):
        return "start", None
    if payload.get("cmd") == "guide" or "гайд" in text:
        return "guide", None
    if payload.get("pick") in CATEGORIES:
        return "pick", payload["pick"]
    for key, label in CATEGORIES.items():
        if text and text in label.lower():
            return "pick", key
    return "unknown", None


def run() -> None:
    answered = 0
    for conv in vk.unanswered_conversations():
        message = conv.get("last_message", {})
        peer_id = conv["conversation"]["peer"]["id"]
        kind, key = classify(message)
        if kind == "start":
            vk.send_message(peer_id, GREETING, keyboard())
        elif kind == "guide":
            vk.send_message(peer_id, guide_text(), keyboard())
        elif kind == "pick":
            vk.send_message(peer_id, pick_text(key), keyboard())
        else:
            continue
        answered += 1
    print(f"Отвечено диалогов: {answered}")
