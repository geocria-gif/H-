"""Blueprint escala: escalas de serviço, escala P2, escalas salvas e escalas de eventos."""
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, make_response
from flask_login import login_required, current_user
from app import data as d
from app.data import base as b
from app.forms import (
    EscalaForm, EscalaP2Form, EscalaP2MetaForm, EscalaP2LegendaForm,
    EscalaSalvaForm, EscalaSalvaItemForm, EscalaSalvaMetaForm
)
from datetime import date, datetime, timedelta

escala_bp = Blueprint('escala', __name__, url_prefix='/escala')


def _calcular_ch(hora_inicio, hora_fim):
    """Calcula carga horária diurna e noturna."""
    if not hora_inicio or not hora_fim:
        return 0, 0

    try:
        hi = datetime.strptime(hora_inicio, '%H:%M')
        hf = datetime.strptime(hora_fim, '%H:%M')
    except ValueError:
        return 0, 0

    if hf <= hi:
        hf += timedelta(days=1)

    ch_diurna = 0
    ch_noturna = 0

    atual = hi
    while atual < hf:
        prox = min(atual + timedelta(hours=1), hf)
        hora_atual = atual.hour + atual.minute / 60

        if 5 <= hora_atual < 22:
            ch_diurna += (prox - atual).total_seconds() / 3600
        else:
            ch_noturna += (prox - atual).total_seconds() / 3600

        atual = prox

    return round(ch_diurna, 2), round(ch_noturna, 2)


def _as_date(value):
    if not value:
        return None
    try:
        return date.fromisoformat(str(value)[:10])
    except (ValueError, TypeError):
        return None


def _as_datetime(value):
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    value = str(value)
    for fmt in ('%Y-%m-%d %H:%M:%S.%f', '%Y-%m-%dT%H:%M:%S.%f',
                '%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%d'):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    return None


def _item_id(doc):
    value = doc.get('id')
    if value is None:
        value = doc.id
    try:
        return int(value)
    except (TypeError, ValueError):
        return value


@escala_bp.route('/')
@login_required
def index():
    hoje = date.today()
    mes = request.args.get('mes', hoje.month, type=int)
    ano = request.args.get('ano', hoje.year, type=int)
    opm_id = request.args.get('opm_id', type=str)

    escalas = d.list_escalas_with_militar(order_by='escala_data', direction='ASC')
    if opm_id:
        oe_ids = [oe.get('opm_evento_id') for oe in d.list_opm_eventos()
                  if str(oe.get('opm_id')) == str(opm_id)]
        escalas = [e for e in escalas if e.get('opm_evento_id') in oe_ids]

    escalas.sort(key=lambda e: (e.get('escala_data') or '', e.get('matricula') or ''))
    for esc in escalas:
        esc['escala_data'] = _as_date(esc.get('escala_data'))

    opms = d.list_opms()

    return render_template('escala/index.html',
                           escalas=escalas,
                           opms=opms,
                           mes=mes, ano=ano,
                           opm_id=opm_id)


@escala_bp.route('/geral-mensal')
@login_required
def geral_mensal():
    return redirect(url_for('escala.p2', mes=request.args.get('mes', ''), ano=request.args.get('ano', '')))


@escala_bp.route('/adicionar-militar', methods=['GET', 'POST'])
@login_required
def adicionar_militar():
    form = EscalaForm()

    form.opm_evento_id.choices = [(0, 'Selecione...')] + d.list_opm_eventos_dropdown()

    if form.validate_on_submit():
        try:
            ch_d, ch_n = _calcular_ch(form.hora_inicio.data or '', form.hora_fim.data or '')
            escala = d.get_escala(
                form.opm_evento_id.data,
                form.matricula.data,
                form.escala_data.data or ''
            )
            if escala:
                d.update_escala(
                    form.opm_evento_id.data, form.matricula.data, form.escala_data.data or '',
                    {
                        'escala_ch_diurna': ch_d,
                        'escala_ch_noturna': ch_n,
                        'hora_inicio': form.hora_inicio.data or '',
                        'hora_fim': form.hora_fim.data or '',
                        'tipo_pagamento': form.tipo_pagamento.data,
                    }
                )
            else:
                d.add_escala({
                    'opm_evento_id': form.opm_evento_id.data,
                    'matricula': form.matricula.data,
                    'escala_data': form.escala_data.data or '',
                    'escala_ch_diurna': ch_d,
                    'escala_ch_noturna': ch_n,
                    'hora_inicio': form.hora_inicio.data or '',
                    'hora_fim': form.hora_fim.data or '',
                    'tipo_pagamento': form.tipo_pagamento.data,
                })
            flash('Escala salva com sucesso!', 'success')
            return redirect(url_for('escala.geral_mensal'))
        except Exception as e:
            flash(f'Erro: {str(e)}', 'danger')

    return render_template('escala/adicionar_militar.html', form=form)


@escala_bp.route('/buscar-militar')
@login_required
def buscar_militar():
    termo = request.args.get('q', '')
    if len(termo) < 2:
        return jsonify([])

    militares = d.search_efetivos(termo).items
    return jsonify([{
        'matricula': m.get('matricula'),
        'nome': m.get('nome'),
        'cargo': m.get('cargo'),
        'posto_grad': m.get('posto_grad'),
        'opm_id': m.get('opm_id'),
        'opm_sigla': m.get('opm_sigla'),
        'sit': m.get('sit'),
        'funcao': m.get('funcao'),
        'telefone': m.get('telefone'),
    } for m in militares])


@escala_bp.route('/p2')
@login_required
def p2():
    mes = request.args.get('mes', type=int)
    ano = request.args.get('ano', type=int)

    escalas = d.list_p2(mes=mes, ano=ano)
    meta = d.get_p2_meta()
    legendas = d.list_p2_legendas()

    effective_mes = mes or (meta.get('mes') if meta else None)
    effective_ano = ano or (meta.get('ano') if meta else None)

    weekdays = ['Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sab', 'Dom']
    dia_semanas = {}
    if effective_mes and effective_ano:
        import calendar
        max_day = calendar.monthrange(effective_ano, effective_mes)[1]
        for dia in range(1, max_day + 1):
            try:
                dt = date(effective_ano, effective_mes, dia)
                dia_semanas[dia] = weekdays[dt.weekday()]
            except Exception:
                pass

    return render_template('escala/p2.html',
                           escalas=escalas,
                           meta=meta,
                           legendas=legendas,
                           mes=mes, ano=ano,
                           dia_semanas=dia_semanas)


@escala_bp.route('/p2/novo', methods=['GET', 'POST'])
@login_required
def p2_novo():
    form = EscalaP2Form()
    legendas = d.list_p2_legendas()
    if form.validate_on_submit():
        dias = {}
        for dia in range(1, 32):
            val = request.form.get(f'd_{dia}', '').strip()
            if val:
                dias[str(dia)] = val
        data = {
            'id': d.next_p2_id(),
            'mes': form.mes.data,
            'ano': form.ano.data,
            'funcao': form.funcao.data,
            'opm': form.opm.data,
            'gh': form.gh.data,
            'nome': form.nome.data,
            'matricula': form.matricula.data,
            'telefone': form.telefone.data or '',
            'dias': dias,
            'is_separador': int(form.is_separador.data or 0),
            'separador_texto': form.separador_texto.data or '',
            'ordem': form.ordem.data or 0,
            'tipo_pagamento': form.tipo_pagamento.data,
        }
        d.add_p2(data, doc_id=data['id'])
        flash('Item adicionado!', 'success')
        return redirect(url_for('escala.p2'))
    return render_template('escala/p2_form.html', form=form, legendas=legendas)


