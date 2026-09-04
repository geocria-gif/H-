"""Blueprint relatorio: relatório de horas, exportação CSV e tabela de valores por posto."""
from flask import Blueprint, render_template, redirect, url_for, flash, request, make_response
from flask_login import login_required, current_user
import csv
import io

from app import data as d
from app.forms import RelatorioForm

relatorio_bp = Blueprint('relatorio', __name__, url_prefix='/relatorio')


def _calcular_valor_militar(militar, ch_diurna, ch_noturna, tipo_pagamento):
    """Calcula o valor devido pelas cargas horárias de um militar."""
    posto = militar.get('posto_grad') if militar else None
    if not posto:
        return 0.0
    valor = d.get_tabela_valor_by_posto(posto)
    if not valor:
        return 0.0
    if tipo_pagamento == 'HE':
        valor_diurno = valor.get('he_diurna', 0) or 0
        valor_noturno = valor.get('ad_he_noturna', 0) or 0
    elif tipo_pagamento == 'VD':
        valor_diurno = valor.get('vd_diurno', 0) or 0
        valor_noturno = valor.get('vd_noturno', 0) or 0
    else:
        return 0.0
    return round((ch_diurna * valor_diurno) + (ch_noturna * valor_noturno), 2)


def _relatorio_rows(mes, ano, tipo_pagamento=None, opm_id=None):
    """Gera as linhas do relatório para o mês/ano, replicando o cálculo legado."""
    for evento in d.list_eventos_por_mes_ano(mes, ano):
        opm_eventos = d.list_opm_eventos_by_evento(evento.get('evento_id'))
        if opm_id:
            opm_eventos = [oe for oe in opm_eventos
                           if str(oe.get('opm_id')) == str(opm_id)]

        dados = d.horas_por_militar(evento.get('evento_id'), tipo_pagamento)

        for oe in opm_eventos:
            opm = d.get_opm(oe.get('opm_id')) if oe.get('opm_id') else None
            opm_sigla = opm.get('opm_sigla') if opm else ''

            for row in dados:
                militar = d.get_efetivo(row['matricula'])
                if not militar:
                    continue
                tp = tipo_pagamento or row.get('tipo_pagamento', 'HE')
                valor = _calcular_valor_militar(
                    militar, row['ch_diurna'] or 0, row['ch_noturna'] or 0, tp
                )
                yield {
                    'evento': evento.get('evento_desc'),
                    'opm': opm_sigla,
                    'matricula': row['matricula'],
                    'nome': row['nome'],
                    'posto': row['cargo'],
                    'cargo': row['cargo'],
                    'ch_diurna': row['ch_diurna'],
                    'ch_noturna': row['ch_noturna'],
                    'dias': row['dias'],
                    'tipo_pagamento': tp,
                    'valor': valor,
                }


@relatorio_bp.route('/', methods=['GET', 'POST'])
@login_required
def index():
    form = RelatorioForm()
    relatorio = []
    total_geral = 0
    valor_geral = 0.0

    if form.validate_on_submit() or request.args.get('gerar'):
        mes = form.mes.data or request.args.get('mes', type=int)
        ano = form.ano.data or request.args.get('ano', type=int)
        tipo_pagamento = form.tipo_pagamento.data or request.args.get('tipo_pagamento')
        opm_id = form.opm_id.data or request.args.get('opm_id')

        if mes and ano:
            for item in _relatorio_rows(mes, ano, tipo_pagamento, opm_id):
                relatorio.append(item)
                total_geral += item['dias'] or 0
                valor_geral += item['valor']

    return render_template('relatorio/index.html',
                           form=form,
                           relatorio=relatorio,
                           total_geral=total_geral,
                           valor_geral=valor_geral)


@relatorio_bp.route('/exportar')
@login_required
def exportar():
    mes = request.args.get('mes', type=int)
    ano = request.args.get('ano', type=int)
    tipo_pagamento = request.args.get('tipo_pagamento')
    opm_id = request.args.get('opm_id')

    if not mes or not ano:
        flash('Mês e ano são obrigatórios.', 'warning')
        return redirect(url_for('relatorio.index'))

    output = io.StringIO()
    writer = csv.writer(output, delimiter=';')
    writer.writerow(['Evento', 'OPM', 'Matrícula', 'Nome', 'Posto/Grad',
                     'CH Diurna', 'CH Noturna', 'Dias', 'Tipo Pagamento', 'Valor'])

    for item in _relatorio_rows(mes, ano, tipo_pagamento, opm_id):
        writer.writerow([
            item['evento'],
            item['opm'],
            item['matricula'],
            item['nome'],
            item['cargo'],
            item['ch_diurna'],
            item['ch_noturna'],
            item['dias'],
            item['tipo_pagamento'],
            f'{item["valor"]:.2f}'.replace('.', ',')
        ])

    response = make_response(output.getvalue())
    response.headers['Content-Type'] = 'text/csv; charset=utf-8'
    response.headers['Content-Disposition'] = f'attachment; filename=relatorio_{mes}_{ano}.csv'
    return response


@relatorio_bp.route('/valores')
@login_required
def valores():
    if not current_user.is_supervisor:
        flash('Acesso negado.', 'danger')
        return redirect(url_for('dashboard.index'))

    valores = d.list_tabela_valores()
    return render_template('relatorio/valores.html', valores=valores)