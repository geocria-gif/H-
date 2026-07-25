from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_required, current_user
from sqlalchemy import func, desc
from app import db
from app.models import (
    Usuario, EfetivoPM, Cargo, OPM, Evento, OpmEvento, Escala,
    TabelaValores, EscalaP2, EscalaP2Meta, EscalaP2Legenda,
    Ocorrencia, Viatura, Municipio, EscalaSalva, EscalaSalvaItem, EscalaSalvaMeta
)
from app.forms import SearchForm, RelatorioForm, ImportForm, BackupForm, RestoreForm
from app.services import backup_service

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


# Dashboard Blueprint
dashboard_bp = Blueprint('dashboard', __name__, url_prefix='/dashboard')


@dashboard_bp.route('/')
@login_required
def index():
    # Estatísticas para cards
    stats = {
        'total_efetivos': EfetivoPM.query.count(),
        'total_eventos': Evento.query.count(),
        'total_ocorrencias': Ocorrencia.query.count(),
        'total_viaturas': Viatura.query.count(),
        'escalas_ativas': EscalaSalva.query.filter_by(ativa=1).count(),
    }
    
    # Ocorrências recentes
    ocorrencias_recentes = Ocorrencia.query.order_by(desc(Ocorrencia.data_hora)).limit(5).all()
    
    # Eventos próximos
    from datetime import date
    hoje = date.today().isoformat()
    eventos_proximos = Evento.query.filter(Evento.evento_dta_fim >= hoje).order_by(Evento.evento_dta_inicio).limit(5).all()
    
    # Ocorrências por tipo (para gráfico)
    ocorrencias_por_tipo = db.session.execute(
        db.select(Ocorrencia.tipo, func.count(Ocorrencia.id))
        .group_by(Ocorrencia.tipo)
    ).all()
    
    # Efetivos por OPM (para gráfico)
    efetivos_por_opm = db.session.execute(
        db.select(OPM.opm_sigla, func.count(EfetivoPM.matricula))
        .join(EfetivoPM, EfetivoPM.opm_id == OPM.opm_id)
        .group_by(OPM.opm_sigla)
    ).all()
    
    return render_template('dashboard/index.html',
                           stats=stats,
                           ocorrencias_recentes=ocorrencias_recentes,
                           eventos_proximos=eventos_proximos,
                           ocorrencias_por_tipo=ocorrencias_por_tipo,
                           efetivos_por_opm=efetivos_por_opm)


@dashboard_bp.route('/mapa')
@login_required
def mapa():
    ocorrencias = Ocorrencia.query.filter(
        Ocorrencia.latitude.isnot(None),
        Ocorrencia.longitude.isnot(None)
    ).all()
    return render_template('dashboard/mapa.html', ocorrencias=ocorrencias)


# Escala Blueprint
escala_bp = Blueprint('escala', __name__, url_prefix='/escala')


@escala_bp.route('/')
@login_required
def index():
    from datetime import date
    hoje = date.today()
    mes = request.args.get('mes', hoje.month, type=int)
    ano = request.args.get('ano', hoje.year, type=int)
    opm_id = request.args.get('opm_id', type=str)
    
    query = db.select(Escala).join(OpmEvento).join(Evento)
    if opm_id:
        query = query.join(OPM, OpmEvento.opm_id == OPM.opm_id).where(OPM.opm_id == opm_id)
    if mes:
        # Filter by month/year - need to check escala_data format
        pass
    
    escalas = db.session.execute(query.order_by(Escala.escala_data, Escala.matricula)).scalars().all()
    opms = OPM.query.order_by(OPM.opm_sigla).all()
    
    return render_template('escala/index.html',
                           escalas=escalas,
                           opms=opms,
                           mes=mes, ano=ano,
                           opm_id=opm_id)


