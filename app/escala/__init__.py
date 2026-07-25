from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from sqlalchemy import extract
from app import db
from app.models import (
    Evento, OpmEvento, Escala, EfetivoPM, OPM, TabelaValores,
    EscalaP2, EscalaP2Meta, EscalaP2Legenda, EscalaSalva, EscalaSalvaItem, EscalaSalvaMeta
)
from app.forms import (
    EscalaForm, EscalaP2Form, EscalaP2MetaForm, EscalaP2LegendaForm,
    EscalaSalvaForm, EscalaSalvaItemForm, EscalaSalvaMetaForm
)
from app.services import escala_service, efetivo_service, escala_salva_service
from app.repository import efetivo_repo
import json
from datetime import date

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
    
    eventos = Evento.query.filter(
        extract('month', Evento.evento_dta_inicio) == mes,
        extract('year', Evento.evento_dta_inicio) == ano
    ).all()
    
    opms = OPM.query.order_by(OPM.opm_sigla).all()
    
    return render_template('escala/geral_mensal.html',
                           eventos=eventos,
                           opms=opms,
                           mes=mes, ano=ano)


@escala_bp.route('/adicionar-militar', methods=['GET', 'POST'])
@login_required
def adicionar_militar():
    form = EscalaForm()
    
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
                data=form.escala_data.data or '',
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


@escala_bp.route('/p2')
@login_required
def p2():
    mes = request.args.get('mes', type=int)
    ano = request.args.get('ano', type=int)
    
    query = db.select(EscalaP2).order_by(EscalaP2.ordem)
    if mes:
        query = query.where(EscalaP2.mes == mes)
    if ano:
        query = query.where(EscalaP2.ano == ano)
    
    escalas = db.session.execute(query).scalars().all()
    meta = EscalaP2Meta.query.first()
    legendas = EscalaP2Legenda.query.order_by(EscalaP2Legenda.codigo).all()
    
    effective_mes = mes or (meta.mes if meta else None)
    effective_ano = ano or (meta.ano if meta else None)
    
    weekdays = ['Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sab', 'Dom']
    dia_semanas = {}
    if effective_mes and effective_ano:
        import calendar
        max_day = calendar.monthrange(effective_ano, effective_mes)[1]
        for d in range(1, max_day + 1):
            try:
                dt = date(effective_ano, effective_mes, d)
                dia_semanas[d] = weekdays[dt.weekday()]
            except:
                pass
    
    return render_template('escala/p2.html',
                           escalas=escalas,
                           meta=meta,
                           legendas=legendas,
                           mes=mes, ano=ano,
                           dia_semanas=dia_semanas)


@escala_bp.route('/p2/novo', methods=['GET', 'POST'])
@login_required
def p2_novo():
    form = EscalaP2Form()
    legendas = EscalaP2Legenda.query.order_by(EscalaP2Legenda.codigo).all()
    if form.validate_on_submit():
        escala = EscalaP2()
        form.populate_obj(escala)
        dias = {}
        for d in range(1, 32):
            val = request.form.get(f'd_{d}', '').strip()
            if val:
                dias[str(d)] = val
        escala.dias = json.dumps(dias, ensure_ascii=False)
        db.session.add(escala)
        db.session.commit()
        flash('Item adicionado!', 'success')
        return redirect(url_for('escala.p2'))
    return render_template('escala/p2_form.html', form=form, legendas=legendas)


@escala_bp.route('/p2/<int:id>/editar', methods=['GET', 'POST'])
@login_required
def p2_editar(id):
    escala = db.session.get(EscalaP2, id)
    if not escala:
        flash('Não encontrado.', 'danger')
        return redirect(url_for('escala.p2'))
    
    form = EscalaP2Form(obj=escala)
    legendas = EscalaP2Legenda.query.order_by(EscalaP2Legenda.codigo).all()
    if form.validate_on_submit():
        form.populate_obj(escala)
        dias = {}
        for d in range(1, 32):
            val = request.form.get(f'd_{d}', '').strip()
            if val:
                dias[str(d)] = val
        escala.dias = json.dumps(dias, ensure_ascii=False)
        db.session.commit()
        flash('Atualizado!', 'success')
        return redirect(url_for('escala.p2'))
    return render_template('escala/p2_form.html', form=form, legendas=legendas, escala=escala)


@escala_bp.route('/p2/<int:id>/excluir', methods=['POST'])
@login_required
def p2_excluir(id):
    if not current_user.is_supervisor:
        flash('Acesso negado.', 'danger')
        return redirect(url_for('escala.p2'))
    
    escala = db.session.get(EscalaP2, id)
    if escala:
        db.session.delete(escala)
        db.session.commit()
        flash('Excluído!', 'success')
    return redirect(url_for('escala.p2'))


@escala_bp.route('/p2/meta', methods=['GET', 'POST'])
@login_required
def p2_meta():
    meta = EscalaP2Meta.query.first()
    if not meta:
        meta = EscalaP2Meta(id=1)
        db.session.add(meta)
        db.session.commit()
    
    form = EscalaP2MetaForm(obj=meta)
    if form.validate_on_submit():
        form.populate_obj(meta)
        db.session.commit()
        flash('Meta salva!', 'success')
        return redirect(url_for('escala.p2'))
    return render_template('escala/p2_meta.html', form=form)


@escala_bp.route('/p2/legenda', methods=['GET', 'POST'])
@login_required
def p2_legenda():
    legendas = EscalaP2Legenda.query.order_by(EscalaP2Legenda.codigo).all()
    form = EscalaP2LegendaForm()
    
    if form.validate_on_submit():
        legenda = EscalaP2Legenda()
        form.populate_obj(legenda)
        db.session.add(legenda)
        db.session.commit()
        flash('Legenda adicionada!', 'success')
        return redirect(url_for('escala.p2_legenda'))
    
    return render_template('escala/p2_legenda.html', legendas=legendas, form=form)


