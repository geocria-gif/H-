from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from sqlalchemy import func, or_, and_, desc
from app import db, limiter
from app.models import (
    Usuario, EfetivoPM, Cargo, OPM, Evento, OpmEvento, Escala,
    TabelaValores, EscalaP2, EscalaP2Meta, EscalaP2Legenda,
    Ocorrencia, Viatura, Municipio, EscalaSalva, EscalaSalvaItem, EscalaSalvaMeta
)
from app.services import (
    usuario_service, efetivo_service, evento_service, escala_service,
    tabela_valores_service, ocorrencia_service, escala_salva_service
)
from app.repository import (
    usuario_repo, efetivo_repo, evento_repo, escala_repo,
    tabela_valores_repo, ocorrencia_repo, escala_salva_repo,
    viatura_repo, municipio_repo
)
from marshmallow import Schema, fields, validate, post_load, ValidationError


api_bp = Blueprint('api', __name__, url_prefix='/api/v1')


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


def paginate_response(query, page=1, per_page=20, schema=None):
    pagination = db.paginate(query, page=page, per_page=per_page, error_out=False)
    items = pagination.items
    if schema:
        items = schema(many=True).dump(items)
    else:
        items = [item.to_dict() for item in items]
    return {
        'items': items,
        'pagination': {
            'page': pagination.page,
            'per_page': pagination.per_page,
            'total': pagination.total,
            'pages': pagination.pages,
            'has_next': pagination.has_next,
            'has_prev': pagination.has_prev
        }
    }


# Usuario API
@api_bp.route('/usuarios', methods=['GET'])
@jwt_required()
@limiter.limit('100 per minute')
def get_usuarios():
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 20, type=int), 100)
    query = db.select(Usuario).order_by(Usuario.nome)
    return jsonify(paginate_response(query, page, per_page, UsuarioSchema()))


@api_bp.route('/usuarios/<int:id>', methods=['GET'])
@jwt_required()
def get_usuario(id):
    usuario = db.session.get(Usuario, id)
    if not usuario:
        return jsonify(error='Not Found', message='Usuário não encontrado'), 404
    return jsonify(UsuarioSchema().dump(usuario))


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
    
    if usuario_repo.get_by_matricula(data['matricula']):
        return jsonify(error='Conflict', message='Matrícula já existe'), 409
    
    usuario = Usuario(
        matricula=data['matricula'],
        nome=data['nome'],
        tipo=data.get('tipo', 'USER'),
        ativo=data.get('ativo', True)
    )
    usuario.set_senha(data.get('senha', '123456'))
    db.session.add(usuario)
    db.session.commit()
    
    return jsonify(UsuarioSchema().dump(usuario)), 201


@api_bp.route('/usuarios/<int:id>', methods=['PUT'])
@jwt_required()
def update_usuario(id):
    claims = get_jwt()
    if claims.get('tipo') != 'ADMIN' and int(get_jwt_identity()) != id:
        return jsonify(error='Forbidden', message='Sem permissão'), 403
    
    usuario = db.session.get(Usuario, id)
    if not usuario:
        return jsonify(error='Not Found', message='Usuário não encontrado'), 404
    
    schema = UsuarioSchema(partial=True)
    try:
        data = schema.load(request.get_json())
    except ValidationError as err:
        return jsonify(error='Validation Error', messages=err.messages), 400
    
    if 'matricula' in data and data['matricula'] != usuario.matricula:
        if usuario_repo.get_by_matricula(data['matricula']):
            return jsonify(error='Conflict', message='Matrícula já existe'), 409
    
    for key, value in data.items():
        setattr(usuario, key, value)
    db.session.commit()
    
    return jsonify(UsuarioSchema().dump(usuario))


@api_bp.route('/usuarios/<int:id>', methods=['DELETE'])
@jwt_required()
def delete_usuario(id):
    claims = get_jwt()
    if claims.get('tipo') != 'ADMIN':
        return jsonify(error='Forbidden', message='Apenas administradores'), 403
    
    usuario = db.session.get(Usuario, id)
    if not usuario:
        return jsonify(error='Not Found', message='Usuário não encontrado'), 404
    
    db.session.delete(usuario)
    db.session.commit()
    return jsonify(message='Usuário removido'), 200


