from app import db
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
import json


class Usuario(db.Model):
    __tablename__ = 'tbUsuario'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    matricula = db.Column(db.String(20), unique=True, nullable=False, index=True)
    nome = db.Column(db.String(200), nullable=False)
    _senha = db.Column('senha', db.String(255), nullable=False)
    tipo = db.Column(db.String(20), nullable=False, default='USER')
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)
    ultimo_login = db.Column(db.DateTime)
    ativo = db.Column(db.Boolean, default=True)
    
    TIPOS = ['ADMIN', 'SUPERVISOR', 'OPERADOR', 'VISITANTE']
    
    def set_senha(self, senha):
        self._senha = generate_password_hash(senha)
    
    def check_senha(self, senha):
        return check_password_hash(self._senha, senha)
    
    @property
    def is_admin(self):
        return self.tipo == 'ADMIN'
    
    @property
    def is_supervisor(self):
        return self.tipo in ['ADMIN', 'SUPERVISOR']
    
    @property
    def is_operador(self):
        return self.tipo in ['ADMIN', 'SUPERVISOR', 'OPERADOR']
    
    def to_dict(self):
        return {
            'id': self.id,
            'matricula': self.matricula,
            'nome': self.nome,
            'tipo': self.tipo,
            'criado_em': self.criado_em.isoformat() if self.criado_em else None,
            'ultimo_login': self.ultimo_login.isoformat() if self.ultimo_login else None,
            'ativo': self.ativo
        }
    
    def __repr__(self):
        return f'<Usuario {self.matricula} - {self.nome}>'


class Cargo(db.Model):
    __tablename__ = 'tbCargo'
    
    cargo_id = db.Column('CargoId', db.String(20), primary_key=True)
    posto_grad = db.Column('PostoGrad', db.String(100))
    tipo_servidor = db.Column('TipoServidor', db.String(50))
    tipo_militar = db.Column('TipoMilitar', db.String(50))
    classif_of = db.Column('ClassifOf', db.String(50))
    
    efetivos = db.relationship('EfetivoPM', back_populates='cargo_rel')
    valores = db.relationship('TabelaValores', back_populates='posto_grad_rel')
    
    def to_dict(self):
        return {
            'cargo_id': self.cargo_id,
            'posto_grad': self.posto_grad,
            'tipo_servidor': self.tipo_servidor,
            'tipo_militar': self.tipo_militar,
            'classif_of': self.classif_of
        }
    
    def __repr__(self):
        return f'<Cargo {self.cargo_id} - {self.posto_grad}>'


class OPM(db.Model):
    __tablename__ = 'tbOPM'
    
    opm_id = db.Column('OpmId', db.String(20), primary_key=True)
    opm_desc = db.Column('OpmDesc', db.String(200))
    opm_sigla = db.Column('OpmSigla', db.String(50))
    opm_ordem = db.Column('OpmOrdem', db.Integer)
    opm_atv = db.Column('OpmAtv', db.String(10))
    opm_regiao = db.Column('OpmRegiao', db.String(50))
    opm_municipio = db.Column('OpmMunicipio', db.String(100))
    opm_bairro = db.Column('OpmBairro', db.String(100))
    comandante = db.Column('Comandante', db.String(200))
    funcao = db.Column('Funcao', db.String(100))
    
    efetivos = db.relationship('EfetivoPM', back_populates='opm_rel')
    opm_eventos = db.relationship('OpmEvento', back_populates='opm_rel')
    escalas_p2 = db.relationship('EscalaP2', back_populates='opm_rel')
    
    def to_dict(self):
        return {
            'opm_id': self.opm_id,
            'opm_desc': self.opm_desc,
            'opm_sigla': self.opm_sigla,
            'opm_ordem': self.opm_ordem,
            'opm_atv': self.opm_atv,
            'opm_regiao': self.opm_regiao,
            'opm_municipio': self.opm_municipio,
            'opm_bairro': self.opm_bairro,
            'comandante': self.comandante,
            'funcao': self.funcao
        }
    
    def __repr__(self):
        return f'<OPM {self.opm_id} - {self.opm_sigla}>'


