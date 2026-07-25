from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SelectField, TextAreaField, IntegerField, FloatField, DateField, BooleanField, HiddenField, SubmitField, FileField
from wtforms.validators import DataRequired, Email, Length, EqualTo, Optional, NumberRange, ValidationError
from wtforms.widgets import TextArea
from app.models import Usuario, Cargo, OPM, EfetivoPM, Evento, TabelaValores, EscalaP2, EscalaP2Meta, EscalaP2Legenda, Ocorrencia, Viatura, Municipio, EscalaSalva
from app import db


class LoginForm(FlaskForm):
    matricula = StringField('Matrícula', validators=[DataRequired(), Length(min=1, max=20)])
    senha = PasswordField('Senha', validators=[DataRequired()])
    remember_me = BooleanField('Lembrar-me')
    submit = SubmitField('Entrar')


class RegisterForm(FlaskForm):
    matricula = StringField('Matrícula', validators=[DataRequired(), Length(max=20)])
    nome = StringField('Nome', validators=[DataRequired(), Length(max=200)])
    senha = PasswordField('Senha', validators=[DataRequired(), Length(min=6)])
    confirmar_senha = PasswordField('Confirmar Senha', validators=[DataRequired(), EqualTo('senha')])
    tipo = SelectField('Tipo', choices=[
        ('OPERADOR', 'Operador'),
        ('SUPERVISOR', 'Supervisor'),
        ('VISITANTE', 'Visitante')
    ], default='OPERADOR')
    submit = SubmitField('Cadastrar')
    
    def validate_matricula(self, field):
        if db.session.get(Usuario, field.data):
            raise ValidationError('Matrícula já cadastrada.')


class UsuarioForm(FlaskForm):
    matricula = StringField('Matrícula', validators=[DataRequired(), Length(max=20)])
    nome = StringField('Nome', validators=[DataRequired(), Length(max=200)])
    senha = PasswordField('Nova Senha', validators=[Optional(), Length(min=6)])
    confirmar_senha = PasswordField('Confirmar Senha', validators=[Optional(), EqualTo('senha')])
    tipo = SelectField('Tipo', choices=[
        ('ADMIN', 'Administrador'),
        ('SUPERVISOR', 'Supervisor'),
        ('OPERADOR', 'Operador'),
        ('VISITANTE', 'Visitante')
    ], default='OPERADOR')
    ativo = BooleanField('Ativo', default=True)
    submit = SubmitField('Salvar')
    
    def __init__(self, *args, **kwargs):
        self.user_id = kwargs.pop('user_id', None)
        super().__init__(*args, **kwargs)
    
    def validate_matricula(self, field):
        user = db.session.execute(
            db.select(Usuario).where(Usuario.matricula == field.data)
        ).scalar_one_or_none()
        if user and user.id != self.user_id:
            raise ValidationError('Matrícula já cadastrada.')


class CargoForm(FlaskForm):
    cargo_id = StringField('Código', validators=[DataRequired(), Length(max=20)])
    posto_grad = StringField('Posto/Graduação', validators=[DataRequired(), Length(max=100)])
    tipo_servidor = SelectField('Tipo Servidor', choices=[
        ('MILITAR', 'Militar'),
        ('CIVIL', 'Civil')
    ], default='MILITAR')
    tipo_militar = SelectField('Tipo Militar', choices=[
        ('OFICIAL', 'Oficial'),
        ('PRACA', 'Praça')
    ], default='PRACA')
    classif_of = StringField('Classificação', validators=[Optional(), Length(max=50)])
    submit = SubmitField('Salvar')


