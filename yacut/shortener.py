import secrets
import string
from typing import Optional
from urllib.parse import urlparse

from sqlalchemy.exc import IntegrityError

from yacut import db
from .models import URLMap

ALPHABET = string.ascii_letters + string.digits
SHORT_URL_LENGTH = 6


def generate_code(length: int = SHORT_URL_LENGTH):
    return ''.join(secrets.choice(ALPHABET) for _ in range(length))


def normalize_url(url: str) -> str:
    url = (url or "").strip()

    if url.startswith("//"):
        url = "https:" + url

    parsed = urlparse(url)

    if not parsed.scheme:
        url = "https://" + url
        parsed = urlparse(url)

    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise ValueError("Введите корректный URL: http(s)://...")

    return url


def create_short_link(
        original_url: str,
        custom_slug: Optional[str] = None,
        attempts: int = 32,
):
    original_url = normalize_url(original_url)
    if custom_slug:
        obj = URLMap(original=original_url, short=custom_slug)
        db.session.add(obj)
        db.session.commit()
        return obj

    for _ in range(attempts):
        slug = generate_code(SHORT_URL_LENGTH)
        if URLMap.query.filter_by(short=slug).first() is not None:
            continue
        obj = URLMap(original=original_url, short=slug)
        db.session.add(obj)
        try:
            db.session.commit()
            return obj
        except IntegrityError:
            db.session.rollback()
            continue
    raise RuntimeError(
        'Ошибка генерации уникальной короткой ссылки. Повторите попытку.')
