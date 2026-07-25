"""
Seed script for SISPM - Creates initial data for development/production
"""
import click
from flask.cli import with_appcontext
from app import db
from app.models import (
    Usuario, Cargo, OPM, EfetivoPM, Evento, OpmEvento,
    TabelaValores, EscalaP2Legenda, EscalaP2Meta
)
from werkzeug.security import generate_password_hash


def seed_admin():
    """Create admin user"""
    if not Usuario.query.filter_by(matricula='30481332').first():
        admin = Usuario(
            matricula='30481332',
            nome='FRANCISCO ROCHA JUNIOR',
            tipo='ADMIN'
        )
        admin.set_senha('30481332')
        db.session.add(admin)
        click.echo('  ✓ Admin user created')


def seed_cargos():
    """Create basic cargos"""
    cargos_data = [
        ('03300', 'RECRUTA', 'MILITAR', 'PRACA', ''),
        ('03330', 'SD PM', 'MILITAR', 'PRACA', ''),
        ('03335', 'AL CB PM', 'MILITAR', 'PRACA', ''),
        ('03340', 'CB PM', 'MILITAR', 'PRACA', ''),
        ('03350', '3º SGT PM', 'MILITAR', 'PRACA', ''),
        ('03360', '2º SGT PM', 'MILITAR', 'PRACA', ''),
        ('03370', '1º SGT PM', 'MILITAR', 'PRACA', ''),
        ('03380', 'SUBTEN PM', 'MILITAR', 'PRACA', ''),
        ('03400', '2º TEN PM', 'MILITAR', 'OFICIAL', ''),
        ('03410', '1º TEN PM', 'MILITAR', 'OFICIAL', ''),
        ('03420', 'CAP PM', 'MILITAR', 'OFICIAL', ''),
        ('03430', 'MAJ PM', 'MILITAR', 'OFICIAL', ''),
        ('03440', 'TEN CEL PM', 'MILITAR', 'OFICIAL', ''),
        ('03450', 'CEL PM', 'MILITAR', 'OFICIAL', ''),
    ]
    
    for cargo_data in cargos_data:
        if not Cargo.query.get(cargo_data[0]):
            cargo = Cargo(
                cargo_id=cargo_data[0],
                posto_grad=cargo_data[1],
                tipo_servidor=cargo_data[2],
                tipo_militar=cargo_data[3],
                classif_of=cargo_data[4]
            )
            db.session.add(cargo)
    click.echo('  ✓ Cargos created')


def seed_opms():
    """Create basic OPMs"""
    opms_data = [
        ('2050510', 'COMANDO DE POLICIAMENTO DA REGIÃO CENTRO NORTE', 'CPR-CN', 0, '', '', 'IRECÊ', '', 'ROBERTO SANTANA DE ARAÚJO - CEL PM', 'COMANDANTE'),
        ('2050107', '7º BATALHÃO DE POLÍCIA MILITAR', '7º BPM', 23, 'FIM', 'INTERIOR', 'IRECÊ', 'BARBALHO', 'ADRIANO SOUZA DIAS - TEN CEL', 'COMANDANTE'),
        ('2050404', '3ª COMPANHIA INDEPENDENTE DE POLÍCIA MILITAR', '3ª CIPM', 68, 'FIM', 'INTERIOR', 'MORRO DO CHAPÉU', 'SEDE', 'CLAUDIO JOSE ARAUJO SOUZA - MAJ PM', 'COMANDANTE'),
        ('2050428', '10ª COMPANHIA INDEPENDENTE DE POLÍCIA MILITAR', '10ª CIPM', 78, 'FIM', 'INTERIOR', 'XIQUE-XIQUE', 'SEDE', 'ALBERT NOGUEIRA DE SOUSA - MAJ PM', 'COMANDANTE'),
        ('2050511', 'COMPANHIA INDEPENDENTE DE POLICIAMENTO TATICO CN', 'CIPT-CN', 0, 'FIM', 'INTERIOR', 'LAPÃO', 'SEDE', 'THIAGO DA SILVA OLIVEIRA - MAJ PM', 'COMANDANTE'),
        ('2050438', 'COMPANHIA INDEPENDENTE DE POLICIAMENTO ESPECIALIZADO SEMIÁRIDO', 'CIPE SEMIÁRIDO', 86, 'FIM', 'INTERIOR', 'XIQUE-XIQUE', 'SEDE', 'FABRÍCIO SOUZA GOMES - MAJ PM', 'COMANDANTE'),
    ]
    
    for opm_data in opms_data:
        if not OPM.query.get(opm_data[0]):
            opm = OPM(
                opm_id=opm_data[0],
                opm_desc=opm_data[1],
                opm_sigla=opm_data[2],
                opm_ordem=opm_data[3],
                opm_atv=opm_data[4],
                opm_regiao=opm_data[5],
                opm_municipio=opm_data[6],
                opm_bairro=opm_data[7],
                comandante=opm_data[8],
                funcao=opm_data[9]
            )
            db.session.add(opm)
    click.echo('  ✓ OPMs created')