# Efetivo PM API
@api_bp.route('/efetivos', methods=['GET'])
@jwt_required()
@limiter.limit('100 per minute')
def get_efetivos():
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 20, type=int), 100)
    search = request.args.get('search', '')
    
    query = db.select(EfetivoPM)
    if search:
        query = query.where(or_(
            EfetivoPM.matricula.ilike(f'%{search}%'),
            EfetivoPM.nome.ilike(f'%{search}%')
        ))
    query = query.order_by(EfetivoPM.nome)
    
    return jsonify(paginate_response(query, page, per_page, EfetivoPMSchema()))


@api_bp.route('/efetivos/<matricula>', methods=['GET'])
@jwt_required()
def get_efetivo(matricula):
    efetivo = efetivo_repo.get_by_matricula(matricula)
    if not efetivo:
        return jsonify(error='Not Found', message='Militar não encontrado'), 404
    return jsonify(EfetivoPMSchema().dump(efetivo))


@api_bp.route('/efetivos', methods=['POST'])
@jwt_required()
def create_efetivo():
    schema = EfetivoPMSchema()
    try:
        data = schema.load(request.get_json())
    except ValidationError as err:
        return jsonify(error='Validation Error', messages=err.messages), 400
    
    if efetivo_repo.get_by_matricula(data['matricula']):
        return jsonify(error='Conflict', message='Matrícula já existe'), 409
    
    efetivo = EfetivoPM(**data)
    db.session.add(efetivo)
    db.session.commit()
    return jsonify(EfetivoPMSchema().dump(efetivo)), 201


@api_bp.route('/efetivos/<matricula>', methods=['PUT'])
@jwt_required()
def update_efetivo(matricula):
    efetivo = efetivo_repo.get_by_matricula(matricula)
    if not efetivo:
        return jsonify(error='Not Found', message='Militar não encontrado'), 404
    
    schema = EfetivoPMSchema(partial=True)
    try:
        data = schema.load(request.get_json())
    except ValidationError as err:
        return jsonify(error='Validation Error', messages=err.messages), 400
    
    for key, value in data.items():
        setattr(efetivo, key, value)
    db.session.commit()
    return jsonify(EfetivoPMSchema().dump(efetivo))


@api_bp.route('/efetivos/<matricula>', methods=['DELETE'])
@jwt_required()
def delete_efetivo(matricula):
    claims = get_jwt()
    if claims.get('tipo') not in ['ADMIN', 'SUPERVISOR']:
        return jsonify(error='Forbidden', message='Sem permissão'), 403
    
    efetivo = efetivo_repo.get_by_matricula(matricula)
    if not efetivo:
        return jsonify(error='Not Found', message='Militar não encontrado'), 404
    
    db.session.delete(efetivo)
    db.session.commit()
    return jsonify(message='Militar removido'), 200


# Evento API
@api_bp.route('/eventos', methods=['GET'])
@jwt_required()
@limiter.limit('100 per minute')
def get_eventos():
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 20, type=int), 100)
    query = db.select(Evento).order_by(desc(Evento.evento_dta_inicio))
    return jsonify(paginate_response(query, page, per_page, EventoSchema()))


@api_bp.route('/eventos/<int:id>', methods=['GET'])
@jwt_required()
def get_evento(id):
    evento = evento_repo.get_with_opms(id)
    if not evento:
        return jsonify(error='Not Found', message='Evento não encontrado'), 404
    return jsonify(EventoSchema().dump(evento))


@api_bp.route('/eventos', methods=['POST'])
@jwt_required()
def create_evento():
    schema = EventoSchema()
    try:
        data = schema.load(request.get_json())
    except ValidationError as err:
        return jsonify(error='Validation Error', messages=err.messages), 400
    
    opm_ids = request.get_json().get('opm_ids', [])
    evento = evento_service.criar_com_opms(data, opm_ids)
    return jsonify(EventoSchema().dump(evento)), 201


@api_bp.route('/eventos/<int:id>', methods=['PUT'])
@jwt_required()
def update_evento(id):
    evento = db.session.get(Evento, id)
    if not evento:
        return jsonify(error='Not Found', message='Evento não encontrado'), 404
    
    schema = EventoSchema(partial=True)
    try:
        data = schema.load(request.get_json())
    except ValidationError as err:
        return jsonify(error='Validation Error', messages=err.messages), 400
    
    for key, value in data.items():
        setattr(evento, key, value)
    db.session.commit()
    return jsonify(EventoSchema().dump(evento))


