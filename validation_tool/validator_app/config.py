# validator_app/config.py
import os

class Config:
    """Base configuration."""
    SECRET_KEY = os.environ.get('SECRET_KEY', 'a_very_secret_key')

    # Directory paths
    SOURCE_DATA_DIR = 'data_source'
    IN_PROGRESS_DATA_DIR = 'data_in_progress'
    VALIDATED_DATA_DIR = 'data_validated'
    IMAGE_DIR = os.path.join('static', 'images')

    # Flask app settings
    DEBUG = True
