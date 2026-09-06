import os
import json
from datetime import timedelta

basedir = os.path.abspath(os.path.dirname(__file__))


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
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
    # Cloud Storage bucket for Firestore managed exports (gs://bucket/path).
    # Empty means the "Export gerenciado" feature stays hidden.
    BACKUP_GCS_URI = os.environ.get('BACKUP_GCS_URI', '')
    
    MAIL_SERVER = os.environ.get('MAIL_SERVER')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'true').lower() in ['true', '1', 'yes']
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER')
    
    CACHE_TYPE = os.environ.get('CACHE_TYPE', 'SimpleCache')
    CACHE_DEFAULT_TIMEOUT = 300

    # Instagram (Meta Graph API)
    INSTAGRAM_ACCESS_TOKEN = os.environ.get('INSTAGRAM_ACCESS_TOKEN', '')
    INSTAGRAM_IG_USER_ID = os.environ.get('INSTAGRAM_IG_USER_ID', '')
    INSTAGRAM_APP_ID = os.environ.get('INSTAGRAM_APP_ID', '')
    INSTAGRAM_APP_SECRET = os.environ.get('INSTAGRAM_APP_SECRET', '')
    INSTAGRAM_API_VERSION = os.environ.get('INSTAGRAM_API_VERSION', 'v21.0')
    INSTAGRAM_GRAPH_URL = os.environ.get('INSTAGRAM_GRAPH_URL', 'https://graph.facebook.com')
    PUBLIC_BASE_URL = os.environ.get('PUBLIC_BASE_URL', 'http://localhost:5000')

    # Firebase (Firestore + Auth)
    _sa_env = os.environ.get('FIREBASE_SERVICE_ACCOUNT')
    if not _sa_env:
        candidates = []
        for entry in os.listdir(basedir):
            if 'firebase-adminsdk' in entry and entry.endswith('.json'):
                candidates.append(os.path.join(basedir, entry))
        _sa_env = candidates[0] if candidates else os.path.join(basedir, 'firebase-service-account.json')
    FIREBASE_SERVICE_ACCOUNT = _sa_env
    FIREBASE_ENABLED = True
    FIREBASE_PROJECT_ID = os.environ.get('FIREBASE_PROJECT_ID', 'gestoper-4ba86')
    # Web API key (console > project settings). Used for server-side password
    # verification via Identity Toolkit; optional when using client-side SDK.
    FIREBASE_WEB_API_KEY = os.environ.get('FIREBASE_WEB_API_KEY',
                                          'AIzaSyAGAZCJwSIGeAWg0Ib5wn5gAG7K-M9Gm9A')
    # Web app config dict delivered to the login template for the Firebase
    # JS SDK. Override via FIREBASE_WEB_CONFIG (JSON) per environment.
    _fb_web = os.environ.get('FIREBASE_WEB_CONFIG', '')
    if _fb_web:
        try:
            FIREBASE_WEB_CONFIG = json.loads(_fb_web)
        except Exception:
            FIREBASE_WEB_CONFIG = None
    else:
        FIREBASE_WEB_CONFIG = {
            'apiKey': 'AIzaSyAGAZCJwSIGeAWg0Ib5wn5gAG7K-M9Gm9A',
            'authDomain': 'gestoper-4ba86.firebaseapp.com',
            'projectId': 'gestoper-4ba86',
            'storageBucket': 'gestoper-4ba86.firebasestorage.app',
            'messagingSenderId': '775991796901',
            'appId': '1:775991796901:web:17f88bf7b9dd1285a7d94c',
            'measurementId': 'G-44FT15NYQ3',
        }
    
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
    SESSION_COOKIE_SECURE = False
    REMEMBER_COOKIE_SECURE = False
    JWT_COOKIE_SECURE = False


class TestingConfig(Config):
    TESTING = True
    WTF_CSRF_ENABLED = False
    JWT_COOKIE_CSRF_PROTECT = False
    FIREBASE_ENABLED = False


class ProductionConfig(Config):
    DEBUG = False
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