class EfetivoPM(db.Model):
    __tablename__ = 'tbEfetivoPM'
    
    matricula = db.Column('Matricula', db.String(20), primary_key=True)
    nome = db.Column('Nome', db.String(200), nullable=False, index=True)
    cargo = db.Column('Cargo', db.String(20), db.ForeignKey('tbCargo.CargoId'))
    opm_id = db.Column('OpmId', db.String(20), db.ForeignKey('tbOPM.OpmId'))
    sit = db.Column('Sit', db.String(10))
    f6 = db.Column('F6', db.String(10))
    lc_trab_desc = db.Column('LcTrabDesc', db.String(200))
    cpf = db.Column('CPF', db.String(14))
    rg = db.Column('RG', db.String(20))
    titulo = db.Column('Titulo', db.String(20))
    cnh = db.Column('CNH', db.String(20))
    categoria = db.Column('Categoria', db.String(10))
    tipo_sanguineo = db.Column('TipoSanguineo', db.String(5))
    funcao = db.Column('Funcao', db.String(100))
    telefone = db.Column('Telefone', db.String(20))
    admissao = db.Column('Admissao', db.String(10))
    data_nascimento = db.Column('DataNascimento', db.String(10))
    local_trabalho = db.Column('LocalTrabalho', db.String(200))
    comportamento = db.Column('Comportamento', db.String(10))
    
    cargo_rel = db.relationship('Cargo', back_populates='efetivos')
    opm_rel = db.relationship('OPM', back_populates='efetivos')
    escalas = db.relationship('Escala', back_populates='militar')
    escalas_p2 = db.relationship('EscalaP2', back_populates='militar')
    escalas_salvas = db.relationship('EscalaSalvaItem', back_populates='militar')
    
    @property
    def posto_grad(self):
        return self.cargo_rel.posto_grad if self.cargo_rel else None
    
    @property
    def opm_sigla(self):
        return self.opm_rel.opm_sigla if self.opm_rel else None
    
    def to_dict(self):
        return {
            'matricula': self.matricula,
            'nome': self.nome,
            'cargo': self.cargo,
            'posto_grad': self.posto_grad,
            'opm_id': self.opm_id,
            'opm_sigla': self.opm_sigla,
            'sit': self.sit,
            'funcao': self.funcao,
            'telefone': self.telefone
        }
    
    def __repr__(self):
        return f'<EfetivoPM {self.matricula} - {self.nome}>'


class Evento(db.Model):
    __tablename__ = 'tbEvento'
    
    evento_id = db.Column('EventoId', db.Integer, primary_key=True, autoincrement=True)
    evento_desc = db.Column('EventoDesc', db.String(200), nullable=False)
    evento_dta_inicio = db.Column('EventoDtaInicio', db.String(10))
    evento_dta_fim = db.Column('EventoDtaFim', db.String(10))
    campo1 = db.Column('Campo1', db.Text)
    tipo_pagamento = db.Column('TipoPagamento', db.String(10), default='HE')
    
    opm_eventos = db.relationship('OpmEvento', back_populates='evento', cascade='all, delete-orphan')
    escalas = db.relationship('Escala', back_populates='evento', cascade='all, delete-orphan')
    
    TIPOS_PAGAMENTO = ['HE', 'VD', 'SO']
    
    @property
    def data_inicio(self):
        if self.evento_dta_inicio:
            try:
                return datetime.strptime(self.evento_dta_inicio, '%Y-%m-%d').date()
            except:
                return None
        return None
    
    @property
    def data_fim(self):
        if self.evento_dta_fim:
            try:
                return datetime.strptime(self.evento_dta_fim, '%Y-%m-%d').date()
            except:
                return None
        return None
    
    def to_dict(self):
        return {
            'evento_id': self.evento_id,
            'evento_desc': self.evento_desc,
            'evento_dta_inicio': self.evento_dta_inicio,
            'evento_dta_fim': self.evento_dta_fim,
            'campo1': self.campo1,
            'tipo_pagamento': self.tipo_pagamento
        }
    
    def __repr__(self):
        return f'<Evento {self.evento_id} - {self.evento_desc}>'


