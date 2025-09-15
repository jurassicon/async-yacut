# yacut/__init__.py
from flask import Flask
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import inspect
from settings import Config

app = Flask(__name__)
app.config.from_object(Config)

db = SQLAlchemy(app)
migrate = Migrate(app, db)

# 1) СНАЧАЛА импортируем модели, чтобы ORM их «увидела».
from . import models
from .models import URLMap

# 2) Опционально: создаём таблицу URLMap, если её нет.
with app.app_context():
    insp = inspect(db.engine)
    table_name = URLMap.__tablename__
    if not insp.has_table(table_name):
        URLMap.__table__.create(db.engine)
        print(f"Таблица создана: {table_name}")
    else:
        print(f"Таблица уже существует: {table_name}")
    print('Текущие таблицы:', insp.get_table_names())


from . import error_handlers
from . import views, api_views