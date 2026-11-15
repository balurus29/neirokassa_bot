"""Минимальный клиент VK API."""
import json
import random
import time

import requests

from . import config

API_URL = "https://api.vk.com/method/"


class VKError(RuntimeError):
    pass


def call(method: str, token: str, **params):
    if not token:
        raise VKError(f"Нет ключа доступа для {method}")
    params.update(access_token=token, v=config.VK_API_VERSION)
    for attempt in range(3):
        resp = requests.post(API_URL + method, data=params, timeout=30)
        data = resp.json()
        if "error" not in data:
            return data["response"]
        err = data["error"]
        # 6 = слишком много запросов в секунду, 10 = внутренняя ошибка
        if err.get("error_code") in (6, 10) and attempt < 2:
            time.sleep(1 + attempt)
            continue
        raise VKError(f"{method}: {err.get('error_code')} {err.get('error_msg')}")
    raise VKError(f"{method}: не удалось выполнить запрос")


# ---------- Стена (ключ пользователя) ----------

def upload_wall_photo(image_bytes: bytes) -> str:
    """Загружает картинку для поста в сообщество, возвращает attachment."""
    token = config.VK_USER_TOKEN or config.VK_GROUP_TOKEN
    server = call("photos.getWallUploadServer", token, group_id=config.VK_GROUP_ID)
    up = requests.post(
        server["upload_url"],
        files={"photo": ("image.jpg", image_bytes, "image/jpeg")},
        timeout=60,
    ).json()
    saved = call(
        "photos.saveWallPhoto", token,
        group_id=config.VK_GROUP_ID,
        photo=up["photo"], server=up["server"], hash=up["hash"],
    )[0]
    return f"photo{saved['owner_id']}_{saved['id']}"


def create_poll(question: str, answers: list[str]) -> str:
    poll = call(
        "polls.create", config.VK_USER_TOKEN,
        question=question,
        add_answers=json.dumps(answers, ensure_ascii=False),
        owner_id=-config.VK_GROUP_ID,
    )
    return f"poll{poll['owner_id']}_{poll['id']}"


def wall_post(message: str, attachments: list[str] | None = None) -> int:
    """Публикует пост. Если ключа пользователя нет — пробует ключом сообщества."""
    params = dict(owner_id=-config.VK_GROUP_ID, from_group=1, message=message)
    if attachments:
        params["attachments"] = ",".join(attachments)
    token = config.VK_USER_TOKEN or config.VK_GROUP_TOKEN
    return call("wall.post", token, **params)["post_id"]


# ---------- Сообщения (ключ сообщества) ----------

def unanswered_conversations(count: int = 50) -> list[dict]:
    resp = call(
        "messages.getConversations", config.VK_GROUP_TOKEN,
        filter="unanswered", count=count, group_id=config.VK_GROUP_ID,
    )
    return resp.get("items", [])


def send_message(peer_id: int, text: str, keyboard: dict | None = None) -> None:
    params = dict(peer_id=peer_id, message=text, random_id=random.randint(1, 2**31 - 1),
                  dont_parse_links=0)
    if keyboard is not None:
        params["keyboard"] = json.dumps(keyboard, ensure_ascii=False)
    call("messages.send", config.VK_GROUP_TOKEN, **params)