class OPMForm(FlaskForm):
    opm_id = StringField('Código OPM', validators=[DataRequired(), Length(max=20)])
    opm_desc = StringField('Descrição', validators=[DataRequired(), Length(max=200)])
    opm_sigla = StringField('Sigla', validators=[DataRequired(), Length(max=50)])
    opm_ordem = IntegerField('Ordem', validators=[Optional()])
    opm_atv = SelectField('Atividade', choices=[
        ('FIM', 'Fim'),
        ('MEIO', 'Meio')
    ], default='FIM')
    opm_regiao = StringField('Região', validators=[Optional(), Length(max=50)])
    opm_municipio = StringField('Município', validators=[Optional(), Length(max=100)])
    opm_bairro = StringField('Bairro', validators=[Optional(), Length(max=100)])
    comandante = StringField('Comandante', validators=[Optional(), Length(max=200)])
    funcao = StringField('Função', validators=[Optional(), Length(max=100)])
    submit = SubmitField('Salvar')


class EfetivoPMForm(FlaskForm):
    matricula = StringField('Matrícula', validators=[DataRequired(), Length(max=20)])
    nome = StringField('Nome', validators=[DataRequired(), Length(max=200)])
    cargo = SelectField('Cargo', coerce=str, validators=[DataRequired()])
    opm_id = SelectField('OPM', coerce=str, validators=[DataRequired()])
    sit = SelectField('Situação', choices=[
        ('ATIVO', 'Ativo'),
        ('RESERVA', 'Reserva'),
        ('LICENCA', 'Licença'),
        ('AFASTADO', 'Afastado')
    ], default='ATIVO')
    f6 = SelectField('F6', choices=[
        ('SIM', 'Sim'),
        ('NAO', 'Não')
    ], default='NAO')
    lc_trab_desc = StringField('Local Trabalho', validators=[Optional(), Length(max=200)])
    cpf = StringField('CPF', validators=[Optional(), Length(max=14)])
    rg = StringField('RG', validators=[Optional(), Length(max=20)])
    titulo = StringField('Título', validators=[Optional(), Length(max=20)])
    cnh = StringField('CNH', validators=[Optional(), Length(max=20)])
    categoria = StringField('Categoria CNH', validators=[Optional(), Length(max=10)])
    tipo_sanguineo = SelectField('Tipo Sanguíneo', choices=[
        ('', 'Selecione'),
        ('A+', 'A+'), ('A-', 'A-'),
        ('B+', 'B+'), ('B-', 'B-'),
        ('AB+', 'AB+'), ('AB-', 'AB-'),
        ('O+', 'O+'), ('O-', 'O-')
    ], validators=[Optional()])
    funcao = StringField('Função', validators=[Optional(), Length(max=100)])
    telefone = StringField('Telefone', validators=[Optional(), Length(max=20)])
    admissao = StringField('Admissão (YYYY-MM-DD)', validators=[Optional()])
    data_nascimento = StringField('Data Nasc. (YYYY-MM-DD)', validators=[Optional()])
    local_trabalho = StringField('Local Trabalho', validators=[Optional(), Length(max=200)])
    comportamento = SelectField('Comportamento', choices=[
        ('BOM', 'Bom'),
        ('REGULAR', 'Regular'),
        ('RUIM', 'Ruim')
    ], default='BOM')
    submit = SubmitField('Salvar')
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.cargo.choices = [(c.cargo_id, f'{c.posto_grad} ({c.cargo_id})') for c in Cargo.query.order_by(Cargo.posto_grad).all()]
        self.opm_id.choices = [(o.opm_id, f'{o.opm_sigla} - {o.opm_desc}') for o in OPM.query.order_by(OPM.opm_sigla).all()]


class EventoForm(FlaskForm):
    evento_desc = StringField('Descrição', validators=[DataRequired(), Length(max=200)])
    evento_dta_inicio = DateField('Data Início', format='%Y-%m-%d', validators=[DataRequired()])
    evento_dta_fim = DateField('Data Fim', format='%Y-%m-%d', validators=[DataRequired()])
    campo1 = TextAreaField('Observações', validators=[Optional()])
    tipo_pagamento = SelectField('Tipo Pagamento', choices=[
        ('HE', 'Hora Extra'),
        ('VD', 'Vale Transporte'),
        ('SO', 'Serviço Ordinário')
    ], default='HE')
    submit = SubmitField('Salvar')