@escala_bp.route('/p2/<int:id>/editar', methods=['GET', 'POST'])
@login_required
def p2_editar(id):
    escala = d.get_p2(id)
    if not escala:
        flash('Não encontrado.', 'danger')
        return redirect(url_for('escala.p2'))

    escala['dias_dict'] = d.p2_dias_dict(escala)
    form = EscalaP2Form(obj=escala)
    legendas = d.list_p2_legendas()
    if form.validate_on_submit():
        dias = {}
        for dia in range(1, 32):
            val = request.form.get(f'd_{dia}', '').strip()
            if val:
                dias[str(dia)] = val
        data = {
            'mes': form.mes.data,
            'ano': form.ano.data,
            'funcao': form.funcao.data,
            'opm': form.opm.data,
            'gh': form.gh.data,
            'nome': form.nome.data,
            'matricula': form.matricula.data,
            'telefone': form.telefone.data or '',
            'dias': dias,
            'is_separador': int(form.is_separador.data or 0),
            'separador_texto': form.separador_texto.data or '',
            'ordem': form.ordem.data or 0,
            'tipo_pagamento': form.tipo_pagamento.data,
        }
        d.update_p2(id, data)
        flash('Atualizado!', 'success')
        return redirect(url_for('escala.p2'))
    return render_template('escala/p2_form.html', form=form, legendas=legendas, escala=escala)


@escala_bp.route('/p2/<int:id>/excluir', methods=['POST'])
@login_required
def p2_excluir(id):
    if not current_user.is_supervisor:
        flash('Acesso negado.', 'danger')
        return redirect(url_for('escala.p2'))

    escala = d.get_p2(id)
    if escala:
        d.delete_p2(id)
        flash('Excluído!', 'success')
    return redirect(url_for('escala.p2'))


@escala_bp.route('/p2/meta', methods=['GET', 'POST'])
@login_required
def p2_meta():
    meta = d.get_p2_meta()
    if not meta:
        d.save_p2_meta({'id': 1})
        meta = d.get_p2_meta()

    form = EscalaP2MetaForm(obj=meta)
    if form.validate_on_submit():
        data = {
            'mes': form.mes.data,
            'ano': form.ano.data,
            'local': form.local.data,
            'responsavel': form.responsavel.data,
            'cargo': form.cargo.data,
            'emissao': form.emissao.data,
            'nota': form.nota.data,
            'titulo': form.titulo.data,
        }
        d.save_p2_meta(data)
        flash('Meta salva!', 'success')
        return redirect(url_for('escala.p2'))
    return render_template('escala/p2_meta.html', form=form)


@escala_bp.route('/p2/legenda', methods=['GET', 'POST'])
@login_required
def p2_legenda():
    legendas = d.list_p2_legendas()
    form = EscalaP2LegendaForm()

    if form.validate_on_submit():
        d.add_p2_legenda({
            'id': d.next_p2_legenda_id(),
            'codigo': form.codigo.data,
            'descricao': form.descricao.data,
        })
        flash('Legenda adicionada!', 'success')
        return redirect(url_for('escala.p2_legenda'))

    return render_template('escala/p2_legenda.html', legendas=legendas, form=form)


@escala_bp.route('/p2/buscar-militar')
@login_required
def p2_buscar_militar():
    termo = request.args.get('q', '').strip()
    if len(termo) < 2:
        return jsonify([])
    militares = d.search_efetivos(termo, 1, 10).items
    return jsonify([{
        'matricula': m.get('matricula'),
        'nome': m.get('nome'),
        'funcao': m.get('funcao') or '',
        'telefone': m.get('telefone') or '',
        'opm': m.get('opm_sigla') or '',
        'cargo': m.get('posto_grad') or '',
    } for m in militares])


def _get_p2_items(mes, ano):
    if mes and ano:
        return d.list_p2(mes, ano)
    return d.list_p2()


def _resolve_p2_mes_ano(form_mes, form_ano):
    mes = form_mes
    ano = form_ano
    if not mes or not ano:
        meta = d.get_p2_meta()
        mes = mes or (meta.get('mes') if meta else None)
        ano = ano or (meta.get('ano') if meta else None)
    if mes and ano:
        items = _get_p2_items(mes, ano)
        if items:
            return mes, ano, items
    all_items = _get_p2_items(None, None)
    if all_items:
        return None, None, all_items
    return mes, ano, []


def _get_p2_meta_dict():
    meta_p2 = d.get_p2_meta()
    if not meta_p2:
        return {}
    return {
        'local': meta_p2.get('local'),
        'responsavel': meta_p2.get('responsavel'),
        'cargo': meta_p2.get('cargo'),
        'emissao': meta_p2.get('emissao'),
        'nota': meta_p2.get('nota'),
        'titulo': meta_p2.get('titulo'),
    }


def _build_itens_from_p2(escalas):
    itens = []
    for e in escalas:
        itens.append({
            'funcao': e.get('funcao'),
            'opm': e.get('opm'),
            'gh': e.get('gh'),
            'nome': e.get('nome'),
            'matricula': e.get('matricula'),
            'telefone': e.get('telefone'),
            'dias': d.p2_dias_dict(e),
            'tipo_pagamento': e.get('tipo_pagamento'),
            'is_separador': e.get('is_separador'),
            'separador_texto': e.get('separador_texto'),
            'ordem': e.get('ordem'),
        })
    return itens


@escala_bp.route('/p2/salvar', methods=['POST'])
@login_required
def p2_salvar():
    if not current_user.is_supervisor:
        flash('Acesso negado.', 'danger')
        return redirect(url_for('escala.p2'))

    form_mes = request.form.get('mes', type=int)
    form_ano = request.form.get('ano', type=int)
    mes, ano, escalas = _resolve_p2_mes_ano(form_mes, form_ano)

    if not escalas:
        flash('Nenhum item para salvar.', 'danger')
        return redirect(url_for('escala.p2'))

    label = f'{mes:02d}/{ano}' if mes and ano else 'Geral'
    nome = f'Escala P2 - {label}'
    itens = _build_itens_from_p2(escalas)
    meta_dict = _get_p2_meta_dict()

    escala_salva = {
        'id': d.next_escala_salva_id(),
        'nome': nome,
        'mes': mes or 0,
        'ano': ano or 0,
        'data_salva': datetime.utcnow().isoformat(),
        'ativa': 1,
        'itens': itens,
    }

    if meta_dict:
        escala_salva['meta'] = meta_dict

    d.add_escala_salva(escala_salva, doc_id=escala_salva['id'])
    flash(f'Escala salva como "{nome}"!', 'success')
    return redirect(url_for('escala.p2'))


@escala_bp.route('/p2/rascunho', methods=['POST'])
@login_required
def p2_rascunho():
    if not current_user.is_supervisor:
        flash('Acesso negado.', 'danger')
        return redirect(url_for('escala.p2'))

    form_mes = request.form.get('mes', type=int)
    form_ano = request.form.get('ano', type=int)
    mes, ano, escalas = _resolve_p2_mes_ano(form_mes, form_ano)

    if not escalas:
        flash('Nenhum item para salvar.', 'danger')
        return redirect(url_for('escala.p2'))

    label = f'{mes:02d}/{ano}' if mes and ano else 'Geral'
    nome = f'Rascunho P2 - {label}'
    itens = _build_itens_from_p2(escalas)
    meta_dict = _get_p2_meta_dict()

    escala_salva = {
        'id': d.next_escala_salva_id(),
        'nome': nome,
        'mes': mes or 0,
        'ano': ano or 0,
        'data_salva': datetime.utcnow().isoformat(),
        'ativa': 0,
        'itens': itens,
    }

    if meta_dict:
        escala_salva['meta'] = meta_dict

    d.add_escala_salva(escala_salva, doc_id=escala_salva['id'])
    flash(f'Rascunho salvo como "{nome}"!', 'success')
    return redirect(url_for('escala.p2'))


