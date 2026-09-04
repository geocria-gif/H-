"""REST API blueprint — Firestore-backed.

Provides JSON endpoints under ``/api/v1`` for all core entities.
Marshmallow schemas are kept for input validation and output serialisation.
Pagination helpers consume ``d.base.Page`` objects returned by the data layer.
"""
import csv
import io
import importlib.util
import pathlib
from datetime import datetime, timedelta

from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from marshmallow import Schema, fields, validate, ValidationError
from app import limiter
from app import data as d


api_bp = Blueprint('api', __name__, url_prefix='/api/v1')


def _load_instagram_service():
    """Load instagram_service.py directly, bypassing the dead services package."""
    module_path = pathlib.Path(__file__).resolve().parents[1] / 'services' / 'instagram_service.py'
    spec = importlib.util.spec_from_file_location('instagram_service', module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_instagram_module = _load_instagram_service()


# ---------------------------------------------------------------------------
# Marshmallow schemas (input validation + output serialisation)
# ---------------------------------------------------------------------------

class UsuarioSchema(Schema):
    id = fields.Int(dump_only=True)
    matricula = fields.Str(required=True, validate=validate.Length(max=20))
    nome = fields.Str(required=True, validate=validate.Length(max=200))
    tipo = fields.Str(validate=validate.OneOf(['ADMIN', 'SUPERVISOR', 'OPERADOR', 'VISITANTE']))
    ativo = fields.Bool()
    criado_em = fields.DateTime(dump_only=True)
    ultimo_login = fields.DateTime(dump_only=True)


class EfetivoPMSchema(Schema):
    matricula = fields.Str(required=True, validate=validate.Length(max=20))
    nome = fields.Str(required=True, validate=validate.Length(max=200))
    cargo = fields.Str(required=True, validate=validate.Length(max=20))
    opm_id = fields.Str(required=True, validate=validate.Length(max=20))
    sit = fields.Str(validate=validate.Length(max=10))
    funcao = fields.Str(validate=validate.Length(max=100))
    telefone = fields.Str(validate=validate.Length(max=20))
    cpf = fields.Str(validate=validate.Length(max=14))
    rg = fields.Str(validate=validate.Length(max=20))
    tipo_sanguineo = fields.Str(validate=validate.Length(max=5))


class EventoSchema(Schema):
    evento_id = fields.Int(dump_only=True)
    evento_desc = fields.Str(required=True, validate=validate.Length(max=200))
    evento_dta_inicio = fields.Date(required=True)
    evento_dta_fim = fields.Date(required=True)
    campo1 = fields.Str()
    tipo_pagamento = fields.Str(validate=validate.OneOf(['HE', 'VD', 'SO']))


class OpmEventoSchema(Schema):
    opm_evento_id = fields.Int(dump_only=True)
    evento_id = fields.Int(required=True)
    opm_id = fields.Str(required=True, validate=validate.Length(max=20))


class EscalaSchema(Schema):
    opm_evento_id = fields.Int(required=True)
    matricula = fields.Str(required=True, validate=validate.Length(max=20))
    escala_data = fields.Date(required=True)
    escala_ch_diurna = fields.Float(validate=validate.Range(min=0))
    escala_ch_noturna = fields.Float(validate=validate.Range(min=0))
    hora_inicio = fields.Time()
    hora_fim = fields.Time()
    tipo_pagamento = fields.Str(validate=validate.OneOf(['HE', 'VD', 'SO']))


class TabelaValoresSchema(Schema):
    id = fields.Int(dump_only=True)
    posto_grad = fields.Str(required=True, validate=validate.Length(max=100))
    he_diurna = fields.Float(required=True, validate=validate.Range(min=0))
    ad_he_noturna = fields.Float(required=True, validate=validate.Range(min=0))
    vd_diurno = fields.Float(required=True, validate=validate.Range(min=0))
    vd_noturno = fields.Float(required=True, validate=validate.Range(min=0))


class OcorrenciaSchema(Schema):
    id = fields.Int(dump_only=True)
    tipo = fields.Str(required=True, validate=validate.Length(max=50))
    data_hora = fields.Str(required=True)
    cidade = fields.Str(validate=validate.Length(max=100))
    latitude = fields.Float()
    longitude = fields.Float()
    vtr = fields.Str(validate=validate.Length(max=50))
    descricao = fields.Str()
    dados_relevantes = fields.Str()


class EscalaP2Schema(Schema):
    id = fields.Int(dump_only=True)
    mes = fields.Int(required=True, validate=validate.Range(min=1, max=12))
    ano = fields.Int(required=True, validate=validate.Range(min=2020, max=2030))
    funcao = fields.Str(required=True, validate=validate.Length(max=100))
    opm = fields.Str(required=True, validate=validate.Length(max=100))
    gh = fields.Str(required=True, validate=validate.Length(max=50))
    nome = fields.Str(required=True, validate=validate.Length(max=200))
    matricula = fields.Str(required=True, validate=validate.Length(max=20))
    telefone = fields.Str(validate=validate.Length(max=20))
    dias = fields.Dict()
    is_separador = fields.Bool()
    separador_texto = fields.Str(validate=validate.Length(max=200))
    ordem = fields.Int()
    tipo_pagamento = fields.Str(validate=validate.OneOf(['HE', 'VD', 'SO']))


class EscalaSalvaSchema(Schema):
    id = fields.Int(dump_only=True)
    nome = fields.Str(required=True, validate=validate.Length(max=200))
    mes = fields.Int(required=True, validate=validate.Range(min=1, max=12))
    ano = fields.Int(required=True, validate=validate.Range(min=2020, max=2030))
    ativa = fields.Bool()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def default_paginate(page_data):
    """Build the standard paginated JSON envelope from a ``d.base.Page``."""
    return {
        'items': [dict(i) if not isinstance(i, dict) else i for i in page_data.items],
        'pagination': {
            'page': page_data.page,
            'per_page': page_data.per_page,
            'total': page_data.total,
            'pages': page_data.pages,
            'has_next': page_data.has_next,
            'has_prev': page_data.has_prev,
        }
    }


def _calcular_ch(hora_inicio, hora_fim):
    """Calculate day/night load (CH) from start/end times."""
    if not hora_inicio or not hora_fim:
        return 0, 0
    try:
        if isinstance(hora_inicio, str):
            hi = datetime.strptime(hora_inicio, '%H:%M')
        else:
            hi = datetime.combine(datetime.today(), hora_inicio)
        if isinstance(hora_fim, str):
            hf = datetime.strptime(hora_fim, '%H:%M')
        else:
            hf = datetime.combine(datetime.today(), hora_fim)
    except ValueError:
        return 0, 0
    if hf <= hi:
        hf += timedelta(days=1)
    ch_diurna = 0.0
    ch_noturna = 0.0
    atual = hi
    while atual < hf:
        prox = min(atual + timedelta(hours=1), hf)
        hora_decimal = atual.hour + atual.minute / 60
        if 5 <= hora_decimal < 22:
            ch_diurna += (prox - atual).total_seconds() / 3600
        else:
            ch_noturna += (prox - atual).total_seconds() / 3600
        atual = prox
    return round(ch_diurna, 2), round(ch_noturna, 2)


# ---------------------------------------------------------------------------
# Usuario API
# ---------------------------------------------------------------------------

@api_bp.route('/usuarios', methods=['GET'])
@jwt_required()
@limiter.limit('100 per minute')
def get_usuarios():
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 20, type=int), 100)
    all_usrs = d.list_usuarios()
    all_usrs.sort(key=lambda u: (u.get('nome') or '').lower())
    total = len(all_usrs)
    start = (page - 1) * per_page
    items = [d.usuario_to_dict(u) for u in all_usrs[start:start + per_page]]
    pages = (total + per_page - 1) // per_page if per_page else 1
    return jsonify({
        'items': items,
        'pagination': {
            'page': page,
            'per_page': per_page,
            'total': total,
            'pages': pages,
            'has_next': page < pages,
            'has_prev': page > 1,
        }
    })


