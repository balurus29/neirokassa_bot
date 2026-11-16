"""Настройки бота.

Секреты приходят из GitHub Secrets, обычные настройки — из GitHub Variables
(все переменные репозитория передаются разом через VARS_JSON).
"""
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
STATE_FILE = ROOT / "state.json"

try:
    _VARS = json.loads(os.getenv("VARS_JSON") or "{}")
except ValueError:
    _VARS = {}


def _get(name: str, default: str = "") -> str:
    return os.getenv(name) or _VARS.get(name) or default


VK_GROUP_ID = int(_get("VK_GROUP_ID", "243319848"))
VK_API_VERSION = "5.199"

# Ключ пользователя-админа (необязательно): даёт загрузку фото напрямую на стену.
VK_USER_TOKEN = _get("VK_USER_TOKEN")
# Ключ сообщества: посты на стену и бот в сообщениях.
VK_GROUP_TOKEN = _get("VK_GROUP_TOKEN")
# Числовой ID страницы админа: нужен, чтобы загружать картинки ключом сообщества.
VK_ADMIN_ID = _get("VK_ADMIN_ID")

GIGACHAT_AUTH_KEY = _get("GIGACHAT_AUTH_KEY")
GIGACHAT_SCOPE = _get("GIGACHAT_SCOPE", "GIGACHAT_API_PERS")
# GigaChat, GigaChat-Pro или GigaChat-Max. Если на модель нет лимита — бот откатится на GigaChat.
GIGACHAT_MODEL = _get("GIGACHAT_MODEL", "GigaChat")
GIGACHAT_CA_BUNDLE = _get("GIGACHAT_CA_BUNDLE")

PIXABAY_KEY = _get("PIXABAY_KEY")
GUIDE_URL = _get("GUIDE_URL")

# 1 = рисовать картинки к постам через GigaChat
IMAGES = _get("IMAGES", "1") == "1"
# 1 = в рубриках разрешены партнёрские ссылки (только офферы с erid)
MONETIZATION = _get("MONETIZATION", "0") == "1"
# 1 = ничего не публиковать, только печатать пост в лог
DRY_RUN = _get("DRY_RUN", "0") == "1"
