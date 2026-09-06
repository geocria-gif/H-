"""Firestore data access for escala/evento entities:
eventos, opm_eventos, escalas, escala_p2, escala_p2_meta,
escala_p2_legendas, escalas_salvas.
"""
import json
from datetime import datetime

from . import base as b
from . import org as org


# --------------------------------------------------------------------------
# Eventos
# --------------------------------------------------------------------------
COL_EVENTOS = 'eventos'


def list_eventos(order_by='evento_dta_inicio'):
    return b.list_docs(COL_EVENTOS, order_by=order_by)


def list_eventos_proximos(hoje, limit=10):
    """Eventos whose ending date >= hoje, ordered by start date."""
    items = b.list_docs(COL_EVENTOS)
    hoje = hoje or ''
    matched = [d for d in items if (d.get('evento_dta_fim') or '9999') >= hoje]
    matched.sort(key=lambda d: d.get('evento_dta_inicio') or '')
    return matched[:limit]


def list_eventos_por_mes_ano(mes, ano):
    """Eventos whose start date falls in mes/ano (dates stored as YYYY-MM-DD)."""
    matched = []
    for d in b.list_docs(COL_EVENTOS):
        ini = d.get('evento_dta_inicio') or ''
        if len(ini) >= 7:
            part = (int(ini[5:7]), int(ini[0:4]))
            if (mes and part[0] == mes and (not ano or part[1] == ano)) or \
                    (not mes and ano and part[1] == ano):
                matched.append(d)
    matched.sort(key=lambda d: d.get('evento_dta_inicio') or '')
    return matched


def get_evento(evento_id):
    return b.get_doc(COL_EVENTOS, evento_id)


def add_evento(data, evento_id=None):
    return b.add_doc(COL_EVENTOS, data, doc_id=evento_id or data.get('evento_id'))


def update_evento(evento_id, data):
    return b.update_doc(COL_EVENTOS, evento_id, data)


def delete_evento(evento_id):
    b.delete_doc(COL_EVENTOS, evento_id)


def count_eventos():
    return b.count_docs(COL_EVENTOS)


def next_evento_id():
    ids = [int(d.get('evento_id') or 0) for d in b.list_docs(COL_EVENTOS)]
    return max(ids, default=0) + 1


def _enrich_evento(doc):
    if doc is None:
        return None
    oes = list_opm_eventos_by_evento(doc.get('evento_id'))
    for oe in oes:
        opm = org.get_opm(oe.get('opm_id'))
        if opm:
            oe.update(opm_rel=opm)
    doc.update(opm_eventos=oes)
    return doc


def get_evento_with_opms(evento_id):
    return _enrich_evento(get_evento(evento_id))


def list_eventos_with_opms():
    return [_enrich_evento(d) for d in list_eventos()]


# --------------------------------------------------------------------------
# OpmEvento
# --------------------------------------------------------------------------
COL_OPM_EVENTO = 'opm_eventos'


def list_opm_eventos():
    return b.list_docs(COL_OPM_EVENTO, order_by='opm_evento_id')


def list_opm_eventos_by_evento(evento_id):
    return b.list_docs(COL_OPM_EVENTO, where=[('evento_id', '==', evento_id)],
                       order_by='opm_evento_id')


def get_opm_evento(opm_evento_id):
    return b.get_doc(COL_OPM_EVENTO, opm_evento_id)


def add_opm_evento(data, opm_evento_id=None):
    return b.add_doc(COL_OPM_EVENTO, data,
                     doc_id=opm_evento_id or data.get('opm_evento_id'))


def update_opm_evento(opm_evento_id, data):
    return b.update_doc(COL_OPM_EVENTO, opm_evento_id, data)


def delete_opm_evento(opm_evento_id):
    b.delete_doc(COL_OPM_EVENTO, opm_evento_id)


def count_opm_eventos():
    return b.count_docs(COL_OPM_EVENTO)


def next_opm_evento_id():
    ids = [int(d.get('opm_evento_id') or 0) for d in b.list_docs(COL_OPM_EVENTO)]
    return max(ids, default=0) + 1


def opm_evento_exists(evento_id, opm_id):
    rows = b.list_docs(COL_OPM_EVENTO, where=[('evento_id', '==', evento_id),
                                              ('opm_id', '==', opm_id)])
    return len(rows) > 0