@api_bp.route('/usuarios/<matricula>', methods=['GET'])
@jwt_required()
def get_usuario(matricula):
    usuario = d.get_usuario(matricula)
    if not usuario:
        return jsonify(error='Not Found', message='Usuário não encontrado'), 404
    return jsonify(d.usuario_to_dict(usuario))


@api_bp.route('/usuarios', methods=['POST'])
@jwt_required()
def create_usuario():
    claims = get_jwt()
    if claims.get('tipo') != 'ADMIN':
        return jsonify(error='Forbidden', message='Apenas administradores'), 403

    schema = UsuarioSchema()
    try:
        data = schema.load(request.get_json())
    except ValidationError as err:
        return jsonify(error='Validation Error', messages=err.messages), 400

    if d.get_usuario(data['matricula']):
        return jsonify(error='Conflict', message='Matrícula já existe'), 409

    senha = (request.get_json() or {}).get('senha', '123456')
    try:
        d.create_auth_user(data['matricula'], senha, data['nome'],
                           data.get('tipo', 'USER'))
    except Exception:
        pass

    user_data = {
        'matricula': data['matricula'],
        'nome': data['nome'],
        'tipo': data.get('tipo', 'USER'),
        'ativo': data.get('ativo', True),
        'criado_em': datetime.utcnow().isoformat(),
        'ultimo_login': None,
    }
    d.add_usuario(user_data)
    return jsonify(d.usuario_to_dict(d.get_usuario(data['matricula']))), 201