class OpmEvento(db.Model):
    __tablename__ = 'tbOpmEvento'
    
    opm_evento_id = db.Column('OpmEventoId', db.Integer, primary_key=True, autoincrement=True)
    evento_id = db.Column('EventoId', db.Integer, db.ForeignKey('tbEvento.EventoId', ondelete='CASCADE'), nullable=False)
    opm_id = db.Column('OpmId', db.String(20), db.ForeignKey('tbOPM.OpmId'), nullable=False)
    
    evento = db.relationship('Evento', back_populates='opm_eventos')
    opm_rel = db.relationship('OPM', back_populates='opm_eventos')
    escalas = db.relationship('Escala', back_populates='opm_evento', cascade='all, delete-orphan')
    
    __table_args__ = (db.UniqueConstraint('EventoId', 'OpmId', name='unique_evento_opm'),)
    
    def to_dict(self):
        return {
            'opm_evento_id': self.opm_evento_id,
            'evento_id': self.evento_id,
            'opm_id': self.opm_id,
            'evento_desc': self.evento.evento_desc if self.evento else None,
            'opm_sigla': self.opm_rel.opm_sigla if self.opm_rel else None
        }
    
    def __repr__(self):
        return f'<OpmEvento {self.opm_evento_id}>'


class Escala(db.Model):
    __tablename__ = 'tbEscala'
    
    opm_evento_id = db.Column('OpmEventoId', db.Integer, db.ForeignKey('tbOpmEvento.OpmEventoId', ondelete='CASCADE'), primary_key=True)
    matricula = db.Column('Matricula', db.String(20), db.ForeignKey('tbEfetivoPM.Matricula'), primary_key=True)
    escala_data = db.Column('EscalaData', db.String(10), primary_key=True)
    escala_ch_diurna = db.Column('EscalaCHDiurna', db.Float, default=0)
    escala_ch_noturna = db.Column('EscalaCHNoturna', db.Float, default=0)
    hora_inicio = db.Column('HoraInicio', db.String(5))
    hora_fim = db.Column('HoraFim', db.String(5))
    tipo_pagamento = db.Column('TipoPagamento', db.String(10), default='HE')
    
    opm_evento = db.relationship('OpmEvento', back_populates='escalas')
    militar = db.relationship('EfetivoPM', back_populates='escalas')
    
    @property
    def ch_total(self):
        return (self.escala_ch_diurna or 0) + (self.escala_ch_noturna or 0)
    
    def to_dict(self):
        return {
            'opm_evento_id': self.opm_evento_id,
            'matricula': self.matricula,
            'escala_data': self.escala_data,
            'escala_ch_diurna': self.escala_ch_diurna,
            'escala_ch_noturna': self.escala_ch_noturna,
            'hora_inicio': self.hora_inicio,
            'hora_fim': self.hora_fim,
            'tipo_pagamento': self.tipo_pagamento,
            'ch_total': self.ch_total,
            'militar_nome': self.militar.nome if self.militar else None,
            'militar_posto': self.militar.posto_grad if self.militar else None
        }
    
    def __repr__(self):
        return f'<Escala {self.matricula} - {self.escala_data}>'


class TabelaValores(db.Model):
    __tablename__ = 'tbTabelaValores'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    posto_grad = db.Column('PostoGrad', db.String(100), unique=True, nullable=False)
    he_diurna = db.Column('HEDiurna', db.Float, default=0)
    ad_he_noturna = db.Column('AdHENoturna', db.Float, default=0)
    vd_diurno = db.Column('VDDiurno', db.Float, default=0)
    vd_noturno = db.Column('VDNoturno', db.Float, default=0)
    
    posto_grad_rel = db.relationship('Cargo', back_populates='valores')
    
    def to_dict(self):
        return {
            'id': self.id,
            'posto_grad': self.posto_grad,
            'he_diurna': self.he_diurna,
            'ad_he_noturna': self.ad_he_noturna,
            'vd_diurno': self.vd_diurno,
            'vd_noturno': self.vd_noturno
        }
    
    def __repr__(self):
        return f'<TabelaValores {self.posto_grad}>'


