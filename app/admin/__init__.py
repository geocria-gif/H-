"""Blueprint admin: usuários, cargos, OPMs, tabela de valores, efetivo,
backup e logs do sistema."""
import json
import os
from datetime import datetime

from flask import (
    Blueprint, render_template, redirect, url_for, flash, request, current_app
)
from flask_login import login_required, current_user
from app import data as d
from app.data import base as b
from app.forms import UsuarioForm, CargoForm, TabelaValoresForm, EfetivoPMForm

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

BACKUP_COLLECTIONS = [
    'usuarios', 'cargos', 'opms', 'efetivopm', 'eventos', 'opm_eventos',
    'escalas', 'tabela_valores', 'escala_p2', 'escala_p2_meta',
    'escala_p2_legendas', 'ocorrencias', 'ocorrencia_eventos',
    'ocorrencia_meta', 'ocorrencia_config', 'municipios', 'viaturas',
    'escalas_salvas',
]


def _list_backups(backup_dir):
    backups = []
    for filename in os.listdir(backup_dir):
        path = os.path.join(backup_dir, filename)
        if os.path.isfile(path):
            stat = os.stat(path)
            backups.append({
                'filename': filename,
                'size': stat.st_size,
                'created': datetime.fromtimestamp(stat.st_ctime).isoformat()
            })
    return sorted(backups, key=lambda x: x['created'], reverse=True)


def _criar_backup(backup_dir):
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filepath = os.path.join(backup_dir, f'firestore_{timestamp}.json')
    payload = {}
    for collection in BACKUP_COLLECTIONS:
        docs = d.base.list_docs(collection)
        payload[collection] = [{'_id': doc.id, **doc.to_dict()} for doc in docs]
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(payload, f, ensure_ascii=False, indent=2, default=str)
    return filepath


def _efetivo_dados(form, incluir_matricula=True):
    dados = {
        'nome': form.nome.data,
        'cargo': form.cargo.data,
        'opm_id': form.opm_id.data,
        'sit': form.sit.data,
        'f6': form.f6.data,
        'cpf': form.cpf.data or None,
        'rg': form.rg.data or None,
        'titulo': form.titulo.data or None,
        'cnh': form.cnh.data or None,
        'categoria': form.categoria.data or None,
        'tipo_sanguineo': form.tipo_sanguineo.data or None,
        'funcao': form.funcao.data or None,
        'telefone': form.telefone.data or None,
        'admissao': form.admissao.data or None,
        'data_nascimento': form.data_nascimento.data or None,
        'local_trabalho': form.local_trabalho.data or None,
        'comportamento': form.comportamento.data,
    }
    if incluir_matricula:
        dados['matricula'] = form.matricula.data
    return dados


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
    usuarios = d.list_usuarios()
    for usuario in usuarios:
        if usuario.get('ativo') is None:
            usuario.update(ativo=True)
    total = len(usuarios)
    start = (page - 1) * 20
    items = usuarios[start:start + 20]
    pagination = b.Page(items, page, 20, total)
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
            matricula = form.matricula.data
            dados = {
                'matricula': matricula,
                'nome': form.nome.data,
                'tipo': form.tipo.data,
                'ativo': bool(form.ativo.data),
                'criado_em': datetime.utcnow().isoformat(),
                'ultimo_login': None,
            }
            d.create_auth_user(matricula, form.senha.data or '', form.nome.data, form.tipo.data)
            d.add_usuario(dados)
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

    matricula = str(id)
    usuario = d.get_usuario(matricula)
    if not usuario:
        flash('Usuário não encontrado.', 'danger')
        return redirect(url_for('admin.usuarios'))

    if usuario.get('ativo') is None:
        usuario.update(ativo=True)

    form = UsuarioForm(obj=usuario, user_id=id)

    if form.validate_on_submit():
        try:
            nova_matricula = str(form.matricula.data)
            dados = {
                'matricula': nova_matricula,
                'nome': form.nome.data,
                'tipo': form.tipo.data,
                'ativo': bool(form.ativo.data),
            }
            if nova_matricula != matricula:
                d.add_usuario(dados)
                d.delete_usuario(matricula)
            else:
                d.update_usuario(matricula, dados)
            d.update_auth_user(nova_matricula, nome=form.nome.data,
                               ativo=bool(form.ativo.data))
            if form.senha.data:
                d.reset_auth_password(nova_matricula, form.senha.data)
            flash('Usuário atualizado!', 'success')
            return redirect(url_for('admin.usuarios'))
        except Exception as e:
            flash(f'Erro: {str(e)}', 'danger')

    return render_template('admin/usuario_form.html', form=form, title='Editar Usuário')


@admin_bp.route('/usuarios/<int:id>/excluir', methods=['POST'])
@login_required
def excluir_usuario(id):
    if not current_user.is_admin:
        flash('Acesso negado.', 'danger')
        return redirect(url_for('dashboard.index'))

    if str(id) == current_user.get_id():
        flash('Não pode excluir a si mesmo.', 'danger')
        return redirect(url_for('admin.usuarios'))

    usuario = d.get_usuario(str(id))
    if usuario:
        d.delete_usuario(str(id))
        flash('Usuário excluído.', 'success')
    return redirect(url_for('admin.usuarios'))


@admin_bp.route('/cargos')
@login_required
def cargos():
    if not current_user.is_admin:
        flash('Acesso negado.', 'danger')
        return redirect(url_for('dashboard.index'))

    cargos = d.list_cargos()
    return render_template('admin/cargos.html', cargos=cargos)


