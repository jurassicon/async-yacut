import re

from flask_wtf import FlaskForm
from flask_wtf.file import MultipleFileField, FileAllowed
from wtforms import StringField, SubmitField
from wtforms.validators import (DataRequired, Length,
                                Optional, ValidationError, Regexp)

from .models import URLMap

SHORT_RE = re.compile(r'^[A-Za-z0-9]+$')
RESERVED = {'files'}
MAX_FILES = 10
MAX_ONE_FILE = 20 * 1024 * 1024

ALLOWED_EXTS = {
    'jpg', 'jpeg', 'png', 'gif', 'webp', 'bmp',
    'pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'txt', 'csv',
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
        validators=[Optional(), Length(max=16, message='Не более 16 символов'),
                    Regexp(r'^[A-Za-z0-9]+$', message='Только буквы и цифры')
                    ])

    submit = SubmitField('Создать')


class FileUploaderForm(FlaskForm):
    files = MultipleFileField(
        validators=[
            FileAllowed(
                ALLOWED_EXTS,
                message=(
                    'Недопустимый формат. Разрешены: '
                    '.jpg, .jpeg, .png, .gif, .webp, .bmp, '
                    '.pdf, .doc, .docx, .xls, .xlsx, .ppt, .pptx, .txt, .csv, '
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