class EscalaP2(db.Model):
    __tablename__ = 'tbEscalaP2'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    mes = db.Column('Mes', db.Integer, nullable=False)
    ano = db.Column('Ano', db.Integer, nullable=False)
    funcao = db.Column('Funcao', db.String(100), nullable=False)
    opm = db.Column('OPM', db.String(100), nullable=False)
    gh = db.Column('GH', db.String(50), nullable=False)
    nome = db.Column('Nome', db.String(200), nullable=False)
    matricula = db.Column('Matricula', db.String(20), db.ForeignKey('tbEfetivoPM.Matricula'), nullable=False)
    telefone = db.Column('Telefone', db.String(20))
    dias = db.Column('Dias', db.Text, default='{}')
    is_separador = db.Column('IsSeparador', db.Integer, default=0)
    separador_texto = db.Column('SeparadorTexto', db.String(200))
    ordem = db.Column('Ordem', db.Integer, default=0)
    tipo_pagamento = db.Column('TipoPagamento', db.String(10), default='HE')
    
    militar = db.relationship('EfetivoPM', back_populates='escalas_p2')
    opm_rel = db.relationship('OPM', foreign_keys=[opm], primaryjoin='EscalaP2.opm==OPM.opm_sigla', back_populates='escalas_p2')
    
    @property
    def dias_dict(self):
        try:
            return json.loads(self.dias) if self.dias else {}
        except:
            return {}
    
    @dias_dict.setter
    def dias_dict(self, value):
        self.dias = json.dumps(value, ensure_ascii=False)
    
    def to_dict(self):
        return {
            'id': self.id,
            'mes': self.mes,
            'ano': self.ano,
            'funcao': self.funcao,
            'opm': self.opm,
            'gh': self.gh,
            'nome': self.nome,
            'matricula': self.matricula,
            'telefone': self.telefone,
            'dias': self.dias_dict,
            'is_separador': bool(self.is_separador),
            'separador_texto': self.separador_texto,
            'ordem': self.ordem,
            'tipo_pagamento': self.tipo_pagamento
        }
    
    def __repr__(self):
        return f'<EscalaP2 {self.id} - {self.nome} {self.mes}/{self.ano}>'


class EscalaP2Meta(db.Model):
    __tablename__ = 'tbEscalaP2Meta'
    
    id = db.Column(db.Integer, primary_key=True, default=1)
    mes = db.Column('Mes', db.Integer)
    ano = db.Column('Ano', db.Integer)
    local = db.Column('Local', db.String(100), default='IRECÊ')
    responsavel = db.Column('Responsavel', db.String(200))
    cargo = db.Column('Cargo', db.String(200))
    emissao = db.Column('Emissao', db.String(10))
    nota = db.Column('Nota', db.Text)
    titulo = db.Column('Titulo', db.String(200), default='ESCALA DE COORDENADOR REGIONAL DO CPR-CN')
    
    def to_dict(self):
        return {
            'id': self.id,
            'mes': self.mes,
            'ano': self.ano,
            'local': self.local,
            'responsavel': self.responsavel,
            'cargo': self.cargo,
            'emissao': self.emissao,
            'nota': self.nota,
            'titulo': self.titulo
        }
    
    def __repr__(self):
        return f'<EscalaP2Meta {self.mes}/{self.ano}>'


class EscalaP2Legenda(db.Model):
    __tablename__ = 'tbEscalaP2Legenda'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    codigo = db.Column('Codigo', db.String(10), nullable=False)
    descricao = db.Column('Descricao', db.String(100), nullable=False)
    
    def to_dict(self):
        return {'id': self.id, 'codigo': self.codigo, 'descricao': self.descricao}
    
    def __repr__(self):
        return f'<EscalaP2Legenda {self.codigo} - {self.descricao}>'


