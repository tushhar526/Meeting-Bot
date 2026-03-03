import logging
from flask import Flask
from flask_cors import CORS
from app.config import Config
from app.extension import db, migrate, celery, jwt
from app.routes.botRoutes import bot_bp
from app.routes.authRoutes import auth_bp
from app.routes.userRoutes import user_bp
from dotenv import load_dotenv


def create_app():
    app = Flask(__name__)
    CORS(
        app,
        resources={
            r"/*": {
                "origins": "http://localhost:5173",
                "methods": [
                    "GET",
                    "POST",
                    "PUT",
                    "DELETE",
                    "OPTIONS",
                ],  # <--- Specify here
                "allow_headers": ["Content-Type", "Authorization"],
            }
        },
        supports_credentials=True,
    )

    load_dotenv()

    app.config.from_object(Config)
    db.init_app(app)
    jwt.init_app(app)
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
    app.register_blueprint(auth_bp)
    app.register_blueprint(user_bp)
    return app