@api_bp.route('/usuarios/<matricula>', methods=['PUT'])
@jwt_required()
def update_usuario(matricula):
    claims = get_jwt()
    if claims.get('tipo') != 'ADMIN' and get_jwt_identity() != matricula:
        return jsonify(error='Forbidden', message='Sem permissão'), 403

    usuario = d.get_usuario(matricula)
    if not usuario:
        return jsonify(error='Not Found', message='Usuário não encontrado'), 404

    schema = UsuarioSchema(partial=True)
    try:
        data = schema.load(request.get_json())
    except ValidationError as err:
        return jsonify(error='Validation Error', messages=err.messages), 400

    if 'matricula' in data and data['matricula'] != matricula:
        if d.get_usuario(data['matricula']):
            return jsonify(error='Conflict', message='Matrícula já existe'), 409

    d.update_usuario(matricula, data)
    updated = d.get_usuario(matricula)
    return jsonify(d.usuario_to_dict(updated))


@api_bp.route('/usuarios/<matricula>', methods=['DELETE'])
@jwt_required()
def delete_usuario(matricula):
    claims = get_jwt()
    if claims.get('tipo') != 'ADMIN':
        return jsonify(error='Forbidden', message='Apenas administradores'), 403

    if not d.get_usuario(matricula):
        return jsonify(error='Not Found', message='Usuário não encontrado'), 404

    d.delete_usuario(matricula)
    return jsonify(message='Usuário removido'), 200


# ---------------------------------------------------------------------------
# Efetivo PM API
# ---------------------------------------------------------------------------

@api_bp.route('/efetivos', methods=['GET'])
@jwt_required()
@limiter.limit('100 per minute')
def get_efetivos():
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 20, type=int), 100)
    search = request.args.get('search', '')

    if search:
        page_data = d.search_efetivos(search, page=page, per_page=per_page)
    else:
        page_data = d.list_efetivos(page=page, per_page=per_page)
    return jsonify(default_paginate(page_data))


@api_bp.route('/efetivos/<matricula>', methods=['GET'])
@jwt_required()
def get_efetivo(matricula):
    efetivo = d.get_efetivo(matricula)
    if not efetivo:
        return jsonify(error='Not Found', message='Militar não encontrado'), 404
    return jsonify(EfetivoPMSchema().dump(dict(efetivo)))


@api_bp.route('/efetivos', methods=['POST'])
@jwt_required()
def create_efetivo():
    schema = EfetivoPMSchema()
    try:
        data = schema.load(request.get_json())
    except ValidationError as err:
        return jsonify(error='Validation Error', messages=err.messages), 400

    if d.get_efetivo(data['matricula']):
        return jsonify(error='Conflict', message='Matrícula já existe'), 409

    d.add_efetivo(data)
    return jsonify(EfetivoPMSchema().dump(dict(d.get_efetivo(data['matricula'])))), 201


@api_bp.route('/efetivos/<matricula>', methods=['PUT'])
@jwt_required()
def update_efetivo(matricula):
    efetivo = d.get_efetivo(matricula)
    if not efetivo:
        return jsonify(error='Not Found', message='Militar não encontrado'), 404

    schema = EfetivoPMSchema(partial=True)
    try:
        data = schema.load(request.get_json())
    except ValidationError as err:
        return jsonify(error='Validation Error', messages=err.messages), 400

    d.update_efetivo(matricula, data)
    return jsonify(EfetivoPMSchema().dump(dict(d.get_efetivo(matricula))))


@api_bp.route('/efetivos/<matricula>', methods=['DELETE'])
@jwt_required()
def delete_efetivo(matricula):
    claims = get_jwt()
    if claims.get('tipo') not in ['ADMIN', 'SUPERVISOR']:
        return jsonify(error='Forbidden', message='Sem permissão'), 403

    if not d.get_efetivo(matricula):
        return jsonify(error='Not Found', message='Militar não encontrado'), 404

    d.delete_efetivo(matricula)
    return jsonify(message='Militar removido'), 200


# ---------------------------------------------------------------------------
# Evento API
# ---------------------------------------------------------------------------

@api_bp.route('/eventos', methods=['GET'])
@jwt_required()
@limiter.limit('100 per minute')
def get_eventos():
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 20, type=int), 100)
    eventos = d.list_eventos()
    eventos.sort(key=lambda e: (e.get('evento_dta_inicio') or ''), reverse=True)
    total = len(eventos)
    start = (page - 1) * per_page
    items = [EventoSchema().dump(dict(e)) for e in eventos[start:start + per_page]]
    pages = (total + per_page - 1) // per_page if per_page else 1
    return jsonify({
        'items': items,
        'pagination': {
            'page': page,
            'per_page': per_page,
            'total': total,
            'pages': pages,
            'has_next': page < pages,
            'has_prev': page > 1,
        }
    })


@api_bp.route('/eventos/<int:id>', methods=['GET'])
@jwt_required()
def get_evento(id):
    evento = d.get_evento_with_opms(id)
    if not evento:
        return jsonify(error='Not Found', message='Evento não encontrado'), 404
    return jsonify(EventoSchema().dump(dict(evento)))


