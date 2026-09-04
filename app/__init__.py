import os
import time
import logging
import requests
from logging.handlers import RotatingFileHandler
from flask import Flask, request, current_app
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_caching import Cache
from flask_jwt_extended import JWTManager
from flask_mail import Mail
from flask_talisman import Talisman
from flask_compress import Compress
from werkzeug.middleware.proxy_fix import ProxyFix

from config import config
from app.firebase_db import init_firebase

login_manager = LoginManager()
csrf = CSRFProtect()
limiter = Limiter(key_func=get_remote_address, default_limits=[])
cache = Cache()
jwt = JWTManager()
mail = Mail()
talisman = Talisman()
compress = Compress()


def create_app(config_name=None):
    if config_name is None:
        config_name = os.environ.get('FLASK_CONFIG', 'default')

    app = Flask(__name__)
    app.config.from_object(config[config_name])
    config[config_name].init_app(app)

    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

    login_manager.init_app(app)
    csrf.init_app(app)
    limiter.init_app(app)
    cache.init_app(app)
    jwt.init_app(app)
    mail.init_app(app)
    compress.init_app(app)

    # Initialize Firebase (Firestore + Auth)
    if app.config.get('FIREBASE_ENABLED', True):
        init_firebase(app)

    if not app.debug and not app.testing:
        talisman.init_app(app,
            force_https=app.config.get('SESSION_COOKIE_SECURE', False),
            strict_transport_security=True,
            content_security_policy={
                'default-src': "'self'",
                'script-src': "'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net https://unpkg.com https://www.gstatic.com https://www.googleapis.com",
                'style-src': "'self' 'unsafe-inline' https://cdn.jsdelivr.net https://fonts.googleapis.com",
                'font-src': "'self' https://fonts.gstatic.com",
                'img-src': "'self' data: https:",
                'connect-src': "'self' https://identitytoolkit.googleapis.com https://securetoken.googleapis.com https://*.googleapis.com https://nominatim.openstreetmap.org",
                'frame-src': "'self'",
            },
            frame_options='DENY',
        )

    setup_logging(app)
    register_blueprints(app)
    register_error_handlers(app)
    register_shell_context(app)
    register_template_filters(app)
    register_request_hooks(app)
    register_jwt_callbacks(app)
    register_login_manager(app)

    with app.app_context():
        @login_manager.user_loader
        def load_user(user_id):
            from app.auth.session import load_user_by_matricula
            return load_user_by_matricula(user_id)

        login_manager.session_protection = 'strong'
        login_manager.login_view = 'auth.login'
        login_manager.login_message = 'Por favor, faça login para acessar esta página.'
        login_manager.login_message_category = 'info'

    return app


def setup_logging(app):
    log_dir = app.config['LOG_DIR']
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    if not app.debug and not app.testing:
        access_handler = RotatingFileHandler(
            os.path.join(log_dir, 'access.log'),
            maxBytes=10240000,
            backupCount=10
        )
        error_handler = RotatingFileHandler(
            os.path.join(log_dir, 'error.log'),
            maxBytes=10240000,
            backupCount=10
        )
        error_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        error_handler.setLevel(logging.ERROR)

        security_handler = RotatingFileHandler(
            os.path.join(log_dir, 'security.log'),
            maxBytes=10240000,
            backupCount=10
        )
        security_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [IP: %(remote_addr)s User: %(user_id)s]'
        ))
        security_handler.setLevel(logging.INFO)

        class SecurityFilter(logging.Filter):
            def filter(self, record):
                record.remote_addr = getattr(request, 'remote_addr', '-')
                record.user_id = getattr(request, 'user_id', 'anonymous')
                return True

        security_handler.addFilter(SecurityFilter())

        app.logger.addHandler(error_handler)
        app.logger.setLevel(getattr(logging, app.config['LOG_LEVEL']))

        security_logger = logging.getLogger('security')
        security_logger.addHandler(security_handler)
        security_logger.setLevel(logging.INFO)
        security_logger.propagate = False


def register_blueprints(app):
    from app.auth import bp as auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')

    from app.routes import main_bp
    app.register_blueprint(main_bp)

    from app.dashboard import dashboard_bp
    app.register_blueprint(dashboard_bp)

    from app.escala import escala_bp
    app.register_blueprint(escala_bp)

    from app.evento import evento_bp
    app.register_blueprint(evento_bp)

    from app.relatorio import relatorio_bp
    app.register_blueprint(relatorio_bp)

    from app.admin import admin_bp
    app.register_blueprint(admin_bp)

    from app.ocorrencia import ocorrencia_bp, viatura_bp
    app.register_blueprint(ocorrencia_bp)
    app.register_blueprint(viatura_bp)

    from app.api import api_bp
    app.register_blueprint(api_bp)

    from app.upload import upload_bp
    app.register_blueprint(upload_bp)

    from app.instagram import instagram_bp
    app.register_blueprint(instagram_bp)


