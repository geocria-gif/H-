from functools import wraps
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, current_app
from flask_login import login_user, logout_user, login_required, current_user
from flask_jwt_extended import (
    create_access_token, create_refresh_token,
    jwt_required, get_jwt_identity, get_jwt,
    verify_jwt_in_request
)
from werkzeug.security import generate_password_hash
from app import db, limiter
from app.models import Usuario
from app.forms import LoginForm, RegisterForm
from app.forms import (
    SearchForm, RelatorioForm, ImportForm, BackupForm, RestoreForm
)

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


@bp.route('/login', methods=['GET', 'POST'])
@limiter.limit('5 per minute')
def login():
    form = LoginForm()
    if form.validate_on_submit():
        matricula = form.matricula.data
        senha = form.senha.data
        remember = form.remember_me.data
        
        usuario = Usuario.query.filter_by(matricula=matricula).first()
        
        if usuario and usuario.check_senha(senha) and usuario.ativo:
            login_user(usuario, remember=remember)
            usuario.ultimo_login = db.func.now()
            db.session.commit()
            
            next_page = request.args.get('next')
            if not next_page or not next_page.startswith('/'):
                next_page = url_for('dashboard.index')
            
            flash(f'Bem-vindo, {usuario.nome}!', 'success')
            return redirect(next_page)
        else:
            flash('Matrícula ou senha inválidos.', 'danger')
    
    return render_template('auth/login.html', form=form)


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
            usuario = Usuario(
                matricula=form.matricula.data,
                nome=form.nome.data,
                tipo=form.tipo.data
            )
            usuario.set_senha(form.senha.data)
            db.session.add(usuario)
            db.session.commit()
            flash('Usuário criado com sucesso!', 'success')
            return redirect(url_for('admin.usuarios'))
        except Exception as e:
            db.session.rollback()
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
    
    form = PerfilForm(obj=current_user)
    if form.validate_on_submit():
        current_user.nome = form.nome.data
        if form.senha_atual.data and form.nova_senha.data:
            if current_user.check_senha(form.senha_atual.data):
                current_user.set_senha(form.nova_senha.data)
                flash('Senha alterada com sucesso!', 'success')
            else:
                flash('Senha atual incorreta.', 'danger')
                return render_template('auth/perfil.html', form=form)
        db.session.commit()
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
        usuario = Usuario.query.filter_by(matricula=form.matricula.data).first()
        if usuario:
            flash('Se a matrícula existir, um link de recuperação será enviado.', 'info')
        else:
            flash('Se a matrícula existir, um link de recuperação será enviado.', 'info')
    return render_template('auth/recuperar.html', form=form)


# API Auth endpoints
@bp.route('/api/login', methods=['POST'])
@limiter.limit('10 per minute')
def api_login():
    data = request.get_json()
    if not data or not data.get('matricula') or not data.get('senha'):
        return jsonify(error='Bad Request', message='Matrícula e senha são obrigatórios'), 400
    
    usuario = Usuario.query.filter_by(matricula=data['matricula']).first()
    
    if usuario and usuario.check_senha(data['senha']) and usuario.ativo:
        access_token = create_access_token(identity=usuario.id, additional_claims={
            'matricula': usuario.matricula,
            'nome': usuario.nome,
            'tipo': usuario.tipo
        })
        refresh_token = create_refresh_token(identity=usuario.id)
        
        return jsonify(
            access_token=access_token,
            refresh_token=refresh_token,
            user={
                'id': usuario.id,
                'matricula': usuario.matricula,
                'nome': usuario.nome,
                'tipo': usuario.tipo
            }
        ), 200
    
    return jsonify(error='Unauthorized', message='Credenciais inválidas'), 401


@bp.route('/api/refresh', methods=['POST'])
@jwt_required(refresh=True)
def api_refresh():
    current_user_id = get_jwt_identity()
    usuario = Usuario.query.get(current_user_id)
    if not usuario or not usuario.ativo:
        return jsonify(error='Unauthorized', message='Usuário inativo'), 401
    
    access_token = create_access_token(identity=usuario.id, additional_claims={
        'matricula': usuario.matricula,
        'nome': usuario.nome,
        'tipo': usuario.tipo
    })
    return jsonify(access_token=access_token), 200


@bp.route('/api/me', methods=['GET'])
@jwt_required()
def api_me():
    current_user_id = get_jwt_identity()
    usuario = Usuario.query.get(current_user_id)
    if not usuario:
        return jsonify(error='Not Found', message='Usuário não encontrado'), 404
    
    return jsonify(usuario.to_dict()), 200


@bp.route('/api/change-password', methods=['POST'])
@jwt_required()
def api_change_password():
    current_user_id = get_jwt_identity()
    usuario = Usuario.query.get(current_user_id)
    if not usuario:
        return jsonify(error='Not Found', message='Usuário não encontrado'), 404
    
    data = request.get_json()
    if not data or not data.get('senha_atual') or not data.get('nova_senha'):
        return jsonify(error='Bad Request', message='Senha atual e nova senha são obrigatórias'), 400
    
    if not usuario.check_senha(data['senha_atual']):
        return jsonify(error='Unauthorized', message='Senha atual incorreta'), 401
    
    usuario.set_senha(data['nova_senha'])
    db.session.commit()
    
    return jsonify(message='Senha alterada com sucesso'), 200