@escala_bp.route('/p2/exportar-pdf')
@login_required
def p2_exportar_pdf():
    from xhtml2pdf import pisa
    import calendar as cal
    from io import BytesIO
    from html import escape as hesc

    mes = request.args.get('mes', type=int)
    ano = request.args.get('ano', type=int)

    if not mes or not ano:
        meta = d.get_p2_meta()
        mes = mes or (meta.get('mes') if meta else None)
        ano = ano or (meta.get('ano') if meta else None)

    if not mes or not ano:
        flash('Defina mes e ano nas configuracoes da P2.', 'danger')
        return redirect(url_for('escala.p2'))

    items = d.list_p2(mes, ano)
    meta = d.get_p2_meta()
    legendas = d.list_p2_legendas()

    dias_no_mes = cal.monthrange(ano, mes)[1]
    dias_com_dados = set()
    for item in items:
        if item.get('is_separador'):
            continue
        dias = d.p2_dias_dict(item)
        for k in dias:
            dias_com_dados.add(int(k))
    dias_com_dados = sorted(dias_com_dados)

    dias_nomes = ['DOM','SEG','TER','QUA','QUI','SEX','SAB']
    meses_nome = ['','Janeiro','Fevereiro','Marco','Abril','Maio','Junho',
                  'Julho','Agosto','Setembro','Outubro','Novembro','Dezembro']
    titulo = (meta.get('titulo') if meta else '') or f'ESCALA DE COORDENADOR REGIONAL DO CPR-CN - {meses_nome[mes].upper()} DE {ano}'
    n = len(dias_com_dados)
    total_cols = 7 + n + 3

    h = '<html><head><meta charset="UTF-8"><style>'
    h += '@page { size: A4 landscape; margin: 6mm 5mm 8mm 5mm; }'
    h += 'body { font-family: Calibri,Helvetica,Arial,sans-serif; font-size: 8pt; margin: 0; padding: 0; color: #1a1a1a; }'
    h += 'table { width: 100%; border-collapse: collapse; }'
    h += 'th, td { border: 1px solid #bbb; padding: 2px 4px; text-align: center; vertical-align: middle; }'
    h += 'th { background: #2B488B; color: #fff; font-weight: 700; }'
    h += 'td.txt { text-align: left; font-weight: 600; }'
    h += 'td.cod { font-weight: 700; font-size: 8pt; }'
    h += 'td.horas { font-weight: 700; }'
    h += 'tr.alt td { background: #F5F5FA; }'
    h += 'tr.sep td { background: #F5F0E8; font-weight: 600; color: #666; text-align: center; font-size: 8pt; }'
    h += '</style></head><body>'

    h += f'<table>'

    h += f'<tr><td colspan="{total_cols}" style="text-align:center;font-size:13pt;font-weight:700;border:none;padding:2px 0">POLICIA MILITAR DA BAHIA</td></tr>'
    h += f'<tr><td colspan="{total_cols}" style="text-align:center;font-size:9pt;border:none;padding:1px 0">COPPM CPR-CN</td></tr>'
    h += f'<tr><td colspan="{total_cols}" style="text-align:center;font-size:9pt;border:none;color:#666">CENTRO DE PLANEJAMENTO OPERACIONAL E DECISOES ESTRATEGICAS</td></tr>'
    h += f'<tr><td colspan="{total_cols}" style="text-align:center;font-size:13pt;font-weight:700;border:none;padding:6px 0 4px 0">{hesc(titulo)}</td></tr>'

    h += f'<tr style="height:4pt"><td colspan="{total_cols}" style="background:#2B488B;border:none;padding:0">&nbsp;</td></tr>'

    h += '<tr style="height:18pt">'
    for c in ['FUNCAO','OPM','GH','NOME','MATRICULA','TEL.','TIPO']:
        h += f'<th style="background:#2B488B;color:#fff;font-weight:700;border:1px solid #2B488B;padding:2px 4px;font-size:8pt">{c}</th>'
    for dia in dias_com_dados:
        dn = dias_nomes[date(ano, mes, dia).weekday()]
        h += f'<th style="background:#2B488B;color:#fff;font-weight:700;border:1px solid #2B488B;padding:2px 4px;font-size:9pt">{dia:02d}<br><span style="font-weight:400;font-size:6pt;color:#C8D7FF">{dn[:3]}</span></th>'
    h += '<th style="background:#2B488B;color:#fff;border:1px solid #2B488B;padding:2px 4px;font-size:8pt">D</th>'
    h += '<th style="background:#2B488B;color:#fff;border:1px solid #2B488B;padding:2px 4px;font-size:8pt">N</th>'
    h += '<th style="background:#2B488B;color:#fff;border:1px solid #2B488B;padding:2px 4px;font-size:8pt">HORAS</th></tr>'

    idx = 0
    for item in items:
        if item.get('is_separador'):
            h += f'<tr class="sep"><td colspan="{total_cols}" style="text-align:center;font-weight:600;font-size:8pt;color:#666;border:1px solid #ddd;background:#F5F0E8;padding:3px 4px">{hesc(item.get("separador_texto") or "-")}</td></tr>'
        else:
            dias = d.p2_dias_dict(item)
            hd = hn = 0
            for dk, dv in dias.items():
                if dv in ('C1',): hd += 12
                elif dv in ('C2',): hd += 5; hn += 7
                elif dv in ('A1',): hd += 8
                elif dv in ('A2',): hd += 6
                elif dv in ('B1',): hd += 6
            bg_class = ' class="alt"' if idx % 2 == 1 else ''
            h += f'<tr{bg_class}>'
            for v in [item.get('funcao') or '', item.get('opm') or '', item.get('gh') or '', item.get('nome') or '', item.get('matricula') or '', item.get('telefone') or '', item.get('tipo_pagamento') or 'HE']:
                h += f'<td class="txt" style="border:1px solid #bbb;padding:2px 4px;font-size:9pt">{hesc(v)}</td>'
            for dia in dias_com_dados:
                cod = dias.get(str(dia), '')
                h += f'<td class="cod" style="border:1px solid #bbb;padding:2px 4px;font-size:9pt">{hesc(cod)}</td>'
            h += f'<td class="horas" style="border:1px solid #bbb;padding:2px 4px;font-size:9pt">{hd or ""}</td>'
            h += f'<td class="horas" style="border:1px solid #bbb;padding:2px 4px;font-size:9pt">{hn or ""}</td>'
            h += f'<td class="horas" style="border:1px solid #bbb;padding:2px 4px;font-size:9pt">{hd+hn or ""}</td></tr>'
            idx += 1

    h += f'<tr style="height:4pt"><td colspan="{total_cols}" style="background:#2B488B;border:none;padding:0">&nbsp;</td></tr>'

    if meta:
        h += f'<tr><td colspan="{total_cols}" style="text-align:center;font-size:9pt;border:none;padding-top:8px">{hesc(meta.get("local") or "IRECE")}, {date.today().day} DE {meses_nome[date.today().month].upper()} DE {ano}</td></tr>'
        h += f'<tr><td colspan="{total_cols}" style="text-align:center;font-size:10pt;font-weight:700;border:none;padding-top:6px">{hesc(meta.get("responsavel") or "")}</td></tr>'
        h += f'<tr><td colspan="{total_cols}" style="text-align:center;font-size:8pt;border:none;color:#555">{hesc(meta.get("cargo") or "")}</td></tr>'
    if legendas:
        h += f'<tr><td colspan="{total_cols}" style="text-align:center;font-size:7pt;border:none;color:#888;padding-top:4px">Legenda: {hesc(" | ".join(f"{l.get(chr(99)+chr(111)+chr(100)+chr(105)+chr(103)+chr(111))} ({l.get(chr(100)+chr(101)+chr(115)+chr(99)+chr(114)+chr(105)+chr(99)+chr(97)+chr(111))})" for l in legendas))}</td></tr>'

    h += '</table></body></html>'

    result = BytesIO()
    pdf = pisa.pisaDocument(BytesIO(h.encode('utf-8')), result)
    if pdf.err:
        flash('Erro ao gerar PDF.', 'danger')
        return redirect(url_for('escala.p2'))

    response = make_response(result.getvalue())
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename=escala_p2_{mes:02d}_{ano}.pdf'
    return response