@escala_bp.route('/geral-mensal')
@login_required
def geral_mensal():
    mes = request.args.get('mes', type=int)
    ano = request.args.get('ano', type=int)
    
    if not mes or not ano:
        from datetime import date
        hoje = date.today()
        mes = mes or hoje.month
        ano = ano or hoje.year
    
    # Get eventos for this month
    eventos = Evento.query.filter(
        db.extract('month', Evento.evento_dta_inicio) == mes,
        db.extract('year', Evento.evento_dta_inicio) == ano
    ).all()
    
    opms = OPM.query.order_by(OPM.opm_sigla).all()
    
    return render_template('escala/geral_mensal.html',
                           eventos=eventos,
                           opms=opms,
                           mes=mes, ano=ano)


@escala_bp.route('/adicionar-militar', methods=['GET', 'POST'])
@login_required
def adicionar_militar():
    from app.forms import EscalaForm
    from app.services import escala_service
    
    form = EscalaForm()
    
    # Populate OPM Evento choices
    opm_eventos = db.session.execute(
        db.select(OpmEvento).join(Evento).join(OPM)
        .order_by(Evento.evento_dta_inicio, OPM.opm_sigla)
    ).scalars().all()
    
    form.opm_evento_id.choices = [(0, 'Selecione...')] + [
        (oe.opm_evento_id, f'{oe.evento.evento_desc} - {oe.opm_rel.opm_sigla}')
        for oe in opm_eventos
    ]
    
    if form.validate_on_submit():
        try:
            escala = escala_service.salvar_escala(
                opm_evento_id=form.opm_evento_id.data,
                matricula=form.matricula.data,
                data=form.escala_data.data.isoformat() if form.escala_data.data else '',
                hora_inicio=form.hora_inicio.data or '',
                hora_fim=form.hora_fim.data or '',
                tipo_pagamento=form.tipo_pagamento.data
            )
            flash('Escala salva com sucesso!', 'success')
            return redirect(url_for('escala.geral_mensal'))
        except Exception as e:
            flash(f'Erro: {str(e)}', 'danger')
    
    return render_template('escala/adicionar_militar.html', form=form)


@escala_bp.route('/buscar-militar')
@login_required
def buscar_militar():
    termo = request.args.get('q', '')
    if len(termo) < 2:
        return jsonify([])
    
    militares = efetivo_service.buscar_por_matricula_ou_nome(termo)
    return jsonify([m.to_dict() for m in militares])


# Evento Blueprint
evento_bp = Blueprint('evento', __name__, url_prefix='/evento')


@evento_bp.route('/')
@login_required
def index():
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')
    
    query = db.select(Evento).order_by(desc(Evento.evento_dta_inicio))
    if search:
        query = query.where(Evento.evento_desc.ilike(f'%{search}%'))
    
    pagination = db.paginate(query, page=page, per_page=20, error_out=False)
    
    return render_template('evento/index.html',
                           pagination=pagination,
                           search=search)


@evento_bp.route('/novo', methods=['GET', 'POST'])
@login_required
def novo():
    from app.forms import EventoForm
    
    form = EventoForm()
    opms = OPM.query.order_by(OPM.opm_sigla).all()
    
    if form.validate_on_submit():
        opm_ids = request.form.getlist('opms')
        evento = evento_service.criar_com_opms({
            'evento_desc': form.evento_desc.data,
            'evento_dta_inicio': form.evento_dta_inicio.data.isoformat() if form.evento_dta_inicio.data else None,
            'evento_dta_fim': form.evento_dta_fim.data.isoformat() if form.evento_dta_fim.data else None,
            'campo1': form.campo1.data,
            'tipo_pagamento': form.tipo_pagamento.data
        }, opm_ids)
        flash('Evento criado com sucesso!', 'success')
        return redirect(url_for('evento.index'))
    
    return render_template('evento/form.html', form=form, opms=opms)