@api_bp.route('/eventos', methods=['POST'])
@jwt_required()
def create_evento():
    schema = EventoSchema()
    try:
        data = schema.load(request.get_json())
    except ValidationError as err:
        return jsonify(error='Validation Error', messages=err.messages), 400

    opm_ids = request.get_json().get('opm_ids', [])
    evento_id = d.next_evento_id()

    evento_data = {
        'evento_id': evento_id,
        'evento_desc': data['evento_desc'],
        'evento_dta_inicio': str(data.get('evento_dta_inicio', '')),
        'evento_dta_fim': str(data.get('evento_dta_fim', '')),
        'campo1': data.get('campo1'),
        'tipo_pagamento': data.get('tipo_pagamento', 'HE'),
    }
    d.add_evento(evento_data, evento_id=evento_id)

    for opm_id in opm_ids:
        oe_id = d.next_opm_evento_id()
        d.add_opm_evento({'opm_evento_id': oe_id, 'evento_id': evento_id, 'opm_id': opm_id},
                         opm_evento_id=oe_id)

    return jsonify(EventoSchema().dump(dict(d.get_evento(evento_id)))), 201


@api_bp.route('/eventos/<int:id>', methods=['PUT'])
@jwt_required()
def update_evento(id):
    evento = d.get_evento(id)
    if not evento:
        return jsonify(error='Not Found', message='Evento não encontrado'), 404

    schema = EventoSchema(partial=True)
    try:
        data = schema.load(request.get_json())
    except ValidationError as err:
        return jsonify(error='Validation Error', messages=err.messages), 400

    update = {}
    if 'evento_desc' in data:
        update['evento_desc'] = data['evento_desc']
    if 'evento_dta_inicio' in data:
        update['evento_dta_inicio'] = str(data['evento_dta_inicio'])
    if 'evento_dta_fim' in data:
        update['evento_dta_fim'] = str(data['evento_dta_fim'])
    if 'campo1' in data:
        update['campo1'] = data['campo1']
    if 'tipo_pagamento' in data:
        update['tipo_pagamento'] = data['tipo_pagamento']

    d.update_evento(id, update)
    return jsonify(EventoSchema().dump(dict(d.get_evento(id))))


@api_bp.route('/eventos/<int:id>', methods=['DELETE'])
@jwt_required()
def delete_evento(id):
    claims = get_jwt()
    if claims.get('tipo') not in ['ADMIN', 'SUPERVISOR']:
        return jsonify(error='Forbidden', message='Sem permissão'), 403

    evento = d.get_evento(id)
    if not evento:
        return jsonify(error='Not Found', message='Evento não encontrado'), 404

    d.delete_evento(id)
    return jsonify(message='Evento removido'), 200


@api_bp.route('/eventos/<int:id>/opms', methods=['POST'])
@jwt_required()
def add_opm_to_evento(id):
    schema = OpmEventoSchema()
    try:
        data = schema.load(request.get_json())
    except ValidationError as err:
        return jsonify(error='Validation Error', messages=err.messages), 400

    oe_id = d.next_opm_evento_id()
    oe_data = {'opm_evento_id': oe_id, 'evento_id': id, 'opm_id': data['opm_id']}
    d.add_opm_evento(oe_data, opm_evento_id=oe_id)
    return jsonify(OpmEventoSchema().dump(dict(d.get_opm_evento(oe_id)))), 201


@api_bp.route('/eventos/<int:id>/opms/<opm_id>', methods=['DELETE'])
@jwt_required()
def remove_opm_from_evento(id, opm_id):
    found = None
    for oe in d.list_opm_eventos_by_evento(id):
        if oe.get('opm_id') == opm_id:
            found = oe
            break
    if not found:
        return jsonify(error='Not Found', message='OPM não vinculado ao evento'), 404
    d.delete_opm_evento(found.get('opm_evento_id'))
    return jsonify(message='OPM removido do evento'), 200


# ---------------------------------------------------------------------------
# Escala API
# ---------------------------------------------------------------------------

@api_bp.route('/escalas', methods=['GET'])
@jwt_required()
@limiter.limit('100 per minute')
def get_escalas():
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 20, type=int), 100)
    opm_evento_id = request.args.get('opm_evento_id', type=int)
    matricula = request.args.get('matricula')
    data_inicio = request.args.get('data_inicio')
    data_fim = request.args.get('data_fim')
    tipo_pagamento = request.args.get('tipo_pagamento')

    if opm_evento_id:
        escalas = d.list_escalas_by_opm_evento(opm_evento_id)
    else:
        escalas = d.list_escalas(order_by='escala_data')

    if matricula:
        escalas = [e for e in escalas if e.get('matricula') == matricula]
    if data_inicio:
        escalas = [e for e in escalas if (e.get('escala_data') or '') >= data_inicio]
    if data_fim:
        escalas = [e for e in escalas if (e.get('escala_data') or '') <= data_fim]
    if tipo_pagamento:
        escalas = [e for e in escalas if e.get('tipo_pagamento') == tipo_pagamento]

    escalas.sort(key=lambda e: ((e.get('escala_data') or ''), (e.get('matricula') or '')))

    total = len(escalas)
    start = (page - 1) * per_page
    items = [EscalaSchema().dump(dict(e)) for e in escalas[start:start + per_page]]
    pages = (total + per_page - 1) // per_page if per_page else 1
    return jsonify({
        'items': items,
        'pagination': {
            'page': page,
            'per_page': per_page,
            'total': total,
            'pages': pages,
            'has_next': page < pages,
            'has_prev': page > 1,
        }
    })


