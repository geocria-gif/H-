"""Unit tests for models"""
import pytest
from datetime import date
from app.models import Usuario, Cargo, OPM, EfetivoPM, TabelaValores, EscalaP2Legenda, Evento, OpmEvento, Escala


class TestUsuarioModel:
    """Tests for Usuario model"""
    
    def test_create_user(self, app, db_session):
        user = Usuario(
            matricula='99999999',
            nome='TEST USER',
            tipo='OPERADOR'
        )
        user.set_senha('password123')
        db_session.add(user)
        db_session.commit()
        
        assert user.id is not None
        assert user.check_senha('password123')
        assert not user.check_senha('wrong')
    
    def test_user_roles(self, admin_user, operador_user):
        assert admin_user.is_admin
        assert admin_user.is_supervisor
        assert admin_user.is_operador
        
        assert not operador_user.is_admin
        assert not operador_user.is_supervisor
        assert operador_user.is_operador
    
    def test_user_to_dict(self, admin_user):
        data = admin_user.to_dict()
        assert data['matricula'] == '30481332'
        assert data['tipo'] == 'ADMIN'
        assert 'senha' not in data


class TestCargoModel:
    """Tests for Cargo model"""
    
    def test_create_cargo(self, app, db_session):
        cargo = Cargo(
            cargo_id='09999',
            posto_grad='TESTE',
            tipo_servidor='MILITAR',
            tipo_militar='PRACA'
        )
        db_session.add(cargo)
        db_session.commit()
        
        assert cargo.cargo_id == '09999'
        assert cargo.posto_grad == 'TESTE'
    
    def test_cargo_to_dict(self, sample_cargo):
        data = sample_cargo.to_dict()
        assert data['cargo_id'] == '03330'
        assert data['posto_grad'] == 'SD PM'


class TestOPMModel:
    """Tests for OPM model"""
    
    def test_create_opm(self, app, db_session):
        opm = OPM(
            opm_id='9999999',
            opm_desc='OPM TESTE',
            opm_sigla='TESTE',
            opm_ordem=99
        )
        db_session.add(opm)
        db_session.commit()
        
        assert opm.opm_id == '9999999'
    
    def test_opm_to_dict(self, sample_opm):
        data = sample_opm.to_dict()
        assert data['opm_id'] == '2050107'
        assert data['opm_sigla'] == '7º BPM'


class TestEfetivoPMModel:
    """Tests for EfetivoPM model"""
    
    def test_create_efetivo(self, app, db_session, sample_cargo, sample_opm):
        efetivo = EfetivoPM(
            matricula='88888888',
            nome='TESTE EFETIVO',
            cargo=sample_cargo.cargo_id,
            opm_id=sample_opm.opm_id,
            sit='ATIVO'
        )
        db_session.add(efetivo)
        db_session.commit()
        
        assert efetivo.matricula == '88888888'
    
    def test_efetivo_properties(self, sample_efetivo):
        assert sample_efetivo.posto_grad == 'SD PM'
        assert sample_efetivo.opm_sigla == '7º BPM'
    
    def test_efetivo_to_dict(self, sample_efetivo):
        data = sample_efetivo.to_dict()
        assert data['matricula'] == '12345678'
        assert data['posto_grad'] == 'SD PM'
        assert data['opm_sigla'] == '7º BPM'


class TestTabelaValoresModel:
    """Tests for TabelaValores model"""
    
    def test_create_valor(self, app, db_session, sample_cargo):
        valor = TabelaValores(
            posto_grad=sample_cargo.posto_grad,
            he_diurna=10.0,
            ad_he_noturna=5.0,
            vd_diurno=60.0,
            vd_noturno=70.0
        )
        db_session.add(valor)
        db_session.commit()
        
        assert valor.id is not None
    
    def test_valor_to_dict(self, sample_tabela_valor):
        data = sample_tabela_valor.to_dict()
        assert data['posto_grad'] == 'SD PM'
        assert data['he_diurna'] == 13.87


class TestEscalaP2LegendaModel:
    """Tests for EscalaP2Legenda model"""
    
    def test_create_legenda(self, app, db_session):
        legenda = EscalaP2Legenda(codigo='X1', descricao='Teste')
        db_session.add(legenda)
        db_session.commit()
        
        assert legenda.id is not None
    
    def test_legenda_to_dict(self, sample_legenda):
        data = sample_legenda.to_dict()
        assert data['codigo'] == 'C1'
        assert data['descricao'] == '7h-19h'


