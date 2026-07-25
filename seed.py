#!/usr/bin/env python3
"""
Seed script for SISPM - Creates initial data for development/production
"""
import os
import sys
from datetime import date, datetime

# Add app to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models import (
    Usuario, Cargo, OPM, EfetivoPM, Evento, OpmEvento,
    TabelaValores, EscalaP2Legenda, EscalaP2Meta
)
from werkzeug.security import generate_password_hash


def seed_basic():
    """Seed basic required data"""
    app = create_app('development')
    
    with app.app_context():
        print("Seeding basic data...")
        
        # Create admin user
        if not Usuario.query.filter_by(matricula='30481332').first():
            admin = Usuario(
                matricula='30481332',
                nome='FRANCISCO ROCHA JUNIOR',
                tipo='ADMIN'
            )
            admin.set_senha('30481332')
            db.session.add(admin)
            print("  ✓ Admin user created")
        
        # Create basic cargos
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
        print("  ✓ Cargos created")
        
        # Create basic OPMs
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
        print("  ✓ OPMs created")
        
        # Create tabela de valores
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
        print("  ✓ Tabela de valores created")
        
        # Create escalas P2 legendas
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
        print("  ✓ Legendas created")
        
        # Create escala P2 meta
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
        print("  ✓ Escala P2 Meta created")
        
        db.session.commit()
        print("✅ Basic seed completed!")


def seed_full():
    """Seed with sample data for development"""
    seed_basic()
    
    app = create_app('development')
    
    with app.app_context():
        print("Seeding sample data...")
        
        # Create sample efetivos
        efetivos_data = [
            ('30481332', 'FRANCISCO ROCHA JUNIOR', '03430', '2050510', 'ATIVO', 'SIM', 'CB PM', 'CPR-CN', '(74) 99926-7070', 'MOTORISTA'),
            ('12345678', 'JOÃO SILVA SANTOS', '03340', '2050107', 'ATIVO', 'NAO', 'SD PM', '7º BPM', '(74) 99999-1111', 'PATRULHEIRO'),
            ('87654321', 'MARIA OLIVEIRA COSTA', '03350', '2050404', 'ATIVO', 'SIM', '3º SGT PM', '3ª CIPM', '(74) 98888-2222', 'CHEFE DE EQUIPE'),
            ('11223344', 'CARLOS EDUARDO LIMA', '03360', '2050428', 'ATIVO', 'NAO', '2º SGT PM', '10ª CIPM', '(74) 97777-3333', 'OPERADOR DE RADIO'),
            ('55667788', 'ANA PAULA FERREIRA', '03370', '2050511', 'ATIVO', 'SIM', '1º SGT PM', 'CIPT-CN', '(74) 96666-4444', 'SUPERVISOR'),
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
                    funcao=ef_data[8],
                    telefone=ef_data[7],
                    lc_trab_desc=ef_data[8],
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
        print("  ✓ Sample efetivos created")
        
        # Create sample events
        eventos_data = [
            ('OPERAÇÃO COMANDO PRESENTE - JANEIRO', '2024-01-15', '2024-01-16', 'OPERAÇÃO DE PRESENÇA', 'HE'),
            ('FESTA DO PADROEIRO - IRECÊ', '2024-02-10', '2024-02-12', 'EVENTO RELIGIOSO', 'HE'),
            ('CARNAVAL 2024 - INTERIOR', '2024-02-28', '2024-03-05', 'CARNAVAL', 'VD'),
            ('OPERAÇÃO PÁSCOA', '2024-03-28', '2024-03-31', 'OPERAÇÃO ESPECIAL', 'HE'),
        ]
        
        for ev_data in eventos_data:
            if not Evento.query.filter_by(evento_desc=ev_data[0]).first():
                evento = Evento(
                    evento_desc=ev_data[0],
                    evento_dta_inicio=ev_data[1],
                    evento_dta_fim=ev_data[2],
                    campo1=ev_data[3],
                    tipo_pagamento=ev_data[4]
                )
                db.session.add(evento)
                db.session.flush()
                
                # Add OPMs to event
                opms = OPM.query.limit(3).all()
                for opm in opms:
                    oe = OpmEvento(evento_id=evento.evento_id, opm_id=opm.opm_id)
                    db.session.add(oe)
        print("  ✓ Sample events created")
        
        db.session.commit()
        print("✅ Full seed completed!")


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Seed SISPM database')
    parser.add_argument('--full', action='store_true', help='Seed with sample data')
    args = parser.parse_args()
    
    if args.full:
        seed_full()
    else:
        seed_basic()