@evento_bp.route('/<int:id>/editar', methods=['GET', 'POST'])
@login_required
def editar(id):
    from app.forms import EventoForm
    
    evento = db.session.get(Evento, id)
    if not evento:
        flash('Evento não encontrado.', 'danger')
        return redirect(url_for('evento.index'))
    
    form = EventoForm(obj=evento)
    opms = OPM.query.order_by(OPM.opm_sigla).all()
    evento_opms = [oe.opm_id for oe in evento.opm_eventos]
    
    if form.validate_on_submit():
        opm_ids = request.form.getlist('opms')
        
        evento.evento_desc = form.evento_desc.data
        evento.evento_dta_inicio = form.evento_dta_inicio.data.isoformat() if form.evento_dta_inicio.data else None
        evento.evento_dta_fim = form.evento_dta_fim.data.isoformat() if form.evento_dta_fim.data else None
        evento.campo1 = form.campo1.data
        evento.tipo_pagamento = form.tipo_pagamento.data
        
        # Update OPMs
        current_opms = set(evento_opms)
        new_opms = set(opm_ids)
        
        for opm_id in current_opms - new_opms:
            evento_service.remover_opm(id, opm_id)
        for opm_id in new_opms - current_opms:
            evento_service.adicionar_opm(id, opm_id)
        
        db.session.commit()
        flash('Evento atualizado!', 'success')
        return redirect(url_for('evento.index'))
    
    return render_template('evento/form.html', form=form, opms=opms, evento=evento, evento_opms=evento_opms)


@evento_bp.route('/<int:id>/excluir', methods=['POST'])
@login_required
def excluir(id):
    if not current_user.is_admin:
        flash('Acesso negado.', 'danger')
        return redirect(url_for('evento.index'))
    
    evento = db.session.get(Evento, id)
    if evento:
        db.session.delete(evento)
        db.session.commit()
        flash('Evento excluído.', 'success')
    return redirect(url_for('evento.index'))


# Relatório Blueprint
relatorio_bp = Blueprint('relatorio', __name__, url_prefix='/relatorio')


@relatorio_bp.route('/')
@login_required
def index():
    from app.forms import RelatorioForm
    from app.services import escala_service, tabela_valores_service, efetivo_service
    
    form = RelatorioForm()
    relatorio = None
    
    if form.validate_on_submit() or request.args.get('gerar'):
        mes = form.mes.data or request.args.get('mes', type=int)
        ano = form.ano.data or request.args.get('ano', type=int)
        tipo_pagamento = form.tipo_pagamento.data or request.args.get('tipo_pagamento')
        opm_id = form.opm_id.data or request.args.get('opm_id')
        
        if mes and ano:
            # Get eventos for this month
            eventos = Evento.query.filter(
                db.extract('month', Evento.evento_dta_inicio) == mes,
                db.extract('year', Evento.evento_dta_inicio) == ano
            ).all()
            
            relatorio = []
            for evento in eventos:
                if opm_id:
                    opm_eventos = OpmEvento.query.filter_by(evento_id=evento.evento_id, opm_id=opm_id).all()
                else:
                    opm_eventos = evento.opm_eventos
                
                for oe in opm_eventos:
                    dados = escala_service.get_relatorio_horas(evento.evento_id, tipo_pagamento)
                    for row in dados:
                        militar = efetivo_service.repo.get_by_matricula(row['matricula'])
                        if militar and (not opm_id or militar.opm_id == opm_id):
                            valor = tabela_valores_service.calcular_valor_militar(
                                militar, row['ch_diurna'] or 0, row['ch_noturna'] or 0,
                                tipo_pagamento or 'HE'
                            )
                            relatorio.append({
                                'evento': evento.evento_desc,
                                'opm': oe.opm_rel.opm_sigla if oe.opm_rel else '',
                                'matricula': row['matricula'],
                                'nome': row['nome'],
                                'posto': row['cargo'],
                                'ch_diurna': row['ch_diurna'],
                                'ch_noturna': row['ch_noturna'],
                                'dias': row['dias'],
                                'tipo_pagamento': tipo_pagamento or 'HE/VD/SO',
                                'valor': valor
                            })
    
    return render_template('relatorio/index.html', form=form, relatorio=relatorio)


