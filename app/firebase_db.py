"""Firebase Firestore connection + low-level document helpers.

The whole app's data access is routed through this module. It mirrors the
previous SQLAlchemy model layer with a Firestore-backed implementation.

Collections (Firestore) mirror the legacy tables:
    usuarios, cargos, opms, efetivopm, eventos, opm_eventos, escalas,
    tabela_valores, escala_p2, escala_p2_meta, escala_p2_legendas,
    ocorrencias, ocorrencia_eventos, ocorrencia_meta, ocorrencia_config,
    municipios, viaturas, escalas_salvas
"""
import math
import os
from datetime import datetime

import firebase_admin
from firebase_admin import credentials, auth, firestore

_fs = None
_initialized = False


def init_firebase(app=None):
    """Initialize the Firebase Admin SDK using the app config / env vars."""
    global _fs, _initialized
    if _initialized:
        return _fs

    sa_path = os.environ.get('FIREBASE_SERVICE_ACCOUNT')
    if app is not None:
        sa_path = app.config.get('FIREBASE_SERVICE_ACCOUNT', sa_path)

    if not _fs:
        if sa_path and os.path.exists(sa_path):
            cred = credentials.Certificate(sa_path)
        else:
            # Fallback to Application Default Credentials.
            cred = credentials.ApplicationDefault()
        firebase_admin.initialize_app(cred)
        _fs = firestore.client()
    _initialized = True
    return _fs


def get_fs():
    if not _initialized:
        init_firebase()
    return _fs


def get_auth():
    return auth


def close_firebase():
    global _fs, _initialized
    if firebase_admin._apps:
        for app_ in list(firebase_admin._apps.values()):
            firebase_admin.delete_app(app_)
    _fs = None
    _initialized = False


def _safe(value):
    """Recursively make a value Firestore-safe."""
    if isinstance(value, dict):
        return {k: _safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_safe(v) for v in value]
    if isinstance(value, float):
        return None if value != value else value  # NaN -> None
    if isinstance(value, datetime):
        return value.isoformat()
    return value


class Doc:
    """Attribute + item access wrapper around a Firestore document dict."""

    def __init__(self, data, id_=None, collection=None):
        object.__setattr__(self, '_Doc__data', dict(data or {}))
        object.__setattr__(self, '_Doc__id', id_)
        object.__setattr__(self, '_Doc__collection', collection)

    @property
    def id(self):
        return self._Doc__id

    @property
    def data(self):
        return self._Doc__data

    def __getattr__(self, name):
        data = self._Doc__data
        if name in data:
            value = data[name]
            if isinstance(value, dict):
                sub = Doc(value)
                object.__setattr__(sub, '_Doc__id', name)
                return sub
            return value
        raise AttributeError(name)

    def __getitem__(self, key):
        return self._Doc__data[key]

    def __setitem__(self, key, value):
        self._Doc__data[key] = value

    def __contains__(self, key):
        return key in self._Doc__data

    def __iter__(self):
        return iter(self._Doc__data)

    def keys(self):
        return self._Doc__data.keys()

    def items(self):
        return self._Doc__data.items()

    def get(self, key, default=None):
        return self._Doc__data.get(key, default)

    def update(self, **kwargs):
        self._Doc__data.update(kwargs)

    def to_dict(self):
        return dict(self._Doc__data)

    def __repr__(self):
        return f'<Doc {self._Doc__collection}:{self._Doc__id}>'


class Page:
    """Pagination object mimicking the SQLAlchemy pagination API."""

    def __init__(self, items, page, per_page, total):
        self.items = items
        self.page = page or 1
        self.per_page = per_page or 20
        self.total = total
        self.total_count = total
        self.pages = max(1, math.ceil(total / self.per_page)) if self.per_page else 1

    @property
    def has_prev(self):
        return self.page > 1

    @property
    def has_next(self):
        return self.page < self.pages

    @property
    def prev_num(self):
        return self.page - 1

    @property
    def next_num(self):
        return self.page + 1

    def iter_pages(self, left_edge=2, left_current=2, right_current=4, right_edge=2):
        last = 0
        for num in range(1, self.pages + 1):
            if num <= left_edge or \
               (self.page - left_current - 1 < num < self.page + right_current) or \
               num > self.pages - right_edge:
                if last + 1 != num:
                    yield None
                yield num
                last = num


