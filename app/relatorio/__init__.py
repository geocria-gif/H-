from flask import Blueprint, render_template, redirect, url_for, flash, request, make_response
from flask_login import login_required, current_user
from sqlalchemy import extract
import csv
import io
from app import db
from app.models import (
    Evento, OpmEvento, Escala, EfetivoPM, OPM, TabelaValores, EscalaSalva
)
from app.forms import RelatorioForm
from app.repository import escala_repo, efetivo_repo
from app.services import tabela_valores_service

relatorio_bp = Blueprint('relatorio', __name__, url_prefix='/relatorio')


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
            eventos = Evento.query.filter(
                extract('month', Evento.evento_dta_inicio) == mes,
                extract('year', Evento.evento_dta_inicio) == ano
            ).all()
            
            for evento in eventos:
                oe_query = db.select(OpmEvento).where(OpmEvento.evento_id == evento.evento_id)
                if opm_id:
                    oe_query = oe_query.where(OpmEvento.opm_id == opm_id)
                
                opm_eventos = db.session.execute(oe_query).scalars().all()
                
                for oe in opm_eventos:
                    tp_filter = tipo_pagamento if tipo_pagamento else None
                    dados = escala_repo.get_horas_por_militar(evento.evento_id, tp_filter)
                    
                    for row in dados:
                        militar = efetivo_repo.get_by_matricula(row['matricula'])
                        if militar:
                            tp = tipo_pagamento or row.get('tipo_pagamento', 'HE')
                            valor = tabela_valores_service.calcular_valor_militar(
                                militar, row['ch_diurna'] or 0, row['ch_noturna'] or 0, tp
                            )
                            relatorio.append({
                                'evento': evento.evento_desc,
                                'opm': oe.opm_rel.opm_sigla if oe.opm_rel else '',
                                'matricula': row['matricula'],
                                'nome': row['nome'],
                                'posto': row['cargo'],
                                'ch_diurna': row['ch_diurna'],
                                'ch_noturna': row['ch_noturna'],
                                'dias': row['dias'],
                                'tipo_pagamento': tp,
                                'valor': valor
                            })
                            total_geral += row['dias'] or 0
                            valor_geral += valor
    
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
    writer.writerow(['Evento', 'OPM', 'Matrícula', 'Nome', 'Posto/Grad', 'CH Diurna', 'CH Noturna', 'Dias', 'Tipo Pagamento', 'Valor'])
    
    eventos = Evento.query.filter(
        extract('month', Evento.evento_dta_inicio) == mes,
        extract('year', Evento.evento_dta_inicio) == ano
    ).all()
    
    for evento in eventos:
        oe_query = db.select(OpmEvento).where(OpmEvento.evento_id == evento.evento_id)
        if opm_id:
            oe_query = oe_query.where(OpmEvento.opm_id == opm_id)
        
        opm_eventos = db.session.execute(oe_query).scalars().all()
        
        for oe in opm_eventos:
            tp_filter = tipo_pagamento if tipo_pagamento else None
            dados = escala_repo.get_horas_por_militar(evento.evento_id, tp_filter)
            
            for row in dados:
                militar = efetivo_repo.get_by_matricula(row['matricula'])
                if militar:
                    tp = tipo_pagamento or row.get('tipo_pagamento', 'HE')
                    valor = tabela_valores_service.calcular_valor_militar(
                        militar, row['ch_diurna'] or 0, row['ch_noturna'] or 0, tp
                    )
                    writer.writerow([
                        evento.evento_desc,
                        oe.opm_rel.opm_sigla if oe.opm_rel else '',
                        row['matricula'],
                        row['nome'],
                        row['cargo'],
                        row['ch_diurna'],
                        row['ch_noturna'],
                        row['dias'],
                        tp,
                        f'{valor:.2f}'.replace('.', ',')
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
    
    valores = TabelaValores.query.order_by(TabelaValores.posto_grad).all()
    return render_template('relatorio/valores.html', valores=valores)