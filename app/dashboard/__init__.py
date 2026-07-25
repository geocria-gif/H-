from flask import Blueprint, render_template
from flask_login import login_required
from sqlalchemy import func, desc
from app import db
from app.models import (
    Usuario, EfetivoPM, Cargo, OPM, Evento, OpmEvento, Escala,
    TabelaValores, EscalaP2, EscalaP2Meta, EscalaP2Legenda,
    Ocorrencia, Viatura, Municipio, EscalaSalva, EscalaSalvaItem, EscalaSalvaMeta
)

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