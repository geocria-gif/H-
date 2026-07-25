"""Integration tests for API endpoints"""
import pytest
from app import create_app, db
from app.models import Usuario, Cargo, OPM, EfetivoPM, Evento, OpmEvento, TabelaValores, Escala, EscalaP2Legenda, EscalaP2Meta
from werkzeug.security import generate_password_hash


@pytest.fixture
def client():
    app = create_app('testing')
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    
    with app.test_client() as client:
        with app.app_context():
            db.create_all()
            
            # Create test admin
            admin = Usuario(matricula='admin', nome='Admin', tipo='ADMIN')
            admin.set_senha('admin123')
            db.session.add(admin)
            
            # Create test cargo
            cargo = Cargo(cargo_id='09999', posto_grad='TESTE', tipo_servidor='MILITAR', tipo_militar='PRACA')
            db.session.add(cargo)
            
            # Create test OPM
            opm = OPM(opm_id='9999999', opm_desc='OPM TESTE', opm_sigla='TESTE', opm_ordem=99)
            db.session.add(opm)
            
            # Create tabela valor
            valor = TabelaValores(posto_grad='TESTE', he_diurna=10.0, ad_he_noturna=5.0, vd_diurno=60.0, vd_noturno=70.0)
            db.session.add(valor)
            
            db.session.commit()
        
        yield client
        
        with app.app_context():
            db.drop_all()


@pytest.fixture
def auth_headers(client):
    """Get auth headers for API requests"""
    response = client.post('/api/v1/auth/login', json={
        'matricula': 'admin',
        'senha': 'admin123'
    })
    assert response.status_code == 200
    token = response.get_json()['access_token']
    return {'Authorization': f'Bearer {token}'}


class TestAuthAPI:
    """Tests for authentication API"""
    
    def test_login_success(self, client):
        response = client.post('/api/v1/auth/login', json={
            'matricula': 'admin',
            'senha': 'admin123'
        })
        assert response.status_code == 200
        data = response.get_json()
        assert 'access_token' in data
        assert 'refresh_token' in data
        assert data['user']['matricula'] == 'admin'
    
    def test_login_invalid_credentials(self, client):
        response = client.post('/api/v1/auth/login', json={
            'matricula': 'admin',
            'senha': 'wrong'
        })
        assert response.status_code == 401
    
    def test_login_missing_fields(self, client):
        response = client.post('/api/v1/auth/login', json={
            'matricula': 'admin'
        })
        assert response.status_code == 400
    
    def test_refresh_token(self, client, auth_headers):
        response = client.post('/api/v1/auth/refresh', headers=auth_headers)
        assert response.status_code == 200
        data = response.get_json()
        assert 'access_token' in data
    
    def test_me_endpoint(self, client, auth_headers):
        response = client.get('/api/v1/auth/me', headers=auth_headers)
        assert response.status_code == 200
        data = response.get_json()
        assert data['matricula'] == 'admin'
        assert data['tipo'] == 'ADMIN'
    
    def test_change_password(self, client, auth_headers):
        response = client.post('/api/v1/auth/change-password', 
            headers=auth_headers,
            json={'senha_atual': 'admin123', 'nova_senha': 'newpassword123'}
        )
        assert response.status_code == 200
        
        # Verify new password works
        response = client.post('/api/v1/auth/login', json={
            'matricula': 'admin',
            'senha': 'newpassword123'
        })
        assert response.status_code == 200


