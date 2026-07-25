from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app import db
from app.models import Usuario, Cargo, OPM, TabelaValores, EfetivoPM
from app.forms import UsuarioForm, CargoForm, OPMForm, TabelaValoresForm
from app.services import backup_service
import os

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


@admin_bp.route('/')
@login_required
def index():
    if not current_user.is_admin:
        flash('Acesso negado.', 'danger')
        return redirect(url_for('dashboard.index'))
    return redirect(url_for('admin.usuarios'))


@admin_bp.route('/usuarios')
@login_required
def usuarios():
    if not current_user.is_admin:
        flash('Acesso negado.', 'danger')
        return redirect(url_for('dashboard.index'))
    
    page = request.args.get('page', 1, type=int)
    pagination = Usuario.query.order_by(Usuario.nome).paginate(page=page, per_page=20, error_out=False)
    return render_template('admin/usuarios.html', pagination=pagination)


@admin_bp.route('/usuarios/novo', methods=['GET', 'POST'])
@login_required
def novo_usuario():
    if not current_user.is_admin:
        flash('Acesso negado.', 'danger')
        return redirect(url_for('dashboard.index'))
    
    form = UsuarioForm()
    
    if form.validate_on_submit():
        try:
            usuario = Usuario(
                matricula=form.matricula.data,
                nome=form.nome.data,
                tipo=form.tipo.data,
                ativo=form.ativo.data
            )
            usuario.set_senha(form.senha.data)
            db.session.add(usuario)
            db.session.commit()
            flash('Usuário criado!', 'success')
            return redirect(url_for('admin.usuarios'))
        except Exception as e:
            flash(f'Erro: {str(e)}', 'danger')
    
    return render_template('admin/usuario_form.html', form=form, title='Novo Usuário')


@admin_bp.route('/usuarios/<int:id>/editar', methods=['GET', 'POST'])
@login_required
def editar_usuario(id):
    if not current_user.is_admin:
        flash('Acesso negado.', 'danger')
        return redirect(url_for('dashboard.index'))
    
    usuario = db.session.get(Usuario, id)
    if not usuario:
        flash('Usuário não encontrado.', 'danger')
        return redirect(url_for('admin.usuarios'))
    
    form = UsuarioForm(obj=usuario, user_id=id)
    
    if form.validate_on_submit():
        usuario.matricula = form.matricula.data
        usuario.nome = form.nome.data
        usuario.tipo = form.tipo.data
        usuario.ativo = form.ativo.data
        if form.senha.data:
            usuario.set_senha(form.senha.data)
        db.session.commit()
        flash('Usuário atualizado!', 'success')
        return redirect(url_for('admin.usuarios'))
    
    return render_template('admin/usuario_form.html', form=form, title='Editar Usuário')


@admin_bp.route('/usuarios/<int:id>/excluir', methods=['POST'])
@login_required
def excluir_usuario(id):
    if not current_user.is_admin:
        flash('Acesso negado.', 'danger')
        return redirect(url_for('dashboard.index'))
    
    if id == current_user.id:
        flash('Não pode excluir a si mesmo.', 'danger')
        return redirect(url_for('admin.usuarios'))
    
    usuario = db.session.get(Usuario, id)
    if usuario:
        db.session.delete(usuario)
        db.session.commit()
        flash('Usuário excluído.', 'success')
    return redirect(url_for('admin.usuarios'))


@admin_bp.route('/cargos')
@login_required
def cargos():
    if not current_user.is_admin:
        flash('Acesso negado.', 'danger')
        return redirect(url_for('dashboard.index'))
    
    cargos = Cargo.query.order_by(Cargo.posto_grad).all()
    return render_template('admin/cargos.html', cargos=cargos)


@admin_bp.route('/cargos/novo', methods=['GET', 'POST'])
@login_required
def novo_cargo():
    if not current_user.is_admin:
        flash('Acesso negado.', 'danger')
        return redirect(url_for('dashboard.index'))
    
    form = CargoForm()
    
    if form.validate_on_submit():
        cargo = Cargo(
            cargo_id=form.cargo_id.data,
            posto_grad=form.posto_grad.data,
            tipo_servidor=form.tipo_servidor.data,
            tipo_militar=form.tipo_militar.data,
            classif_of=form.classif_of.data
        )
        db.session.add(cargo)
        db.session.commit()
        flash('Cargo criado!', 'success')
        return redirect(url_for('admin.cargos'))
    
    return render_template('admin/cargo_form.html', form=form, title='Novo Cargo')


@admin_bp.route('/opms')
@login_required
def opms():
    if not current_user.is_admin:
        flash('Acesso negado.', 'danger')
        return redirect(url_for('dashboard.index'))
    
    opms = OPM.query.order_by(OPM.opm_ordem).all()
    return render_template('admin/opms.html', opms=opms)


@admin_bp.route('/tabela-valores')
@login_required
def tabela_valores():
    if not current_user.is_supervisor:
        flash('Acesso negado.', 'danger')
        return redirect(url_for('dashboard.index'))
    
    valores = TabelaValores.query.order_by(TabelaValores.posto_grad).all()
    return render_template('admin/tabela_valores.html', valores=valores)


@admin_bp.route('/tabela-valores/novo', methods=['GET', 'POST'])
@login_required
def novo_tabela_valor():
    if not current_user.is_supervisor:
        flash('Acesso negado.', 'danger')
        return redirect(url_for('dashboard.index'))
    
    form = TabelaValoresForm()
    
    if form.validate_on_submit():
        valor = TabelaValores(
            posto_grad=form.posto_grad.data,
            he_diurna=form.he_diurna.data,
            ad_he_noturna=form.ad_he_noturna.data,
            vd_diurno=form.vd_diurno.data,
            vd_noturno=form.vd_noturno.data
        )
        db.session.add(valor)
        db.session.commit()
        flash('Valor criado!', 'success')
        return redirect(url_for('admin.tabela_valores'))
    
    return render_template('admin/tabela_valor_form.html', form=form, title='Novo Valor')


@admin_bp.route('/backup', methods=['GET', 'POST'])
@login_required
def backup():
    if not current_user.is_admin:
        flash('Acesso negado.', 'danger')
        return redirect(url_for('dashboard.index'))
    
    from app.forms import BackupForm
    form = BackupForm()
    backups = backup_service.list_backups()
    
    if form.validate_on_submit():
        try:
            filepath = backup_service.backup_postgresql(current_app.config['SQLALCHEMY_DATABASE_URI'])
            flash(f'Backup criado: {filepath}', 'success')
            backups = backup_service.list_backups()
        except Exception as e:
            flash(f'Erro no backup: {str(e)}', 'danger')
    
    return render_template('admin/backup.html', form=form, backups=backups)


@admin_bp.route('/logs')
@login_required
def logs():
    if not current_user.is_admin:
        flash('Acesso negado.', 'danger')
        return redirect(url_for('dashboard.index'))
    
    log_files = ['access.log', 'error.log', 'database.log', 'security.log']
    logs = {}
    
    log_dir = current_app.config['LOG_DIR']
    for log_file in log_files:
        path = os.path.join(log_dir, log_file)
        if os.path.exists(path):
            with open(path, 'r') as f:
                lines = f.readlines()[-100:]
            logs[log_file] = lines
        else:
            logs[log_file] = ['Arquivo não encontrado']
    
    return render_template('admin/logs.html', logs=logs)