def list_opm_eventos_dropdown():
    """[(opm_evento_id, 'EVENTO - SIGLA'), ...] sorted by event start."""
    items = []
    for oe in b.list_docs(COL_OPM_EVENTO):
        ev = get_evento(oe.get('evento_id'))
        opm = org.get_opm(oe.get('opm_id'))
        items.append({
            'opm_evento_id': oe.get('opm_evento_id'),
            'label': f'{ev.get("evento_desc") if ev else "?"} - {(opm.get("opm_sigla") if opm else "?")}',
            'start': ev.get('evento_dta_inicio') or '' if ev else '',
        })
    items.sort(key=lambda x: x['start'])
    return [(i['opm_evento_id'], i['label']) for i in items]


# --------------------------------------------------------------------------
# Escalas (horas de serviço por militar em evento/OPM)
# --------------------------------------------------------------------------
COL_ESCALAS = 'escalas'


def _escala_key(opm_evento_id, matricula, escala_data):
    return f'{opm_evento_id}_{matricula}_{escala_data}'


def list_escalas(where=None, order_by=None, direction='ASCENDING', limit=None):
    return b.list_docs(COL_ESCALAS, where=where, order_by=order_by,
                       direction=direction, limit=limit)


def list_escalas_by_opm_evento(opm_evento_id):
    return b.list_docs(COL_ESCALAS, where=[('opm_evento_id', '==', int(opm_evento_id))],
                       order_by='escala_data')


def get_escala(opm_evento_id, matricula, escala_data):
    return b.get_doc(COL_ESCALAS, _escala_key(opm_evento_id, matricula, escala_data))


def add_escala(data):
    key = _escala_key(data.get('opm_evento_id'), data.get('matricula'),
                      data.get('escala_data'))
    return b.add_doc(COL_ESCALAS, data, doc_id=key)


def update_escala(opm_evento_id, matricula, escala_data, data):
    return b.update_doc(COL_ESCALAS, _escala_key(opm_evento_id, matricula, escala_data), data)


def delete_escala(opm_evento_id, matricula, escala_data):
    b.delete_doc(COL_ESCALAS, _escala_key(opm_evento_id, matricula, escala_data))


def count_escalas_by_opm_evento(opm_evento_id):
    return b.count_docs(COL_ESCALAS, where=[('opm_evento_id', '==', int(opm_evento_id))])


def horas_por_militar(evento_id, tipo_pagamento=None):
    """Aggregate escala CH totals per military for a given evento."""
    rows = []
    oes = list_opm_eventos_by_evento(int(evento_id))
    for oe in oes:
        for esc in list_escalas_by_opm_evento(oe.get('opm_evento_id')):
            if tipo_pagamento and esc.get('tipo_pagamento') != tipo_pagamento:
                continue
            rows.append(esc)

    agg = {}
    for esc in rows:
        mat = esc.get('matricula')
        a = agg.setdefault(mat, {
            'matricula': mat, 'nome': '', 'cargo': '', 'ch_diurna': 0.0,
            'ch_noturna': 0.0, 'dias': 0,
        })
        a['ch_diurna'] += float(esc.get('escala_ch_diurna') or 0)
        a['ch_noturna'] += float(esc.get('escala_ch_noturna') or 0)
        a['dias'] += 1
    for mat, a in agg.items():
        ef = org.get_efetivo(mat)
        if ef:
            a['nome'] = ef.get('nome') or ''
            a['cargo'] = ef.get('posto_grad') or ef.get('cargo') or ''
        a['ch_diurna'] = round(a['ch_diurna'], 2)
        a['ch_noturna'] = round(a['ch_noturna'], 2)
    return sorted(agg.values(), key=lambda x: x['nome'])


def _enrich_escala(doc):
    if doc is None:
        return None
    mil = org.get_efetivo(doc.get('matricula'))
    if mil:
        doc.update(militar=mil)
        doc.update(militar_nome=mil.get('nome'))
        doc.update(militar_posto=mil.get('posto_grad'))
    return doc


def list_escalas_with_militar(where=None, order_by=None, direction='ASC', limit=None):
    items = list_escalas(where=where, order_by=order_by, direction=direction, limit=limit)
    return [_enrich_escala(d) for d in items]


def get_escala_with_militar(opm_evento_id, matricula, escala_data):
    return _enrich_escala(get_escala(opm_evento_id, matricula, escala_data))


# --------------------------------------------------------------------------
# Escala P2
# --------------------------------------------------------------------------
COL_P2 = 'escala_p2'


def list_p2(mes=None, ano=None):
    where = []
    if mes:
        where.append(('mes', '==', int(mes)))
    if ano:
        where.append(('ano', '==', int(ano)))
    return b.list_docs(COL_P2, where=where if where else None, order_by='ordem')


def get_p2(id_):
    return b.get_doc(COL_P2, id_)


