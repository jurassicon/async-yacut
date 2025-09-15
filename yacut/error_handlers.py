# error_handlers.py
from flask import jsonify, render_template, request, redirect, url_for, flash
from werkzeug.exceptions import RequestEntityTooLarge

from . import app, db


class InvalidAPIUsage(Exception):
    status_code = 400

    def __init__(self, message, status_code=None):
        super().__init__()
        self.message = message
        if status_code is not None:
            self.status_code = status_code

    def to_dict(self):
        return dict(message=self.message)


def _wants_json() -> bool:
    if request.path.startswith('/api/'):
        return True
    best = request.accept_mimetypes.best_match(
        ['application/json', 'text/html'])
    return request.path.startswith('/api/') or best == 'application/json'


@app.errorhandler(InvalidAPIUsage)
def invalid_api_usage(error: InvalidAPIUsage):
    if _wants_json():
        return jsonify(error.to_dict()), error.status_code

    flash(error.message, 'danger')
    return redirect(request.referrer or url_for('upload_file_and_get_url'))


@app.errorhandler(404)
def page_not_found(error):
    if _wants_json():
        return jsonify({'message': 'Not found'}), 404
    return render_template('404.html'), 404


@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    if _wants_json():
        return jsonify({'message': 'Internal server error'}), 500
    return render_template('500.html'), 500