@api_bp.route('/escalas', methods=['POST'])
@jwt_required()
def create_escala():
    schema = EscalaSchema()
    try:
        data = schema.load(request.get_json())
    except ValidationError as err:
        return jsonify(error='Validation Error', messages=err.messages), 400

    if data.get('hora_inicio') and data.get('hora_fim'):
        ch_d, ch_n = _calcular_ch(data['hora_inicio'], data['hora_fim'])
        data['escala_ch_diurna'] = ch_d
        data['escala_ch_noturna'] = ch_n

    escala_data_dict = {
        'opm_evento_id': int(data['opm_evento_id']),
        'matricula': data['matricula'],
        'escala_data': str(data['escala_data']),
        'escala_ch_diurna': float(data.get('escala_ch_diurna') or 0),
        'escala_ch_noturna': float(data.get('escala_ch_noturna') or 0),
        'tipo_pagamento': data.get('tipo_pagamento', 'HE'),
    }
    if data.get('hora_inicio'):
        escala_data_dict['hora_inicio'] = str(data['hora_inicio'])
    if data.get('hora_fim'):
        escala_data_dict['hora_fim'] = str(data['hora_fim'])

    d.add_escala(escala_data_dict)
    result = d.get_escala(data['opm_evento_id'], data['matricula'], str(data['escala_data']))
    return jsonify(EscalaSchema().dump(dict(result))), 201


@api_bp.route('/eventos/<int:evento_id>/relatorio-horas', methods=['GET'])
@jwt_required()
def get_relatorio_horas(evento_id):
    tipo_pagamento = request.args.get('tipo_pagamento')
    dados = d.horas_por_militar(evento_id, tipo_pagamento)

    results = []
    for row in dados:
        row_dict = dict(row)
        ef = d.get_efetivo(row.get('matricula'))
        if ef and row_dict.get('ch_diurna') is not None and row_dict.get('ch_noturna') is not None:
            posto = ef.get('posto_grad') or ef.get('cargo') or ''
            tabela = d.get_tabela_valor_by_posto(posto)
            if tabela:
                tp = tipo_pagamento or row_dict.get('tipo_pagamento', 'HE')
                if tp == 'HE':
                    vd = float(tabela.get('he_diurna') or 0)
                    vn = float(tabela.get('ad_he_noturna') or 0)
                elif tp == 'VD':
                    vd = float(tabela.get('vd_diurno') or 0)
                    vn = float(tabela.get('vd_noturno') or 0)
                else:
                    vd = 0.0
                    vn = 0.0
                row_dict['valor'] = round(
                    float(row_dict.get('ch_diurna') or 0) * vd
                    + float(row_dict.get('ch_noturna') or 0) * vn, 2)
        results.append(row_dict)

    return jsonify({
        'evento_id': evento_id,
        'tipo_pagamento': tipo_pagamento,
        'dados': results
    })


@api_bp.route('/eventos/<int:evento_id>/exportar-csv', methods=['GET'])
@jwt_required()
def exportar_csv_horas(evento_id):
    tipo_pagamento = request.args.get('tipo_pagamento')
    dados = d.horas_por_militar(evento_id, tipo_pagamento)

    output = io.StringIO()
    writer = csv.writer(output, delimiter=';')
    writer.writerow(['Matrícula', 'Nome', 'Posto/Grad', 'CH Diurna', 'CH Noturna', 'Total Dias', 'Tipo Pagamento'])
    for row in dados:
        writer.writerow([
            row.get('matricula'),
            row.get('nome'),
            row.get('cargo'),
            row.get('ch_diurna'),
            row.get('ch_noturna'),
            row.get('dias'),
            tipo_pagamento or 'HE/VD/SO'
        ])

    return jsonify({'csv': output.getvalue()})


# ---------------------------------------------------------------------------
# Tabela Valores API
# ---------------------------------------------------------------------------

@api_bp.route('/tabela-valores', methods=['GET'])
@jwt_required()
@limiter.limit('100 per minute')
def get_tabela_valores():
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 20, type=int), 100)
    all_vals = d.list_tabela_valores()
    all_vals.sort(key=lambda v: (v.get('posto_grad') or '').lower())
    total = len(all_vals)
    start = (page - 1) * per_page
    items = [TabelaValoresSchema().dump(dict(v)) for v in all_vals[start:start + per_page]]
    pages = (total + per_page - 1) // per_page if per_page else 1
    return jsonify({
        'items': items,
        'pagination': {
            'page': page,
            'per_page': per_page,
            'total': total,
            'pages': pages,
            'has_next': page < pages,
            'has_prev': page > 1,
        }
    })


