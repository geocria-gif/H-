from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from sqlalchemy import desc
from app import db
from app.models import Ocorrencia, Viatura, Municipio
from app.forms import OcorrenciaForm, ViaturaForm, MunicipioForm
from app.services import ocorrencia_service

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
    municipios = [m.to_dict() for m in Municipio.query.order_by(Municipio.nome).all()]
    ocorrencias = [
        o.to_dict() for o in Ocorrencia.query.order_by(desc(Ocorrencia.data_hora)).all()
    ]
    return render_template('ocorrencia/mapa.html',
                           municipios_json=municipios,
                           ocorrencias_json=ocorrencias)


@ocorrencia_bp.route('/estatisticas')
@login_required
def estatisticas():
    data_inicio = request.args.get('data_inicio')
    data_fim = request.args.get('data_fim')
    
    stats = ocorrencia_service.get_estatisticas(data_inicio, data_fim)
    return render_template('ocorrencia/estatisticas.html', stats=stats)


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