@escala_bp.route('/salvas')
@login_required
def salvas():
    page = request.args.get('page', 1, type=int)
    pagination = d.list_escalas_salvas(page=page, per_page=20)
    for esc in pagination.items:
        if esc.get('data_salva'):
            esc['data_salva'] = _as_datetime(esc.get('data_salva'))
    return render_template('escala/salvas.html', pagination=pagination)


@escala_bp.route('/salvas/nova', methods=['GET', 'POST'])
@login_required
def salvas_nova():
    form = EscalaSalvaForm()
    if form.validate_on_submit():
        escala = {
            'id': d.next_escala_salva_id(),
            'nome': form.nome.data,
            'mes': form.mes.data,
            'ano': form.ano.data,
            'data_salva': datetime.utcnow().isoformat(),
            'ativa': 0,
        }
        d.add_escala_salva(escala, doc_id=escala['id'])
        flash('Escala salva criada!', 'success')
        return redirect(url_for('escala.salvas_editar', id=escala['id']))
    return render_template('escala/salvas_form.html', form=form)


@escala_bp.route('/salvas/<int:id>/editar', methods=['GET', 'POST'])
@login_required
def salvas_editar(id):
    escala = d.get_escala_salva(id)
    if not escala:
        flash('Não encontrada.', 'danger')
        return redirect(url_for('escala.salvas'))

    form = EscalaSalvaForm(obj=escala)
    itens = escala.get('itens') or []
    meta = escala.get('meta')

    if form.validate_on_submit():
        d.update_escala_salva(id, {
            'nome': form.nome.data,
            'mes': form.mes.data,
            'ano': form.ano.data,
        })
        escala = d.get_escala_salva(id)
        itens = escala.get('itens') or []
        meta = escala.get('meta')
        flash('Atualizada!', 'success')

    return render_template('escala/salvas_editar.html',
                           escala=escala, form=form, itens=itens, meta=meta)


@escala_bp.route('/salvas/<int:id>/item/novo', methods=['GET', 'POST'])
@login_required
def salvas_item_novo(id):
    escala = d.get_escala_salva(id)
    if not escala:
        return redirect(url_for('escala.salvas'))

    form = EscalaSalvaItemForm()
    if form.validate_on_submit():
        itens = escala.get('itens') or []
        item_id = max([it.get('id') or 0 for it in itens], default=0) + 1
        item = {
            'id': item_id,
            'funcao': form.funcao.data,
            'opm': form.opm.data,
            'gh': form.gh.data,
            'nome': form.nome.data,
            'matricula': form.matricula.data,
            'telefone': form.telefone.data or '',
            'dias': {},
            'tipo_pagamento': form.tipo_pagamento.data,
            'is_separador': int(form.is_separador.data or 0),
            'separador_texto': form.separador_texto.data or '',
            'ordem': form.ordem.data or 0,
        }
        d.update_escala_salva(id, {'itens': itens + [item]})
        flash('Item adicionado!', 'success')
        return redirect(url_for('escala.salvas_editar', id=id))
    return render_template('escala/salvas_item_form.html', form=form, escala=escala)


@escala_bp.route('/salvas/<int:escala_id>/item/<int:item_id>/editar', methods=['GET', 'POST'])
@login_required
def salvas_item_editar(escala_id, item_id):
    escala = d.get_escala_salva(escala_id)
    if not escala:
        return redirect(url_for('escala.salvas_editar', id=escala_id))

    itens = escala.get('itens') or []
    item = next((it for it in itens if it.get('id') == item_id), None)
    if not item:
        return redirect(url_for('escala.salvas_editar', id=escala_id))

    form = EscalaSalvaItemForm(obj=b.Doc(item))
    if form.validate_on_submit():
        updated = {
            'id': item_id,
            'funcao': form.funcao.data,
            'opm': form.opm.data,
            'gh': form.gh.data,
            'nome': form.nome.data,
            'matricula': form.matricula.data,
            'telefone': form.telefone.data or '',
            'dias': item.get('dias') or {},
            'tipo_pagamento': form.tipo_pagamento.data,
            'is_separador': int(form.is_separador.data or 0),
            'separador_texto': form.separador_texto.data or '',
            'ordem': form.ordem.data or 0,
        }
        new_itens = [updated if it.get('id') == item_id else it for it in itens]
        d.update_escala_salva(escala_id, {'itens': new_itens})
        flash('Atualizado!', 'success')
        return redirect(url_for('escala.salvas_editar', id=escala_id))
    return render_template('escala/salvas_item_form.html', form=form, escala=escala)


@escala_bp.route('/salvas/<int:escala_id>/item/<int:item_id>/excluir', methods=['POST'])
@login_required
def salvas_item_excluir(escala_id, item_id):
    escala = d.get_escala_salva(escala_id)
    if escala:
        itens = escala.get('itens') or []
        if any(it.get('id') == item_id for it in itens):
            d.update_escala_salva(escala_id, {'itens': [it for it in itens if it.get('id') != item_id]})
            flash('Excluído!', 'success')
    return redirect(url_for('escala.salvas_editar', id=escala_id))


@escala_bp.route('/salvas/<int:id>/meta', methods=['GET', 'POST'])
@login_required
def salvas_meta(id):
    escala = d.get_escala_salva(id)
    if not escala:
        return redirect(url_for('escala.salvas'))

    meta = escala.get('meta')
    form = EscalaSalvaMetaForm(obj=b.Doc(meta) if meta else None)
    if form.validate_on_submit():
        d.update_escala_salva(id, {
            'meta': {
                'local': form.local.data,
                'responsavel': form.responsavel.data,
                'cargo': form.cargo.data,
                'emissao': form.emissao.data,
                'nota': form.nota.data,
                'titulo': form.titulo.data,
            }
        })
        flash('Meta salva!', 'success')
        return redirect(url_for('escala.salvas_editar', id=id))

    return render_template('escala/salvas_meta.html', form=form, escala=escala)


@escala_bp.route('/salvas/<int:id>/ativar', methods=['POST'])
@login_required
def salvas_ativar(id):
    result = d.set_escala_salva_ativa(id)
    if result:
        flash('Escala ativada!', 'success')
    else:
        flash('Erro ao ativar.', 'danger')
    return redirect(url_for('escala.salvas'))