@escala_bp.route('/salvas')
@login_required
def salvas():
    page = request.args.get('page', 1, type=int)
    query = db.select(EscalaSalva).order_by(EscalaSalva.data_salva.desc())
    pagination = db.paginate(query, page=page, per_page=20, error_out=False)
    return render_template('escala/salvas.html', pagination=pagination)


@escala_bp.route('/salvas/nova', methods=['GET', 'POST'])
@login_required
def salvas_nova():
    form = EscalaSalvaForm()
    if form.validate_on_submit():
        escala = EscalaSalva(
            nome=form.nome.data,
            mes=form.mes.data,
            ano=form.ano.data
        )
        db.session.add(escala)
        db.session.commit()
        flash('Escala salva criada!', 'success')
        return redirect(url_for('escala.salvas_editar', id=escala.id))
    return render_template('escala/salvas_form.html', form=form)


@escala_bp.route('/salvas/<int:id>/editar', methods=['GET', 'POST'])
@login_required
def salvas_editar(id):
    escala = db.session.get(EscalaSalva, id)
    if not escala:
        flash('Não encontrada.', 'danger')
        return redirect(url_for('escala.salvas'))
    
    form = EscalaSalvaForm(obj=escala)
    itens = escala.itens
    meta = escala.meta
    
    if form.validate_on_submit():
        form.populate_obj(escala)
        db.session.commit()
        flash('Atualizada!', 'success')
    
    return render_template('escala/salvas_editar.html', 
                           escala=escala, form=form, itens=itens, meta=meta)


@escala_bp.route('/salvas/<int:id>/item/novo', methods=['GET', 'POST'])
@login_required
def salvas_item_novo(id):
    escala = db.session.get(EscalaSalva, id)
    if not escala:
        return redirect(url_for('escala.salvas'))
    
    form = EscalaSalvaItemForm()
    if form.validate_on_submit():
        item = EscalaSalvaItem(escala_salva_id=id)
        form.populate_obj(item)
        db.session.add(item)
        db.session.commit()
        flash('Item adicionado!', 'success')
        return redirect(url_for('escala.salvas_editar', id=id))
    return render_template('escala/salvas_item_form.html', form=form, escala=escala)


@escala_bp.route('/salvas/<int:escala_id>/item/<int:item_id>/editar', methods=['GET', 'POST'])
@login_required
def salvas_item_editar(escala_id, item_id):
    item = db.session.get(EscalaSalvaItem, item_id)
    if not item or item.escala_salva_id != escala_id:
        return redirect(url_for('escala.salvas_editar', id=escala_id))
    
    form = EscalaSalvaItemForm(obj=item)
    if form.validate_on_submit():
        form.populate_obj(item)
        db.session.commit()
        flash('Atualizado!', 'success')
        return redirect(url_for('escala.salvas_editar', id=escala_id))
    return render_template('escala/salvas_item_form.html', form=form, escala=item.escala_salva)


@escala_bp.route('/salvas/<int:escala_id>/item/<int:item_id>/excluir', methods=['POST'])
@login_required
def salvas_item_excluir(escala_id, item_id):
    item = db.session.get(EscalaSalvaItem, item_id)
    if item and item.escala_salva_id == escala_id:
        db.session.delete(item)
        db.session.commit()
        flash('Excluído!', 'success')
    return redirect(url_for('escala.salvas_editar', id=escala_id))


@escala_bp.route('/salvas/<int:id>/meta', methods=['GET', 'POST'])
@login_required
def salvas_meta(id):
    escala = db.session.get(EscalaSalva, id)
    if not escala:
        return redirect(url_for('escala.salvas'))
    
    meta = escala.meta
    if not meta:
        meta = EscalaSalvaMeta(escala_salva_id=id)
        db.session.add(meta)
        db.session.flush()
    
    form = EscalaSalvaMetaForm(obj=meta)
    if form.validate_on_submit():
        form.populate_obj(meta)
        db.session.commit()
        flash('Meta salva!', 'success')
        return redirect(url_for('escala.salvas_editar', id=id))
    
    return render_template('escala/salvas_meta.html', form=form, escala=escala)


@escala_bp.route('/salvas/<int:id>/ativar', methods=['POST'])
@login_required
def salvas_ativar(id):
    result = escala_salva_service.ativar_escala(id)
    if result:
        flash('Escala ativada!', 'success')
    else:
        flash('Erro ao ativar.', 'danger')
    return redirect(url_for('escala.salvas'))


@escala_bp.route('/salvas/<int:id>/carregar')
@login_required
def salvas_carregar(id):
    data = escala_salva_service.carregar_escala(id)
    if not data:
        flash('Escala não encontrada.', 'danger')
        return redirect(url_for('escala.salvas'))
    
    flash('Escala carregada! Redirecionando...', 'success')
    return redirect(url_for('escala.geral_mensal', mes=data['escala']['mes'], ano=data['escala']['ano']))


@escala_bp.route('/salvas/<int:id>/excluir', methods=['POST'])
@login_required
def salvas_excluir(id):
    if not current_user.is_admin:
        flash('Acesso negado.', 'danger')
        return redirect(url_for('escala.salvas'))
    
    escala = db.session.get(EscalaSalva, id)
    if escala:
        db.session.delete(escala)
        db.session.commit()
        flash('Excluída!', 'success')
    return redirect(url_for('escala.salvas'))