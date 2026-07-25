from flask import Blueprint, redirect, url_for, send_file, Response
from flask_login import current_user
import os

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
    return redirect(url_for('auth.login'))


@main_bp.route('/health')
def health():
    return {'status': 'ok', 'service': 'SISPM'}, 200


FAVICON_SVG = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
<rect width="100" height="100" rx="15" fill="#1a365d"/>
<text x="50" y="68" font-family="Arial,sans-serif" font-size="42" font-weight="bold" fill="#ffd700" text-anchor="middle">SPM</text>
</svg>'''


@main_bp.route('/favicon.ico')
def favicon():
    favicon_path = os.path.join(os.path.dirname(__file__), '..', 'static', 'img', 'favicon.ico')
    if os.path.exists(favicon_path):
        return send_file(favicon_path, mimetype='image/x-icon')
    return Response(FAVICON_SVG, mimetype='image/svg+xml')
