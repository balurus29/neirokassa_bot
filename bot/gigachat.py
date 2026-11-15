"""Клиент GigaChat API (Сбер)."""
import uuid

import requests
import urllib3

from . import config

OAUTH_URL = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
CHAT_URL = "https://gigachat.devices.sberbank.ru/api/v1/chat/completions"

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


def ask(system: str, user: str, temperature: float = 0.7, max_tokens: int = 900) -> str:
    resp = requests.post(
        CHAT_URL,
        headers={"Authorization": f"Bearer {_get_token()}", "Accept": "application/json"},
        json={
            "model": "GigaChat",
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        },
        verify=_verify(),
        timeout=90,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"].strip()