@escala_bp.route('/salvas/<int:id>/carregar')
@login_required
def salvas_carregar(id):
    escala = d.get_escala_salva(id)
    if not escala:
        flash('Escala não encontrada.', 'danger')
        return redirect(url_for('escala.salvas'))

    flash('Escala carregada! Redirecionando...', 'success')
    return redirect(url_for('escala.geral_mensal', mes=escala.get('mes'), ano=escala.get('ano')))


@escala_bp.route('/salvas/<int:id>/excluir', methods=['POST'])
@login_required
def salvas_excluir(id):
    if not current_user.is_admin:
        flash('Acesso negado.', 'danger')
        return redirect(url_for('escala.salvas'))

    escala = d.get_escala_salva(id)
    if escala:
        d.delete_escala_salva(id)
        flash('Excluída!', 'success')
    return redirect(url_for('escala.salvas'))


@escala_bp.route('/p2/api/items')
@login_required
def p2_api_items():
    mes = request.args.get('mes', type=int)
    ano = request.args.get('ano', type=int)
    items = d.list_p2(mes=mes, ano=ano)
    return jsonify([{
        'id': _item_id(it),
        'mes': it.get('mes'),
        'ano': it.get('ano'),
        'funcao': it.get('funcao'),
        'opm': it.get('opm'),
        'gh': it.get('gh'),
        'nome': it.get('nome'),
        'matricula': it.get('matricula'),
        'telefone': it.get('telefone'),
        'dias': d.p2_dias_dict(it),
        'is_separador': bool(it.get('is_separador')),
        'separador_texto': it.get('separador_texto'),
        'ordem': it.get('ordem'),
        'tipo_pagamento': it.get('tipo_pagamento'),
    } for it in items])


@escala_bp.route('/p2/api/cell', methods=['POST'])
@login_required
def p2_api_cell():
    data = request.get_json()
    item_id = data.get('id')
    dia = str(data.get('dia', ''))
    codigo = data.get('codigo', '')
    item = d.get_p2(item_id)
    if not item:
        return jsonify({'error': 'Item nao encontrado'}), 404
    dias = d.p2_dias_dict(item)
    if codigo:
        dias[dia] = codigo
    else:
        dias.pop(dia, None)
    d.update_p2(item_id, {'dias': dias})
    return jsonify({'ok': True, 'dias': dias})


@escala_bp.route('/p2/api/bulk', methods=['POST'])
@login_required
def p2_api_bulk():
    data = request.get_json()
    mes = data.get('mes')
    ano = data.get('ano')
    tipo = data.get('tipo')
    codigo = data.get('codigo')
    if not all([mes, ano, tipo, codigo]):
        return jsonify({'error': 'Parametros incompletos'}), 400
    import calendar
    dias_no_mes = calendar.monthrange(ano, mes)[1]
    items = [it for it in d.list_p2(mes, ano) if not it.get('is_separador')]
    for item in items:
        dias = d.p2_dias_dict(item)
        for dia in range(1, dias_no_mes + 1):
            dow = date(ano, mes, dia).weekday()
            if tipo == 'sex-sab-dom' and dow in (4, 5, 6):
                dias[str(dia)] = codigo
            elif tipo == 'sab-dom' and dow in (5, 6):
                dias[str(dia)] = codigo
            elif tipo == 'sex' and dow == 4:
                dias[str(dia)] = codigo
        d.update_p2(item.id, {'dias': dias})
    return jsonify({'ok': True, 'count': len(items)})


@escala_bp.route('/p2/api/clear', methods=['POST'])
@login_required
def p2_api_clear():
    data = request.get_json()
    mes = data.get('mes')
    ano = data.get('ano')
    tipo = data.get('tipo', 'fds')
    if not all([mes, ano]):
        return jsonify({'error': 'Parametros incompletos'}), 400
    import calendar
    dias_no_mes = calendar.monthrange(ano, mes)[1]
    items = [it for it in d.list_p2(mes, ano) if not it.get('is_separador')]
    for item in items:
        dias = d.p2_dias_dict(item)
        for dia in range(1, dias_no_mes + 1):
            dow = date(ano, mes, dia).weekday()
            if tipo == 'todos':
                dias.pop(str(dia), None)
            elif tipo == 'fds' and dow in (4, 5, 6):
                dias.pop(str(dia), None)
        d.update_p2(item.id, {'dias': dias})
    return jsonify({'ok': True, 'count': len(items)})


@escala_bp.route('/p2/api/move', methods=['POST'])
@login_required
def p2_api_move():
    data = request.get_json()
    item_id = data.get('id')
    direcao = data.get('direcao', 0)
    item = d.get_p2(item_id)
    if not item:
        return jsonify({'error': 'Item nao encontrado'}), 404
    items = d.list_p2(item.get('mes'), item.get('ano'))
    if direcao < 0:
        viz = None
        for it in items:
            if (it.get('ordem') or 0) < (item.get('ordem') or 0):
                viz = it
    else:
        viz = None
        for it in items:
            if (it.get('ordem') or 0) > (item.get('ordem') or 0):
                viz = it
                break
    if not viz:
        return jsonify({'ok': False})
    item_ordem = item.get('ordem')
    viz_ordem = viz.get('ordem')
    d.update_p2(item.id, {'ordem': viz_ordem})
    d.update_p2(viz.id, {'ordem': item_ordem})
    return jsonify({'ok': True})


@escala_bp.route('/p2/api/item', methods=['POST'])
@login_required
def p2_api_item_add():
    data = request.get_json()
    mes = data.get('mes')
    ano = data.get('ano')
    max_ord = max([it.get('ordem') or 0 for it in d.list_p2(mes, ano)], default=0)
    item = {
        'id': d.next_p2_id(),
        'mes': mes,
        'ano': ano,
        'funcao': data.get('funcao', ''),
        'opm': data.get('opm', ''),
        'gh': data.get('gh', ''),
        'nome': data.get('nome', ''),
        'matricula': data.get('matricula', ''),
        'telefone': data.get('telefone', ''),
        'tipo_pagamento': data.get('tipo_pagamento', 'HE'),
        'dias': {},
        'ordem': max_ord + 1,
    }
    d.add_p2(item, doc_id=item['id'])
    return jsonify({'ok': True, 'id': item['id']})


@escala_bp.route('/p2/api/item/<int:item_id>', methods=['PUT'])
@login_required
def p2_api_item_edit(item_id):
    item = d.get_p2(item_id)
    if not item:
        return jsonify({'error': 'Item nao encontrado'}), 404
    data = request.get_json()
    updates = {}
    for field in ['funcao', 'opm', 'gh', 'nome', 'matricula', 'telefone', 'tipo_pagamento']:
        if field in data:
            updates[field] = data[field]
    if updates:
        d.update_p2(item_id, updates)
    return jsonify({'ok': True})


@escala_bp.route('/p2/api/item/<int:item_id>', methods=['DELETE'])
@login_required
def p2_api_item_del(item_id):
    item = d.get_p2(item_id)
    if item:
        d.delete_p2(item_id)
    return jsonify({'ok': True})


@escala_bp.route('/p2/api/separador', methods=['POST'])
@login_required
def p2_api_separador():
    data = request.get_json()
    mes = data.get('mes')
    ano = data.get('ano')
    texto = data.get('texto', '')
    max_ord = max([it.get('ordem') or 0 for it in d.list_p2(mes, ano)], default=0)
    item = {
        'id': d.next_p2_id(),
        'mes': mes,
        'ano': ano,
        'funcao': '-',
        'opm': '-',
        'gh': '-',
        'nome': '-',
        'matricula': '-',
        'telefone': '',
        'dias': {},
        'is_separador': 1,
        'separador_texto': texto,
        'ordem': max_ord + 1,
    }
    d.add_p2(item, doc_id=item['id'])
    return jsonify({'ok': True, 'id': item['id']})


