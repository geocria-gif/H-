"""Test configuration and fixtures"""
import pytest
import os
import sys
from datetime import date

# Add app to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app import create_app, db
from app.models import Usuario, Cargo, OPM, EfetivoPM, TabelaValores, EscalaP2Legenda


@pytest.fixture(scope='session')
def app():
    """Create test app"""
    os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
    os.environ['SECRET_KEY'] = 'test-secret-key'
    os.environ['JWT_SECRET_KEY'] = 'test-jwt-secret-key'
    os.environ['FLASK_CONFIG'] = 'testing'
    
    app = create_app('testing')
    
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


@pytest.fixture(scope='function')
def client(app):
    """Test client"""
    return app.test_client()


@pytest.fixture(scope='function')
def db_session(app):
    """Database session for tests"""
    with app.app_context():
        yield db.session
        db.session.rollback()


@pytest.fixture
def admin_user(app, db_session):
    """Create admin user"""
    user = Usuario(
        matricula='30481332',
        nome='ADMIN TEST',
        tipo='ADMIN'
    )
    user.set_senha('30481332')
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def operador_user(app, db_session):
    """Create operador user"""
    user = Usuario(
        matricula='12345678',
        nome='OPERADOR TEST',
        tipo='OPERADOR'
    )
    user.set_senha('123456')
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def sample_cargo(app, db_session):
    """Create sample cargo"""
    cargo = Cargo(
        cargo_id='03330',
        posto_grad='SD PM',
        tipo_servidor='MILITAR',
        tipo_militar='PRACA'
    )
    db_session.add(cargo)
    db_session.commit()
    return cargo


@pytest.fixture
def sample_opm(app, db_session):
    """Create sample OPM"""
    opm = OPM(
        opm_id='2050107',
        opm_desc='7º BATALHÃO DE POLÍCIA MILITAR',
        opm_sigla='7º BPM',
        opm_ordem=23,
        opm_atv='FIM',
        opm_regiao='INTERIOR',
        opm_municipio='IRECE'
    )
    db_session.add(opm)
    db_session.commit()
    return opm


@pytest.fixture
def sample_efetivo(app, db_session, sample_cargo, sample_opm):
    """Create sample efetivo"""
    efetivo = EfetivoPM(
        matricula='12345678',
        nome='JOÃO SILVA TESTE',
        cargo=sample_cargo.cargo_id,
        opm_id=sample_opm.opm_id,
        sit='ATIVO',
        f6='NAO',
        funcao='PATRULHEIRO',
        telefone='(74) 99999-9999'
    )
    db_session.add(efetivo)
    db_session.commit()
    return efetivo


@pytest.fixture
def sample_tabela_valor(app, db_session, sample_cargo):
    """Create sample tabela valor"""
    valor = TabelaValores(
        posto_grad=sample_cargo.posto_grad,
        he_diurna=13.87,
        ad_he_noturna=6.93,
        vd_diurno=62.46,
        vd_noturno=75.01
    )
    db_session.add(valor)
    db_session.commit()
    return valor


@pytest.fixture
def sample_legenda(app, db_session):
    """Create sample legenda"""
    legenda = EscalaP2Legenda(codigo='C1', descricao='7h-19h')
    db_session.add(legenda)
    db_session.commit()
    return legenda


# Pytest configuration
def pytest_configure(config):
    config.addinivalue_line('markers', 'unit: Unit tests')
    config.addinivalue_line('markers', 'integration: Integration tests')
    config.addinivalue_line('markers', 'slow: Slow tests')