@relatorio_bp.route('/exportar')
@login_required
def exportar():
    from app.services import escala_service
    from flask import make_response
    
    mes = request.args.get('mes', type=int)
    ano = request.args.get('ano', type=int)
    tipo_pagamento = request.args.get('tipo_pagamento')
    opm_id = request.args.get('opm_id')
    
    # Get first evento for this period
    evento = Evento.query.filter(
        db.extract('month', Evento.evento_dta_inicio) == mes,
        db.extract('year', Evento.evento_dta_inicio) == ano
    ).first()
    
    if evento:
        csv_content = escala_service.exportar_csv(evento.evento_id, tipo_pagamento)
        response = make_response(csv_content)
        response.headers['Content-Type'] = 'text/csv; charset=utf-8'
        response.headers['Content-Disposition'] = f'attachment; filename=relatorio_{mes}_{ano}.csv'
        return response
    
    flash('Nenhum evento encontrado para o período.', 'warning')
    return redirect(url_for('relatorio.index'))


# Admin Blueprint
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
    
    from app.forms import UsuarioForm
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
    
    from app.forms import UsuarioForm
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
    
    from app.forms import CargoForm
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
    
    from app.forms import TabelaValoresForm
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
    
    form = BackupForm()
    from app.services import backup_service
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
                lines = f.readlines()[-100:]  # Last 100 lines
            logs[log_file] = lines
        else:
            logs[log_file] = ['Arquivo não encontrado']
    
    return render_template('admin/logs.html', logs=logs)


import os
from flask import jsonify

# Ocorrência Blueprint
ocorrencia_bp = Blueprint('ocorrencia', __name__, url_prefix='/ocorrencia')


@ocorrencia_bp.route('/')
@login_required
def index():
    page = request.args.get('page', 1, type=int)
    tipo = request.args.get('tipo')
    data_inicio = request.args.get('data_inicio')
    data_fim = request.args.get('data_fim')
    
    query = db.select(Ocorrencia).order_by(desc(Ocorrencia.data_hora))
    
    if tipo:
        query = query.where(Ocorrencia.tipo == tipo)
    if data_inicio:
        query = query.where(Ocorrencia.data_hora >= data_inicio)
    if data_fim:
        query = query.where(Ocorrencia.data_hora <= data_fim)
    
    pagination = db.paginate(query, page=page, per_page=20, error_out=False)
    
    return render_template('ocorrencia/index.html',
                           pagination=pagination,
                           tipo=tipo,
                           data_inicio=data_inicio,
                           data_fim=data_fim)


@ocorrencia_bp.route('/nova', methods=['GET', 'POST'])
@login_required
def nova():
    from app.forms import OcorrenciaForm
    
    form = OcorrenciaForm()
    
    if form.validate_on_submit():
        ocorrencia = Ocorrencia(
            tipo=form.tipo.data,
            data_hora=form.data_hora.data,
            cidade=form.cidade.data,
            latitude=form.latitude.data,
            longitude=form.longitude.data,
            vtr=form.vtr.data,
            descricao=form.descricao.data,
            dados_relevantes=form.dados_relevantes.data
        )
        db.session.add(ocorrencia)
        db.session.commit()
        flash('Ocorrência registrada!', 'success')
        return redirect(url_for('ocorrencia.index'))
    
    return render_template('ocorrencia/form.html', form=form)


@ocorrencia_bp.route('/mapa')
@login_required
def mapa():
    ocorrencias = Ocorrencia.query.filter(
        Ocorrencia.latitude.isnot(None),
        Ocorrencia.longitude.isnot(None)
    ).all()
    return render_template('ocorrencia/mapa.html', ocorrencias=ocorrencias)


@ocorrencia_bp.route('/estatisticas')
@login_required
def estatisticas():
    from app.services import ocorrencia_service
    
    data_inicio = request.args.get('data_inicio')
    data_fim = request.args.get('data_fim')
    
    stats = ocorrencia_service.get_estatisticas(data_inicio, data_fim)
    return render_template('ocorrencia/estatisticas.html', stats=stats)