@api_bp.route('/tabela-valores/<int:id>', methods=['GET'])
@jwt_required()
def get_tabela_valor(id):
    valor = d.get_tabela_valor(id)
    if not valor:
        return jsonify(error='Not Found', message='Valor não encontrado'), 404
    return jsonify(TabelaValoresSchema().dump(dict(valor)))


@api_bp.route('/tabela-valores', methods=['POST'])
@jwt_required()
def create_tabela_valor():
    claims = get_jwt()
    if claims.get('tipo') not in ['ADMIN', 'SUPERVISOR']:
        return jsonify(error='Forbidden', message='Sem permissão'), 403

    schema = TabelaValoresSchema()
    try:
        data = schema.load(request.get_json())
    except ValidationError as err:
        return jsonify(error='Validation Error', messages=err.messages), 400

    if d.get_tabela_valor_by_posto(data['posto_grad']):
        return jsonify(error='Conflict', message='Posto/Graduação já existe'), 409

    doc_id = d.next_opm_evento_id()  # unique numeric id
    tv_data = {'id': doc_id, **data}
    d.add_tabela_valor(tv_data, doc_id=doc_id)
    return jsonify(TabelaValoresSchema().dump(dict(d.get_tabela_valor(doc_id)))), 201


@api_bp.route('/tabela-valores/<int:id>', methods=['PUT'])
@jwt_required()
def update_tabela_valor(id):
    claims = get_jwt()
    if claims.get('tipo') not in ['ADMIN', 'SUPERVISOR']:
        return jsonify(error='Forbidden', message='Sem permissão'), 403

    valor = d.get_tabela_valor(id)
    if not valor:
        return jsonify(error='Not Found', message='Valor não encontrado'), 404

    schema = TabelaValoresSchema(partial=True)
    try:
        data = schema.load(request.get_json())
    except ValidationError as err:
        return jsonify(error='Validation Error', messages=err.messages), 400

    d.update_tabela_valor(id, data)
    return jsonify(TabelaValoresSchema().dump(dict(d.get_tabela_valor(id))))


# ---------------------------------------------------------------------------
# Ocorrencia API
# ---------------------------------------------------------------------------

@api_bp.route('/ocorrencias', methods=['GET'])
@jwt_required()
@limiter.limit('100 per minute')
def get_ocorrencias():
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 20, type=int), 100)
    tipo = request.args.get('tipo')
    data_inicio = request.args.get('data_inicio')
    data_fim = request.args.get('data_fim')

    page_data = d.list_ocorrencias(page=page, per_page=per_page,
                                   tipo=tipo, data_inicio=data_inicio, data_fim=data_fim)
    return jsonify({
        'items': [OcorrenciaSchema().dump(dict(o)) for o in page_data.items],
        'pagination': {
            'page': page_data.page,
            'per_page': page_data.per_page,
            'total': page_data.total,
            'pages': page_data.pages,
            'has_next': page_data.has_next,
            'has_prev': page_data.has_prev,
        }
    })


@api_bp.route('/ocorrencias/estatisticas', methods=['GET'])
@jwt_required()
def get_estatisticas_ocorrencias():
    data_inicio = request.args.get('data_inicio')
    data_fim = request.args.get('data_fim')

    all_oc = d.list_all_ocorrencias()
    if data_inicio:
        all_oc = [o for o in all_oc if (o.get('data_hora') or '') >= data_inicio]
    if data_fim:
        all_oc = [o for o in all_oc if (o.get('data_hora') or '') <= data_fim]

    stats = {
        'total': len(all_oc),
        'por_tipo': {},
        'por_cidade': {},
        'por_mes': {}
    }
    for oc in all_oc:
        t = oc.get('tipo') or 'OUTRO'
        stats['por_tipo'][t] = stats['por_tipo'].get(t, 0) + 1
        cidade = oc.get('cidade')
        if cidade:
            stats['por_cidade'][cidade] = stats['por_cidade'].get(cidade, 0) + 1
        dh = oc.get('data_hora') or ''
        if len(dh) >= 7:
            mes = dh[:7]
            stats['por_mes'][mes] = stats['por_mes'].get(mes, 0) + 1

    return jsonify(stats)


@api_bp.route('/ocorrencias/<int:id>', methods=['GET'])
@jwt_required()
def get_ocorrencia(id):
    ocorrencia = d.get_ocorrencia(id)
    if not ocorrencia:
        return jsonify(error='Not Found', message='Ocorrência não encontrada'), 404
    return jsonify(OcorrenciaSchema().dump(dict(ocorrencia)))


@api_bp.route('/ocorrencias', methods=['POST'])
@jwt_required()
def create_ocorrencia():
    schema = OcorrenciaSchema()
    try:
        data = schema.load(request.get_json())
    except ValidationError as err:
        return jsonify(error='Validation Error', messages=err.messages), 400

    oid = d.next_ocorrencia_id()
    data['id'] = oid
    d.add_ocorrencia(data, doc_id=oid)
    return jsonify(OcorrenciaSchema().dump(dict(d.get_ocorrencia(oid)))), 201


