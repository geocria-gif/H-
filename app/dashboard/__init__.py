from flask import Blueprint, render_template
from flask_login import login_required
from app import data as d

dashboard_bp = Blueprint('dashboard', __name__, url_prefix='/dashboard')


@dashboard_bp.route('/')
@login_required
def index():
    stats = {
        'total_efetivos': d.count_efetivos(),
        'total_eventos': d.count_eventos(),
        'total_ocorrencias': d.count_ocorrencias(),
        'total_viaturas': len(d.list_all_viaturas()),
        'escalas_ativas': len(d.list_all_escalas_salvas_ativas()),
    }

    ocorrencias_recentes = d.list_ocorrencias_recentes(5)

    from datetime import date
    hoje = date.today().isoformat()
    eventos_proximos = d.list_eventos_proximos(hoje, limit=5)

    ocorrencias_por_tipo = d.list_ocorrencias_por_tipo()

    efetivos_por_opm = []
    for opm in d.list_opms():
        n = d.count_efetivos(where=[('opm_id', '==', opm.opm_id)])
        efetivos_por_opm.append((opm.get('opm_sigla') or opm.opm_id, n))

    municipios = [m.to_dict() for m in d.list_municipios()]

    ocorrencias = [o.to_dict() for o in d.list_all_ocorrencias()]

    return render_template('dashboard/index.html',
                           stats=stats,
                           ocorrencias_recentes=ocorrencias_recentes,
                           eventos_proximos=eventos_proximos,
                           ocorrencias_por_tipo=ocorrencias_por_tipo,
                           efetivos_por_opm=efetivos_por_opm,
                           municipios_json=municipios,
                           ocorrencias_json=ocorrencias)


@dashboard_bp.route('/mapa')
@login_required
def mapa():
    municipios = [m.to_dict() for m in d.list_municipios()]
    ocorrencias = [o.to_dict() for o in d.list_all_ocorrencias()]
    return render_template('dashboard/mapa.html',
                           municipios_json=municipios,
                           ocorrencias_json=ocorrencias)