import re
import secrets
import string
from datetime import datetime
from typing import Optional
from urllib.parse import urlparse

from sqlalchemy.exc import IntegrityError

from yacut import db

SHORT_LEN = 6
SHORT_RE = re.compile(r'^[A-Za-z0-9]{1,16}$')
ALPHABET = string.ascii_letters + string.digits


class SlugInvalid(ValueError):
    """
    Поднимается, когда пользовательский алиас (custom_id) не проходит проверку
    формата: содержит недопустимые символы, либо длина > 16.
    Пример сообщения: 'Указано недопустимое имя для короткой ссылки'.
    """


class SlugConflict(ValueError):
    """
    Поднимается, когда алиас уже занят в базе или относится к зарезервированным
    значениям (например, 'files'). Используется для ответа пользователю с
    сообщением: 'Предложенный вариант короткой ссылки уже существует.'.
    """


class UrlInvalid(ValueError):
    """
    Поднимается при невалидном исходном URL: отсутствует http(s)-схема
    или домен не распознан. Сообщение: 'Введите корректный URL:
    http(s)://...'.
    """


class URLMap(db.Model):
    __tablename__ = 'url_map'
    RESERVED = {'files'}

    id = db.Column(db.Integer, primary_key=True)
    original = db.Column(db.String(2048), nullable=False)
    short = db.Column(db.String(16), unique=True, index=True, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    @staticmethod
    def _normalize_url(url: str) -> str:
        raw = (url or '').strip()
        if raw.startswith('//'):
            raw = 'https:' + raw
        if '://' not in raw:
            raw = 'https://' + raw
        p = urlparse(raw)
        if p.scheme not in ('http', 'https') or not p.netloc:
            raise UrlInvalid('Введите корректный URL: http(s)://...')
        return raw

    @staticmethod
    def validate_custom(custom: Optional[str], *,
                        check_unique: bool = False) -> Optional[str]:
        if custom is None:
            return None
        s = custom.strip()
        if not s:
            return None
        if len(s) > 16 or not re.fullmatch(r'[A-Za-z0-9]+', s):
            raise SlugInvalid('Указано недопустимое имя для короткой ссылки')
        if s.lower() in URLMap.RESERVED:
            raise SlugConflict(
                'Предложенный вариант короткой ссылки уже существует.')
        if check_unique and URLMap.query.filter_by(short=s).first():
            raise SlugConflict(
                'Предложенный вариант короткой ссылки уже существует.')
        return s

    @classmethod
    def get_by_short(cls, short_id: str) -> Optional["URLMap"]:
        s = (short_id or "").strip()
        if not SHORT_RE.fullmatch(s):
            return None
        return cls.query.filter_by(short=s).first()

    @classmethod
    def create_one(cls, original_url: str, custom_slug: Optional[str] = None,
                   attempts: int = 32) -> "URLMap":
        original = cls._normalize_url(original_url)
        slug = (custom_slug or '').strip()
        if slug:
            if not SHORT_RE.fullmatch(slug):
                raise SlugInvalid(
                    'Указано недопустимое имя для короткой ссылки')
            if slug.lower() in cls.RESERVED:
                raise SlugConflict(
                    'Предложенный вариант короткой ссылки уже существует.')
            if cls.query.filter_by(short=slug).first():
                raise SlugConflict(
                    'Предложенный вариант короткой ссылки уже существует.')
        else:
            for _ in range(attempts):
                guess = ''.join(
                    secrets.choice(ALPHABET) for _ in range(SHORT_LEN))
                if not cls.query.filter_by(short=guess).first():
                    slug = guess
                    break
            if not slug:
                raise RuntimeError(
                    'Ошибка генерации уникальной короткой ссылки. '
                    'Повторите попытку.')
        obj = cls(original=original, short=slug)
        db.session.add(obj)
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            raise SlugConflict(
                'Предложенный вариант короткой ссылки уже существует.')
        return obj