class TestEventoModel:
    """Tests for Evento model"""
    
    def test_create_evento(self, app, db_session):
        evento = Evento(
            evento_desc='EVENTO TESTE',
            evento_dta_inicio='2024-01-15',
            evento_dta_fim='2024-01-16',
            tipo_pagamento='HE'
        )
        db_session.add(evento)
        db_session.commit()
        
        assert evento.evento_id is not None
    
    def test_evento_data_properties(self, app, db_session):
        evento = Evento(
            evento_desc='TESTE DATA',
            evento_dta_inicio='2024-01-15',
            evento_dta_fim='2024-01-16'
        )
        db_session.add(evento)
        db_session.commit()
        
        assert evento.data_inicio == date(2024, 1, 15)
        assert evento.data_fim == date(2024, 1, 16)
    
    def test_evento_to_dict(self, app, db_session):
        evento = Evento(
            evento_desc='TESTE DICT',
            evento_dta_inicio='2024-01-15',
            evento_dta_fim='2024-01-16',
            tipo_pagamento='HE'
        )
        db_session.add(evento)
        db_session.commit()
        
        data = evento.to_dict()
        assert data['evento_desc'] == 'TESTE DICT'
        assert data['tipo_pagamento'] == 'HE'


class TestEscalaModel:
    """Tests for Escala model"""
    
    def test_create_escala(self, app, db_session, sample_efetivo):
        # Create evento and opm_evento first
        evento = Evento(
            evento_desc='TESTE ESCALA',
            evento_dta_inicio='2024-01-15',
            evento_dta_fim='2024-01-15',
            tipo_pagamento='HE'
        )
        db_session.add(evento)
        db_session.flush()
        
        opm = OPM.query.first()
        opm_evento = OpmEvento(evento_id=evento.evento_id, opm_id=opm.opm_id)
        db_session.add(opm_evento)
        db_session.flush()
        
        escala = Escala(
            opm_evento_id=opm_evento.opm_evento_id,
            matricula=sample_efetivo.matricula,
            escala_data='2024-01-15',
            escala_ch_diurna=8.0,
            escala_ch_noturna=0.0,
            hora_inicio='07:00',
            hora_fim='15:00',
            tipo_pagamento='HE'
        )
        db_session.add(escala)
        db_session.commit()
        
        assert escala.opm_evento_id == opm_evento.opm_evento_id
    
    def test_escala_ch_total(self, app, db_session, sample_efetivo):
        evento = Evento(evento_desc='TESTE CH', evento_dta_inicio='2024-01-15', evento_dta_fim='2024-01-15', tipo_pagamento='HE')
        db_session.add(evento)
        db_session.flush()
        
        opm = OPM.query.first()
        opm_evento = OpmEvento(evento_id=evento.evento_id, opm_id=opm.opm_id)
        db_session.add(opm_evento)
        db_session.flush()
        
        escala = Escala(
            opm_evento_id=opm_evento.opm_evento_id,
            matricula=sample_efetivo.matricula,
            escala_data='2024-01-15',
            escala_ch_diurna=8.0,
            escala_ch_noturna=4.0,
            tipo_pagamento='HE'
        )
        
        assert escala.ch_total == 12.0
    
    def test_escala_to_dict(self, app, db_session, sample_efetivo):
        evento = Evento(evento_desc='TESTE DICT', evento_dta_inicio='2024-01-15', evento_dta_fim='2024-01-15', tipo_pagamento='HE')
        db_session.add(evento)
        db_session.flush()
        
        opm = OPM.query.first()
        opm_evento = OpmEvento(evento_id=evento.evento_id, opm_id=opm.opm_id)
        db_session.add(opm_evento)
        db_session.flush()
        
        escala = Escala(
            opm_evento_id=opm_evento.opm_evento_id,
            matricula=sample_efetivo.matricula,
            escala_data='2024-01-15',
            escala_ch_diurna=8.0,
            escala_ch_noturna=0.0,
            tipo_pagamento='HE'
        )
        db_session.add(escala)
        db_session.commit()
        
        data = escala.to_dict()
        assert data['matricula'] == sample_efetivo.matricula
        assert data['ch_total'] == 8.0
        assert data['militar_nome'] == sample_efetivo.nome