@escala_bp.route('/p2/api/meta', methods=['GET', 'POST'])
@login_required
def p2_api_meta():
    if request.method == 'GET':
        meta = d.get_p2_meta()
        if not meta:
            return jsonify({'local':'IRECE','resp':'','cargo':'','emissao':'','nota':'','titulo':'','mes':'','ano':''})
        return jsonify({
            'local': meta.get('local') or '', 'resp': meta.get('responsavel') or '',
            'cargo': meta.get('cargo') or '', 'emissao': meta.get('emissao') or '',
            'nota': meta.get('nota') or '', 'titulo': meta.get('titulo') or '',
            'mes': meta.get('mes') or '', 'ano': meta.get('ano') or ''
        })
    data = request.get_json()
    meta = d.get_p2_meta()
    meta_data = {'id': 1}
    if 'resp' in data:
        meta_data['responsavel'] = data['resp']
    for field in ['local', 'responsavel', 'cargo', 'emissao', 'nota', 'titulo']:
        if field in data:
            meta_data[field] = data[field]
    meta_data['mes'] = data.get('mes', meta.get('mes') if meta else None)
    meta_data['ano'] = data.get('ano', meta.get('ano') if meta else None)
    d.save_p2_meta(meta_data)
    return jsonify({'ok': True})


@escala_bp.route('/p2/api/legendas')
@login_required
def p2_api_legendas():
    legendas = d.list_p2_legendas()
    return jsonify([{'id': _item_id(l), 'codigo': l.get('codigo'), 'descricao': l.get('descricao')} for l in legendas])


@escala_bp.route('/p2/api/legenda', methods=['POST'])
@login_required
def p2_api_legenda_add():
    data = request.get_json()
    leg = {
        'id': d.next_p2_legenda_id(),
        'codigo': data.get('codigo', ''),
        'descricao': data.get('descricao', ''),
    }
    d.add_p2_legenda(leg, doc_id=leg['id'])
    return jsonify({'ok': True, 'id': leg['id']})


@escala_bp.route('/p2/api/legenda/<int:leg_id>', methods=['DELETE'])
@login_required
def p2_api_legenda_del(leg_id):
    leg = d.get_p2_legenda(leg_id)
    if leg:
        d.delete_p2_legenda(leg_id)
    return jsonify({'ok': True})


@escala_bp.route('/p2/api/opms')
@login_required
def p2_api_opms():
    opms = [o for o in d.list_opms() if o.get('opm_sigla')]
    return jsonify([{'sigla': o.get('opm_sigla')} for o in opms])


@escala_bp.route('/p2/api/funcoes')
@login_required
def p2_api_funcoes():
    return jsonify(["CSO","NUGAF/C.L.C.","COMANDANTE","CMD. DE UOP","CAAF","CH. CPO","CH. NUGAF","ASS. ESPECIAL","MOTORISTA","PATRULHEIRO"])


@escala_bp.route('/p2/api/ghs')
@login_required
def p2_api_ghs():
    cargos = d.list_cargos()
    return jsonify([c.get('posto_grad') for c in cargos])


@escala_bp.route('/p2/exportar-csv')
@login_required
def p2_exportar_csv():
    import calendar as cal
    from io import StringIO
    mes = request.args.get('mes', type=int)
    ano = request.args.get('ano', type=int)
    if not mes or not ano:
        return redirect(url_for('escala.p2'))
    meta = d.get_p2_meta()
    legendas = d.list_p2_legendas()
    items = d.list_p2(mes, ano)
    dias_no_mes = cal.monthrange(ano, mes)[1]
    dias_com_dados = set()
    for item in items:
        if item.get('is_separador'):
            continue
        dias = d.p2_dias_dict(item)
        for k in dias:
            dias_com_dados.add(int(k))
    dias_com_dados = sorted(dias_com_dados)
    dias_nomes = ['DOM','SEG','TER','QUA','QUI','SEX','SAB']
    meses_nome = ['','Janeiro','Fevereiro','Marco','Abril','Maio','Junho','Julho','Agosto','Setembro','Outubro','Novembro','Dezembro']
    titulo = (meta.get('titulo') if meta else '') or f'ESCALA DE COORDENADOR REGIONAL DO CPR-CN - {meses_nome[mes].upper()} DE {ano}'
    si = StringIO()
    si.write('POLICIA MILITAR DA BAHIA\n')
    si.write('COPPM CPR-CN\n')
    si.write(f'{titulo}\n\n')
    si.write('FUNCAO;OPM;GH;NOME;MATRICULA;TELEFONE;TIPO')
    for dia in dias_com_dados:
        si.write(f';{dia:02d}')
    si.write(';D;N;HORAS\n')
    for item in items:
        if item.get('is_separador'):
            si.write(f'\n--- {item.get("separador_texto") or ""} ---\n')
            continue
        dias = d.p2_dias_dict(item)
        hd = hn = 0
        for dk, dv in dias.items():
            if dv in ('C1',): hd += 12
            elif dv in ('C2',): hd += 5; hn += 7
            elif dv in ('A1',): hd += 8
            elif dv in ('A2',): hd += 6
            elif dv in ('B1',): hd += 6
        si.write(f'{item.get("funcao")};{item.get("opm")};{item.get("gh")};{item.get("nome")};{item.get("matricula")};{item.get("telefone") or ""};{item.get("tipo_pagamento") or "HE"}')
        for dia in dias_com_dados:
            si.write(f';{dias.get(str(dia), "")}')
        si.write(f';{hd};{hn};{hd+hn}\n')
    if meta:
        si.write(f'\n{meta.get("local") or "IRECE"}, {date.today().day} DE {meses_nome[date.today().month].upper()} DE {ano}\n')
        si.write(f'{meta.get("responsavel") or ""}\n')
        si.write(f'{meta.get("cargo") or ""}\n')
    if legendas:
        si.write(f'Legenda: {" | ".join(f"{l.get("codigo")} ({l.get("descricao")})" for l in legendas)}\n')
    resp = make_response(si.getvalue())
    resp.headers['Content-Type'] = 'text/csv; charset=utf-8'
    resp.headers['Content-Disposition'] = f'attachment; filename=escala_p2_{ano}_{mes:02d}.csv'
    return resp


