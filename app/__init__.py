import logging
from flask import Flask
from app.config import Config
from app.extension import db, migrate, celery
from app.routes.botRoutes import bot_bp


def create_app():
    app = Flask(__name__)

    app.config.from_object(Config)
    db.init_app(app)
    migrate.init_app(app, db)

    celery.conf.update(
        broker_url=app.config["CELERY_BROKER_URL"],
        result_backend=app.config["CELERY_RESULT_BACKEND"],
    )

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        handlers=[logging.FileHandler("app.log"), logging.StreamHandler()],
    )

    app.register_blueprint(bot_bp)
    return app