class OpmEventoForm(FlaskForm):
    evento_id = SelectField('Evento', coerce=int, validators=[DataRequired()])
    opm_id = SelectField('OPM', coerce=str, validators=[DataRequired()])
    submit = SubmitField('Adicionar')
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.evento_id.choices = [(e.evento_id, e.evento_desc) for e in Evento.query.order_by(Evento.evento_desc).all()]
        self.opm_id.choices = [(o.opm_id, f'{o.opm_sigla} - {o.opm_desc}') for o in OPM.query.order_by(OPM.opm_sigla).all()]


class EscalaForm(FlaskForm):
    opm_evento_id = HiddenField('OPM Evento', validators=[DataRequired()])
    matricula = StringField('Matrícula', validators=[DataRequired()])
    escala_data = DateField('Data', format='%Y-%m-%d', validators=[DataRequired()])
    escala_ch_diurna = FloatField('CH Diurna', validators=[Optional(), NumberRange(min=0)], default=0)
    escala_ch_noturna = FloatField('CH Noturna', validators=[Optional(), NumberRange(min=0)], default=0)
    hora_inicio = StringField('Hora Início (HH:MM)', validators=[Optional(), Length(max=5)])
    hora_fim = StringField('Hora Fim (HH:MM)', validators=[Optional(), Length(max=5)])
    tipo_pagamento = SelectField('Tipo Pagamento', choices=[
        ('HE', 'Hora Extra'),
        ('VD', 'Vale Transporte'),
        ('SO', 'Serviço Ordinário')
    ], default='HE')
    submit = SubmitField('Salvar')


class TabelaValoresForm(FlaskForm):
    posto_grad = SelectField('Posto/Graduação', coerce=str, validators=[DataRequired()])
    he_diurna = FloatField('HE Diurna', validators=[DataRequired(), NumberRange(min=0)], default=0)
    ad_he_noturna = FloatField('Ad. HE Noturna', validators=[DataRequired(), NumberRange(min=0)], default=0)
    vd_diurno = FloatField('VD Diurno', validators=[DataRequired(), NumberRange(min=0)], default=0)
    vd_noturno = FloatField('VD Noturno', validators=[DataRequired(), NumberRange(min=0)], default=0)
    submit = SubmitField('Salvar')
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.posto_grad.choices = [(c.posto_grad, c.posto_grad) for c in Cargo.query.order_by(Cargo.posto_grad).all()]


class EscalaP2Form(FlaskForm):
    mes = IntegerField('Mês', validators=[DataRequired(), NumberRange(min=1, max=12)])
    ano = IntegerField('Ano', validators=[DataRequired(), NumberRange(min=2020, max=2030)])
    funcao = StringField('Função', validators=[DataRequired(), Length(max=100)])
    opm = StringField('OPM', validators=[DataRequired(), Length(max=100)])
    gh = StringField('GH', validators=[DataRequired(), Length(max=50)])
    nome = StringField('Nome', validators=[DataRequired(), Length(max=200)])
    matricula = StringField('Matrícula', validators=[DataRequired(), Length(max=20)])
    telefone = StringField('Telefone', validators=[Optional(), Length(max=20)])
    is_separador = BooleanField('É Separador')
    separador_texto = StringField('Texto Separador', validators=[Optional(), Length(max=200)])
    ordem = IntegerField('Ordem', validators=[Optional()], default=0)
    tipo_pagamento = SelectField('Tipo Pagamento', choices=[
        ('HE', 'Hora Extra'),
        ('VD', 'Vale Transporte'),
        ('SO', 'Serviço Ordinário')
    ], default='HE')
    submit = SubmitField('Salvar')


class EscalaP2MetaForm(FlaskForm):
    mes = IntegerField('Mês', validators=[DataRequired(), NumberRange(min=1, max=12)])
    ano = IntegerField('Ano', validators=[DataRequired(), NumberRange(min=2020, max=2030)])
    local = StringField('Local', validators=[Optional(), Length(max=100)], default='IRECÊ')
    responsavel = StringField('Responsável', validators=[Optional(), Length(max=200)])
    cargo = StringField('Cargo', validators=[Optional(), Length(max=200)])
    emissao = StringField('Emissão (YYYY-MM-DD)', validators=[Optional()])
    nota = TextAreaField('Nota', validators=[Optional()])
    titulo = StringField('Título', validators=[Optional(), Length(max=200)], default='ESCALA DE COORDENADOR REGIONAL DO CPR-CN')
    submit = SubmitField('Salvar')