def seed_tabela_valores():
    """Create tabela de valores"""
    valores_data = [
        ('CEL PM', 130.46, 65.23, 70.83, 84.95),
        ('TEN CEL PM', 118.70, 59.35, 68.95, 82.71),
        ('MAJ PM', 109.17, 54.59, 68.36, 82.01),
        ('CAP PM', 99.64, 49.82, 67.77, 81.31),
        ('1º TEN PM', 90.11, 45.06, 67.18, 80.61),
        ('2º TEN PM', 80.58, 40.29, 66.59, 79.91),
        ('SUBTEN PM', 71.05, 35.53, 66.00, 79.21),
        ('1º SGT PM', 61.52, 30.76, 65.41, 78.51),
        ('2º SGT PM', 51.99, 25.99, 64.82, 77.81),
        ('3º SGT PM', 42.46, 21.23, 64.23, 77.11),
        ('CB PM', 32.93, 16.47, 63.64, 76.41),
        ('AL CB PM', 23.40, 11.70, 63.05, 75.71),
        ('SD PM', 13.87, 6.94, 62.46, 75.01),
        ('RECRUTA', 4.34, 2.17, 61.87, 74.31),
    ]
    
    for valor_data in valores_data:
        if not TabelaValores.query.filter_by(posto_grad=valor_data[0]).first():
            valor = TabelaValores(
                posto_grad=valor_data[0],
                he_diurna=valor_data[1],
                ad_he_noturna=valor_data[2],
                vd_diurno=valor_data[3],
                vd_noturno=valor_data[4]
            )
            db.session.add(valor)
    click.echo('  ✓ Tabela de valores created')


def seed_legendas():
    """Create escalas P2 legendas"""
    legendas_data = [
        ('C1', '7h-19h'),
        ('C2', '19h-7h'),
        ('F', 'Férias'),
        ('A1', '8h-12h + 14h-18h'),
        ('A2', '7h-13h'),
        ('B1', '13h-19h'),
    ]
    
    for leg_data in legendas_data:
        if not EscalaP2Legenda.query.filter_by(codigo=leg_data[0]).first():
            legenda = EscalaP2Legenda(codigo=leg_data[0], descricao=leg_data[1])
            db.session.add(legenda)
    click.echo('  ✓ Legendas created')


def seed_meta_p2():
    """Create escala P2 meta"""
    from datetime import date
    if not EscalaP2Meta.query.first():
        meta = EscalaP2Meta(
            id=1,
            mes=date.today().month,
            ano=date.today().year,
            local='IRECÊ',
            responsavel='CARLOS AUGUSTO FERREIRA DIAS - Ten Cel PM',
            cargo='CHEFE DO CPODE',
            emissao=date.today().isoformat(),
            nota='',
            titulo='ESCALA DE COORDENADOR REGIONAL DO CPR-CN'
        )
        db.session.add(meta)
    click.echo('  ✓ Escala P2 Meta created')


