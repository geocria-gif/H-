"""Session-aware user object backed by Firestore (replaces the SQLAlchemy
Usuario). Works with flask-login and flask-jwt-extended.
"""
from app import data as d


class FireUser:
    """Wraps a Firestore usuario doc and exposes the interface the app
    templates/views expect (is_authenticated, is_admin, ...)."""

    def __init__(self, doc, uid=None, email=None, id_token=None):
        self._doc = doc
        self._uid = uid
        self._email = email
        self._id_token = id_token

    # -- flask-login interface -------------------------------------------
    @property
    def is_active(self):
        return bool(self._doc.get('ativo', True) if self._doc else True)

    @property
    def is_authenticated(self):
        return self._doc is not None

    @property
    def is_anonymous(self):
        return False

    def get_id(self):
        mat = self._doc.get('matricula') if self._doc else None
        return str(mat or self._uid or '').strip() or 'anon'

    # -- role helpers ------------------------------------------------------
    @property
    def is_admin(self):
        return (self.tipo or '') == 'ADMIN'

    @property
    def is_supervisor(self):
        return (self.tipo or '') in ('ADMIN', 'SUPERVISOR')

    @property
    def is_operador(self):
        return (self.tipo or '') in ('ADMIN', 'SUPERVISOR', 'OPERADOR')

    @property
    def tipo(self):
        return self._doc.get('tipo') if self._doc else 'USER'

    @property
    def nome(self):
        return self._doc.get('nome') if self._doc else ''

    @property
    def matricula(self):
        return self._doc.get('matricula') if self._doc else ''

    @property
    def uid(self):
        return self._uid

    @property
    def email(self):
        return self._email or (d.auth_email(self.matricula) if self.matricula else '')

    @property
    def id_token(self):
        return self._id_token

    def to_dict(self):
        base = d.usuario_to_dict(self._doc) or {}
        base.setdefault('matricula', self.matricula)
        base.setdefault('nome', self.nome)
        base.setdefault('tipo', self.tipo)
        base['email'] = self.email
        base['uid'] = self.uid
        return base

    def __repr__(self):
        return f'<FireUser {self.matricula} - {self.nome}>'


def load_user_by_matricula(matricula):
    doc = d.get_usuario(matricula)
    if doc is None:
        return None
    return FireUser(doc)


def load_user_by_uid(uid):
    """Look up a user by Firebase Auth UID/custom claims."""
    auth = d.get_auth()
    try:
        user = auth.get_user(uid)
    except auth.UserNotFoundError:
        return None
    doc = None
    email = user.email or ''
    if email:
        doc = d.get_usuario_by_email(email)
    if doc is None:
        claims = user.custom_claims or {}
        mat = claims.get('matricula')
        if mat:
            doc = d.get_usuario(mat)
    if doc is None:
        mat = (email or '').split('@')[0]
        if mat and mat.isdigit():
            doc = d.get_usuario(mat)
    if doc is None:
        return None
    return FireUser(doc, uid=uid, email=email)