class Ocorrencia(db.Model):
    __tablename__ = 'tbOcorrencia'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    tipo = db.Column('Tipo', db.String(50), nullable=False)
    data_hora = db.Column('DataHora', db.String(30), nullable=False)
    cidade = db.Column('Cidade', db.String(100))
    latitude = db.Column('Latitude', db.Float)
    longitude = db.Column('Longitude', db.Float)
    vtr = db.Column('VTR', db.String(50))
    descricao = db.Column('Descricao', db.Text)
    dados_relevantes = db.Column('DadosRelevantes', db.Text)
    created_at = db.Column('CreatedAt', db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'tipo': self.tipo,
            'data_hora': self.data_hora,
            'cidade': self.cidade,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'vtr': self.vtr,
            'descricao': self.descricao,
            'dados_relevantes': self.dados_relevantes,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    def __repr__(self):
        return f'<Ocorrencia {self.id} - {self.tipo}>'


class Viatura(db.Model):
    __tablename__ = 'tbViatura'
    
    prefixo = db.Column('Prefixo', db.String(20), primary_key=True)
    item = db.Column('Item', db.Integer)
    placa = db.Column('Placa', db.String(10))
    chassi = db.Column('Chassi', db.String(50))
    renavam = db.Column('Renavam', db.String(20))
    patrimonio = db.Column('Patrimonio', db.String(20))
    cod_secretaria = db.Column('CodSecretaria', db.String(20))
    cod_unidade_gestora = db.Column('CodUnidadeGestora', db.String(20))
    municipio = db.Column('Municipio', db.String(100))
    combustivel = db.Column('Combustivel', db.String(20))
    marca = db.Column('Marca', db.String(50))
    modelo = db.Column('Modelo', db.String(50))
    ano_modelo = db.Column('AnoModelo', db.Integer)
    ano_fabricacao = db.Column('AnoFabricacao', db.Integer)
    cor = db.Column('Cor', db.String(20))
    propriedade = db.Column('Propriedade', db.String(20))
    situacao = db.Column('Situacao', db.String(20))
    unidade = db.Column('Unidade', db.String(100))
    telefone = db.Column('Telefone', db.String(20))
    
    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}
    
    def __repr__(self):
        return f'<Viatura {self.prefixo} - {self.placa}>'


class Municipio(db.Model):
    __tablename__ = 'tbMunicipio'
    
    id = db.Column('Id', db.Integer, primary_key=True)
    nome = db.Column('Nome', db.String(100), nullable=False)
    uf = db.Column('UF', db.String(2), default='BA')
    regiao = db.Column('Regiao', db.String(50))
    latitude = db.Column('Latitude', db.Float)
    longitude = db.Column('Longitude', db.Float)
    codigo_ibge = db.Column('CodigoIBGE', db.String(10))
    area = db.Column('Area', db.Float)
    cep = db.Column('CEP', db.String(10))
    populacao = db.Column('Populacao', db.Integer)
    dist_irece = db.Column('DistIrece', db.Float)
    prefeito = db.Column('Prefeito', db.String(100))
    partido = db.Column('Partido', db.String(50))
    
    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}
    
    def __repr__(self):
        return f'<Municipio {self.nome}>'


class OcorrenciaEvento(db.Model):
    __tablename__ = 'tbOcorrenciaEvento'
    
    data_ref = db.Column('DataRef', db.String(10), primary_key=True)
    grupo = db.Column('Grupo', db.String(100), nullable=False)
    metrica = db.Column('Metrica', db.String(100), nullable=False)
    valor = db.Column('Valor', db.Float)
    ordem_grupo = db.Column('OrdemGrupo', db.Integer, default=0)
    ordem_metrica = db.Column('OrdemMetrica', db.Integer, default=0)
    
    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class OcorrenciaMeta(db.Model):
    __tablename__ = 'tbOcorrenciaMeta'
    
    data_ref = db.Column('DataRef', db.String(10), primary_key=True)
    source_id = db.Column('SourceId', db.String(100))
    sheet_name = db.Column('SheetName', db.String(100))
    operation_title = db.Column('OperationTitle', db.String(200))
    category = db.Column('Category', db.String(100))
    subtitle = db.Column('Subtitle', db.String(200))
    source_type = db.Column('SourceType', db.String(50))
    highlights_json = db.Column('HighlightsJson', db.Text)


class OcorrenciaConfig(db.Model):
    __tablename__ = 'tbOcorrenciaConfig'
    
    chave = db.Column('Chave', db.String(100), primary_key=True)
    valor = db.Column('Valor', db.Text)


