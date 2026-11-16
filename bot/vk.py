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

def _upload(server_url: str, image_bytes: bytes) -> dict:
    return requests.post(
        server_url,
        files={"photo": ("image.jpg", image_bytes, "image/jpeg")},
        timeout=60,
    ).json()


def upload_wall_photo(image_bytes: bytes) -> str:
    """Загружает картинку для поста. Возвращает attachment.

    1) С ключом пользователя — обычная загрузка на стену.
    2) Без него — загрузка ключом сообщества через сообщения (нужен VK_ADMIN_ID).
    """
    if config.VK_USER_TOKEN:
        token = config.VK_USER_TOKEN
        server = call("photos.getWallUploadServer", token, group_id=config.VK_GROUP_ID)
        up = _upload(server["upload_url"], image_bytes)
        saved = call("photos.saveWallPhoto", token, group_id=config.VK_GROUP_ID,
                     photo=up["photo"], server=up["server"], hash=up["hash"])[0]
        return f"photo{saved['owner_id']}_{saved['id']}"

    if not config.VK_ADMIN_ID:
        raise VKError("нет ни ключа пользователя, ни VK_ADMIN_ID — картинку загрузить нечем")
    token = config.VK_GROUP_TOKEN
    server = call("photos.getMessagesUploadServer", token, peer_id=config.VK_ADMIN_ID)
    up = _upload(server["upload_url"], image_bytes)
    saved = call("photos.saveMessagesPhoto", token,
                 photo=up["photo"], server=up["server"], hash=up["hash"])[0]
    attachment = f"photo{saved['owner_id']}_{saved['id']}"
    if saved.get("access_key"):
        attachment += f"_{saved['access_key']}"
    return attachment


def create_poll(question: str, answers: list[str]) -> str:
    poll = call(
        "polls.create", config.VK_USER_TOKEN or config.VK_GROUP_TOKEN,
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
    try:
        return call("wall.post", token, **params)["post_id"]
    except VKError as exc:
        if "attachments" not in params:
            raise
        # ВК не принял вложение — публикуем пост без него, чтобы рубрика не пропала.
        print(f"[vk] вложение не принято ({exc}), публикую без него")
        params.pop("attachments")
        return call("wall.post", token, **params)["post_id"]


# ---------- Сообщения (ключ сообщества) ----------

def unanswered_conversations(count: int = 50) -> list[dict]:
    resp = call(
        "messages.getConversations", config.VK_GROUP_TOKEN,
        filter="unanswered", count=count, group_id=config.VK_GROUP_ID,
    )
    return resp.get("items", [])


def unanswered_messages(peer_id: int, count: int = 20) -> list[dict]:
    """Входящие сообщения после последнего ответа сообщества, от старых к новым."""
    resp = call("messages.getHistory", config.VK_GROUP_TOKEN,
                peer_id=peer_id, count=count, group_id=config.VK_GROUP_ID)
    incoming = []
    for msg in resp.get("items", []):  # от новых к старым
        if msg.get("out"):
            break
        incoming.append(msg)
    return list(reversed(incoming))


def send_message(peer_id: int, text: str, keyboard: dict | None = None) -> None:
    params = dict(peer_id=peer_id, message=text, random_id=random.randint(1, 2**31 - 1),
                  dont_parse_links=0)
    if keyboard is not None:
        params["keyboard"] = json.dumps(keyboard, ensure_ascii=False)
    call("messages.send", config.VK_GROUP_TOKEN, **params)
