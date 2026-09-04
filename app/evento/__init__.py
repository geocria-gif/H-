"""Blueprint evento: gestão de eventos e das OPMs vinculadas."""
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app import data as d
from app.data import base as b
from app.forms import EventoForm

evento_bp = Blueprint('evento', __name__, url_prefix='/evento')


def _delete_opm_evento(oe):
    """Remove um vínculo OPM-evento e as escalas associadas (cascade)."""
    opm_evento_id = oe.get('opm_evento_id')
    if opm_evento_id is None:
        opm_evento_id = oe.id
    for esc in d.list_escalas_by_opm_evento(opm_evento_id):
        d.delete_escala(opm_evento_id, esc.get('matricula'), esc.get('escala_data'))
    d.delete_opm_evento(opm_evento_id)


@evento_bp.route('/')
@login_required
def index():
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')

    items = d.list_eventos()
    if search:
        termo = search.lower()
        items = [e for e in items if termo in (e.get('evento_desc') or '').lower()]
    items.sort(key=lambda e: e.get('evento_dta_inicio') or '', reverse=True)

    total = len(items)
    start = (page - 1) * 20
    pagination = b.Page(items[start:start + 20], page, 20, total)

    return render_template('evento/index.html',
                           pagination=pagination,
                           search=search)


@evento_bp.route('/novo', methods=['GET', 'POST'])
@login_required
def novo():
    form = EventoForm()
    opms = d.list_opms(order_by='opm_sigla')

    if form.validate_on_submit():
        opm_ids = request.form.getlist('opms')
        evento_id = d.next_evento_id()
        d.add_evento({
            'evento_id': evento_id,
            'evento_desc': form.evento_desc.data,
            'evento_dta_inicio': form.evento_dta_inicio.data,
            'evento_dta_fim': form.evento_dta_fim.data,
            'campo1': form.campo1.data,
            'tipo_pagamento': form.tipo_pagamento.data or 'HE'
        }, evento_id=evento_id)
        for opm_id in opm_ids:
            d.add_opm_evento({
                'opm_evento_id': d.next_opm_evento_id(),
                'evento_id': evento_id,
                'opm_id': opm_id
            })
        flash('Evento criado com sucesso!', 'success')
        return redirect(url_for('evento.index'))

    return render_template('evento/form.html', form=form, opms=opms, title='Novo Evento')


@evento_bp.route('/<int:id>/editar', methods=['GET', 'POST'])
@login_required
def editar(id):
    evento = d.get_evento_with_opms(id)
    if not evento:
        flash('Evento não encontrado.', 'danger')
        return redirect(url_for('evento.index'))

    form = EventoForm(obj=evento)
    opms = d.list_opms(order_by='opm_sigla')
    evento_opms = [oe.get('opm_id') for oe in (evento.get('opm_eventos') or [])]

    if form.validate_on_submit():
        opm_ids = request.form.getlist('opms')

        d.update_evento(id, {
            'evento_desc': form.evento_desc.data,
            'evento_dta_inicio': form.evento_dta_inicio.data,
            'evento_dta_fim': form.evento_dta_fim.data,
            'campo1': form.campo1.data,
            'tipo_pagamento': form.tipo_pagamento.data or 'HE'
        })

        opm_eventos = evento.get('opm_eventos') or []
        current_opms = set(evento_opms)
        new_opms = set(opm_ids)

        for opm_id in current_opms - new_opms:
            for oe in opm_eventos:
                if oe.get('opm_id') == opm_id:
                    _delete_opm_evento(oe)
        for opm_id in new_opms - current_opms:
            d.add_opm_evento({
                'opm_evento_id': d.next_opm_evento_id(),
                'evento_id': id,
                'opm_id': opm_id
            })

        flash('Evento atualizado!', 'success')
        return redirect(url_for('evento.index'))

    return render_template('evento/form.html', form=form, opms=opms, evento=evento,
                           evento_opms=evento_opms, title='Editar Evento')


@evento_bp.route('/<int:id>/excluir', methods=['POST'])
@login_required
def excluir(id):
    if not current_user.is_admin:
        flash('Acesso negado.', 'danger')
        return redirect(url_for('evento.index'))

    evento = d.get_evento(id)
    if evento:
        for oe in d.list_opm_eventos_by_evento(id):
            _delete_opm_evento(oe)
        d.delete_evento(id)
        flash('Evento excluído.', 'success')
    return redirect(url_for('evento.index'))


@evento_bp.route('/<int:id>/opms')
@login_required
def opms(id):
    evento = d.get_evento_with_opms(id)
    if not evento:
        return jsonify({'error': 'Evento não encontrado'}), 404

    result = []
    for oe in (evento.get('opm_eventos') or []):
        opm_rel = oe.get('opm_rel')
        result.append({'opm_id': oe.get('opm_id'),
                       'opm_sigla': opm_rel.get('opm_sigla') if opm_rel else ''})
    return jsonify(result)