@escala_bp.route('/p2/exportar-excel')
@login_required
def p2_exportar_excel():
    import calendar as cal
    mes = request.args.get('mes', type=int)
    ano = request.args.get('ano', type=int)
    if not mes or not ano:
        return redirect(url_for('escala.p2'))
    meta = d.get_p2_meta()
    legendas = d.list_p2_legendas()
    items = d.list_p2(mes, ano)
    dias_no_mes = cal.monthrange(ano, mes)[1]
    dias_com_dados = set()
    rows_only = [i for i in items if not i.get('is_separador')]
    for item in rows_only:
        dias = d.p2_dias_dict(item)
        for k in dias:
            dias_com_dados.add(int(k))
    dias_com_dados = sorted(dias_com_dados)
    dias_nomes = ['DOM','SEG','TER','QUA','QUI','SEX','SAB']
    meses_nome = ['','Janeiro','Fevereiro','Marco','Abril','Maio','Junho','Julho','Agosto','Setembro','Outubro','Novembro','Dezembro']
    titulo = (meta.get('titulo') if meta else '') or f'ESCALA DE COORDENADOR REGIONAL DO CPR-CN - {meses_nome[mes].upper()} DE {ano}'
    n = len(dias_com_dados)
    total_cols = 7 + n + 3
    esc = lambda s: (s or '').replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    h = '<html><head><meta charset="UTF-8"></head><body>'
    h += '<table style="width:100%;border-collapse:collapse;font-family:Calibri,Arial;font-size:10pt">'
    h += f'<tr><td colspan="{total_cols}" style="text-align:center;font-size:12pt;font-weight:700;border:none;padding:2px 0">POLICIA MILITAR DA BAHIA</td></tr>'
    h += f'<tr><td colspan="{total_cols}" style="text-align:center;font-size:9pt;border:none;padding:1px 0">COPPM CPR-CN</td></tr>'
    h += f'<tr><td colspan="{total_cols}" style="text-align:center;font-size:12pt;font-weight:700;border:none;padding:8px 0 6px 0">{esc(titulo)}</td></tr>'
    h += f'<tr style="height:6pt"><td colspan="{total_cols}" style="background:#2B488B;border:none;padding:0;font-size:6pt">&nbsp;</td></tr>'
    h += '<tr style="height:18pt">'
    for c in ['FUNCAO','OPM','GH','NOME','MATRICULA','TEL.','TIPO']:
        h += f'<th style="background:#2B488B;color:#fff;font-weight:700;border:1px solid #2B488B;padding:2px 4px">{c}</th>'
    for dia in dias_com_dados:
        dn = dias_nomes[date(ano, mes, dia).weekday()]
        h += f'<th style="background:#2B488B;color:#fff;font-weight:700;border:1px solid #2B488B;padding:2px 4px;font-size:8pt">{dia:02d}<br><span style="font-weight:400;font-size:6pt;color:#C8D7FF">{dn[:3]}</span></th>'
    h += '<th style="background:#2B488B;color:#fff;border:1px solid #2B488B;padding:2px 4px;font-size:7pt">D</th>'
    h += '<th style="background:#2B488B;color:#fff;border:1px solid #2B488B;padding:2px 4px;font-size:7pt">N</th>'
    h += '<th style="background:#2B488B;color:#fff;border:1px solid #2B488B;padding:2px 4px;font-size:7pt">HORAS</th></tr>'
    idx = 0
    for item in items:
        if item.get('is_separador'):
            h += f'<tr><td colspan="{total_cols}" style="text-align:center;font-weight:600;font-size:8pt;color:#666;border:1px solid #ddd;background:#F5F0E8;padding:3px 4px">{esc(item.get("separador_texto"))}</td></tr>'
        else:
            dias = d.p2_dias_dict(item)
            hd = hn = 0
            for dk, dv in dias.items():
                if dv in ('C1',): hd += 12
                elif dv in ('C2',): hd += 5; hn += 7
                elif dv in ('A1',): hd += 8
                elif dv in ('A2',): hd += 6
                elif dv in ('B1',): hd += 6
            bg = 'background:#F5F5FA' if idx % 2 == 1 else ''
            h += f'<tr style="{bg}">'
            for v in [item.get('funcao'), item.get('opm'), item.get('gh'), item.get('nome'), item.get('matricula'), item.get('telefone') or '', item.get('tipo_pagamento') or 'HE']:
                h += f'<td style="text-align:center;border:1px solid #bbb;padding:2px 4px">{esc(v)}</td>'
            for dia in dias_com_dados:
                cod = dias.get(str(dia), '')
                h += f'<td style="text-align:center;font-weight:{"700" if cod else "400"};border:1px solid #bbb;padding:2px 4px">{esc(cod)}</td>'
            h += f'<td style="text-align:center;font-weight:700;border:1px solid #bbb;padding:2px 4px">{hd or ""}</td>'
            h += f'<td style="text-align:center;font-weight:700;border:1px solid #bbb;padding:2px 4px">{hn or ""}</td>'
            h += f'<td style="text-align:center;font-weight:700;border:1px solid #bbb;padding:2px 4px">{hd+hn or ""}</td></tr>'
            idx += 1
    h += f'<tr style="height:4pt"><td colspan="{total_cols}" style="background:#2B488B;border:none;padding:0;font-size:4pt">&nbsp;</td></tr>'
    if meta:
        h += f'<tr><td colspan="{total_cols}" style="text-align:center;font-size:9pt;border:none;padding-top:8px">{esc(meta.get("local") or "IRECE")}, {date.today().day} DE {meses_nome[date.today().month].upper()} DE {ano}</td></tr>'
        h += f'<tr><td colspan="{total_cols}" style="text-align:center;font-size:9pt;font-weight:700;border:none;padding-top:6px">{esc(meta.get("responsavel") or "")}</td></tr>'
        h += f'<tr><td colspan="{total_cols}" style="text-align:center;font-size:8pt;border:none;color:#555">{esc(meta.get("cargo") or "")}</td></tr>'
    if legendas:
        h += f'<tr><td colspan="{total_cols}" style="text-align:center;font-size:7pt;border:none;color:#888;padding-top:2px">Legenda: {esc(" | ".join(f"{l.get(chr(99)+chr(111)+chr(100)+chr(105)+chr(103)+chr(111))} ({l.get(chr(100)+chr(101)+chr(115)+chr(99)+chr(114)+chr(105)+chr(99)+chr(97)+chr(111))})" for l in legendas))}</td></tr>'
    h += '</table></body></html>'
    resp = make_response(h)
    resp.headers['Content-Type'] = 'application/vnd.ms-excel; charset=utf-8'
    resp.headers['Content-Disposition'] = f'attachment; filename=escala_p2_{ano}_{mes:02d}.xls'
    return resp


# ──────────────────────────────────────────────────────────────────────
# ESCALA DE EVENTOS
# ──────────────────────────────────────────────────────────────────────

@escala_bp.route('/eventos')
@login_required
def eventos():
    eventos_list = sorted(d.list_eventos(), key=lambda e: e.get('evento_dta_inicio') or '', reverse=True)
    return render_template('escala/eventos.html', eventos=eventos_list)


@escala_bp.route('/eventos/api/evento/<int:evento_id>')
@login_required
def eventos_api_evento(evento_id):
    evento = d.get_evento(evento_id)
    if not evento:
        return jsonify({'error': 'Evento nao encontrado'}), 404

    opm_eventos = d.list_opm_eventos_by_evento(evento_id)
    pols = 0
    ch = 0.0
    for oe in opm_eventos:
        escalas = d.list_escalas_by_opm_evento(oe.get('opm_evento_id'))
        pols += len(escalas)
        for esc in escalas:
            ch += float(esc.get('escala_ch_diurna') or 0) + float(esc.get('escala_ch_noturna') or 0)

    return jsonify({
        'evento': evento.to_dict(),
        'opms': len(opm_eventos),
        'pols': pols,
        'ch': round(ch, 2),
    })


@escala_bp.route('/eventos/api/opm-eventos/<int:evento_id>')
@login_required
def eventos_api_opm_eventos(evento_id):
    rows = []
    for oe in d.list_opm_eventos_by_evento(evento_id):
        opm = d.get_opm(oe.get('opm_id'))
        escalas = d.list_escalas_by_opm_evento(oe.get('opm_evento_id'))
        ch = sum(float(esc.get('escala_ch_diurna') or 0) + float(esc.get('escala_ch_noturna') or 0)
                 for esc in escalas)
        rows.append({
            'opm_evento_id': oe.get('opm_evento_id'),
            'opm_id': oe.get('opm_id'),
            'sigla': opm.get('opm_sigla') or '' if opm else '',
            'desc': opm.get('opm_desc') or '' if opm else '',
            'mun': opm.get('opm_municipio') or '-' if opm else '-',
            'pols': len(escalas),
            'ch': round(ch, 2),
        })
    rows.sort(key=lambda r: r['sigla'])
    return jsonify(rows)