# ---------------------------------------------------------------------------
# Low-level Firestore helpers
# ---------------------------------------------------------------------------

# Collections keyed by a natural field (not the document id). The first
# Firestore migration stored docs under fallback ids like "tbEfetivoPM_0", so
# keyed lookups must fall back to an equality query when the doc-id lookup
# misses. (ocorrencia_eventos is always queried by fields; escalas were
# renamed to their composite keys.)
NATURAL_KEYS = {
    'usuarios': 'matricula',
    'efetivopm': 'matricula',
    'cargos': 'cargo_id',
    'opms': 'opm_id',
    'tabela_valores': 'id',
    'municipios': 'id',
    'viaturas': 'prefixo',
    'eventos': 'evento_id',
    'opm_eventos': 'opm_evento_id',
    'escala_p2': 'id',
    'escala_p2_meta': 'id',
    'escala_p2_legendas': 'id',
    'escalas_salvas': 'escala_salva_id',
    'ocorrencias': 'id',
    'ocorrencia_meta': 'data_ref',
    'ocorrencia_config': 'chave',
}


def _resolve(collection, value):
    """Return (doc_id, snapshot) for a natural key.

    Tries the doc-id lookup first; if it misses and ``collection`` has a
    natural field configured, falls back to an equality query on that field
    (legacy fallback ids like ``tbEfetivoPM_0`` live on the value, not the id).
    """
    fs = get_fs()
    ref = fs.collection(collection).document(str(value))
    snap = ref.get()
    if snap.exists:
        return ref.id, snap
    field = NATURAL_KEYS.get(collection)
    if field:
        found = fs.collection(collection).where(field, '==', _safe(value)).limit(1).get()
        if len(found):
            return found[0].id, found[0]
    return ref.id, snap


def list_docs(collection, where=None, order_by=None, direction='ASCENDING',
              limit=None, offset=None):
    """where: list of (field, op, value) tuples. op in ==, !=, >, <, >=, <=, in, array_contains."""
    fs = get_fs()
    q = fs.collection(collection)
    for field, op, value in (where or []):
        value = _safe(value)
        if op in ('==', '!=', '>', '<', '>=', '<='):
            q = q.where(field, op, value)
        elif op == 'in':
            q = q.where(field, 'in', value)
        elif op == 'array_contains':
            q = q.where(field, 'array_contains', value)
    if order_by:
        direction = 'DESCENDING' if direction == 'desc' else 'ASCENDING'
        q = q.order_by(order_by, direction=direction)
    if offset:
        q = q.offset(offset)
    if limit:
        q = q.limit(limit)
    snaps = q.get()
    return [doc_from(snap) for snap in snaps]


def get_doc(collection, doc_id, default=None):
    _, snap = _resolve(collection, doc_id)
    if snap.exists:
        return doc_from(snap)
    return default


def add_doc(collection, data, doc_id=None):
    fs = get_fs()
    data = _safe(data)
    ref = fs.collection(collection).document(doc_id) if doc_id else \
        fs.collection(collection).document()
    ref.set(data)
    return Doc(data, id_=ref.id, collection=collection)


def update_doc(collection, doc_id, data, merge=True):
    fs = get_fs()
    real_id, _ = _resolve(collection, doc_id)
    ref = fs.collection(collection).document(real_id)
    ref.set(_safe(data), merge=merge)
    return Doc(_safe(data), id_=ref.id, collection=collection)


def delete_doc(collection, doc_id):
    fs = get_fs()
    real_id, _ = _resolve(collection, doc_id)
    fs.collection(collection).document(real_id).delete()


def count_docs(collection, where=None):
    """Count documents without reading them.

    Uses Firestore's aggregate count query (O(1), no per-document reads) so a
    paginated page / dashboard never scans the whole collection. Falls back to
    scanning only when the aggregate API is unavailable.
    """
    fs = get_fs()
    q = fs.collection(collection)
    for field, op, value in (where or []):
        q = q.where(field, op, _safe(value))
    try:
        agg = q.count()
        result = agg.get()
        return int(result[0][0].value)
    except Exception:
        return len(q.get())


def delete_all(collection):
    fs = get_fs()
    snaps = fs.collection(collection).get()
    for snap in snaps:
        snap.reference.delete()


def doc_from(snap):
    return Doc(snap.to_dict() or {}, id_=snap.id, collection=snap.reference._path[-2] if len(snap.reference._path) >= 2 else None)