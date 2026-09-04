"""Instagram blueprint — Meta Graph API card publishing (Firestore-friendly).

Publishes institutional card images to the SEGMAF Instagram Business account.
The Meta Graph API client lives in ``app/services/instagram_service.py`` and
has no database dependency; it is loaded directly by file path so the
(now-dead) ``app/services`` package ``__init__`` is not executed.
"""
import os
import uuid
import importlib.util
import pathlib

from flask import Blueprint, render_template, redirect, url_for, flash, current_app, request, jsonify
from flask_login import login_required, current_user

from app.forms import InstagramForm

instagram_bp = Blueprint('instagram', __name__, url_prefix='/instagram')


def _load_instagram_service():
    """Load instagram_service.py directly, bypassing the dead services package."""
    module_path = pathlib.Path(__file__).resolve().parents[1] / 'services' / 'instagram_service.py'
    spec = importlib.util.spec_from_file_location('instagram_service', module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_instagram_module = _load_instagram_service()
instagram_service = _instagram_module.instagram_service
InstagramError = _instagram_module.InstagramError


@instagram_bp.route('/')
@login_required
def index():
    if not current_user.is_supervisor:
        flash('Acesso negado.', 'danger')
        return redirect(url_for('dashboard.index'))

    form = InstagramForm()
    status = instagram_service.get_status()
    public_base = current_app.config.get('PUBLIC_BASE_URL', '')
    return render_template('instagram/index.html', form=form, status=status,
                           public_base=public_base)


@instagram_bp.route('/publicar', methods=['POST'])
@login_required
def publicar():
    if not current_user.is_supervisor:
        flash('Acesso negado.', 'danger')
        return redirect(url_for('dashboard.index'))

    form = InstagramForm()
    if not form.validate_on_submit():
        for field, errors in form.errors.items():
            for error in errors:
                flash(f'{form[field].label.text}: {error}', 'danger')
        return redirect(url_for('instagram.index'))

    arquivo = form.imagem.data
    legenda = form.legenda.data or ''

    try:
        filepath = _salvar_imagem(arquivo)
        resultado = instagram_service.publish_image_file(filepath, legenda)
        flash(
            f'Publicado com sucesso! Media ID: {resultado["media_id"]}',
            'success'
        )
    except InstagramError as e:
        flash(f'Erro ao publicar: {e}', 'danger')
    except Exception as e:
        current_app.logger.exception('Erro ao publicar no Instagram')
        flash(f'Erro inesperado ao publicar: {e}', 'danger')

    return redirect(url_for('instagram.index'))


@instagram_bp.route('/status')
@login_required
def status():
    return jsonify(instagram_service.get_status())


def _salvar_imagem(arquivo) -> str:
    """Salva a imagem enviada em uploads/instagram/ e retorna o caminho."""
    from werkzeug.utils import secure_filename

    ext = os.path.splitext(arquivo.filename or '')[1].lower()
    if ext not in ('.png', '.jpg', '.jpeg'):
        raise InstagramError('A imagem deve ser PNG ou JPG.')

    insta_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'instagram')
    os.makedirs(insta_dir, exist_ok=True)

    nome = f'{uuid.uuid4().hex}{ext}'
    filepath = os.path.join(insta_dir, nome)
    arquivo.save(filepath)
    return filepath
