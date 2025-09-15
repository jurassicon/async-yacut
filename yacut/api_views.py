# what_to_watch/opinions_app/api_views.py

from flask import jsonify, request, url_for

from . import app, db
from .error_handlers import InvalidAPIUsage
from .models import URLMap
from .shortener import create_short_link


@app.route('/api/id/', methods=['POST'])
def add_url():
    data = request.get_json(silent=True)
    if data is None:
        raise InvalidAPIUsage('Отсутствует тело запроса', status_code=400)
    if 'url' not in data:
        raise InvalidAPIUsage('"url" является обязательным полем!', status_code=400)

    # 1) Нормализуем custom_id: '' или пробелы -> None
    custom = data.get('custom_id')
    if isinstance(custom, str):
        custom = custom.strip()
    if not custom:
        custom = None

    # 2) Валидируем ТОЛЬКО если custom задан
    if custom is not None:
        # длина и допустимые символы
        import re
        if len(custom) > 16 or not re.fullmatch(r'[A-Za-z0-9]+', custom):
            raise InvalidAPIUsage('Указано недопустимое имя для короткой ссылки', status_code=400)
        # резервированные пути (пример)
        if custom.lower() == 'files':
            raise InvalidAPIUsage('Указано недопустимое имя для короткой ссылки', status_code=400)
        # уникальность
        if URLMap.query.filter_by(short=custom).first():
            raise InvalidAPIUsage('Предложенный вариант короткой ссылки уже существует.', status_code=400)

    # 3) Создаём запись (автогенерация, если custom=None)
    obj = create_short_link(original_url=data['url'], custom_slug=custom)

    # 4) Правильный ответ API
    return jsonify({
        'url': obj.original,
        'short_link': url_for('follow_short', short=obj.short, _external=True),
    }), 201


@app.route('/api/id/<string:short_id>/', methods=['GET'])
def get_original_url(short_id):
    row = URLMap.query.filter_by(short=short_id).first()
    if not row:
        raise InvalidAPIUsage('Указанный id не найден', status_code=404)
    return jsonify({'url': row.original}), 200
