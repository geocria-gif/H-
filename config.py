import os
from datetime import timedelta

basedir = os.path.abspath(os.path.dirname(__file__))


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_RECORD_QUERIES = True
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = None
    
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER') or os.path.join(basedir, 'uploads')
    MAX_CONTENT_LENGTH = int(os.environ.get('MAX_CONTENT_LENGTH', 16 * 1024 * 1024))
    
    ALLOWED_EXTENSIONS = {'pdf', 'xlsx', 'xls', 'doc', 'docx', 'png', 'jpg', 'jpeg', 'csv'}
    
    SESSION_COOKIE_SECURE = False
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = timedelta(hours=8)
    
    REMEMBER_COOKIE_SECURE = False
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_DURATION = timedelta(days=30)
    
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY') or 'jwt-secret-change-in-production'
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)
    JWT_TOKEN_LOCATION = ['headers', 'cookies']
    JWT_COOKIE_SECURE = False
    JWT_COOKIE_HTTPONLY = True
    JWT_COOKIE_SAMESITE = 'Lax'
    JWT_COOKIE_CSRF_PROTECT = True
    
    RATELIMIT_DEFAULT = '200 per minute'
    RATELIMIT_STORAGE_URL = os.environ.get('RATELIMIT_STORAGE_URL', 'memory://')
    
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    LOG_DIR = os.environ.get('LOG_DIR') or os.path.join(basedir, 'logs')
    
    BACKUP_DIR = os.environ.get('BACKUP_DIR') or os.path.join(basedir, 'backups')
    BACKUP_RETENTION_DAYS = int(os.environ.get('BACKUP_RETENTION_DAYS', 30))
    
    MAIL_SERVER = os.environ.get('MAIL_SERVER')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'true').lower() in ['true', '1', 'yes']
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER')
    
    CACHE_TYPE = os.environ.get('CACHE_TYPE', 'SimpleCache')
    CACHE_DEFAULT_TIMEOUT = 300
    
    SWAGGER = {
        'title': 'SISPM API',
        'version': '1.0.0',
        'description': 'Sistema de Escalas CPR-CN - API REST',
        'openapi_version': '3.0.3',
        'servers': [{'url': '/api/v1', 'description': 'API v1'}],
    }
    
    @staticmethod
    def init_app(app):
        pass


class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('DEV_DATABASE_URL') or \
        f'sqlite:///{os.path.join(basedir, "instance", "sispm_dev.db")}'
    SQLALCHEMY_ECHO = False
    
    SESSION_COOKIE_SECURE = False
    REMEMBER_COOKIE_SECURE = False
    JWT_COOKIE_SECURE = False


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('TEST_DATABASE_URL') or 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False
    JWT_COOKIE_CSRF_PROTECT = False


class ProductionConfig(Config):
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    if SQLALCHEMY_DATABASE_URI and SQLALCHEMY_DATABASE_URI.startswith('postgres://'):
        SQLALCHEMY_DATABASE_URI = SQLALCHEMY_DATABASE_URI.replace('postgres://', 'postgresql://', 1)
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 10,
        'pool_recycle': 3600,
        'pool_pre_ping': True,
        'max_overflow': 20,
    }
    
    SESSION_COOKIE_SECURE = True
    REMEMBER_COOKIE_SECURE = True
    JWT_COOKIE_SECURE = True
    
    @classmethod
    def init_app(cls, app):
        Config.init_app(app)
        
        import logging
        from logging.handlers import RotatingFileHandler
        
        if not os.path.exists(cls.LOG_DIR):
            os.makedirs(cls.LOG_DIR)
        
        file_handler = RotatingFileHandler(
            os.path.join(cls.LOG_DIR, 'error.log'),
            maxBytes=10240000,
            backupCount=10
        )
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(logging.ERROR)
        app.logger.addHandler(file_handler)
        app.logger.setLevel(logging.INFO)
        app.logger.info('SISPM startup')


class DockerConfig(ProductionConfig):
    @classmethod
    def init_app(cls, app):
        ProductionConfig.init_app(app)
        
        import logging
        from logging.handlers import RotatingFileHandler
        
        stream_handler = logging.StreamHandler()
        stream_handler.setLevel(logging.INFO)
        stream_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        app.logger.addHandler(stream_handler)


config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'docker': DockerConfig,
    'default': DevelopmentConfig
}