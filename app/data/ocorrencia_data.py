"""Firestore data access for ocorrencias, viaturas and related metadata."""
from . import base as b
from . import org as org


# --------------------------------------------------------------------------
# Ocorrencias
# --------------------------------------------------------------------------
COL_OCORRENCIAS = 'ocorrencias'


def _enrich_ocorrencia(doc):
    return doc


def list_ocorrencias(page=1, per_page=20, tipo=None, data_inicio=None, data_fim=None):
    """data_* compare lexicographically (stored as string dates / datetime)."""
    where = []
    if tipo:
        where.append(('tipo', '==', tipo))
    docs = b.list_docs(COL_OCORRENCIAS, where=where if where else None)
    docs = sorted(docs, key=lambda d: d.get('data_hora') or '', reverse=True)
    if data_inicio:
        docs = [d for d in docs if (d.get('data_hora') or '') >= data_inicio]
    if data_fim:
        docs = [d for d in docs if (d.get('data_hora') or '') <= data_fim]
    total = len(docs)
    start = (page - 1) * per_page
    return b.Page([_enrich_ocorrencia(d) for d in docs[start:start + per_page]],
                  page, per_page, total)


def list_all_ocorrencias():
    return [_enrich_ocorrencia(d) for d in
            b.list_docs(COL_OCORRENCIAS, order_by='data_hora', direction='DESC')]


def list_ocorrencias_recentes(limit=5):
    return [_enrich_ocorrencia(d) for d in
            b.list_docs(COL_OCORRENCIAS, order_by='data_hora', direction='DESC', limit=limit)]


def list_ocorrencias_por_tipo():
    """Return [(tipo, count)]."""
    counts = {}
    for d in b.list_docs(COL_OCORRENCIAS):
        t = d.get('tipo') or 'OUTRO'
        counts[t] = counts.get(t, 0) + 1
    return sorted(counts.items())


def get_ocorrencia(id_):
    return _enrich_ocorrencia(b.get_doc(COL_OCORRENCIAS, id_))


def add_ocorrencia(data, doc_id=None):
    return b.add_doc(COL_OCORRENCIAS, data, doc_id=doc_id or data.get('id'))


def update_ocorrencia(id_, data):
    return b.update_doc(COL_OCORRENCIAS, id_, data)


def delete_ocorrencia(id_):
    b.delete_doc(COL_OCORRENCIAS, id_)


def count_ocorrencias(where=None):
    return b.count_docs(COL_OCORRENCIAS, where=where)


def next_ocorrencia_id():
    ids = [int(d.get('id') or 0) for d in b.list_docs(COL_OCORRENCIAS)]
    return max(ids, default=0) + 1


# --------------------------------------------------------------------------
# OcorrenciaEvento (metrics grid)
# --------------------------------------------------------------------------
COL_OC_EVENTO = 'ocorrencia_eventos'


def list_ocorrencia_eventos(data_ref=None):
    where = [('data_ref', '==', data_ref)] if data_ref else None
    return b.list_docs(COL_OC_EVENTO, where=where)


def list_ocorrencia_eventos_todos():
    return b.list_docs(COL_OC_EVENTO)


def get_ocorrencia_evento(data_ref, grupo, metrica):
    rows = [r for r in b.list_docs(COL_OC_EVENTO, where=[('data_ref', '==', data_ref)])
            if r.get('grupo') == grupo and r.get('metrica') == metrica]
    return rows[0] if rows else None


def add_ocorrencia_evento(data, doc_id=None):
    return b.add_doc(COL_OC_EVENTO, data, doc_id=doc_id or
                     f"{data.get('data_ref')}_{data.get('grupo')}_{data.get('metrica')}")


def update_ocorrencia_evento(doc_id, data):
    return b.update_doc(COL_OC_EVENTO, doc_id, data)


def delete_ocorrencia_evento(doc_id):
    b.delete_doc(COL_OC_EVENTO, doc_id)


def delete_ocorrencia_eventos_by_data_ref(data_ref):
    for d in list_ocorrencia_eventos(data_ref):
        b.delete_doc(COL_OC_EVENTO, d.id)


# --------------------------------------------------------------------------
# OcorrenciaMeta (source metadata)
# --------------------------------------------------------------------------
COL_OC_META = 'ocorrencia_meta'


def list_ocorrencia_meta():
    return b.list_docs(COL_OC_META, order_by='data_ref', direction='DESC')


def get_ocorrencia_meta(data_ref):
    return b.get_doc(COL_OC_META, data_ref)


def add_ocorrencia_meta(data):
    return b.add_doc(COL_OC_META, data, doc_id=data.get('data_ref'))


def update_ocorrencia_meta(data_ref, data):
    return b.update_doc(COL_OC_META, data_ref, data)


def delete_ocorrencia_meta(data_ref):
    b.delete_doc(COL_OC_META, data_ref)


# --------------------------------------------------------------------------
# OcorrenciaConfig (settings)
# --------------------------------------------------------------------------
COL_OC_CONFIG = 'ocorrencia_config'


def list_ocorrencia_config():
    return b.list_docs(COL_OC_CONFIG)


def get_ocorrencia_config(chave, default=None):
    doc = b.get_doc(COL_OC_CONFIG, chave)
    return doc.get('valor', default) if doc else default


def set_ocorrencia_config(chave, valor):
    return b.add_doc(COL_OC_CONFIG, {'chave': chave, 'valor': valor}, doc_id=chave)


def delete_ocorrencia_config(chave):
    b.delete_doc(COL_OC_CONFIG, chave)


# --------------------------------------------------------------------------
# Viaturas
# --------------------------------------------------------------------------
COL_VIATURAS = 'viaturas'


def list_viaturas(page=1, per_page=20, situacao=None, municipio=None):
    docs = b.list_docs(COL_VIATURAS, order_by='prefixo')
    if situacao:
        docs = [d for d in docs if d.get('situacao') == situacao]
    if municipio:
        docs = [d for d in docs if d.get('municipio') == municipio]
    total = len(docs)
    start = (page - 1) * per_page
    return b.Page(docs[start:start + per_page], page, per_page, total)


def list_all_viaturas():
    return b.list_docs(COL_VIATURAS, order_by='prefixo')


def get_viatura(prefixo):
    return b.get_doc(COL_VIATURAS, prefixo)


def add_viatura(data, doc_id=None):
    return b.add_doc(COL_VIATURAS, data, doc_id=doc_id or data.get('prefixo'))


def update_viatura(prefixo, data):
    return b.update_doc(COL_VIATURAS, prefixo, data)


def delete_viatura(prefixo):
    b.delete_doc(COL_VIATURAS, prefixo)


def viatura_situacoes():
    return sorted({(d.get('situacao') or '') for d in b.list_docs(COL_VIATURAS)})


def viatura_municipios():
    return sorted({(d.get('municipio') or '') for d in b.list_docs(COL_VIATURAS)})