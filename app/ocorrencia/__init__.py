"""Blueprints ocorrencia e viatura: registro, mapa, estatísticas e frota."""
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from datetime import datetime
from app import data as d
from app.data import base as b
from app.forms import OcorrenciaForm, ViaturaForm

ocorrencia_bp = Blueprint('ocorrencia', __name__, url_prefix='/ocorrencia')


def _to_iso_hora(value):
    """Normaliza data/hora (DD/MM/AAAA HH:MM:SS etc.) para ISO (YYYY-MM-DDTHH:MM:SS)."""
    if not value:
        return value
    value = str(value).strip()
    for fmt in ('%Y-%m-%dT%H:%M:%S', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M',
                '%d/%m/%Y %H:%M:%S', '%d/%m/%Y %H:%M', '%Y-%m-%d'):
        try:
            return datetime.strptime(value, fmt).strftime('%Y-%m-%dT%H:%M:%S')
        except ValueError:
            continue
    return value


def _get_estatisticas(data_inicio=None, data_fim=None):
    docs = []
    for o in d.list_all_ocorrencias():
        hora = o.get('data_hora') or ''
        if data_inicio and hora < data_inicio:
            continue
        if data_fim and hora > data_fim:
            continue
        docs.append(o)

    stats = {'total': len(docs), 'por_tipo': {}, 'por_cidade': {}, 'por_mes': {}}
    for o in docs:
        tipo = o.get('tipo') or 'OUTRO'
        stats['por_tipo'][tipo] = stats['por_tipo'].get(tipo, 0) + 1
        cidade = o.get('cidade')
        if cidade:
            stats['por_cidade'][cidade] = stats['por_cidade'].get(cidade, 0) + 1
        mes = (o.get('data_hora') or '')[:7]
        if mes:
            stats['por_mes'][mes] = stats['por_mes'].get(mes, 0) + 1

    stats['por_periodo'] = stats['por_mes']
    stats['acidentes'] = stats['por_tipo'].get('ACIDENTE', 0)
    stats['roubos'] = (stats['por_tipo'].get('ROUBO', 0) +
                       stats['por_tipo'].get('ASSALTO', 0))
    stats['outros'] = stats['total'] - stats['acidentes'] - stats['roubos']
    return stats


@ocorrencia_bp.route('/')
@login_required
def index():
    page = request.args.get('page', 1, type=int)
    tipo = request.args.get('tipo')
    data_inicio = request.args.get('data_inicio')
    data_fim = request.args.get('data_fim')

    pagination = d.list_ocorrencias(page=page, per_page=20, tipo=tipo,
                                    data_inicio=data_inicio, data_fim=data_fim)

    return render_template('ocorrencia/index.html',
                           pagination=pagination,
                           tipo=tipo,
                           data_inicio=data_inicio,
                           data_fim=data_fim)


@ocorrencia_bp.route('/nova', methods=['GET', 'POST'])
@login_required
def nova():
    form = OcorrenciaForm()

    if form.validate_on_submit():
        d.add_ocorrencia({
            'id': d.next_ocorrencia_id(),
            'tipo': form.tipo.data,
            'data_hora': _to_iso_hora(form.data_hora.data),
            'cidade': form.cidade.data,
            'logradouro': form.logradouro.data,
            'latitude': form.latitude.data,
            'longitude': form.longitude.data,
            'vtr': form.vtr.data,
            'descricao': form.descricao.data,
            'dados_relevantes': form.dados_relevantes.data
        })
        flash('Ocorrência registrada!', 'success')
        return redirect(url_for('ocorrencia.index'))

    municipios = [m.to_dict() for m in d.list_municipios(order_by='nome')]
    return render_template('ocorrencia/form.html', form=form, municipios_json=municipios)


@ocorrencia_bp.route('/mapa')
@login_required
def mapa():
    municipios = [m.to_dict() for m in d.list_municipios(order_by='nome')]
    ocorrencias = [o.to_dict() for o in d.list_all_ocorrencias()]
    return render_template('ocorrencia/mapa.html',
                           municipios_json=municipios,
                           ocorrencias_json=ocorrencias)


@ocorrencia_bp.route('/estatisticas')
@login_required
def estatisticas():
    data_inicio = request.args.get('data_inicio')
    data_fim = request.args.get('data_fim')

    stats = _get_estatisticas(data_inicio, data_fim)
    return render_template('ocorrencia/estatisticas.html', stats=stats)


viatura_bp = Blueprint('viatura', __name__, url_prefix='/viatura')


@viatura_bp.route('/')
@login_required
def index():
    page = request.args.get('page', 1, type=int)
    situacao = request.args.get('situacao')
    municipio = request.args.get('municipio')

    pagination = d.list_viaturas(page=page, per_page=20,
                                 situacao=situacao, municipio=municipio)

    situacoes = d.viatura_situacoes()
    municipios = d.viatura_municipios()

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

    form = ViaturaForm()

    if form.validate_on_submit():
        data = {}
        for field in form:
            if field.name not in ('submit', 'csrf_token'):
                data[field.name] = field.data
        d.add_viatura(data)
        flash('Viaturada cadastrada!', 'success')
        return redirect(url_for('viatura.index'))

    return render_template('viatura/form.html', form=form, title='Nova Viatura')


@viatura_bp.route('/<prefixo>/editar', methods=['GET', 'POST'])
@login_required
def editar(prefixo):
    if not current_user.is_supervisor:
        flash('Acesso negado.', 'danger')
        return redirect(url_for('viatura.index'))

    viatura = d.get_viatura(prefixo)
    if not viatura:
        flash('Viaturada não encontrada.', 'danger')
        return redirect(url_for('viatura.index'))

    form = ViaturaForm(obj=viatura)

    if form.validate_on_submit():
        data = {}
        for field in form:
            if field.name not in ('submit', 'csrf_token'):
                data[field.name] = field.data
        d.update_viatura(prefixo, data)
        flash('Viaturada atualizada!', 'success')
        return redirect(url_for('viatura.index'))

    return render_template('viatura/form.html', form=form, title='Editar Viatura')