@api_bp.route('/eventos/<int:id>', methods=['DELETE'])
@jwt_required()
def delete_evento(id):
    claims = get_jwt()
    if claims.get('tipo') not in ['ADMIN', 'SUPERVISOR']:
        return jsonify(error='Forbidden', message='Sem permissão'), 403
    
    evento = db.session.get(Evento, id)
    if not evento:
        return jsonify(error='Not Found', message='Evento não encontrado'), 404
    
    db.session.delete(evento)
    db.session.commit()
    return jsonify(message='Evento removido'), 200


@api_bp.route('/eventos/<int:id>/opms', methods=['POST'])
@jwt_required()
def add_opm_to_evento(id):
    schema = OpmEventoSchema()
    try:
        data = schema.load(request.get_json())
    except ValidationError as err:
        return jsonify(error='Validation Error', messages=err.messages), 400
    
    opm_evento = evento_service.adicionar_opm(id, data['opm_id'])
    return jsonify(OpmEventoSchema().dump(opm_evento)), 201


@api_bp.route('/eventos/<int:id>/opms/<opm_id>', methods=['DELETE'])
@jwt_required()
def remove_opm_from_evento(id, opm_id):
    result = evento_service.remover_opm(id, opm_id)
    if not result:
        return jsonify(error='Not Found', message='OPM não vinculado ao evento'), 404
    return jsonify(message='OPM removido do evento'), 200


# Escala API
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
    
    query = db.select(Escala).join(OpmEvento).join(Evento)
    
    if opm_evento_id:
        query = query.where(Escala.opm_evento_id == opm_evento_id)
    if matricula:
        query = query.where(Escala.matricula == matricula)
    if data_inicio:
        query = query.where(Escala.escala_data >= data_inicio)
    if data_fim:
        query = query.where(Escala.escala_data <= data_fim)
    if tipo_pagamento:
        query = query.where(Escala.tipo_pagamento == tipo_pagamento)
    
    query = query.order_by(Escala.escala_data, Escala.matricula)
    return jsonify(paginate_response(query, page, per_page, EscalaSchema()))


@api_bp.route('/escalas', methods=['POST'])
@jwt_required()
def create_escala():
    schema = EscalaSchema()
    try:
        data = schema.load(request.get_json())
    except ValidationError as err:
        return jsonify(error='Validation Error', messages=err.messages), 400
    
    # Calculate CH if hora_inicio and hora_fim provided
    if data.get('hora_inicio') and data.get('hora_fim'):
        ch_d, ch_n = escala_service.calcular_ch(data['hora_inicio'], data['hora_fim'])
        data['escala_ch_diurna'] = ch_d
        data['escala_ch_noturna'] = ch_n
    
    escala = escala_service.salvar_escala(**data)
    return jsonify(EscalaSchema().dump(escala)), 201


@api_bp.route('/eventos/<int:evento_id>/relatorio-horas', methods=['GET'])
@jwt_required()
def get_relatorio_horas(evento_id):
    tipo_pagamento = request.args.get('tipo_pagamento')
    dados = escala_service.get_relatorio_horas(evento_id, tipo_pagamento)
    
    # Add calculated values
    results = []
    for row in dados:
        row_dict = dict(row)
        militar = efetivo_repo.get_by_matricula(row['matricula'])
        if militar:
            valor = tabela_valores_service.calcular_valor_militar(
                militar, row['ch_diurna'] or 0, row['ch_noturna'] or 0,
                tipo_pagamento or row.get('tipo_pagamento', 'HE')
            )
            row_dict['valor'] = valor
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
    csv_content = escala_service.exportar_csv(evento_id, tipo_pagamento)
    return jsonify({'csv': csv_content})


# Tabela Valores API
@api_bp.route('/tabela-valores', methods=['GET'])
@jwt_required()
@limiter.limit('100 per minute')
def get_tabela_valores():
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 20, type=int), 100)
    query = db.select(TabelaValores).order_by(TabelaValores.posto_grad)
    return jsonify(paginate_response(query, page, per_page, TabelaValoresSchema()))


