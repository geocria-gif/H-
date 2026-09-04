"""Firestore data access for organizational entities:
cargos, opms, efetivopm, tabela_valores, municipios.
"""
from . import base as b


# --------------------------------------------------------------------------
# Cargos
# --------------------------------------------------------------------------
COL_CARGOS = 'cargos'


def list_cargos():
    return b.list_docs(COL_CARGOS, order_by='posto_grad')


def get_cargo(cargo_id):
    return b.get_doc(COL_CARGOS, cargo_id)


def add_cargo(data, cargo_id):
    return b.add_doc(COL_CARGOS, data, doc_id=cargo_id)


def update_cargo(cargo_id, data):
    return b.update_doc(COL_CARGOS, cargo_id, data)


def delete_cargo(cargo_id):
    b.delete_doc(COL_CARGOS, cargo_id)


# --------------------------------------------------------------------------
# OPMs
# --------------------------------------------------------------------------
COL_OPMS = 'opms'


def list_opms(order_by='opm_sigla'):
    return b.list_docs(COL_OPMS, order_by=order_by)


def get_opm(opm_id):
    return b.get_doc(COL_OPMS, opm_id)


def add_opm(data, opm_id=None):
    return b.add_doc(COL_OPMS, data, doc_id=opm_id or data.get('opm_id'))


def update_opm(opm_id, data):
    return b.update_doc(COL_OPMS, opm_id, data)


def delete_opm(opm_id):
    b.delete_doc(COL_OPMS, opm_id)


def count_opms():
    return b.count_docs(COL_OPMS)


# --------------------------------------------------------------------------
# EfetivoPM
# --------------------------------------------------------------------------
COL_EFETIVO = 'efetivopm'


def _enrich_efetivo(doc):
    if doc is None:
        return None
    if doc.get('cargo'):
        cargo = get_cargo(doc['cargo'])
        if cargo:
            doc.update(cargo_rel=cargo)
            doc.update(posto_grad=cargo.get('posto_grad'))
    if doc.get('opm_id'):
        opm = get_opm(doc['opm_id'])
        if opm:
            doc.update(opm_rel=opm)
            doc.update(opm_sigla=opm.get('opm_sigla'))
    return doc


def get_efetivo(matricula):
    doc = b.get_doc(COL_EFETIVO, matricula)
    return _enrich_efetivo(doc)


def list_efetivos(page=1, per_page=20, opm_id=None, cargo=None, sit=None):
    where = []
    if opm_id:
        where.append(('opm_id', '==', opm_id))
    if cargo:
        where.append(('cargo', '==', cargo))
    if sit:
        where.append(('sit', '==', sit))
    total = b.count_docs(COL_EFETIVO, where=where)
    items = b.list_docs(COL_EFETIVO, where=where, order_by='nome',
                        offset=(page - 1) * per_page, limit=per_page)
    items = [_enrich_efetivo(d) for d in items]
    return b.Page(items, page, per_page, total)


def list_all_efetivos():
    return [_enrich_efetivo(d) for d in b.list_docs(COL_EFETIVO, order_by='nome')]


def list_efetivos_by_opm(opm_id):
    return [_enrich_efetivo(d) for d in
            b.list_docs(COL_EFETIVO, where=[('opm_id', '==', opm_id)], order_by='nome')]


def list_efetivos_by_cargo(cargo_id):
    return [_enrich_efetivo(d) for d in
            b.list_docs(COL_EFETIVO, where=[('cargo', '==', cargo_id)], order_by='nome')]


