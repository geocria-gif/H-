from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app import db
from app.models import Evento, OpmEvento, OPM
from app.forms import EventoForm, OpmEventoForm
from app.services import evento_service

evento_bp = Blueprint('evento', __name__, url_prefix='/evento')


@evento_bp.route('/')
@login_required
def index():
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')
    
    query = db.select(Evento).order_by(Evento.evento_dta_inicio.desc())
    if search:
        query = query.where(Evento.evento_desc.ilike(f'%{search}%'))
    
    pagination = db.paginate(query, page=page, per_page=20, error_out=False)
    
    return render_template('evento/index.html',
                           pagination=pagination,
                           search=search)


@evento_bp.route('/novo', methods=['GET', 'POST'])
@login_required
def novo():
    form = EventoForm()
    opms = OPM.query.order_by(OPM.opm_sigla).all()
    
    if form.validate_on_submit():
        opm_ids = request.form.getlist('opms')
        evento = evento_service.criar_com_opms({
            'evento_desc': form.evento_desc.data,
            'evento_dta_inicio': form.evento_dta_inicio.data,
            'evento_dta_fim': form.evento_dta_fim.data,
            'campo1': form.campo1.data,
            'tipo_pagamento': form.tipo_pagamento.data
        }, opm_ids)
        flash('Evento criado com sucesso!', 'success')
        return redirect(url_for('evento.index'))
    
    return render_template('evento/form.html', form=form, opms=opms, title='Novo Evento')


@evento_bp.route('/<int:id>/editar', methods=['GET', 'POST'])
@login_required
def editar(id):
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
        evento.evento_dta_inicio = form.evento_dta_inicio.data
        evento.evento_dta_fim = form.evento_dta_fim.data
        evento.campo1 = form.campo1.data
        evento.tipo_pagamento = form.tipo_pagamento.data
        
        current_opms = set(evento_opms)
        new_opms = set(opm_ids)
        
        for opm_id in current_opms - new_opms:
            evento_service.remover_opm(id, opm_id)
        for opm_id in new_opms - current_opms:
            evento_service.adicionar_opm(id, opm_id)
        
        db.session.commit()
        flash('Evento atualizado!', 'success')
        return redirect(url_for('evento.index'))
    
    return render_template('evento/form.html', form=form, opms=opms, evento=evento, evento_opms=evento_opms, title='Editar Evento')


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


@evento_bp.route('/<int:id>/opms')
@login_required
def opms(id):
    evento = db.session.get(Evento, id)
    if not evento:
        return jsonify({'error': 'Evento não encontrado'}), 404
    
    opms = [{'opm_id': oe.opm_id, 'opm_sigla': oe.opm_rel.opm_sigla if oe.opm_rel else ''} 
            for oe in evento.opm_eventos]
    return jsonify(opms)