class TestUsuariosAPI:
    """Tests for usuarios API"""
    
    def test_get_usuarios(self, client, auth_headers):
        response = client.get('/api/v1/usuarios', headers=auth_headers)
        assert response.status_code == 200
        data = response.get_json()
        assert 'items' in data
        assert 'pagination' in data
        assert len(data['items']) >= 1
    
    def test_get_usuario_by_id(self, client, auth_headers):
        response = client.get('/api/v1/usuarios/1', headers=auth_headers)
        assert response.status_code == 200
        data = response.get_json()
        assert data['matricula'] == 'admin'
    
    def test_create_usuario(self, client, auth_headers):
        response = client.post('/api/v1/usuarios', 
            headers=auth_headers,
            json={
                'matricula': 'newuser',
                'nome': 'New User',
                'tipo': 'OPERADOR',
                'senha': 'password123'
            }
        )
        assert response.status_code == 201
        data = response.get_json()
        assert data['matricula'] == 'newuser'
    
    def test_create_usuario_duplicate(self, client, auth_headers):
        response = client.post('/api/v1/usuarios',
            headers=auth_headers,
            json={
                'matricula': 'admin',
                'nome': 'Duplicate',
                'tipo': 'OPERADOR',
                'senha': 'password123'
            }
        )
        assert response.status_code == 409
    
    def test_update_usuario(self, client, auth_headers):
        response = client.put('/api/v1/usuarios/1',
            headers=auth_headers,
            json={'nome': 'Updated Name'}
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data['nome'] == 'Updated Name'
    
    def test_delete_usuario(self, client, auth_headers):
        # Create user to delete
        client.post('/api/v1/usuarios',
            headers=auth_headers,
            json={'matricula': 'todelete', 'nome': 'To Delete', 'tipo': 'OPERADOR', 'senha': 'password123'}
        )
        
        response = client.delete('/api/v1/usuarios/2', headers=auth_headers)
        assert response.status_code == 200
        
        # Verify deleted
        response = client.get('/api/v1/usuarios/2', headers=auth_headers)
        assert response.status_code == 404


class TestEfetivosAPI:
    """Tests for efetivos API"""
    
    def test_get_efetivos(self, client, auth_headers):
        response = client.get('/api/v1/efetivos', headers=auth_headers)
        assert response.status_code == 200
        data = response.get_json()
        assert 'items' in data
    
    def test_create_efetivo(self, client, auth_headers):
        response = client.post('/api/v1/efetivos',
            headers=auth_headers,
            json={
                'matricula': '99999999',
                'nome': 'TESTE EFETIVO',
                'cargo': '09999',
                'opm_id': '9999999',
                'sit': 'ATIVO',
                'funcao': 'TESTE'
            }
        )
        assert response.status_code == 201
        data = response.get_json()
        assert data['matricula'] == '99999999'
    
    def test_get_efetivo(self, client, auth_headers):
        # First create
        client.post('/api/v1/efetivos',
            headers=auth_headers,
            json={'matricula': '88888888', 'nome': 'GET TEST', 'cargo': '09999', 'opm_id': '9999999', 'sit': 'ATIVO'}
        )
        
        response = client.get('/api/v1/efetivos/88888888', headers=auth_headers)
        assert response.status_code == 200
        data = response.get_json()
        assert data['matricula'] == '88888888'
    
    def test_update_efetivo(self, client, auth_headers):
        client.post('/api/v1/efetivos',
            headers=auth_headers,
            json={'matricula': '77777777', 'nome': 'UPDATE TEST', 'cargo': '09999', 'opm_id': '9999999', 'sit': 'ATIVO'}
        )
        
        response = client.put('/api/v1/efetivos/77777777',
            headers=auth_headers,
            json={'nome': 'UPDATED NAME'}
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data['nome'] == 'UPDATED NAME'
    
    def test_search_efetivos(self, client, auth_headers):
        response = client.get('/api/v1/efetivos?search=TESTE', headers=auth_headers)
        assert response.status_code == 200
        data = response.get_json()
        assert 'items' in data


class TestEventosAPI:
    """Tests for eventos API"""
    
    def test_get_eventos(self, client, auth_headers):
        response = client.get('/api/v1/eventos', headers=auth_headers)
        assert response.status_code == 200
    
    def test_create_evento(self, client, auth_headers):
        response = client.post('/api/v1/eventos',
            headers=auth_headers,
            json={
                'evento_desc': 'TESTE EVENTO',
                'evento_dta_inicio': '2024-01-15',
                'evento_dta_fim': '2024-01-16',
                'tipo_pagamento': 'HE',
                'opm_ids': ['9999999']
            }
        )
        assert response.status_code == 201
        data = response.get_json()
        assert data['evento_desc'] == 'TESTE EVENTO'
    
    def test_add_remove_opm(self, client, auth_headers):
        # Create evento
        resp = client.post('/api/v1/eventos',
            headers=auth_headers,
            json={'evento_desc': 'TEST OPM', 'evento_dta_inicio': '2024-01-15', 'evento_dta_fim': '2024-01-15', 'tipo_pagamento': 'HE'}
        )
        evento_id = resp.get_json()['evento_id']
        
        # Add OPM
        response = client.post(f'/api/v1/eventos/{evento_id}/opms',
            headers=auth_headers,
            json={'opm_id': '9999999'}
        )
        assert response.status_code == 201
        
        # Remove OPM
        response = client.delete(f'/api/v1/eventos/{evento_id}/opms/9999999', headers=auth_headers)
        assert response.status_code == 200


class TestEscalasAPI:
    """Tests for escalas API"""
    
    def test_create_escala(self, client, auth_headers):
        # Create evento with OPM
        resp = client.post('/api/v1/eventos',
            headers=auth_headers,
            json={'evento_desc': 'ESCALA EVENTO', 'evento_dta_inicio': '2024-01-15', 'evento_dta_fim': '2024-01-15', 'tipo_pagamento': 'HE', 'opm_ids': ['9999999']}
        )
        evento_id = resp.get_json()['evento_id']
        
        # Get opm_evento_id
        opm_evento = OpmEvento.query.filter_by(evento_id=evento_id).first()
        
        response = client.post('/api/v1/escalas',
            headers=auth_headers,
            json={
                'opm_evento_id': opm_evento.opm_evento_id,
                'matricula': 'admin',
                'escala_data': '2024-01-15',
                'hora_inicio': '07:00',
                'hora_fim': '15:00',
                'tipo_pagamento': 'HE'
            }
        )
        assert response.status_code == 201
    
    def test_relatorio_horas(self, client, auth_headers):
        # Setup escala
        resp = client.post('/api/v1/eventos',
            headers=auth_headers,
            json={'evento_desc': 'RELATORIO EVENTO', 'evento_dta_inicio': '2024-01-15', 'evento_dta_fim': '2024-01-15', 'tipo_pagamento': 'HE', 'opm_ids': ['9999999']}
        )
        evento_id = resp.get_json()['evento_id']
        
        response = client.get(f'/api/v1/eventos/{evento_id}/relatorio-horas', headers=auth_headers)
        assert response.status_code == 200
        data = response.get_json()
        assert 'dados' in data
    
    def test_exportar_csv(self, client, auth_headers):
        resp = client.post('/api/v1/eventos',
            headers=auth_headers,
            json={'evento_desc': 'CSV EVENTO', 'evento_dta_inicio': '2024-01-15', 'evento_dta_fim': '2024-01-15', 'tipo_pagamento': 'HE', 'opm_ids': ['9999999']}
        )
        evento_id = resp.get_json()['evento_id']
        
        response = client.get(f'/api/v1/eventos/{evento_id}/exportar-csv', headers=auth_headers)
        assert response.status_code == 200
        data = response.get_json()
        assert 'csv' in data


class TestTabelaValoresAPI:
    """Tests for tabela valores API"""
    
    def test_get_tabela_valores(self, client, auth_headers):
        response = client.get('/api/v1/tabela-valores', headers=auth_headers)
        assert response.status_code == 200
        data = response.get_json()
        assert 'items' in data
    
    def test_create_tabela_valor(self, client, auth_headers):
        response = client.post('/api/v1/tabela-valores',
            headers=auth_headers,
            json={'posto_grad': 'NOVO POSTO', 'he_diurna': 20.0, 'ad_he_noturna': 10.0, 'vd_diurno': 65.0, 'vd_noturno': 75.0}
        )
        assert response.status_code == 201
        data = response.get_json()
        assert data['posto_grad'] == 'NOVO POSTO'
    
    def test_update_tabela_valor(self, client, auth_headers):
        # Get existing
        response = client.get('/api/v1/tabela-valores', headers=auth_headers)
        first_id = response.get_json()['items'][0]['id']
        
        response = client.put(f'/api/v1/tabela-valores/{first_id}',
            headers=auth_headers,
            json={'he_diurna': 99.99}
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data['he_diurna'] == 99.99


class TestOcorrenciasAPI:
    """Tests for ocorrencias API"""
    
    def test_create_ocorrencia(self, client, auth_headers):
        response = client.post('/api/v1/ocorrencias',
            headers=auth_headers,
            json={
                'tipo': 'ACIDENTE',
                'data_hora': '2024-01-15 10:00',
                'cidade': 'IRECÊ',
                'latitude': -11.3,
                'longitude': -41.8,
                'descricao': 'Teste ocorrência'
            }
        )
        assert response.status_code == 201
    
    def test_estatisticas_ocorrencias(self, client, auth_headers):
        response = client.get('/api/v1/ocorrencias/estatisticas', headers=auth_headers)
        assert response.status_code == 200
        data = response.get_json()
        assert 'total' in data
        assert 'por_tipo' in data


class TestEscalasP2API:
    """Tests for escalas P2 API"""
    
    def test_get_escalas_p2(self, client, auth_headers):
        response = client.get('/api/v1/escalas-p2', headers=auth_headers)
        assert response.status_code == 200
    
    def test_create_escala_p2(self, client, auth_headers):
        response = client.post('/api/v1/escalas-p2',
            headers=auth_headers,
            json={
                'mes': 1,
                'ano': 2024,
                'funcao': 'MOTORISTA',
                'opm': 'CPR-CN',
                'gh': 'CB PM',
                'nome': 'TESTE P2',
                'matricula': 'admin',
                'tipo_pagamento': 'HE'
            }
        )
        assert response.status_code == 201


class TestEscalasSalvasAPI:
    """Tests for escalas salvas API"""
    
    def test_create_escala_salva(self, client, auth_headers):
        response = client.post('/api/v1/escalas-salvas',
            headers=auth_headers,
            json={
                'nome': 'ESCALA TESTE',
                'mes': 1,
                'ano': 2024,
                'itens': [],
                'meta': {}
            }
        )
        assert response.status_code == 201
    
    def test_ativar_escala_salva(self, client, auth_headers):
        # Create
        resp = client.post('/api/v1/escalas-salvas',
            headers=auth_headers,
            json={'nome': 'ATIVAR TESTE', 'mes': 1, 'ano': 2024, 'itens': [], 'meta': {}}
        )
        escala_id = resp.get_json()['id']
        
        # Activate
        response = client.post(f'/api/v1/escalas-salvas/{escala_id}/ativar', headers=auth_headers)
        assert response.status_code == 200


class TestHealthCheck:
    """Tests for health check"""
    
    def test_health_check(self, client):
        response = client.get('/api/v1/health')
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'healthy'
        assert data['service'] == 'SISPM API'


class TestCargosOpmAPI:
    """Tests for cargos and OPMs list endpoints"""
    
    def test_get_cargos(self, client, auth_headers):
        response = client.get('/api/v1/cargos', headers=auth_headers)
        assert response.status_code == 200
        data = response.get_json()
        assert isinstance(data, list)
        assert len(data) > 0
    
    def test_get_opms(self, client, auth_headers):
        response = client.get('/api/v1/opms', headers=auth_headers)
        assert response.status_code == 200
        data = response.get_json()
        assert isinstance(data, list)
        assert len(data) > 0


class TestUnauthorizedAccess:
    """Tests for unauthorized access"""
    
    def test_unauthorized(self, client):
        response = client.get('/api/v1/usuarios')
        assert response.status_code == 401
    
    def test_invalid_token(self, client):
        response = client.get('/api/v1/usuarios', headers={'Authorization': 'Bearer invalid'})
        assert response.status_code == 401


class TestPagination:
    """Tests for pagination"""
    
    def test_pagination_params(self, client, auth_headers):
        response = client.get('/api/v1/usuarios?page=1&per_page=5', headers=auth_headers)
        assert response.status_code == 200
        data = response.get_json()
        assert data['pagination']['page'] == 1
        assert data['pagination']['per_page'] == 5