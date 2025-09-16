from flask import render_template, request, flash, redirect, url_for, abort
from werkzeug.utils import secure_filename

from . import app
from .forms import FileUploaderForm, ShortLinkForm
from .models import URLMap, SlugInvalid, SlugConflict, UrlInvalid
from .shortener import create_short_link
from .yandexdisk import upload_files_to_disk


@app.route('/', methods=['GET', 'POST'], endpoint='index_view')
async def index_view():
    form = ShortLinkForm()
    if request.method == 'POST' and form.validate_on_submit():
        try:
            obj = URLMap.create_one(
                original_url=form.original_link.data,
                custom_slug=form.custom_id.data or None
            )
            short_url = url_for('follow_short', short=obj.short,
                                _external=True)
            flash('Ссылка создана.', 'success')
            return render_template('index.html', form=form, new_url=short_url,
                                   old_url=obj.original)
        except SlugConflict as e:
            form.custom_id.errors.append(str(e))
        except (SlugInvalid, UrlInvalid) as e:
            form.custom_id.errors.append(str(e))
        except Exception:
            app.logger.exception('Ошибка при создании короткой ссылки')
            flash('Внутренняя ошибка. Попробуйте позже.', 'danger')
    return render_template('index.html', form=form)


@app.route('/<string:short>')
def follow_short(short):
    row = URLMap.query.filter_by(short=short).first_or_404()
    if not row:
        abort(404)
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
