"""
Seed script for SISPM - Creates initial data for development/production
"""
import click
from flask.cli import with_appcontext
from app import db
from app.models import (
    Usuario, Cargo, OPM, EfetivoPM, Evento, OpmEvento,
    TabelaValores, EscalaP2Legenda, EscalaP2Meta, Municipio
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


def seed_municipios():
    """Seed the 22 municipalities of CPR-CN with IBGE codes and coordinates"""
    municipios = [
        (1,'America Dourada','BA','Centro-Norte',-11.455,-41.436,'290115',841.62,'44910-000',15170,35,'Joelson','PSD'),
        (2,'Barra do Mendes','BA','Centro-Norte',-11.81,-42.06,'290300',1582.16,'44990-000',12620,70,'Dr. Neu','PP'),
        (3,'Barro Alto','BA','Centro-Norte',-11.76,-41.91,'290323',416.88,'44895-000',13430,55,'Orlando Amorim','PSD'),
        (4,'Bonito','BA','Centro-Norte',-11.967,-41.268,'2904050',791.3,'46820-000',18812,61,'Reinan Cedro de Oliveira','PSD'),
        (5,'Cafarnaum','BA','Centro-Norte',-11.693,-41.469,'290530',684.63,'44880-000',18770,45,'Sueli Fernandes','PSD'),
        (6,'Canarana','BA','Centro-Norte',-11.686,-41.767,'290682',605.3,'44890-000',25180,25,'Ezenivaldo Alves Dourado (Zeni)','PSD'),
        (7,'Central','BA','Centro-Norte',-11.139,-42.111,'290760',566.1,'44940-000',16050,40,'Renatinho','AVANTE'),
        (8,'Gentio do Ouro','BA','Centro-Norte',-11.434,-42.507,'291130',3674.22,'47450-000',10990,90,'Murilo Franca','PSD'),
        (9,'Ibipeba','BA','Centro-Norte',-11.641,-42.011,'291240',1383.68,'44970-000',16650,45,'Demostenes Sousa Barreto Filho (Deme)','PSD'),
        (10,'Ibitita','BA','Centro-Norte',-11.546,-41.974,'291300',623.08,'44960-000',17100,30,'Dr. Afonso','PSD'),
        (11,'Ipupiara','BA','Centro-Norte',-11.823,-42.617,'291410',1055.8,'47590-000',8950,105,'Ascir Leite','PSD'),
        (12,'Irece','BA','Centro-Norte',-11.304,-41.857,'291460',319.03,'44900-000',74507,0,'Murilo Franca','PSB'),
        (13,'Itaguacu da Bahia','BA','Centro-Norte',-11.013,-42.399,'291535',4451.27,'47440-000',14240,80,'Adozinho','PSD'),
        (14,'Joao Dourado','BA','Centro-Norte',-11.35,-41.654,'291835',913.55,'44920-000',22420,22,'Di Cardoso','PCdoB'),
        (15,'Jussara','BA','Centro-Norte',-11.045,-41.971,'291850',876.68,'44925-000',14620,38,'Tacinho Mendes','PSD'),
        (16,'Lapao','BA','Centro-Norte',-11.385,-41.828,'291915',627.68,'44905-000',30620,10,'Marcio Messias','PDT'),
        (17,'Morro do Chapueu','BA','Centro-Norte',-11.549,-41.156,'2921708',5744.97,'44850-000',33594,98,'Juliana Pereira Araujo Leal','PDT'),
        (18,'Mulungu do Morro','BA','Centro-Norte',-11.965,-41.639,'292205',567.17,'44885-000',12340,60,'Acio Teles','MDB'),
        (19,'Presidente Dutra','BA','Centro-Norte',-11.296,-41.987,'292340',244.76,'44930-000',14690,15,'Roberto','MDB'),
        (20,'Sao Gabriel','BA','Centro-Norte',-11.229,-41.911,'292925',1145.56,'44915-000',19660,12,'Mateus Machado','PSD'),
        (21,'Uibai','BA','Centro-Norte',-11.339,-42.136,'293240',504.2,'44950-000',13840,30,'Dr. Jarbas','PSD'),
        (22,'Xique-Xique','BA','Centro-Norte',-10.823,-42.73,'293360',5052.81,'47400-000',46997,98,'Reinaldinho Braga','MDB'),
    ]
    for m in municipios:
        if not db.session.get(Municipio, m[0]):
            db.session.add(Municipio(
                id=m[0], nome=m[1], uf=m[2], regiao=m[3],
                latitude=m[4], longitude=m[5], codigo_ibge=m[6],
                area=m[7], cep=m[8], populacao=m[9],
                dist_irece=m[10], prefeito=m[11], partido=m[12]
            ))
    click.echo('  ✓ 22 municípios CPR-CN created')


def seed_all(full=False):
    """Run all seed functions"""
    click.echo("🌱 Starting database seeding...")
    
    db.create_all()
    
    seed_admin()
    seed_cargos()
    seed_opms()
    seed_tabela_valores()
    seed_legendas()
    seed_meta_p2()
    seed_municipios()
    
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