@api_bp.route('/tabela-valores/<int:id>', methods=['GET'])
@jwt_required()
def get_tabela_valor(id):
    valor = db.session.get(TabelaValores, id)
    if not valor:
        return jsonify(error='Not Found', message='Valor não encontrado'), 404
    return jsonify(TabelaValoresSchema().dump(valor))


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
    
    if tabela_valores_repo.get_by_posto(data['posto_grad']):
        return jsonify(error='Conflict', message='Posto/Graduação já existe'), 409
    
    valor = TabelaValores(**data)
    db.session.add(valor)
    db.session.commit()
    return jsonify(TabelaValoresSchema().dump(valor)), 201


@api_bp.route('/tabela-valores/<int:id>', methods=['PUT'])
@jwt_required()
def update_tabela_valor(id):
    claims = get_jwt()
    if claims.get('tipo') not in ['ADMIN', 'SUPERVISOR']:
        return jsonify(error='Forbidden', message='Sem permissão'), 403
    
    valor = db.session.get(TabelaValores, id)
    if not valor:
        return jsonify(error='Not Found', message='Valor não encontrado'), 404
    
    schema = TabelaValoresSchema(partial=True)
    try:
        data = schema.load(request.get_json())
    except ValidationError as err:
        return jsonify(error='Validation Error', messages=err.messages), 400
    
    for key, value in data.items():
        setattr(valor, key, value)
    db.session.commit()
    return jsonify(TabelaValoresSchema().dump(valor))


# Ocorrência API
@api_bp.route('/ocorrencias', methods=['GET'])
@jwt_required()
@limiter.limit('100 per minute')
def get_ocorrencias():
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 20, type=int), 100)
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
    
    return jsonify(paginate_response(query, page, per_page, OcorrenciaSchema()))


@api_bp.route('/ocorrencias/<int:id>', methods=['GET'])
@jwt_required()
def get_ocorrencia(id):
    ocorrencia = db.session.get(Ocorrencia, id)
    if not ocorrencia:
        return jsonify(error='Not Found', message='Ocorrência não encontrada'), 404
    return jsonify(OcorrenciaSchema().dump(ocorrencia))


@api_bp.route('/ocorrencias', methods=['POST'])
@jwt_required()
def create_ocorrencia():
    schema = OcorrenciaSchema()
    try:
        data = schema.load(request.get_json())
    except ValidationError as err:
        return jsonify(error='Validation Error', messages=err.messages), 400
    
    ocorrencia = ocorrencia_service.criar_com_coordenadas(data)
    return jsonify(OcorrenciaSchema().dump(ocorrencia)), 201


@api_bp.route('/ocorrencias/estatisticas', methods=['GET'])
@jwt_required()
def get_estatisticas_ocorrencias():
    data_inicio = request.args.get('data_inicio')
    data_fim = request.args.get('data_fim')
    stats = ocorrencia_service.get_estatisticas(data_inicio, data_fim)
    return jsonify(stats)


# Escala P2 API
@api_bp.route('/escalas-p2', methods=['GET'])
@jwt_required()
@limiter.limit('100 per minute')
def get_escalas_p2():
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 20, type=int), 100)
    mes = request.args.get('mes', type=int)
    ano = request.args.get('ano', type=int)
    
    query = db.select(EscalaP2).order_by(EscalaP2.ordem)
    if mes:
        query = query.where(EscalaP2.mes == mes)
    if ano:
        query = query.where(EscalaP2.ano == ano)
    
    return jsonify(paginate_response(query, page, per_page, EscalaP2Schema()))


@api_bp.route('/escalas-p2', methods=['POST'])
@jwt_required()
def create_escala_p2():
    schema = EscalaP2Schema()
    try:
        data = schema.load(request.get_json())
    except ValidationError as err:
        return jsonify(error='Validation Error', messages=err.messages), 400
    
    escala = EscalaP2(**data)
    db.session.add(escala)
    db.session.commit()
    return jsonify(EscalaP2Schema().dump(escala)), 201


# Escala Salva API
@api_bp.route('/escalas-salvas', methods=['GET'])
@jwt_required()
@limiter.limit('100 per minute')
def get_escalas_salvas():
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 20, type=int), 100)
    mes = request.args.get('mes', type=int)
    ano = request.args.get('ano', type=int)
    
    query = db.select(EscalaSalva).order_by(desc(EscalaSalva.data_salva))
    if mes:
        query = query.where(EscalaSalva.mes == mes)
    if ano:
        query = query.where(EscalaSalva.ano == ano)
    
    return jsonify(paginate_response(query, page, per_page, EscalaSalvaSchema()))


