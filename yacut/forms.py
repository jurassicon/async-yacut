import re

from flask_wtf import FlaskForm
from flask_wtf.file import MultipleFileField, FileAllowed
from wtforms import StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Length, Optional, ValidationError

from .models import URLMap

SHORT_RE = re.compile(r'^[A-Za-z0-9]+$')
# Резервированные пути (по ТЗ нужен как минимум files)
RESERVED = {'files'}
MAX_FILES = 10
MAX_ONE_FILE = 20 * 1024 * 1024

ALLOWED_EXTS = {
    'jpg', 'jpeg', 'png', 'gif', 'webp', 'bmp',
    'pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'rtf', 'txt', 'csv',
    'zip', 'rar', '7z', 'tar',
    'mp3', 'wav',
    'mp4', 'mov',
}


def _is_taken(slug: str) -> bool:
    return URLMap.query.filter_by(short=slug).first() is not None


class ShortLinkForm(FlaskForm):
    original_link = StringField(
        'Длинная ссылка',
        validators=[DataRequired(message='Введите URL')]
    )
    custom_id = StringField(
        'Ваш вариант короткой ссылки',
        validators=[Optional(), Length(max=16, message='Не более 16 символов')]
    )

    submit = SubmitField('Создать')

    def validate_custom_id(self, field):
        if not field.data:
            return
        slug = field.data.strip()
        # 1) Проверяем набор символов
        if not SHORT_RE.match(slug):
            raise ValidationError('Допустимы только латинские буквы и цифры.')
        # 2) Резерв
        if slug.lower() in RESERVED:
            raise ValidationError(
                'Предложенный вариант короткой ссылки уже существует.')
        # 3) Занятость
        if _is_taken(slug):
            raise ValidationError(
                'Предложенный вариант короткой ссылки уже существует.')


class FileUploaderForm(FlaskForm):
    files = MultipleFileField(
        validators=[
            FileAllowed(
                # Список разрешенных расширений для файлов.
                ALLOWED_EXTS,
                # Сообщение, в случае если расширение не совпадает.
                message=(
                    'Недопустимый формат. Разрешены: '
                    '.jpg, .jpeg, .png, .gif, .webp, .bmp, '
                    '.pdf, .doc, .docx, .xls, .xlsx, .ppt, .pptx, .rtf, .txt, .csv, '
                    '.zip, .rar, .7z, .tar, '
                    '.mp3, .wav, .mp4, .mov'
                ),
            )
        ]
    )
    submit = SubmitField('Загрузить')

    def validate_files(self, field):

        if not field.data:
            raise ValidationError('Необходимо загрузить хотя бы один файл')


