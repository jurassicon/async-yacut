from flask import jsonify, request, url_for

from . import app
from .error_handlers import InvalidAPIUsage
from .models import URLMap, SlugConflict, SlugInvalid, UrlInvalid


@app.route('/api/id/', methods=['POST'])
def add_url():
    data = request.get_json(silent=True)
    if data is None:
        raise InvalidAPIUsage('Отсутствует тело запроса', status_code=400)
    if 'url' not in data:
        raise InvalidAPIUsage('"url" является обязательным полем!',
                              status_code=400)

    custom = (data.get('custom_id') or '').strip() or None
    try:
        obj = URLMap.create_one(original_url=data['url'], custom_slug=custom)
    except (SlugConflict, SlugInvalid, UrlInvalid) as e:
        raise InvalidAPIUsage(str(e), status_code=400)

    return jsonify({'url': obj.original,
                    'short_link': url_for('follow_short', short=obj.short,
                                          _external=True)}), 201


@app.route('/api/id/<string:short_id>/', methods=['GET'])
def get_original_url(short_id):
    row = URLMap.get_by_short(short_id)
    if not row:
        raise InvalidAPIUsage('Указанный id не найден', status_code=404)
    return jsonify({'url': row.original}), 200