def register_error_handlers(app):
    from flask import render_template, jsonify

    @app.errorhandler(400)
    def bad_request(e):
        if request.path.startswith('/api/'):
            return jsonify(error='Bad Request', message=str(e)), 400
        return render_template('errors/400.html'), 400

    @app.errorhandler(401)
    def unauthorized(e):
        if request.path.startswith('/api/'):
            return jsonify(error='Unauthorized', message='Authentication required'), 401
        return render_template('errors/401.html'), 401

    @app.errorhandler(403)
    def forbidden(e):
        if request.path.startswith('/api/'):
            return jsonify(error='Forbidden', message='Insufficient permissions'), 403
        return render_template('errors/403.html'), 403

    @app.errorhandler(404)
    def not_found(e):
        if request.path.startswith('/api/'):
            return jsonify(error='Not Found', message='Resource not found'), 404
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def internal_error(e):
        app.logger.error(f'Internal Server Error: {e}', exc_info=True)
        if request.path.startswith('/api/'):
            return jsonify(error='Internal Server Error', message='An unexpected error occurred'), 500
        return render_template('errors/500.html'), 500

    @app.errorhandler(413)
    def file_too_large(e):
        if request.path.startswith('/api/'):
            return jsonify(error='File Too Large', message='File exceeds maximum size'), 413
        return render_template('errors/413.html'), 413

    @app.errorhandler(429)
    def ratelimit_handler(e):
        app.logger.warning(f'Rate limit exceeded: {request.remote_addr} - {request.path}')
        if request.path.startswith('/api/'):
            return jsonify(error='Rate Limited', message='Too many requests'), 429
        return render_template('errors/429.html'), 429


def register_shell_context(app):
    @app.shell_context_processor
    def make_shell_context():
        from app import data as d
        return dict(data=d,
                    usuarios=d.usuarios,
                    org=d.org,
                    escala=d.escala_app,
                    ocorrencia=d.ocorrencia_data)


def register_template_filters(app):
    @app.template_filter('currency')
    def currency_filter(value):
        if value is None:
            return 'R$ 0,00'
        return f'R$ {value:,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.')

    @app.template_filter('date_br')
    def date_br_filter(value, fmt='%d/%m/%Y'):
        if value is None:
            return ''
        from datetime import datetime
        if isinstance(value, str):
            for f in ('%Y-%m-%d', '%d/%m/%Y', '%Y-%m-%d %H:%M:%S'):
                try:
                    return datetime.strptime(value[:19], f).strftime(fmt)
                except ValueError:
                    continue
            return value
        return value.strftime(fmt)

    @app.template_filter('datetime_br')
    def datetime_br_filter(value, fmt='%d/%m/%Y %H:%M'):
        if value is None:
            return ''
        from datetime import datetime
        if isinstance(value, str):
            for f in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M', '%Y-%m-%dT%H:%M:%S'):
                try:
                    return datetime.strptime(value[:19], f).strftime(fmt)
                except ValueError:
                    continue
            return value
        return value.strftime(fmt)

    @app.template_filter('ch_format')
    def ch_format_filter(value):
        if value is None:
            return '0h00'
        try:
            value = float(value)
        except (TypeError, ValueError):
            return '0h00'
        hours = int(value)
        minutes = int(round((value - hours) * 60))
        return f'{hours}h{minutes:02d}'

    @app.template_global()
    def current_year():
        from datetime import datetime
        return datetime.now().year


def register_request_hooks(app):
    @app.before_request
    def before_request():
        request.start_time = time.time()
        request.user_id = 'anonymous'
        from flask_login import current_user
        if current_user.is_authenticated:
            request.user_id = getattr(current_user, 'matricula', 'anonymous')

    @app.after_request
    def after_request(response):
        if hasattr(request, 'start_time'):
            duration = time.time() - request.start_time
            response.headers['X-Response-Time'] = f'{duration:.3f}s'
        return response


def register_jwt_callbacks(app):
    from flask import jsonify
    from flask_jwt_extended import get_jwt_identity

    @jwt.user_identity_loader
    def user_identity_lookup(user):
        if hasattr(user, 'matricula'):
            return str(user.matricula)
        if isinstance(user, dict):
            return str(user.get('matricula') or user.get('id') or user)
        return str(user)

    @jwt.user_lookup_loader
    def user_lookup_callback(_jwt_header, jwt_data):
        from app.auth.session import load_user_by_matricula
        identity = jwt_data["sub"]
        return load_user_by_matricula(identity)

    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        return jsonify(error='Token expired', message='Token has expired'), 401

    @jwt.invalid_token_loader
    def invalid_token_callback(error):
        return jsonify(error='Invalid token', message=error), 401

    @jwt.unauthorized_loader
    def missing_token_callback(error):
        return jsonify(error='Authorization required', message=error), 401

    @jwt.revoked_token_loader
    def revoked_token_callback(jwt_header, jwt_payload):
        return jsonify(error='Token revoked', message='Token has been revoked'), 401


def register_login_manager(app):
    # Plugin point for future CLI commands (e.g., firebase sync).
    pass