class EscalaP2LegendaForm(FlaskForm):
    codigo = StringField('Código', validators=[DataRequired(), Length(max=10)])
    descricao = StringField('Descrição', validators=[DataRequired(), Length(max=100)])
    submit = SubmitField('Salvar')


class OcorrenciaForm(FlaskForm):
    tipo = SelectField('Tipo', choices=[
        ('ACIDENTE', 'Acidente de Trânsito'),
        ('ROUBO', 'Roubo/Furto'),
        ('ASSALTO', 'Assalto'),
        ('HOMICIDIO', 'Homicídio'),
        ('OUTRO', 'Outro')
    ], validators=[DataRequired()])
    data_hora = StringField('Data/Hora', validators=[DataRequired()])
    cidade = StringField('Cidade', validators=[Optional(), Length(max=100)])
    latitude = FloatField('Latitude', validators=[Optional()])
    longitude = FloatField('Longitude', validators=[Optional()])
    vtr = StringField('VTR', validators=[Optional(), Length(max=50)])
    descricao = TextAreaField('Descrição', validators=[Optional()])
    dados_relevantes = TextAreaField('Dados Relevantes', validators=[Optional()])
    submit = SubmitField('Registrar')


class ViaturaForm(FlaskForm):
    prefixo = StringField('Prefixo', validators=[DataRequired(), Length(max=20)])
    item = IntegerField('Item', validators=[Optional()])
    placa = StringField('Placa', validators=[Optional(), Length(max=10)])
    chassi = StringField('Chassi', validators=[Optional(), Length(max=50)])
    renavam = StringField('Renavam', validators=[Optional(), Length(max=20)])
    patrimonio = StringField('Patrimônio', validators=[Optional(), Length(max=20)])
    cod_secretaria = StringField('Cod. Secretaria', validators=[Optional(), Length(max=20)])
    cod_unidade_gestora = StringField('Cod. Unidade Gestora', validators=[Optional(), Length(max=20)])
    municipio = StringField('Município', validators=[Optional(), Length(max=100)])
    combustivel = StringField('Combustível', validators=[Optional(), Length(max=20)])
    marca = StringField('Marca', validators=[Optional(), Length(max=50)])
    modelo = StringField('Modelo', validators=[Optional(), Length(max=50)])
    ano_modelo = IntegerField('Ano Modelo', validators=[Optional()])
    ano_fabricacao = IntegerField('Ano Fabricação', validators=[Optional()])
    cor = StringField('Cor', validators=[Optional(), Length(max=20)])
    propriedade = StringField('Propriedade', validators=[Optional(), Length(max=20)])
    situacao = StringField('Situação', validators=[Optional(), Length(max=20)])
    unidade = StringField('Unidade', validators=[Optional(), Length(max=100)])
    telefone = StringField('Telefone', validators=[Optional(), Length(max=20)])
    submit = SubmitField('Salvar')


class MunicipioForm(FlaskForm):
    nome = StringField('Nome', validators=[DataRequired(), Length(max=100)])
    uf = StringField('UF', validators=[Optional(), Length(max=2)], default='BA')
    regiao = StringField('Região', validators=[Optional(), Length(max=50)])
    latitude = FloatField('Latitude', validators=[Optional()])
    longitude = FloatField('Longitude', validators=[Optional()])
    codigo_ibge = StringField('Código IBGE', validators=[Optional(), Length(max=10)])
    area = FloatField('Área', validators=[Optional()])
    cep = StringField('CEP', validators=[Optional(), Length(max=10)])
    populacao = IntegerField('População', validators=[Optional()])
    dist_irece = FloatField('Dist. Irecê', validators=[Optional()])
    prefeito = StringField('Prefeito', validators=[Optional(), Length(max=100)])
    partido = StringField('Partido', validators=[Optional(), Length(max=50)])
    submit = SubmitField('Salvar')


