import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Base configuration"""
    SECRET_KEY = os.environ.get('SECRET_KEY', 'ahmed')
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER', 'static/uploads')
    MAX_CONTENT_LENGTH = int(os.environ.get('MAX_CONTENT_LENGTH', 5242880))
    API_KEY = os.environ.get('API_KEY', 'your-secret-api-key-123')

class DevelopmentConfig(Config):
    """Development configuration - uses SQLite"""
    DEBUG = True
    DATABASE_URL = None  # Will use SQLite

class ProductionConfig(Config):
    """Production configuration - uses PostgreSQL"""
    DEBUG = False
    DATABASE_URL = os.environ.get('DATABASE_URL')

# Select configuration based on FLASK_ENV
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}

def get_config():
    env = os.environ.get('FLASK_ENV', 'development')
    return config.get(env, config['default'])