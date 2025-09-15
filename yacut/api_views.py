from flask import jsonify, request, url_for

from . import app
from .error_handlers import InvalidAPIUsage
from .models import URLMap
from .shortener import create_short_link


@app.route('/api/id/', methods=['POST'])
def add_url():
    data = request.get_json(silent=True)
    if data is None:
        raise InvalidAPIUsage('Отсутствует тело запроса', status_code=400)
    if 'url' not in data:
        raise InvalidAPIUsage('"url" является обязательным полем!',
                              status_code=400)

    custom = data.get('custom_id')
    if isinstance(custom, str):
        custom = custom.strip()
    if not custom:
        custom = None

    if custom is not None:

        import re
        if len(custom) > 16 or not re.fullmatch(r'[A-Za-z0-9]+', custom):
            raise InvalidAPIUsage(
                'Указано недопустимое имя для короткой ссылки',
                status_code=400)

        if custom.lower() == 'files':
            raise InvalidAPIUsage(
                'Указано недопустимое имя для короткой ссылки',
                status_code=400)

        if URLMap.query.filter_by(short=custom).first():
            raise InvalidAPIUsage(
                'Предложенный вариант короткой ссылки уже существует.',
                status_code=400)

    obj = create_short_link(original_url=data['url'], custom_slug=custom)

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