# Viatura Blueprint
viatura_bp = Blueprint('viatura', __name__, url_prefix='/viatura')


@viatura_bp.route('/')
@login_required
def index():
    page = request.args.get('page', 1, type=int)
    situacao = request.args.get('situacao')
    municipio = request.args.get('municipio')
    
    query = db.select(Viatura).order_by(Viatura.prefixo)
    if situacao:
        query = query.where(Viatura.situacao == situacao)
    if municipio:
        query = query.where(Viatura.municipio == municipio)
    
    pagination = db.paginate(query, page=page, per_page=20, error_out=False)
    
    situacoes = db.session.execute(db.select(Viatura.situacao).distinct()).scalars().all()
    municipios = db.session.execute(db.select(Viatura.municipio).distinct()).scalars().all()
    
    return render_template('viatura/index.html',
                           pagination=pagination,
                           situacoes=situacoes,
                           municipios=municipios,
                           situacao=situacao,
                           municipio=municipio)


@viatura_bp.route('/nova', methods=['GET', 'POST'])
@login_required
def nova():
    if not current_user.is_supervisor:
        flash('Acesso negado.', 'danger')
        return redirect(url_for('viatura.index'))
    
    from app.forms import ViaturaForm
    form = ViaturaForm()
    
    if form.validate_on_submit():
        viatura = Viatura()
        for field in form:
            if field.name != 'submit' and field.name != 'csrf_token':
                setattr(viatura, field.name, field.data)
        db.session.add(viatura)
        db.session.commit()
        flash('Viaturada cadastrada!', 'success')
        return redirect(url_for('viatura.index'))
    
    return render_template('viatura/form.html', form=form, title='Nova Viatura')


@viatura_bp.route('/<prefixo>/editar', methods=['GET', 'POST'])
@login_required
def editar(prefixo):
    if not current_user.is_supervisor:
        flash('Acesso negado.', 'danger')
        return redirect(url_for('viatura.index'))
    
    from app.forms import ViaturaForm
    viatura = db.session.get(Viatura, prefixo)
    if not viatura:
        flash('Viaturada não encontrada.', 'danger')
        return redirect(url_for('viatura.index'))
    
    form = ViaturaForm(obj=viatura)
    
    if form.validate_on_submit():
        for field in form:
            if field.name != 'submit' and field.name != 'csrf_token':
                setattr(viatura, field.name, field.data)
        db.session.commit()
        flash('Viaturada atualizada!', 'success')
        return redirect(url_for('viatura.index'))
    
    return render_template('viatura/form.html', form=form, title='Editar Viatura')


# Upload Blueprint
upload_bp = Blueprint('upload', __name__, url_prefix='/upload')


@upload_bp.route('/')
@login_required
def index():
    if not current_user.is_supervisor:
        flash('Acesso negado.', 'danger')
        return redirect(url_for('dashboard.index'))
    
    from app.forms import ImportForm
    form = ImportForm()
    return render_template('upload/index.html', form=form)


@upload_bp.route('/importar', methods=['POST'])
@login_required
def importar():
    if not current_user.is_supervisor:
        flash('Acesso negado.', 'danger')
        return redirect(url_for('dashboard.index'))
    
    from app.forms import ImportForm
    from app.services import upload_service, efetivo_service
    import csv
    import io
    
    form = ImportForm()
    if form.validate_on_submit():
        arquivo = form.arquivo.data
        tipo = form.tipo.data
        
        try:
            filepath = upload_service.save_file(arquivo, 'imports')
            
            if tipo == 'efetivo':
                stats = efetivo_service.importar_csv(filepath)
                flash(f'Importação concluída: {stats["criados"]} criados, {stats["atualizados"]} atualizados, {stats["erros"]} erros', 'success')
            
            # Clean up
            upload_service.delete_file(filepath)
        except Exception as e:
            flash(f'Erro na importação: {str(e)}', 'danger')
    
    return redirect(url_for('upload.index'))