def seed_sample_efetivo():
    """Create sample efetivos for development"""
    efetivos_data = [
        ('30481332', 'FRANCISCO ROCHA JUNIOR', '03430', '2050510', 'ATIVO', 'SIM', 'MOTORISTA', 'CPR-CN', '(74) 99926-7070'),
        ('12345678', 'JOÃO SILVA SANTOS', '03340', '2050107', 'ATIVO', 'NAO', 'PATRULHEIRO', '7º BPM', '(74) 99999-1111'),
        ('87654321', 'MARIA OLIVEIRA COSTA', '03350', '2050404', 'ATIVO', 'SIM', 'CHEFE DE EQUIPE', '3ª CIPM', '(74) 98888-2222'),
        ('11223344', 'CARLOS EDUARDO LIMA', '03360', '2050428', 'ATIVO', 'NAO', 'OPERADOR DE RADIO', '10ª CIPM', '(74) 97777-3333'),
        ('55667788', 'ANA PAULA FERREIRA', '03370', '2050511', 'ATIVO', 'SIM', 'SUPERVISOR', 'CIPT-CN', '(74) 96666-4444'),
    ]
    
    for ef_data in efetivos_data:
        if not EfetivoPM.query.get(ef_data[0]):
            efetivo = EfetivoPM(
                matricula=ef_data[0],
                nome=ef_data[1],
                cargo=ef_data[2],
                opm_id=ef_data[3],
                sit=ef_data[4],
                f6=ef_data[5],
                funcao=ef_data[6],
                telefone=ef_data[8],
                lc_trab_desc=ef_data[6],
                cpf='',
                rg='',
                titulo='',
                cnh='',
                categoria='',
                tipo_sanguineo='',
                admissao='',
                data_nascimento='',
                local_trabalho='',
                comportamento='BOM'
            )
            db.session.add(efetivo)
    click.echo('  ✓ Sample efetivos created')


def seed_sample_eventos():
    """Create sample eventos for development"""
    eventos_data = [
        {
            'evento_desc': 'OPERAÇÃO COMANDO PRESENTE - JANEIRO',
            'evento_dta_inicio': '2024-01-15',
            'evento_dta_fim': '2024-01-16',
            'campo1': 'OPERAÇÃO DE PRESENÇA',
            'tipo_pagamento': 'HE'
        },
        {
            'evento_desc': 'FESTA DO PADROEIRO - IRECÊ',
            'evento_dta_inicio': '2024-02-10',
            'evento_dta_fim': '2024-02-12',
            'campo1': 'EVENTO RELIGIOSO',
            'tipo_pagamento': 'HE'
        },
        {
            'evento_desc': 'CARNAVAL 2024 - INTERIOR',
            'evento_dta_inicio': '2024-02-28',
            'evento_dta_fim': '2024-03-05',
            'campo1': 'CARNAVAL',
            'tipo_pagamento': 'VD'
        },
        {
            'evento_desc': 'OPERAÇÃO PÁSCOA',
            'evento_dta_inicio': '2024-03-28',
            'evento_dta_fim': '2024-03-31',
            'campo1': 'OPERAÇÃO ESPECIAL',
            'tipo_pagamento': 'HE'
        },
        {
            'evento_desc': 'OPERAÇÃO COMANDO PRESENTE - JULHO',
            'evento_dta_inicio': '2026-07-10',
            'evento_dta_fim': '2026-07-10',
            'campo1': 'XIQUE-XIQUE',
            'tipo_pagamento': 'HE'
        },
        {
            'evento_desc': 'OPERAÇÃO PAREDÃO - JULHO',
            'evento_dta_inicio': '2026-07-11',
            'evento_dta_fim': '2026-07-11',
            'campo1': 'Evento em VD',
            'tipo_pagamento': 'VD'
        },
        {
            'evento_desc': 'SÃO JOÃO DE IRECÊ 2026',
            'evento_dta_inicio': '2026-06-19',
            'evento_dta_fim': '2026-06-24',
            'campo1': 'SÃO JOÃO DO SÉCULO',
            'tipo_pagamento': 'HE'
        }
    ]
    
    for ev_data in eventos_data:
        if not Evento.query.filter_by(evento_desc=ev_data['evento_desc']).first():
            evento = Evento(**ev_data)
            db.session.add(evento)
            db.session.flush()
            
            # Add OPMs to event
            opms = OPM.query.limit(3).all()
            for opm in opms:
                opm_evento = OpmEvento(evento_id=evento.evento_id, opm_id=opm.opm_id)
                db.session.add(opm_evento)
    click.echo('  ✓ Sample eventos created')


def seed_all(full=False):
    """Run all seed functions"""
    click.echo("🌱 Starting database seeding...")
    
    seed_admin()
    seed_cargos()
    seed_opms()
    seed_tabela_valores()
    seed_legendas()
    seed_meta_p2()
    
    if full:
        seed_sample_efetivo()
        seed_sample_eventos()
    
    db.session.commit()
    click.echo("✅ Seeding completed!")


@click.command('seed')
@click.option('--full', is_flag=True, help='Include sample data for development')
@with_appcontext
def seed_command(full):
    """Seed database with initial data"""
    seed_all(full=full)


def init_app(app):
    app.cli.add_command(seed_command)