# ---------------------------------------------------------------------------
# Escala P2 API
# ---------------------------------------------------------------------------

@api_bp.route('/escalas-p2', methods=['GET'])
@jwt_required()
@limiter.limit('100 per minute')
def get_escalas_p2():
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 20, type=int), 100)
    mes = request.args.get('mes', type=int)
    ano = request.args.get('ano', type=int)

    all_p2 = d.list_p2(mes=mes, ano=ano)
    total = len(all_p2)
    start = (page - 1) * per_page
    items = [EscalaP2Schema().dump(dict(p)) for p in all_p2[start:start + per_page]]
    pages = (total + per_page - 1) // per_page if per_page else 1
    return jsonify({
        'items': items,
        'pagination': {
            'page': page,
            'per_page': per_page,
            'total': total,
            'pages': pages,
            'has_next': page < pages,
            'has_prev': page > 1,
        }
    })


@api_bp.route('/escalas-p2', methods=['POST'])
@jwt_required()
def create_escala_p2():
    schema = EscalaP2Schema()
    try:
        data = schema.load(request.get_json())
    except ValidationError as err:
        return jsonify(error='Validation Error', messages=err.messages), 400

    p2_id = d.next_p2_id()
    data['id'] = p2_id
    d.add_p2(data, doc_id=str(p2_id))
    return jsonify(EscalaP2Schema().dump(dict(d.get_p2(p2_id)))), 201


# ---------------------------------------------------------------------------
# Escala Salva API
# ---------------------------------------------------------------------------

@api_bp.route('/escalas-salvas', methods=['GET'])
@jwt_required()
@limiter.limit('100 per minute')
def get_escalas_salvas():
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 20, type=int), 100)

    page_data = d.list_escalas_salvas(page=page, per_page=per_page)
    return jsonify({
        'items': [EscalaSalvaSchema().dump(dict(s)) for s in page_data.items],
        'pagination': {
            'page': page_data.page,
            'per_page': page_data.per_page,
            'total': page_data.total,
            'pages': page_data.pages,
            'has_next': page_data.has_next,
            'has_prev': page_data.has_prev,
        }
    })


@api_bp.route('/escalas-salvas/<int:id>', methods=['GET'])
@jwt_required()
def get_escala_salva(id):
    escala = d.get_escala_salva(id)
    if not escala:
        return jsonify(error='Not Found', message='Escala salva não encontrada'), 404
    result = dict(escala)
    itens = escala.get('itens') if isinstance(escala.get('itens'), list) else []
    meta = escala.get('meta') or {}
    return jsonify(escala=result, itens=itens, meta=meta)


@api_bp.route('/escalas-salvas', methods=['POST'])
@jwt_required()
def create_escala_salva():
    data = request.get_json()
    if not data or not data.get('nome') or not data.get('mes') or not data.get('ano'):
        return jsonify(error='Bad Request', message='Nome, mês e ano são obrigatórios'), 400

    salva_id = d.next_escala_salva_id()
    salva_data = {
        'id': salva_id,
        'nome': data['nome'],
        'mes': data['mes'],
        'ano': data['ano'],
        'ativa': 0,
        'data_salva': datetime.utcnow().isoformat(),
        'itens': data.get('itens', []),
        'meta': data.get('meta'),
    }
    d.add_escala_salva(salva_data, doc_id=str(salva_id))
    return jsonify(EscalaSalvaSchema().dump(dict(d.get_escala_salva(salva_id)))), 201


@api_bp.route('/escalas-salvas/<int:id>/ativar', methods=['POST'])
@jwt_required()
def ativar_escala_salva(id):
    result = d.set_escala_salva_ativa(id)
    if not result:
        return jsonify(error='Not Found', message='Escala salva não encontrada'), 404
    return jsonify(message='Escala ativada com sucesso')


# ---------------------------------------------------------------------------
# Viaturas API
# ---------------------------------------------------------------------------

@api_bp.route('/viaturas', methods=['GET'])
@jwt_required()
@limiter.limit('100 per minute')
def get_viaturas():
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 20, type=int), 100)
    situacao = request.args.get('situacao')
    municipio = request.args.get('municipio')

    page_data = d.list_viaturas(page=page, per_page=per_page,
                                situacao=situacao, municipio=municipio)
    return jsonify({
        'items': [dict(v) for v in page_data.items],
        'pagination': {
            'page': page_data.page,
            'per_page': page_data.per_page,
            'total': page_data.total,
            'pages': page_data.pages,
            'has_next': page_data.has_next,
            'has_prev': page_data.has_prev,
        }
    })


# ---------------------------------------------------------------------------
# Municípios API
# ---------------------------------------------------------------------------

