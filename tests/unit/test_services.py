"""Unit tests for SISPM services and utilities"""
import pytest
from datetime import time
from app.services import EscalaService, TabelaValoresService
from app.models import EfetivoPM, Cargo, OPM


class TestEscalaService:
    """Tests for EscalaService"""
    
    def test_calcular_ch_diurna(self, app):
        """Test calculating diurnal hours"""
        with app.app_context():
            service = EscalaService()
            ch_d, ch_n = service.calcular_ch('07:00', '15:00')
            # 8 hours diurnal (07:00-15:00, all in 05:00-22:00)
            assert ch_d == 8.0
            assert ch_n == 0.0
    
    def test_calcular_ch_noturna(self, app):
        """Test calculating nocturnal hours"""
        with app.app_context():
            service = EscalaService()
            ch_d, ch_n = service.calcular_ch('22:00', '06:00')
            # 8 hours nocturnal (22:00-06:00, all in 22:00-05:00)
            assert ch_d == 0.0
            assert ch_n == 8.0
    
    def test_calcular_ch_mista(self, app):
        """Test mixed diurnal/nocturnal"""
        with app.app_context():
            service = EscalaService()
            ch_d, ch_n = service.calcular_ch('20:00', '04:00')
            # 2h diurnal (20:00-22:00) + 6h nocturnal (22:00-04:00)
            assert ch_d == 2.0
            assert ch_n == 6.0
    
    def test_calcular_ch_midnight_cross(self, app):
        """Test crossing midnight"""
        with app.app_context():
            service = EscalaService()
            ch_d, ch_n = service.calcular_ch('23:00', '07:00')
            # 0h diurnal + 8h nocturnal
            assert ch_d == 0.0
            assert ch_n == 8.0
    
    def test_calcular_ch_full_day(self, app):
        """Test 24h shift"""
        with app.app_context():
            service = EscalaService()
            ch_d, ch_n = service.calcular_ch('07:00', '07:00')
            # 17h diurnal (07:00-22:00) + 7h nocturnal (22:00-05:00)
            assert ch_d == 17.0
            assert ch_n == 7.0


class TestTabelaValoresService:
    """Tests for TabelaValoresService"""
    
    def test_get_valor_he_diurna(self, app, db_session):
        with app.app_context():
            # Create cargo and valor
            cargo = Cargo(cargo_id='99999', posto_grad='TESTE POSTO', tipo_servidor='MILITAR', tipo_militar='PRACA')
            db_session.add(cargo)
            
            valor = TabelaValores(
                posto_grad='TESTE POSTO',
                he_diurna=50.0,
                ad_he_noturna=25.0,
                vd_diurno=60.0,
                vd_noturno=70.0
            )
            db_session.add(valor)
            db_session.commit()
            
            service = TabelaValoresService()
            result = service.get_valor('TESTE POSTO', 'HE', False)
            assert result == 50.0
    
    def test_get_valor_he_noturna(self, app, db_session):
        with app.app_context():
            cargo = Cargo(cargo_id='99998', posto_grad='TESTE POSTO 2', tipo_servidor='MILITAR', tipo_militar='PRACA')
            db_session.add(cargo)
            
            valor = TabelaValores(
                posto_grad='TESTE POSTO 2',
                he_diurna=50.0,
                ad_he_noturna=25.0,
                vd_diurno=60.0,
                vd_noturno=70.0
            )
            db_session.add(valor)
            db_session.commit()
            
            service = TabelaValoresService()
            result = service.get_valor('TESTE POSTO 2', 'HE', True)
            assert result == 25.0
    
    def test_get_valor_vd_diurno(self, app, db_session):
        with app.app_context():
            cargo = Cargo(cargo_id='99997', posto_grad='TESTE POSTO 3', tipo_servidor='MILITAR', tipo_militar='PRACA')
            db_session.add(cargo)
            
            valor = TabelaValores(
                posto_grad='TESTE POSTO 3',
                he_diurna=50.0,
                ad_he_noturna=25.0,
                vd_diurno=60.0,
                vd_noturno=70.0
            )
            db_session.add(valor)
            db_session.commit()
            
            service = TabelaValoresService()
            result = service.get_valor('TESTE POSTO 3', 'VD', False)
            assert result == 60.0
    
    def test_get_valor_not_found(self, app):
        with app.app_context():
            service = TabelaValoresService()
            result = service.get_valor('POSTO INEXISTENTE', 'HE', False)
            assert result == 0.0
    
    def test_calcular_valor_militar(self, app, db_session):
        with app.app_context():
            # Setup
            cargo = Cargo(cargo_id='TEST01', posto_grad='CB PM', tipo_servidor='MILITAR', tipo_militar='PRACA')
            db_session.add(cargo)
            
            opm = OPM(opm_id='TESTOPM', opm_sigla='TESTE', opm_desc='OPM TESTE')
            db_session.add(opm)
            
            valor = TabelaValores(
                posto_grad='CB PM',
                he_diurna=32.93,
                ad_he_noturna=16.47,
                vd_diurno=62.46,
                vd_noturno=75.01
            )
            db_session.add(valor)
            
            militar = EfetivoPM(
                matricula='99999999',
                nome='MILITAR TESTE',
                cargo='TEST01',
                opm_id='TESTOPM',
                sit='ATIVO'
            )
            db_session.add(militar)
            db_session.commit()
            
            service = TabelaValoresService()
            # 4h diurna + 2h noturna HE
            valor_total = service.calcular_valor_militar(militar, 4.0, 2.0, 'HE')
            # 4 * 32.93 + 2 * 16.47 = 131.72 + 32.94 = 164.66
            assert valor_total == 164.66