@escala_bp.route('/eventos/api/opm-evento', methods=['POST'])
@login_required
def eventos_api_add_opm():
    data = request.get_json()
    evento_id = data.get('evento_id')
    opm_id = data.get('opm_id')
    if not evento_id or not opm_id:
        return jsonify({'error': 'Parametros incompletos'}), 400
    if d.opm_evento_exists(evento_id, opm_id):
        return jsonify({'error': 'OPM ja alocada'}), 409
    opm_evento_id = d.next_opm_evento_id()
    d.add_opm_evento({
        'opm_evento_id': opm_evento_id,
        'evento_id': evento_id,
        'opm_id': opm_id,
    })
    return jsonify({'ok': True, 'opm_evento_id': opm_evento_id})


@escala_bp.route('/eventos/api/opm-evento/<int:opm_evento_id>', methods=['DELETE'])
@login_required
def eventos_api_del_opm(opm_evento_id):
    oe = d.get_opm_evento(opm_evento_id)
    if not oe:
        return jsonify({'error': 'Nao encontrado'}), 404
    for esc in d.list_escalas_by_opm_evento(opm_evento_id):
        d.delete_escala(esc.get('opm_evento_id'), esc.get('matricula'), esc.get('escala_data'))
    d.delete_opm_evento(opm_evento_id)
    return jsonify({'ok': True})


@escala_bp.route('/eventos/api/escalas/<int:opm_evento_id>')
@login_required
def eventos_api_escalas(opm_evento_id):
    rows = d.list_escalas_with_militar(
        where=[('opm_evento_id', '==', int(opm_evento_id))],
        order_by='escala_data',
        direction='ASC',
    )
    rows.sort(key=lambda e: (e.get('escala_data') or '', e.get('militar_nome') or ''))
    result = []
    for e in rows:
        item = e.to_dict()
        result.append(item)
    return jsonify(result)


@escala_bp.route('/eventos/api/escala', methods=['POST'])
@login_required
def eventos_api_add_escala():
    data = request.get_json()
    opm_evento_id = data.get('opm_evento_id')
    matricula = data.get('matricula')
    escala_data = data.get('escala_data', '')
    hora_inicio = data.get('hora_inicio', '')
    hora_fim = data.get('hora_fim', '')
    tipo_pagamento = data.get('tipo_pagamento', 'HE')
    if not opm_evento_id or not matricula:
        return jsonify({'error': 'Parametros incompletos'}), 400
    ch_d, ch_n = _calcular_ch(hora_inicio, hora_fim)
    exists = d.get_escala(opm_evento_id, matricula, escala_data)
    if exists:
        d.update_escala(opm_evento_id, matricula, escala_data, {
            'escala_ch_diurna': ch_d,
            'escala_ch_noturna': ch_n,
            'hora_inicio': hora_inicio,
            'hora_fim': hora_fim,
            'tipo_pagamento': tipo_pagamento,
        })
    else:
        d.add_escala({
            'opm_evento_id': opm_evento_id,
            'matricula': matricula,
            'escala_data': escala_data,
            'escala_ch_diurna': ch_d,
            'escala_ch_noturna': ch_n,
            'hora_inicio': hora_inicio,
            'hora_fim': hora_fim,
            'tipo_pagamento': tipo_pagamento,
        })
    return jsonify({'ok': True})


@escala_bp.route('/eventos/api/escala', methods=['DELETE'])
@login_required
def eventos_api_del_escala():
    data = request.get_json()
    opm_evento_id = data.get('opm_evento_id')
    matricula = data.get('matricula')
    escala_data = data.get('escala_data', '')
    d.delete_escala(opm_evento_id, matricula, escala_data)
    return jsonify({'ok': True})


@escala_bp.route('/eventos/api/escala/horario', methods=['PUT'])
@login_required
def eventos_api_upd_horario():
    data = request.get_json()
    opm_evento_id = data.get('opm_evento_id')
    matricula = data.get('matricula')
    escala_data = data.get('escala_data', '')
    e = d.get_escala(opm_evento_id, matricula, escala_data)
    if not e:
        return jsonify({'error': 'Nao encontrado'}), 404
    hora_inicio = data.get('hora_inicio') or e.hora_inicio or ''
    hora_fim = data.get('hora_fim') or e.hora_fim or ''
    ch_d, ch_n = _calcular_ch(hora_inicio, hora_fim)
    d.update_escala(opm_evento_id, matricula, escala_data, {
        'hora_inicio': hora_inicio,
        'hora_fim': hora_fim,
        'escala_ch_diurna': ch_d,
        'escala_ch_noturna': ch_n,
    })
    return jsonify({'ok': True})


@escala_bp.route('/eventos/api/escala/tipo-pagamento', methods=['PUT'])
@login_required
def eventos_api_upd_tipo_pagamento():
    data = request.get_json()
    opm_evento_id = data.get('opm_evento_id')
    matricula = data.get('matricula')
    escala_data = data.get('escala_data', '')
    tipo = data.get('tipo_pagamento', 'HE')
    e = d.get_escala(opm_evento_id, matricula, escala_data)
    if e:
        d.update_escala(opm_evento_id, matricula, escala_data, {'tipo_pagamento': tipo})
    return jsonify({'ok': True})


@escala_bp.route('/eventos/api/escala/data', methods=['PUT'])
@login_required
def eventos_api_upd_data():
    data = request.get_json()
    opm_evento_id = data.get('opm_evento_id')
    matricula = data.get('matricula')
    old_data = data.get('old_data', '')
    new_data = data.get('new_data', '')
    e = d.get_escala(opm_evento_id, matricula, old_data)
    if e:
        escala = e.to_dict()
        d.delete_escala(opm_evento_id, matricula, old_data)
        escala['escala_data'] = new_data
        d.add_escala(escala)
    return jsonify({'ok': True})


@escala_bp.route('/eventos/api/opms')
@login_required
def eventos_api_opms():
    opms = [o for o in d.list_opms() if o.get('opm_sigla')]
    return jsonify([{'opm_id': o.get('opm_id'), 'sigla': o.get('opm_sigla')} for o in opms])


# ──────────────────────────────────────────────────────────────────────
# GERAR ESCALA DE SERVIÇO (reuses P2 data)
# ──────────────────────────────────────────────────────────────────────

@escala_bp.route('/gerar-servico')
@login_required
def gerar_servico():
    mes = request.args.get('mes', type=int)
    ano = request.args.get('ano', type=int)
    escalas = d.list_p2(mes=mes, ano=ano)
    meta = d.get_p2_meta()
    legendas = d.list_p2_legendas()
    effective_mes = mes or (meta.get('mes') if meta else None)
    effective_ano = ano or (meta.get('ano') if meta else None)
    weekdays = ['Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sab', 'Dom']
    dia_semanas = {}
    if effective_mes and effective_ano:
        import calendar
        max_day = calendar.monthrange(effective_ano, effective_mes)[1]
        for dia in range(1, max_day + 1):
            try:
                dt = date(effective_ano, effective_mes, dia)
                dia_semanas[dia] = weekdays[dt.weekday()]
            except Exception:
                pass
    return render_template('escala/gerar_servico.html',
                           escalas=escalas, meta=meta, legendas=legendas,
                           mes=mes, ano=ano, dia_semanas=dia_semanas)