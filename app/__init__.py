import logging
from flask import Flask
from flask_cors import CORS
from dotenv import load_dotenv

load_dotenv()

from app.config import Config
from app.extension import db, migrate, celery, jwt
from sqlalchemy import text
from app.routes.botRoutes import bot_bp
from app.routes.authRoutes import auth_bp
from app.routes.userRoutes import user_bp
from app.routes.webhookReceieveRoutes import webhook_receiver_bp
from app.routes.adminRoutes import admin_bp
from app.routes.calendarRoutes import multi_calendar_bp

# from app.routes.authCallbackRoutes import auth_callback_bp  # Commented out - using multi-platform instead
from app.routes.superadminRoutes import superadmin_bp


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
                ],
                "allow_headers": [
                    "Content-Type",
                    "Authorization",
                    "Range",  # For audio streaming/seeking
                    "Accept-Ranges",  # For audio streaming
                ],
                "expose_headers": [
                    "Content-Range",  # Expose range headers to frontend
                    "Accept-Ranges",
                    "Content-Length",
                    "X-Audio-Duration",  # Audio metadata headers
                    "X-Audio-Duration-Formatted",
                    "X-Audio-File-Size",
                    "X-Audio-File-Size-MB",
                ],
                "supports_credentials": True,  # Enable cookie support
            }
        },
        supports_credentials=True,  # Global cookie support
        expose_headers=["Set-Cookie"],  # Expose cookie headers
    )

    # load_dotenv() is already called at the top - no need to call again

    print("YOU BET ON THIS ... THE PROJECT GETS UPDATED ON NEW CONTAINER COMMAND")
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
    app.register_blueprint(admin_bp)
    app.register_blueprint(multi_calendar_bp)
    # app.register_blueprint(auth_callback_bp)  # Commented out - using multi-platform instead
    app.register_blueprint(webhook_receiver_bp)
    app.register_blueprint(superadmin_bp)

    # Initialize Meeting Bot Cron Scheduler
    with app.app_context():
        try:
            # Enable WAL mode for SQLite to handle concurrent writes
            if db.engine.url.drivername == "sqlite":
                db.session.execute(text("PRAGMA journal_mode=WAL"))
                db.session.commit()
                print("SQLite WAL mode enabled for concurrent access")

            # Initialize and start SchedulerService
            from app.services.schedulerService import scheduler_service
            scheduler_service.initialize()
            scheduler_service.start()
            print("SchedulerService initialized and started successfully!")

        except Exception as e:
            print(f"Warning: Failed to initialize scheduler: {e}")
            print("Scheduler functionality temporarily disabled")

    return app
