"""Клиент GigaChat API (Сбер): текст и картинки (Kandinsky внутри GigaChat)."""
import re
import uuid

import requests
import urllib3

from . import config

OAUTH_URL = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
API_URL = "https://gigachat.devices.sberbank.ru/api/v1"

_token: str | None = None


def _verify():
    if config.GIGACHAT_CA_BUNDLE:
        return config.GIGACHAT_CA_BUNDLE
    # Сертификаты Сбера выпущены российским УЦ, которого нет в стандартных хранилищах.
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    return False


def _get_token() -> str:
    global _token
    if _token:
        return _token
    if not config.GIGACHAT_AUTH_KEY:
        raise RuntimeError("Не задан GIGACHAT_AUTH_KEY")
    resp = requests.post(
        OAUTH_URL,
        headers={
            "Authorization": f"Basic {config.GIGACHAT_AUTH_KEY}",
            "RqUID": str(uuid.uuid4()),
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
        },
        data={"scope": config.GIGACHAT_SCOPE},
        verify=_verify(),
        timeout=30,
    )
    resp.raise_for_status()
    _token = resp.json()["access_token"]
    return _token


def _chat(payload: dict) -> dict:
    resp = requests.post(
        f"{API_URL}/chat/completions",
        headers={"Authorization": f"Bearer {_get_token()}", "Accept": "application/json"},
        json=payload, verify=_verify(), timeout=120,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]


def ask(system: str, user: str, temperature: float = 0.7, max_tokens: int = 1500) -> str:
    payload = {
        "model": config.GIGACHAT_MODEL,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    try:
        return _chat(payload)["content"].strip()
    except requests.HTTPError as exc:
        # Если на выбранную модель нет лимита — откатываемся на базовую.
        if config.GIGACHAT_MODEL == "GigaChat":
            raise
        print(f"[gigachat] модель {config.GIGACHAT_MODEL} недоступна ({exc}), беру GigaChat")
        payload["model"] = "GigaChat"
        return _chat(payload)["content"].strip()


def draw(prompt: str) -> bytes | None:
    """Генерирует картинку. Возвращает байты JPG или None, если не получилось."""
    try:
        message = _chat({
            "model": config.GIGACHAT_MODEL,
            "messages": [
                {"role": "system", "content": "Ты — художник-иллюстратор."},
                {"role": "user", "content": prompt},
            ],
            "function_call": "auto",
        })
        match = re.search(r'<img[^>]+src="([^"]+)"', message.get("content", ""))
        if not match:
            print("[gigachat] картинка не сгенерирована: в ответе нет изображения")
            return None
        resp = requests.get(
            f"{API_URL}/files/{match.group(1)}/content",
            headers={"Authorization": f"Bearer {_get_token()}", "Accept": "application/jpg"},
            verify=_verify(), timeout=120,
        )
        resp.raise_for_status()
        return resp.content
    except Exception as exc:
        print(f"[gigachat] картинка не сгенерирована: {exc}")
        return None
