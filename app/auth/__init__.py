from functools import wraps
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, current_app
from flask_login import login_user, logout_user, login_required, current_user
from flask_jwt_extended import (
    create_access_token, create_refresh_token,
    jwt_required, get_jwt_identity, get_jwt,
    verify_jwt_in_request
)
import requests

from app import limiter
from app import data as d
from app.forms import LoginForm, RegisterForm
from app.auth.session import FireUser, load_user_by_matricula, load_user_by_uid

bp = Blueprint('auth', __name__, url_prefix='/auth')


def role_required(*roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for('auth.login', next=request.url))
            if current_user.tipo not in roles:
                flash('Acesso negado. Permissão insuficiente.', 'danger')
                return redirect(url_for('main.index'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def api_role_required(*roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            verify_jwt_in_request()
            claims = get_jwt()
            user_type = claims.get('tipo', 'USER')
            if user_type not in roles:
                return jsonify(error='Forbidden', message='Insufficient permissions'), 403
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def _verify_with_password(matricula, senha):
    """Server-side Firebase sign-in via Identity Toolkit REST API.

    Requires FIREBASE_WEB_API_KEY to be configured. Returns uid on success
    or None."""
    api_key = current_app.config.get('FIREBASE_WEB_API_KEY')
    if not api_key:
        return None
    email = d.auth_email(matricula)
    url = f'https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={api_key}'
    try:
        resp = requests.post(url, json={
            'email': email,
            'password': senha,
            'returnSecureToken': True,
        }, timeout=10)
        if resp.status_code != 200:
            return None
        payload = resp.json()
        return payload.get('idToken')
    except requests.RequestException:
        return None


def _login_by_token(id_token, remember=False):
    claims = d.verify_id_token(id_token)
    if not claims:
        return None
    user = load_user_by_uid(claims.get('uid'))
    if user is None or not user.is_active:
        return None
    user._id_token = id_token
    login_user(user, remember=remember)
    if user.matricula:
        d.touch_ultimo_login(user.matricula)
    return user


def _login_by_credentials(matricula, senha, remember=False):
    id_token = _verify_with_password(matricula, senha)
    if not id_token:
        return None
    return _login_by_token(id_token, remember)


@bp.route('/login', methods=['GET', 'POST'])
@limiter.limit('20 per minute')
def login():
    form = LoginForm()
    if form.validate_on_submit():
        matricula = form.matricula.data
        senha = form.senha.data
        remember = form.remember_me.data

        id_token = form.id_token.data or (request.form.get('id_token') or '')
        user = None
        if id_token:
            user = _login_by_token(id_token, remember)
        else:
            user = _login_by_credentials(matricula, senha, remember)

        if user:
            next_page = request.args.get('next')
            if not next_page or not next_page.startswith('/'):
                next_page = url_for('dashboard.index')
            flash(f'Bem-vindo, {user.nome}!', 'success')
            return redirect(next_page)
        flash('Matrícula ou senha inválidos.', 'danger')

    return render_template('auth/login.html', form=form,
                           firebase_config=current_app.config.get('FIREBASE_WEB_CONFIG'))


@bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Você saiu do sistema.', 'info')
    return redirect(url_for('auth.login'))


@bp.route('/register', methods=['GET', 'POST'])
@login_required
@role_required('ADMIN')
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        try:
            d.create_auth_user(
                matricula=form.matricula.data,
                senha=form.senha.data,
                nome=form.nome.data,
                tipo=form.tipo.data,
            )
            d.add_usuario({
                'matricula': form.matricula.data,
                'nome': form.nome.data,
                'tipo': form.tipo.data,
                'ativo': True,
                'senha': '',
                'criado_em': None,
                'ultimo_login': None,
            })
            flash('Usuário criado com sucesso!', 'success')
            return redirect(url_for('admin.usuarios'))
        except Exception as e:
            flash(f'Erro ao criar usuário: {str(e)}', 'danger')
    return render_template('auth/register.html', form=form)


@bp.route('/perfil', methods=['GET', 'POST'])
@login_required
def perfil():
    from app.forms import FlaskForm
    from wtforms import StringField, PasswordField, SubmitField
    from wtforms.validators import DataRequired, Length, Optional, EqualTo

    class PerfilForm(FlaskForm):
        nome = StringField('Nome', validators=[DataRequired(), Length(max=200)])
        senha_atual = PasswordField('Senha Atual', validators=[Optional(), Length(min=6)])
        nova_senha = PasswordField('Nova Senha', validators=[Optional(), Length(min=6), EqualTo('confirmar_senha')])
        confirmar_senha = PasswordField('Confirmar Nova Senha', validators=[Optional()])
        submit = SubmitField('Atualizar')

    form = PerfilForm()
    form.nome.data = current_user.nome
    if form.validate_on_submit():
        if current_user.matricula:
            d.update_usuario(current_user.matricula, {'nome': form.nome.data})
        if form.senha_atual.data and form.nova_senha.data:
            token = _verify_with_password(current_user.matricula, form.senha_atual.data)
            if token:
                d.reset_auth_password(current_user.matricula, form.nova_senha.data)
                flash('Senha alterada com sucesso!', 'success')
            else:
                flash('Senha atual incorreta.', 'danger')
                return render_template('auth/perfil.html', form=form)
        flash('Perfil atualizado!', 'success')
        return redirect(url_for('auth.perfil'))
    return render_template('auth/perfil.html', form=form)


@bp.route('/recuperar', methods=['GET', 'POST'])
def recuperar_senha():
    from app.forms import FlaskForm
    from wtforms import StringField, SubmitField
    from wtforms.validators import DataRequired

    class RecuperarForm(FlaskForm):
        matricula = StringField('Matrícula', validators=[DataRequired()])
        submit = SubmitField('Enviar Link')

    form = RecuperarForm()
    if form.validate_on_submit():
        flash('Se a matrícula existir, um link de recuperação será enviado.', 'info')
    return render_template('auth/recuperar.html', form=form)


# ---------------------------------------------------------------------------
# API Auth endpoints
# ---------------------------------------------------------------------------
@bp.route('/api/login', methods=['POST'])
@limiter.limit('10 per minute')
def api_login():
    data = request.get_json(silent=True) or {}
    matricula = data.get('matricula')
    senha = data.get('senha')
    if not matricula or not senha:
        return jsonify(error='Bad Request', message='Matrícula e senha são obrigatórios'), 400

    id_token = data.get('id_token')
    user = None
    if id_token:
        claims = d.verify_id_token(id_token)
        if claims:
            user = load_user_by_uid(claims.get('uid'))
    else:
        token = _verify_with_password(matricula, senha)
        if token:
            claims = d.verify_id_token(token)
            if claims:
                user = load_user_by_uid(claims.get('uid'))

    if user and user.is_active:
        access_token = create_access_token(identity=user.matricula, additional_claims={
            'matricula': user.matricula,
            'nome': user.nome,
            'tipo': user.tipo
        })
        refresh_token = create_refresh_token(identity=user.matricula)
        if user.matricula:
            d.touch_ultimo_login(user.matricula)
        return jsonify(
            access_token=access_token,
            refresh_token=refresh_token,
            user=user.to_dict()
        ), 200

    return jsonify(error='Unauthorized', message='Credenciais inválidas'), 401


@bp.route('/api/refresh', methods=['POST'])
@jwt_required(refresh=True)
def api_refresh():
    matricula = get_jwt_identity()
    user = load_user_by_matricula(matricula)
    if not user or not user.is_active:
        return jsonify(error='Unauthorized', message='Usuário inativo'), 401
    access_token = create_access_token(identity=user.matricula, additional_claims={
        'matricula': user.matricula,
        'nome': user.nome,
        'tipo': user.tipo
    })
    return jsonify(access_token=access_token), 200


@bp.route('/api/me', methods=['GET'])
@jwt_required()
def api_me():
    matricula = get_jwt_identity()
    user = load_user_by_matricula(matricula)
    if not user:
        return jsonify(error='Not Found', message='Usuário não encontrado'), 404
    return jsonify(user.to_dict()), 200


@bp.route('/api/change-password', methods=['POST'])
@jwt_required()
def api_change_password():
    matricula = get_jwt_identity()
    user = load_user_by_matricula(matricula)
    if not user:
        return jsonify(error='Not Found', message='Usuário não encontrado'), 404
    data = request.get_json(silent=True) or {}
    if not data.get('senha_atual') or not data.get('nova_senha'):
        return jsonify(error='Bad Request', message='Senha atual e nova senha são obrigatórias'), 400
    token = _verify_with_password(matricula, data['senha_atual'])
    if not token:
        return jsonify(error='Unauthorized', message='Senha atual incorreta'), 401
    d.reset_auth_password(matricula, data['nova_senha'])
    return jsonify(message='Senha alterada com sucesso'), 200