class EscalaSalvaForm(FlaskForm):
    nome = StringField('Nome', validators=[DataRequired(), Length(max=200)])
    mes = IntegerField('Mês', validators=[DataRequired(), NumberRange(min=1, max=12)])
    ano = IntegerField('Ano', validators=[DataRequired(), NumberRange(min=2020, max=2030)])
    submit = SubmitField('Salvar')


class EscalaSalvaItemForm(FlaskForm):
    funcao = StringField('Função', validators=[DataRequired(), Length(max=100)])
    opm = StringField('OPM', validators=[DataRequired(), Length(max=100)])
    gh = StringField('GH', validators=[DataRequired(), Length(max=50)])
    nome = StringField('Nome', validators=[DataRequired(), Length(max=200)])
    matricula = StringField('Matrícula', validators=[DataRequired(), Length(max=20)])
    telefone = StringField('Telefone', validators=[Optional(), Length(max=20)])
    tipo_pagamento = SelectField('Tipo Pagamento', choices=[
        ('HE', 'Hora Extra'),
        ('VD', 'Vale Transporte'),
        ('SO', 'Serviço Ordinário')
    ], default='HE')
    is_separador = BooleanField('É Separador')
    separador_texto = StringField('Texto Separador', validators=[Optional(), Length(max=200)])
    ordem = IntegerField('Ordem', validators=[Optional()], default=0)
    submit = SubmitField('Salvar')


class EscalaSalvaMetaForm(FlaskForm):
    local = StringField('Local', validators=[Optional(), Length(max=100)], default='IRECÊ')
    responsavel = StringField('Responsável', validators=[Optional(), Length(max=200)])
    cargo = StringField('Cargo', validators=[Optional(), Length(max=200)])
    emissao = StringField('Emissão (YYYY-MM-DD)', validators=[Optional()])
    nota = TextAreaField('Nota', validators=[Optional()])
    titulo = StringField('Título', validators=[Optional(), Length(max=200)], default='ESCALA DE COORDENADOR REGIONAL DO CPR-CN')
    submit = SubmitField('Salvar')


class SearchForm(FlaskForm):
    q = StringField('Buscar', validators=[Optional()])
    submit = SubmitField('Buscar')


class RelatorioForm(FlaskForm):
    mes = IntegerField('Mês', validators=[DataRequired(), NumberRange(min=1, max=12)])
    ano = IntegerField('Ano', validators=[DataRequired(), NumberRange(min=2020, max=2030)])
    tipo_pagamento = SelectField('Tipo Pagamento', choices=[
        ('', 'Todos'),
        ('HE', 'Hora Extra'),
        ('VD', 'Vale Transporte'),
        ('SO', 'Serviço Ordinário')
    ], validators=[Optional()])
    opm_id = SelectField('OPM', coerce=str, validators=[Optional()])
    submit = SubmitField('Gerar')
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.opm_id.choices = [('', 'Todas')] + [(o.opm_id, f'{o.opm_sigla} - {o.opm_desc}') for o in OPM.query.order_by(OPM.opm_sigla).all()]


class ImportForm(FlaskForm):
    arquivo = FileField('Arquivo', validators=[DataRequired()])
    tipo = SelectField('Tipo', choices=[
        ('efetivo', 'Efetivo PM'),
        ('evento', 'Eventos'),
        ('escala', 'Escala P2'),
        ('valores', 'Tabela Valores'),
        ('viaturas', 'Viaturas'),
        ('municipios', 'Municípios'),
        ('ocorrencias', 'Ocorrências')
    ], validators=[DataRequired()])
    submit = SubmitField('Importar')


class BackupForm(FlaskForm):
    submit = SubmitField('Gerar Backup')


class RestoreForm(FlaskForm):
    arquivo = FileField('Arquivo de Backup (.sql)', validators=[DataRequired()])
    submit = SubmitField('Restaurar')