def add_p2(data, doc_id=None):
    return b.add_doc(COL_P2, data, doc_id=doc_id or data.get('id'))


def update_p2(id_, data):
    return b.update_doc(COL_P2, id_, data)


def delete_p2(id_):
    b.delete_doc(COL_P2, id_)


def count_p2(where=None):
    return b.count_docs(COL_P2, where=where)


def next_p2_id():
    ids = [int(d.get('id') or 0) for d in b.list_docs(COL_P2)]
    return max(ids, default=0) + 1


def p2_dias_dict(data):
    """`dias` may be a dict, a JSON string, or missing."""
    dias = data.get('dias')
    if isinstance(dias, dict):
        return dias
    if isinstance(dias, str) and dias.strip():
        try:
            return json.loads(dias)
        except Exception:
            return {}
    return {}


def list_p2_funcs(mes=None, ano=None):
    return sorted({(d.get('funcao') or '') for d in list_p2(mes, ano)})


def list_p2_ghs(mes=None, ano=None):
    return sorted({(d.get('gh') or '') for d in list_p2(mes, ano)})


def list_p2_opms(mes=None, ano=None):
    return sorted({(d.get('opm') or '') for d in list_p2(mes, ano)})


# --------------------------------------------------------------------------
# Escala P2 Meta / Legenda
# --------------------------------------------------------------------------
COL_P2_META = 'escala_p2_meta'
COL_P2_LEGENDA = 'escala_p2_legendas'


def get_p2_meta():
    docs = b.list_docs(COL_P2_META)
    return docs[0] if docs else None


def save_p2_meta(data):
    docs = b.list_docs(COL_P2_META)
    if docs:
        return b.update_doc(COL_P2_META, docs[0].id, data)
    return b.add_doc(COL_P2_META, data, doc_id=data.get('id') or '1')


def list_p2_legendas(order_by='codigo'):
    return b.list_docs(COL_P2_LEGENDA, order_by=order_by)


def get_p2_legenda(id_):
    return b.get_doc(COL_P2_LEGENDA, id_)


def add_p2_legenda(data, doc_id=None):
    return b.add_doc(COL_P2_LEGENDA, data, doc_id=doc_id or data.get('id'))


def update_p2_legenda(id_, data):
    return b.update_doc(COL_P2_LEGENDA, id_, data)


def delete_p2_legenda(id_):
    b.delete_doc(COL_P2_LEGENDA, id_)


def next_p2_legenda_id():
    ids = [int(d.get('id') or 0) for d in b.list_docs(COL_P2_LEGENDA)]
    return max(ids, default=0) + 1


# --------------------------------------------------------------------------
# EscalaSalva (snapshots), with embedded itens + meta
# --------------------------------------------------------------------------
COL_SALVA = 'escalas_salvas'


def list_escalas_salvas(page=1, per_page=20):
    total = b.count_docs(COL_SALVA)
    items = b.list_docs(COL_SALVA, order_by='data_salva', direction='DESC',
                        offset=(page - 1) * per_page, limit=per_page)
    return b.Page(items, page, per_page, total)


def list_all_escalas_salvas():
    return b.list_docs(COL_SALVA, order_by='data_salva', direction='DESC')


def list_escalas_salvas_ativas():
    return b.list_docs(COL_SALVA, where=[('ativa', '==', 1)])


def get_escala_salva(id_):
    return b.get_doc(COL_SALVA, id_)


def get_escala_salva_ativa(mes, ano):
    rows = b.list_docs(COL_SALVA, where=[('mes', '==', int(mes)), ('ano', '==', int(ano)),
                                         ('ativa', '==', 1)])
    return rows[0] if rows else None


def set_escala_salva_ativa(id_):
    escala = get_escala_salva(id_)
    if not escala:
        return False
    # deactivate same mes/ano
    for other in b.list_docs(COL_SALVA, where=[('mes', '==', int(escala.get('mes'))),
                                               ('ano', '==', int(escala.get('ano')))]):
        if other.get('ativa'):
            b.update_doc(COL_SALVA, other.id, {'ativa': 0})
    b.update_doc(COL_SALVA, id_, {'ativa': 1})
    return True


def add_escala_salva(data, doc_id=None):
    return b.add_doc(COL_SALVA, data, doc_id=doc_id or data.get('id'))


def update_escala_salva(id_, data):
    return b.update_doc(COL_SALVA, id_, data)


def delete_escala_salva(id_):
    b.delete_doc(COL_SALVA, id_)


def next_escala_salva_id():
    ids = [int(d.get('id') or 0) for d in b.list_docs(COL_SALVA)]
    return max(ids, default=0) + 1