from flask import render_template, request, flash, redirect, url_for
from sqlalchemy.exc import IntegrityError
from werkzeug.utils import secure_filename

from . import app, db
from .forms import FileUploaderForm, ShortLinkForm
from .models import URLMap
from .shortener import create_short_link
from .yandexdisk import upload_files_to_disk


@app.route('/', methods=['GET', 'POST'], endpoint='index_view')
async def index_view():
    form = ShortLinkForm()
    new_url = None
    old_url = None

    if request.method == 'POST' and form.validate_on_submit():
        original_url = form.original_link.data.strip()
        custom = form.custom_id.data.strip() if form.custom_id.data else None
        old_url = original_url

        try:
            obj = create_short_link(original_url, custom_slug=custom)
            new_url = url_for('follow_short', short=obj.short, _external=True)

            flash('Ссылка создана.', 'success')
        except IntegrityError:
            db.session.rollback()
            flash('Предложенный вариант короткой ссылки уже существует.',
                  'danger')
        except Exception as e:
            app.logger.exception('Ошибка при создании короткой ссылки')
            flash(str(e), 'danger')

    if new_url:
        return render_template('index.html', new_url=new_url, old_url=old_url,
                               form=form)
    return render_template('index.html', form=form)


@app.route('/<string:short>')
def follow_short(short):
    row = URLMap.query.filter_by(short=short).first_or_404()
    return redirect(row.original, code=302)


@app.route('/files', methods=['GET', 'POST'])
async def upload_file_and_get_url():
    form = FileUploaderForm()
    items = []
    if request.method == 'POST' and form.validate_on_submit():
        file_objs = []
        file_names = []
        for f in (form.files.data or []):
            if not f:
                continue
            raw = (f.filename or '').strip()
            safe = secure_filename(raw)
            if not safe:
                continue
            file_objs.append(f)
            file_names.append(raw)

        download_urls = await upload_files_to_disk(file_objs)

        items = []
        for fname, download_url in zip(file_names, download_urls):
            obj = create_short_link(original_url=download_url)
            short = url_for('follow_short', short=obj.short, _external=True)
            items.append({'name': fname, 'short': short})

    return render_template('file_uploader.html', form=form, items=items)