@api_bp.route('/escalas-salvas/<int:id>', methods=['GET'])
@jwt_required()
def get_escala_salva(id):
    data = escala_salva_service.carregar_escala(id)
    if not data:
        return jsonify(error='Not Found', message='Escala salva não encontrada'), 404
    return jsonify(data)


@api_bp.route('/escalas-salvas', methods=['POST'])
@jwt_required()
def create_escala_salva():
    data = request.get_json()
    if not data or not data.get('nome') or not data.get('mes') or not data.get('ano'):
        return jsonify(error='Bad Request', message='Nome, mês e ano são obrigatórios'), 400
    
    escala = escala_salva_service.salvar_escala_atual(
        data['nome'], data['mes'], data['ano'],
        data.get('itens', []), data.get('meta')
    )
    return jsonify(EscalaSalvaSchema().dump(escala)), 201


@api_bp.route('/escalas-salvas/<int:id>/ativar', methods=['POST'])
@jwt_required()
def ativar_escala_salva(id):
    result = escala_salva_service.ativar_escala(id)
    if not result:
        return jsonify(error='Not Found', message='Escala salva não encontrada'), 404
    return jsonify(message='Escala ativada com sucesso')


# Viaturas API
@api_bp.route('/viaturas', methods=['GET'])
@jwt_required()
@limiter.limit('100 per minute')
def get_viaturas():
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 20, type=int), 100)
    situacao = request.args.get('situacao')
    municipio = request.args.get('municipio')
    
    query = db.select(Viatura).order_by(Viatura.prefixo)
    if situacao:
        query = query.where(Viatura.situacao == situacao)
    if municipio:
        query = query.where(Viatura.municipio == municipio)
    
    schema = Schema.from_dict({c.name: fields.Str() for c in Viatura.__table__.columns})
    return jsonify(paginate_response(query, page, per_page, schema()))


# Municípios API
@api_bp.route('/municipios', methods=['GET'])
@jwt_required()
@limiter.limit('100 per minute')
def get_municipios():
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 20, type=int), 100)
    uf = request.args.get('uf')
    
    query = db.select(Municipio).order_by(Municipio.nome)
    if uf:
        query = query.where(Municipio.uf == uf)
    
    schema = Schema.from_dict({c.name: fields.Str() for c in Municipio.__table__.columns})
    return jsonify(paginate_response(query, page, per_page, schema()))


# Cargo API
@api_bp.route('/cargos', methods=['GET'])
@jwt_required()
@limiter.limit('100 per minute')
def get_cargos():
    cargos = Cargo.query.order_by(Cargo.posto_grad).all()
    return jsonify([c.to_dict() for c in cargos])


# OPM API
@api_bp.route('/opms', methods=['GET'])
@jwt_required()
@limiter.limit('100 per minute')
def get_opms():
    opms = OPM.query.order_by(OPM.opm_sigla).all()
    return jsonify([o.to_dict() for o in opms])


# Backup API
@api_bp.route('/backup', methods=['POST'])
@jwt_required()
def create_backup():
    claims = get_jwt()
    if claims.get('tipo') != 'ADMIN':
        return jsonify(error='Forbidden', message='Apenas administradores'), 403
    
    from app.services import backup_service
    from app import current_app
    
    database_url = current_app.config['SQLALCHEMY_DATABASE_URI']
    try:
        filepath = backup_service.backup_postgresql(database_url)
        return jsonify(message='Backup criado', file=filepath), 200
    except Exception as e:
        return jsonify(error='Backup failed', message=str(e)), 500


@api_bp.route('/backups', methods=['GET'])
@jwt_required()
def list_backups():
    claims = get_jwt()
    if claims.get('tipo') != 'ADMIN':
        return jsonify(error='Forbidden', message='Apenas administradores'), 403
    
    from app.services import backup_service
    backups = backup_service.list_backups()
    return jsonify(backups)


# Health check
@api_bp.route('/health', methods=['GET'])
def health_check():
    return jsonify(status='healthy', service='SISPM API'), 200