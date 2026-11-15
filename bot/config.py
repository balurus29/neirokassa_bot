"""Настройки бота. Все секреты берутся из переменных окружения (GitHub Secrets)."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
STATE_FILE = ROOT / "state.json"

VK_GROUP_ID = int(os.getenv("VK_GROUP_ID", "243319848"))
VK_API_VERSION = "5.199"

# Ключ пользователя-админа: нужен для wall.post, загрузки фото и опросов.
VK_USER_TOKEN = os.getenv("VK_USER_TOKEN", "")
# Ключ сообщества: нужен для бота в сообщениях.
VK_GROUP_TOKEN = os.getenv("VK_GROUP_TOKEN", "")

# Ключ авторизации GigaChat (Authorization key из личного кабинета, base64).
GIGACHAT_AUTH_KEY = os.getenv("GIGACHAT_AUTH_KEY", "")
GIGACHAT_SCOPE = os.getenv("GIGACHAT_SCOPE", "GIGACHAT_API_PERS")
# Путь к сертификату Минцифры (russian_trusted_root_ca.cer). Пусто = без проверки SSL.
GIGACHAT_CA_BUNDLE = os.getenv("GIGACHAT_CA_BUNDLE", "")

PIXABAY_KEY = os.getenv("PIXABAY_KEY", "")

# Ссылка на статью с гайдом в сообществе.
GUIDE_URL = os.getenv("GUIDE_URL", "")

# 1 = в рубриках разрешены партнёрские ссылки (только офферы с erid).
MONETIZATION = os.getenv("MONETIZATION", "0") == "1"

# Режим проверки: ничего не публикует, печатает пост в лог.
DRY_RUN = os.getenv("DRY_RUN", "0") == "1"