class EscalaSalva(db.Model):
    __tablename__ = 'tbEscalaSalva'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    nome = db.Column('Nome', db.String(200), nullable=False)
    mes = db.Column('Mes', db.Integer, nullable=False)
    ano = db.Column('Ano', db.Integer, nullable=False)
    data_salva = db.Column('DataSalva', db.DateTime, default=datetime.utcnow)
    ativa = db.Column('Ativa', db.Integer, default=0)
    
    itens = db.relationship('EscalaSalvaItem', back_populates='escala_salva', cascade='all, delete-orphan')
    meta = db.relationship('EscalaSalvaMeta', back_populates='escala_salva', cascade='all, delete-orphan', uselist=False)
    
    def to_dict(self):
        return {
            'id': self.id,
            'nome': self.nome,
            'mes': self.mes,
            'ano': self.ano,
            'data_salva': self.data_salva.isoformat() if self.data_salva else None,
            'ativa': bool(self.ativa)
        }
    
    def __repr__(self):
        return f'<EscalaSalva {self.id} - {self.nome}>'


class EscalaSalvaItem(db.Model):
    __tablename__ = 'tbEscalaSalvaItem'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    escala_salva_id = db.Column('EscalaSalvaId', db.Integer, db.ForeignKey('tbEscalaSalva.Id', ondelete='CASCADE'), nullable=False)
    funcao = db.Column('Funcao', db.String(100), nullable=False)
    opm = db.Column('OPM', db.String(100), nullable=False)
    gh = db.Column('GH', db.String(50), nullable=False)
    nome = db.Column('Nome', db.String(200), nullable=False)
    matricula = db.Column('Matricula', db.String(20), db.ForeignKey('tbEfetivoPM.Matricula'), nullable=False)
    telefone = db.Column('Telefone', db.String(20))
    dias = db.Column('Dias', db.Text, default='{}')
    tipo_pagamento = db.Column('TipoPagamento', db.String(10), default='HE')
    is_separador = db.Column('IsSeparador', db.Integer, default=0)
    separador_texto = db.Column('SeparadorTexto', db.String(200))
    ordem = db.Column('Ordem', db.Integer, default=0)
    
    escala_salva = db.relationship('EscalaSalva', back_populates='itens')
    militar = db.relationship('EfetivoPM', back_populates='escalas_salvas')
    
    @property
    def dias_dict(self):
        try:
            return json.loads(self.dias) if self.dias else {}
        except:
            return {}
    
    @dias_dict.setter
    def dias_dict(self, value):
        self.dias = json.dumps(value, ensure_ascii=False)
    
    def to_dict(self):
        return {
            'id': self.id,
            'escala_salva_id': self.escala_salva_id,
            'funcao': self.funcao,
            'opm': self.opm,
            'gh': self.gh,
            'nome': self.nome,
            'matricula': self.matricula,
            'telefone': self.telefone,
            'dias': self.dias_dict,
            'tipo_pagamento': self.tipo_pagamento,
            'is_separador': bool(self.is_separador),
            'separador_texto': self.separador_texto,
            'ordem': self.ordem
        }


class EscalaSalvaMeta(db.Model):
    __tablename__ = 'tbEscalaSalvaMeta'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    escala_salva_id = db.Column('EscalaSalvaId', db.Integer, db.ForeignKey('tbEscalaSalva.Id', ondelete='CASCADE'), nullable=False)
    local = db.Column('Local', db.String(100), default='IRECÊ')
    responsavel = db.Column('Responsavel', db.String(200))
    cargo = db.Column('Cargo', db.String(200))
    emissao = db.Column('Emissao', db.String(10))
    nota = db.Column('Nota', db.Text)
    titulo = db.Column('Titulo', db.String(200), default='ESCALA DE COORDENADOR REGIONAL DO CPR-CN')
    
    escala_salva = db.relationship('EscalaSalva', back_populates='meta')
    
    def to_dict(self):
        return {
            'id': self.id,
            'escala_salva_id': self.escala_salva_id,
            'local': self.local,
            'responsavel': self.responsavel,
            'cargo': self.cargo,
            'emissao': self.emissao,
            'nota': self.nota,
            'titulo': self.titulo
        }