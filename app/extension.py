from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from celery import Celery
from flask_jwt_extended import JWTManager

db = SQLAlchemy()
migrate = Migrate()
celery = Celery(__name__)
jwt  = JWTManager()
