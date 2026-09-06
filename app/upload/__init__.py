"""Upload blueprint — file import for efetivo (Firestore-backed).

Provides a page to upload a CSV/Excel of efetivos and writes each row
into Firestore via ``app.data``.  No SQLAlchemy dependency remains.
"""
import csv
import unicodedata

from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user

from app import data as d

upload_bp = Blueprint('upload', __name__, url_prefix='/upload')


def _normalize(s):
    """Strip accents, lower-case and strip whitespace."""
    return unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode().lower().strip()


def _resolve_cargo(posto_text, cargo_cache):
    """Fuzzy-match a posto/grad text to a cargo_id."""
    if not posto_text:
        return None
    key = _normalize(posto_text)
    if key in cargo_cache:
        return cargo_cache[key]
    for norm, cid in cargo_cache.items():
        if key in norm or norm in key:
            return cid
    return None


def _resolve_opm(opm_text, opm_cache):
    """Fuzzy-match an OPM text (desc or sigla) to an opm_id."""
    if not opm_text:
        return None
    key = _normalize(opm_text)
    if key in opm_cache:
        return opm_cache[key]
    for norm, oid in opm_cache.items():
        if key in norm or norm in key:
            return oid
    return None


COLUMN_MAP = {
    'matricula': 'matricula',
    'nome': 'nome',
    'funcao': 'funcao',
    'telefone': 'telefone',
    'posto/grad': '_cargo_posto',
    'opm': '_opm_texto',
    'situacao': 'sit',
    'cpf': 'cpf',
    'rg': 'rg',
    'titulo': 'titulo',
    'cnh': 'cnh',
    'categoria': 'categoria',
    'tipo sanguineo': 'tipo_sanguineo',
    'admissao': 'admissao',
    'data nascimento': 'data_nascimento',
    'local trabalho': 'local_trabalho',
    'comportamento': 'comportamento',
}


def _importar_csv(filepath):
    """Parse a semicolon-delimited CSV and upsert rows into Firestore."""
    stats = {'criados': 0, 'atualizados': 0, 'erros': 0}

    cargo_cache = {}
    for c in d.list_cargos():
        cargo_cache[_normalize(c.get('posto_grad') or '')] = c.get('cargo_id') or c.get('id')

    opm_cache = {}
    for o in d.list_opms():
        desc = _normalize(o.get('opm_desc') or '')
        sigla = _normalize(o.get('opm_sigla') or '')
        if desc:
            opm_cache[desc] = o.get('opm_id')
        if sigla:
            opm_cache[sigla] = o.get('opm_id')

    with open(filepath, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f, delimiter=';')
        for row in reader:
            try:
                raw_matricula = (
                    row.get('Matrícula', '') or row.get('Matricula', '')
                ).strip()
                if not raw_matricula:
                    stats['erros'] += 1
                    continue

                mapped = {}
                for csv_header, value in row.items():
                    norm_key = _normalize(csv_header)
                    attr = COLUMN_MAP.get(norm_key)
                    if attr and not attr.startswith('_'):
                        mapped[attr] = (value.strip() if value else '')

                cargo_id = _resolve_cargo(row.get('Posto/Grad', ''), cargo_cache)
                if cargo_id:
                    mapped['cargo'] = cargo_id

                opm_id = _resolve_opm(row.get('OPM', ''), opm_cache)
                if opm_id:
                    mapped['opm_id'] = opm_id

                sit_raw = mapped.pop('sit', '')
                if sit_raw:
                    sit_norm = _normalize(sit_raw)
                    if 'ativo' in sit_norm or 'ativa' in sit_norm:
                        mapped['sit'] = 'AT'
                    elif 'reserva' in sit_norm:
                        mapped['sit'] = 'RS'
                    elif 'licen' in sit_norm:
                        mapped['sit'] = 'LC'
                    elif 'afast' in sit_norm:
                        mapped['sit'] = 'AF'
                    else:
                        mapped['sit'] = sit_raw[:10]

                existed = d.upsert_efetivo(raw_matricula, mapped)
                if existed:
                    stats['atualizados'] += 1
                else:
                    stats['criados'] += 1

            except Exception:
                stats['erros'] += 1

    return stats


@upload_bp.route('/')
@login_required
def index():
    if not current_user.is_supervisor:
        flash('Acesso negado.', 'danger')
        return redirect(url_for('dashboard.index'))

    from app.forms import ImportForm
    form = ImportForm()
    return render_template('upload/index.html', form=form)


@upload_bp.route('/importar', methods=['POST'])
@login_required
def importar():
    if not current_user.is_supervisor:
        flash('Acesso negado.', 'danger')
        return redirect(url_for('dashboard.index'))

    from app.forms import ImportForm
    from werkzeug.utils import secure_filename
    import os
    import uuid

    form = ImportForm()
    if form.validate_on_submit():
        arquivo = form.arquivo.data
        tipo = form.tipo.data

        try:
            filename = secure_filename(arquivo.filename or 'import.csv')
            name, ext = os.path.splitext(filename)
            unique_name = f"{name}_{uuid.uuid4().hex[:8]}{ext}"
            upload_folder = os.path.join(
                os.environ.get('UPLOAD_FOLDER', '/app/uploads'), 'imports')
            os.makedirs(upload_folder, exist_ok=True)
            filepath = os.path.join(upload_folder, unique_name)
            arquivo.save(filepath)

            if tipo == 'efetivo':
                stats = _importar_csv(filepath)
                flash(
                    f'Importacao concluida: {stats["criados"]} criados, '
                    f'{stats["atualizados"]} atualizados, {stats["erros"]} erros',
                    'success',
                )

            try:
                os.remove(filepath)
            except OSError:
                pass
        except Exception as e:
            flash(f'Erro na importacao: {str(e)}', 'danger')

    return redirect(url_for('upload.index'))
