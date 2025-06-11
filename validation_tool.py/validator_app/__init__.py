# validator_app/__init__.py
import os
from flask import Flask


def create_app():
    """Create and configure an instance of the Flask application."""
    app = Flask(__name__, instance_relative_config=True)

    # Load configuration from config.py
    app.config.from_object("validator_app.config.Config")

    # Ensure data directories exist
    with app.app_context():
        os.makedirs(app.config["SOURCE_DATA_DIR"], exist_ok=True)
        os.makedirs(app.config["IN_PROGRESS_DATA_DIR"], exist_ok=True)
        os.makedirs(app.config["VALIDATED_DATA_DIR"], exist_ok=True)

    # Register Blueprints
    from .routes.main import main_bp

    app.register_blueprint(main_bp)

    from .routes.api import api_bp

    app.register_blueprint(api_bp)

    return app