@admin_bp.route('/cargos/novo', methods=['GET', 'POST'])
@login_required
def novo_cargo():
    if not current_user.is_admin:
        flash('Acesso negado.', 'danger')
        return redirect(url_for('dashboard.index'))

    form = CargoForm()

    if form.validate_on_submit():
        dados = {
            'cargo_id': form.cargo_id.data,
            'posto_grad': form.posto_grad.data,
            'tipo_servidor': form.tipo_servidor.data,
            'tipo_militar': form.tipo_militar.data,
            'classif_of': form.classif_of.data or None,
        }
        d.add_cargo(dados, form.cargo_id.data)
        flash('Cargo criado!', 'success')
        return redirect(url_for('admin.cargos'))

    return render_template('admin/cargo_form.html', form=form, title='Novo Cargo')


@admin_bp.route('/opms')
@login_required
def opms():
    if not current_user.is_admin:
        flash('Acesso negado.', 'danger')
        return redirect(url_for('dashboard.index'))

    opms = d.list_opms(order_by='opm_ordem')
    return render_template('admin/opms.html', opms=opms)


@admin_bp.route('/tabela-valores')
@login_required
def tabela_valores():
    if not current_user.is_supervisor:
        flash('Acesso negado.', 'danger')
        return redirect(url_for('dashboard.index'))

    valores = d.list_tabela_valores()
    return render_template('admin/tabela_valores.html', valores=valores)


@admin_bp.route('/tabela-valores/novo', methods=['GET', 'POST'])
@login_required
def novo_tabela_valor():
    if not current_user.is_supervisor:
        flash('Acesso negado.', 'danger')
        return redirect(url_for('dashboard.index'))

    form = TabelaValoresForm()

    if form.validate_on_submit():
        dados = {
            'posto_grad': form.posto_grad.data,
            'he_diurna': form.he_diurna.data,
            'ad_he_noturna': form.ad_he_noturna.data,
            'vd_diurno': form.vd_diurno.data,
            'vd_noturno': form.vd_noturno.data,
        }
        d.add_tabela_valor(dados)
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
    backup_dir = current_app.config['BACKUP_DIR']
    os.makedirs(backup_dir, exist_ok=True)
    backups = _list_backups(backup_dir)

    if form.validate_on_submit():
        try:
            filepath = _criar_backup(backup_dir)
            flash(f'Backup criado: {filepath}', 'success')
            backups = _list_backups(backup_dir)
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
            with open(path, 'r', encoding='utf-8', errors='replace') as f:
                lines = f.readlines()[-100:]
            logs[log_file] = lines
        else:
            logs[log_file] = ['Arquivo não encontrado']

    return render_template('admin/logs.html', logs=logs)


@admin_bp.route('/efetivo')
@login_required
def efetivo():
    if not current_user.is_supervisor:
        flash('Acesso negado.', 'danger')
        return redirect(url_for('dashboard.index'))

    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')
    opm_filter = request.args.get('opm', '')
    per_page = 30

    itens = d.list_all_efetivos()
    if search:
        term = search.lower()
        itens = [m for m in itens if term in (m.get('nome') or '').lower()
                 or term in (m.get('matricula') or '').lower()]
    if opm_filter:
        itens = [m for m in itens if str(m.get('opm_id')) == str(opm_filter)]

    total = len(itens)
    start = (page - 1) * per_page
    pagination = b.Page(itens[start:start + per_page], page, per_page, total)
    opms = d.list_opms()
    return render_template('admin/efetivo.html', pagination=pagination,
                           search=search, opm_filter=opm_filter, opms=opms)


@admin_bp.route('/efetivo/novo', methods=['GET', 'POST'])
@login_required
def novo_efetivo():
    if not current_user.is_supervisor:
        flash('Acesso negado.', 'danger')
        return redirect(url_for('dashboard.index'))

    form = EfetivoPMForm()

    if form.validate_on_submit():
        try:
            d.add_efetivo(_efetivo_dados(form), matricula=form.matricula.data)
            flash('Militar adicionado!', 'success')
            return redirect(url_for('admin.efetivo'))
        except Exception as e:
            flash(f'Erro: {str(e)}', 'danger')

    return render_template('admin/efetivo_form.html', form=form, title='Adicionar Militar')


@admin_bp.route('/efetivo/<matricula>/editar', methods=['GET', 'POST'])
@login_required
def editar_efetivo(matricula):
    if not current_user.is_supervisor:
        flash('Acesso negado.', 'danger')
        return redirect(url_for('dashboard.index'))

    efetivo = d.get_efetivo(matricula)
    if not efetivo:
        flash('Militar não encontrado.', 'danger')
        return redirect(url_for('admin.efetivo'))

    form = EfetivoPMForm(obj=efetivo)

    if form.validate_on_submit():
        try:
            d.update_efetivo(matricula, _efetivo_dados(form))
            flash('Militar atualizado!', 'success')
            return redirect(url_for('admin.efetivo'))
        except Exception as e:
            flash(f'Erro: {str(e)}', 'danger')

    return render_template('admin/efetivo_form.html', form=form,
                           title='Editar Militar', efetivo=efetivo)


@admin_bp.route('/efetivo/<matricula>/excluir', methods=['POST'])
@login_required
def excluir_efetivo(matricula):
    if not current_user.is_supervisor:
        flash('Acesso negado.', 'danger')
        return redirect(url_for('dashboard.index'))

    efetivo = d.get_efetivo(matricula)
    if efetivo:
        d.delete_efetivo(matricula)
        flash('Militar excluído.', 'success')
    return redirect(url_for('admin.efetivo'))