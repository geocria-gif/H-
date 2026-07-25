import csv
import io
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user

upload_bp = Blueprint('upload', __name__, url_prefix='/upload')


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
    from app.services import upload_service, efetivo_service

    form = ImportForm()
    if form.validate_on_submit():
        arquivo = form.arquivo.data
        tipo = form.tipo.data

        try:
            filepath = upload_service.save_file(arquivo, 'imports')

            if tipo == 'efetivo':
                stats = efetivo_service.importar_csv(filepath)
                flash(
                    f'Importacao concluida: {stats["criados"]} criados, '
                    f'{stats["atualizados"]} atualizados, {stats["erros"]} erros',
                    'success',
                )

            upload_service.delete_file(filepath)
        except Exception as e:
            flash(f'Erro na importacao: {str(e)}', 'danger')

    return redirect(url_for('upload.index'))