class TestModelProperties:
    """Tests for model properties"""
    
    def test_efetivo_posto_grad(self, app, db_session):
        with app.app_context():
            cargo = Cargo(cargo_id='TEST02', posto_grad='SGT PM', tipo_servidor='MILITAR', tipo_militar='PRACA')
            db_session.add(cargo)
            
            efetivo = EfetivoPM(matricula='88888888', nome='TESTE', cargo='TEST02', opm_id='TESTOPM')
            db_session.add(efetivo)
            db_session.commit()
            
            assert efetivo.posto_grad == 'SGT PM'
    
    def test_efetivo_opm_sigla(self, app, db_session):
        with app.app_context():
            opm = OPM(opm_id='TESTOPM2', opm_sigla='TST', opm_desc='OPM TESTE 2')
            db_session.add(opm)
            
            efetivo = EfetivoPM(matricula='77777777', nome='TESTE 2', cargo='03330', opm_id='TESTOPM2')
            db_session.add(efetivo)
            db_session.commit()
            
            assert efetivo.opm_sigla == 'TST'
    
    def test_escala_ch_total(self, app, db_session):
        with app.app_context():
            from app.models import Escala, Evento, OpmEvento
            
            opm = OPM(opm_id='TESTOPM3', opm_sigla='TST3', opm_desc='OPM TESTE 3')
            db_session.add(opm)
            
            evento = Evento(evento_desc='TESTE EVENTO', evento_dta_inicio='2024-01-15', evento_dta_fim='2024-01-15', tipo_pagamento='HE')
            db_session.add(evento)
            db_session.flush()
            
            opm_evento = OpmEvento(evento_id=evento.evento_id, opm_id='TESTOPM3')
            db_session.add(opm_evento)
            db_session.flush()
            
            escala = Escala(
                opm_evento_id=opm_evento.opm_evento_id,
                matricula='99999999',
                escala_data='2024-01-15',
                escala_ch_diurna=4.0,
                escala_ch_noturna=2.0
            )
            db_session.add(escala)
            db_session.commit()
            
            assert escala.ch_total == 6.0


class TestEscalaP2DiasDict:
    """Tests for EscalaP2 dias_dict property"""
    
    def test_dias_dict_getter_setter(self, app):
        with app.app_context():
            from app.models import EscalaP2
            
            escala = EscalaP2(
                mes=1, ano=2024, funcao='TESTE', opm='TESTE', gh='TESTE',
                nome='TESTE', matricula='99999999', dias='{"1": "C1", "2": "C2"}'
            )
            
            # Test getter
            assert escala.dias_dict == {"1": "C1", "2": "C2"}
            
            # Test setter
            escala.dias_dict = {"3": "F", "4": "A1"}
            assert escala.dias == '{"3": "F", "4": "A1"}'


class TestEscalaSalvaItemDiasDict:
    """Tests for EscalaSalvaItem dias_dict property"""
    
    def test_dias_dict_getter_setter(self, app):
        with app.app_context():
            from app.models import EscalaSalva, EscalaSalvaItem
            
            escala_salva = EscalaSalva(nome='TESTE', mes=1, ano=2024)
            db.session.add(escala_salva)
            db.session.flush()
            
            item = EscalaSalvaItem(
                escala_salva_id=escala_salva.id,
                funcao='TESTE', opm='TESTE', gh='TESTE',
                nome='TESTE', matricula='99999999',
                dias='{"5": "C1", "6": "C2"}'
            )
            
            assert item.dias_dict == {"5": "C1", "6": "C2"}
            
            item.dias_dict = {"7": "F"}
            assert item.dias == '{"7": "F"}'


class TestUserAuthentication:
    """Tests for user authentication methods"""
    
    def test_set_check_senha(self, app):
        with app.app_context():
            from app.models import Usuario
            
            user = Usuario(matricula='TESTUSER', nome='Test User', tipo='OPERADOR')
            user.set_senha('minhasenha123')
            
            assert user.check_senha('minhasenha123') is True
            assert user.check_senha('senhaerrada') is False
    
    def test_user_roles(self, app):
        with app.app_context():
            from app.models import Usuario
            
            admin = Usuario(matricula='ADM001', nome='Admin', tipo='ADMIN')
            supervisor = Usuario(matricula='SUP001', nome='Supervisor', tipo='SUPERVISOR')
            operador = Usuario(matricula='OPE001', nome='Operador', tipo='OPERADOR')
            visitante = Usuario(matricula='VIS001', nome='Visitante', tipo='VISITANTE')
            
            assert admin.is_admin is True
            assert admin.is_supervisor is True
            assert admin.is_operador is True
            
            assert supervisor.is_admin is False
            assert supervisor.is_supervisor is True
            assert supervisor.is_operador is True
            
            assert operador.is_admin is False
            assert operador.is_supervisor is False
            assert operador.is_operador is True
            
            assert visitante.is_admin is False
            assert visitante.is_supervisor is False
            assert visitante.is_operador is False