def search_efetivos(term, page=1, per_page=20):
    """Firestore cannot 'LIKE' a string; we filter by collective prefix where
    possible, then filter in Python. Term may be matricula or name fragment."""
    term = (term or '').strip()
    where = []
    if term.isdigit() and len(term) >= 2:
        # Matriculas are numeric; approximate with >= prefix scan is not
        # supported directly, so we filter client-side over a window.
        prefix = term
        cand = b.list_docs(COL_EFETIVO, limit=2000)
        matched = [d for d in cand if
                   (d.get('matricula') or '').startswith(prefix) or
                   prefix in (d.get('matricula') or '')]
        matched = [d for d in matched if d.get('nome')]
        total = len(matched)
        items = matched[(page - 1) * per_page: page * per_page]
        items = [_enrich_efetivo(d) for d in items]
        return b.Page(items, page, per_page, total)

    cand = b.list_docs(COL_EFETIVO, limit=5000)
    term_l = term.lower()
    matched = []
    for d in cand:
        nome = (d.get('nome') or '').lower()
        mat = (d.get('matricula') or '').lower()
        if term_l in nome or term_l in mat:
            matched.append(d)
    matched.sort(key=lambda d: (d.get('nome') or ''))
    total = len(matched)
    items = matched[(page - 1) * per_page: page * per_page]
    items = [_enrich_efetivo(d) for d in items]
    return b.Page(items, page, per_page, total)


def search_efetivos_json(term, limit=20):
    cand = b.list_docs(COL_EFETIVO, limit=5000)
    term_l = (term or '').strip().lower()
    matched = []
    for d in cand:
        nome = (d.get('nome') or '').lower()
        mat = (d.get('matricula') or '').lower()
        if term_l in nome or term_l in mat:
            matched.append(d)
        if len(matched) >= limit:
            break
    result = []
    for d in matched:
        d = _enrich_efetivo(d)
        result.append({
            'matricula': d.get('matricula'),
            'nome': d.get('nome'),
            'funcao': d.get('funcao'),
            'telefone': d.get('telefone'),
            'opm': d.get('opm_sigla'),
            'cargo': d.get('posto_grad'),
        })
    return result


def add_efetivo(data, matricula=None):
    mid = matricula or data.get('matricula')
    return b.add_doc(COL_EFETIVO, data, doc_id=mid)


def update_efetivo(matricula, data):
    return b.update_doc(COL_EFETIVO, matricula, data)


def delete_efetivo(matricula):
    b.delete_doc(COL_EFETIVO, matricula)


def count_efetivos(where=None):
    return b.count_docs(COL_EFETIVO, where=where)


def efetivo_matriculas():
    """Return all matriculas (for bulk client-side joins)."""
    return [d.get('matricula') for d in b.list_docs(COL_EFETIVO)]


# --------------------------------------------------------------------------
# Tabela Valores
# --------------------------------------------------------------------------
COL_TABELA = 'tabela_valores'


def list_tabela_valores():
    return b.list_docs(COL_TABELA, order_by='posto_grad')


def get_tabela_valor(id_):
    return b.get_doc(COL_TABELA, id_)


def get_tabela_valor_by_posto(posto_grad):
    rows = b.list_docs(COL_TABELA, where=[('posto_grad', '==', posto_grad)])
    return rows[0] if rows else None


def add_tabela_valor(data, doc_id=None):
    return b.add_doc(COL_TABELA, data, doc_id=doc_id or data.get('id'))


def update_tabela_valor(id_, data):
    return b.update_doc(COL_TABELA, id_, data)


def delete_tabela_valor(id_):
    b.delete_doc(COL_TABELA, id_)


# --------------------------------------------------------------------------
# Municipios
# --------------------------------------------------------------------------
COL_MUNICIPIOS = 'municipios'


def list_municipios(order_by='nome'):
    return b.list_docs(COL_MUNICIPIOS, order_by=order_by)


def get_municipio(id_):
    return b.get_doc(COL_MUNICIPIOS, id_)


def add_municipio(data, doc_id=None):
    return b.add_doc(COL_MUNICIPIOS, data, doc_id=doc_id or data.get('id'))


def update_municipio(id_, data):
    return b.update_doc(COL_MUNICIPIOS, id_, data)


def delete_municipio(id_):
    b.delete_doc(COL_MUNICIPIOS, id_)