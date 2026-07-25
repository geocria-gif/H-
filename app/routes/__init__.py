from flask import Blueprint, redirect, url_for, current_app
from flask_login import current_user

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
    return redirect(url_for('auth.login'))


@main_bp.route('/health')
def health():
    return {'status': 'ok', 'service': 'SISPM'}, 200


@main_bp.route('/favicon.ico')
def favicon():
    return current_app.send_static_file('img/favicon.ico')
