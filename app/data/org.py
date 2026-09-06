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
    """Full collection read (~30.5k docs). AVOID in request paths — costs
    ~30.5k Firestore reads. Prefer list_efetivos()/search_efetivos()."""
    return [_enrich_efetivo(d) for d in b.list_docs(COL_EFETIVO, order_by='nome')]


def list_efetivos_by_opm(opm_id):
    return [_enrich_efetivo(d) for d in
            b.list_docs(COL_EFETIVO, where=[('opm_id', '==', opm_id)], order_by='nome')]


def list_efetivos_by_cargo(cargo_id):
    return [_enrich_efetivo(d) for d in
            b.list_docs(COL_EFETIVO, where=[('cargo', '==', cargo_id)], order_by='nome')]


import time as _t

# Firestore read budget: efetivopm has ~30.5k docs (daily cap 50k reads).
# Bounded prefix queries keep every search under a couple hundred reads.
_SEARCH_PREFIX_CAP = 100      # exact-prefix query limit (name/matricula)
_SEARCH_SWEEP_CAP = 250       # bounded substring sweep when the prefix hits none
_SEARCH_TTL = 60              # seconds a candidate window is reused
_search_cache = {}


def _candidates(term, opm_id=None):
    """Bound the Firestore reads a search may trigger.

    Returns a deduplicated candidate Doc list for ``term`` (matricula prefix or
    name prefix), optionally post-filtered by ``opm_id``.  Reads at most
    ``_SEARCH_PREFIX_CAP`` docs for the prefix query, plus at most
    ``_SEARCH_SWEEP_CAP`` on a rare substring fallback — never a full scan.
    """
    cache_key = (term, str(opm_id))
    now = _t.time()
    hit = _search_cache.get(cache_key)
    if hit and now - hit[0] < _SEARCH_TTL:
        return hit[1]

    term = (term or '').strip()
    seen = set()
    cand = []

    def _merge(docs):
        for doc in docs:
            mid = str(doc.get('matricula') or doc.get('id') or getattr(doc, 'id', ''))
            if mid and mid not in seen:
                seen.add(mid)
                cand.append(doc)

    if term.isdigit():
        exact = b.get_doc(COL_EFETIVO, term)
        if exact:
            _merge([exact])
        try:
            _merge(b.list_docs(
                COL_EFETIVO,
                where=[('matricula', '>=', term),
                       ('matricula', '<', term + '\uf8ff')],
                order_by='matricula', limit=_SEARCH_PREFIX_CAP))
        except Exception:
            _merge(b.list_docs(COL_EFETIVO, limit=_SEARCH_PREFIX_CAP))
    elif term:
        upper = term.upper()
        try:
            _merge(b.list_docs(
                COL_EFETIVO,
                where=[('nome', '>=', upper),
                       ('nome', '<', upper + '\uf8ff')],
                order_by='nome', limit=_SEARCH_PREFIX_CAP))
        except Exception:
            _merge(b.list_docs(COL_EFETIVO, limit=_SEARCH_PREFIX_CAP))
        if not cand:
            _merge(b.list_docs(COL_EFETIVO, order_by='nome',
                               limit=_SEARCH_SWEEP_CAP))

    if opm_id:
        cand = [d for d in cand if str(d.get('opm_id')) == str(opm_id)]
    _search_cache[cache_key] = (now, cand)
    return cand


def search_efetivos(term, page=1, per_page=20, opm_id=None):
    """Search efetivo by matricula/name prefix; reads stay bounded.

    Substring matching runs over a bounded candidate window so one search costs
    at most ~(PREFIX_CAP + SWEEP_CAP) reads instead of a 30.5k-doc scan.
    ``total`` counts matches found within that window, not the whole table.
    """
    term = (term or '').strip()
    cand = _candidates(term, opm_id=opm_id)
    term_l = term.lower()
    matched = []
    for d in cand:
        nome = (d.get('nome') or '').lower()
        mat = (d.get('matricula') or '').lower()
        if term_l in nome or term_l in mat:
            matched.append(d)
    total = len(matched)
    start = (page - 1) * per_page
    items = [_enrich_efetivo(d) for d in matched[start:start + per_page]]
    return b.Page(items, page, per_page, total)


def search_efetivos_json(term, limit=20):
    if not (term or '').strip():
        return []
    cand = _candidates(term)
    term_l = term.lower()
    matched = []
    for d in cand:
        if len(matched) >= limit:
            break
        nome = (d.get('nome') or '').lower()
        mat = (d.get('matricula') or '').lower()
        if term_l in nome or term_l in mat:
            matched.append(d)
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


def efetivo_matriculas(limit=None):
    """All matriculas for bulk joins. Pass ``limit`` or prefer paginated scans:
    without a limit this reads the whole ~30.5k collection."""
    return [d.get('matricula') for d in
            b.list_docs(COL_EFETIVO, limit=limit)]


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