@api_bp.route('/municipios', methods=['GET'])
@jwt_required()
@limiter.limit('100 per minute')
def get_municipios():
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 20, type=int), 100)

    all_mun = d.list_municipios()
    total = len(all_mun)
    start = (page - 1) * per_page
    items = [dict(m) for m in all_mun[start:start + per_page]]
    pages = (total + per_page - 1) // per_page if per_page else 1
    return jsonify({
        'items': items,
        'pagination': {
            'page': page,
            'per_page': per_page,
            'total': total,
            'pages': pages,
            'has_next': page < pages,
            'has_prev': page > 1,
        }
    })


# ---------------------------------------------------------------------------
# Cargo API
# ---------------------------------------------------------------------------

@api_bp.route('/cargos', methods=['GET'])
@jwt_required()
@limiter.limit('100 per minute')
def get_cargos():
    cargos = d.list_cargos()
    return jsonify([dict(c) for c in cargos])


# ---------------------------------------------------------------------------
# OPM API
# ---------------------------------------------------------------------------

@api_bp.route('/opms', methods=['GET'])
@jwt_required()
@limiter.limit('100 per minute')
def get_opms():
    opms = d.list_opms()
    return jsonify([dict(o) for o in opms])


# ---------------------------------------------------------------------------
# Backup API — Firestore export (JSON download)
# ---------------------------------------------------------------------------

@api_bp.route('/backup', methods=['POST'])
@jwt_required()
def create_backup():
    claims = get_jwt()
    if claims.get('tipo') != 'ADMIN':
        return jsonify(error='Forbidden', message='Apenas administradores'), 403

    from app.firebase_db import get_fs
    fs = get_fs()
    collections = [
        'usuarios', 'efetivopm', 'cargos', 'opms', 'tabela_valores',
        'municipios', 'eventos', 'opm_eventos', 'escalas', 'escala_p2',
        'escalas_salvas', 'ocorrencias', 'viaturas',
    ]
    backup_data = {}
    for col in collections:
        docs = list(fs.collection(col).stream())
        backup_data[col] = [{d.id: d.to_dict()} for d in docs]

    return jsonify(
        message='Backup Firestore exportado',
        service='firestore',
        collections=collections,
        data=backup_data
    ), 200


@api_bp.route('/backups', methods=['GET'])
@jwt_required()
def list_backups():
    claims = get_jwt()
    if claims.get('tipo') != 'ADMIN':
        return jsonify(error='Forbidden', message='Apenas administradores'), 403

    from app.firebase_db import get_fs
    fs = get_fs()
    collections = [
        'usuarios', 'efetivopm', 'cargos', 'opms', 'tabela_valores',
        'municipios', 'eventos', 'opm_eventos', 'escalas', 'escala_p2',
        'escalas_salvas', 'ocorrencias', 'viaturas',
    ]
    summary = []
    for col in collections:
        count = len(list(fs.collection(col).stream()))
        summary.append({'collection': col, 'count': count})
    return jsonify(summary)


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

@api_bp.route('/health', methods=['GET'])
def health_check():
    return jsonify(status='healthy', service='SISPM API'), 200


# ---------------------------------------------------------------------------
# Instagram API (delegated to instagram_service — no DB needed)
# ---------------------------------------------------------------------------

@api_bp.route('/instagram/status', methods=['GET'])
@jwt_required()
def instagram_status():
    return jsonify(_instagram_module.instagram_service.get_status()), 200


@api_bp.route('/instagram/publish', methods=['POST'])
@jwt_required()
@limiter.limit('10 per minute')
def instagram_publish():
    instagram_service = _instagram_module.instagram_service
    InstagramError = _instagram_module.InstagramError

    claims = get_jwt()
    if claims.get('tipo') not in ['ADMIN', 'SUPERVISOR']:
        return jsonify(error='Forbidden', message='Sem permissão'), 403

    if 'image' not in request.files:
        return jsonify(error='Bad Request', message='Campo "image" (multipart) é obrigatório'), 400

    arquivo = request.files['image']
    if not arquivo or not arquivo.filename:
        return jsonify(error='Bad Request', message='Arquivo de imagem inválido'), 400

    import os
    import uuid

    ext = os.path.splitext(arquivo.filename)[1].lower()
    if ext not in ('.png', '.jpg', '.jpeg'):
        return jsonify(error='Bad Request', message='A imagem deve ser PNG ou JPG'), 400

    legenda = request.form.get('caption', '') or ''
    insta_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'instagram')
    os.makedirs(insta_dir, exist_ok=True)
    filepath = os.path.join(insta_dir, f'{uuid.uuid4().hex}{ext}')
    arquivo.save(filepath)

    try:
        resultado = instagram_service.publish_image_file(filepath, legenda)
    except InstagramError as e:
        return jsonify(error='Instagram Error', message=str(e)), 502
    except Exception as e:
        current_app.logger.exception('Erro ao publicar no Instagram (API)')
        return jsonify(error='Instagram Error', message=str(e)), 500
    finally:
        try:
            os.remove(filepath)
        except OSError:
            pass

    return jsonify(message='Publicado com sucesso', **resultado), 200
