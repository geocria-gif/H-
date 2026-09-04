"""Firestore data access for usuarios + Firebase Auth helpers."""
from datetime import datetime

from . import base as b

COL_USUARIOS = 'usuarios'
EMAIL_DOMAIN = 'gestoper.local'


def auth_email(matricula):
    return f'{matricula}@{EMAIL_DOMAIN}'


def get_usuario(matricula):
    return b.get_doc(COL_USUARIOS, matricula)


def get_usuario_by_email(email):
    local = (email or '').split('@')[0]
    return get_usuario(local)


def list_usuarios():
    return b.list_docs(COL_USUARIOS, order_by='nome')


def add_usuario(data):
    return b.add_doc(COL_USUARIOS, data, doc_id=data.get('matricula'))


def update_usuario(matricula, data):
    return b.update_doc(COL_USUARIOS, matricula, data)


def delete_usuario(matricula):
    b.delete_doc(COL_USUARIOS, matricula)


def usuario_to_dict(doc):
    if doc is None:
        return None
    return {
        'id': doc.get('id'),
        'matricula': doc.get('matricula'),
        'nome': doc.get('nome'),
        'tipo': doc.get('tipo'),
        'criado_em': doc.get('criado_em'),
        'ultimo_login': doc.get('ultimo_login'),
        'ativo': bool(doc.get('ativo', True)),
    }


def create_auth_user(matricula, senha, nome, tipo='USER'):
    """Create a Firebase Auth password user. Returns (uid, email)."""
    auth = b.get_auth()
    email = auth_email(matricula)
    try:
        existing = auth.get_user_by_email(email)
        return existing.uid, email
    except auth.UserNotFoundError:
        pass
    user = auth.create_user(
        email=email,
        password=str(senha),
        display_name=nome,
        disabled=False,
    )
    auth.set_custom_user_claims(user.uid, {'tipo': tipo, 'matricula': matricula})
    return user.uid, email


def reset_auth_password(matricula, nova_senha):
    auth = b.get_auth()
    email = auth_email(matricula)
    user = auth.get_user_by_email(email)
    auth.update_user(user.uid, password=str(nova_senha))


def update_auth_user(matricula, nome=None, ativo=None):
    auth = b.get_auth()
    email = auth_email(matricula)
    user = auth.get_user_by_email(email)
    kw = {}
    if nome:
        kw['display_name'] = nome
    if ativo is not None:
        kw['disabled'] = not ativo
    return auth.update_user(user.uid, **kw)


def verify_id_token(id_token):
    """Verify a client-provided Firebase ID token. Returns dict or None."""
    auth = b.get_auth()
    try:
        claims = auth.verify_id_token(id_token, check_revoked=False)
        return claims
    except auth.InvalidIdTokenError:
        return None
    except auth.ExpiredIdTokenError:
        return None
    except auth.RevokedIdTokenError:
        return None


def get_user_by_uid(uid):
    auth = b.get_auth()
    try:
        user = auth.get_user(uid)
    except auth.UserNotFoundError:
        return None
    email = user.email or ''
    local = email.split('@')[0]
    ori = get_usuario(local)
    if ori is not None:
        return ori
    # Fallback: custom claim matricula
    claims = user.custom_claims or {}
    mat = claims.get('matricula')
    if mat:
        ori = get_usuario(mat)
        if ori is not None:
            return ori
    return usuario_doc_from_auth(user)


def usuario_doc_from_auth(user):
    claims = user.custom_claims or {}
    mat = claims.get('matricula') or (user.email or '').split('@')[0]
    return {
        'matricula': mat,
        'nome': user.display_name or '',
        'tipo': claims.get('tipo', 'USER'),
        'ativo': not user.disabled,
        'email': user.email,
        'uid': user.uid,
        'ultimo_login': None,
        'criado_em': None,
    }


def touch_ultimo_login(matricula):
    update_usuario(matricula, {'ultimo_login': datetime.utcnow().isoformat()})