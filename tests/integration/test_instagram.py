"""Integration tests for Instagram API endpoints"""
import io
import os

import pytest


@pytest.fixture
def insta_client():
    from app import create_app, db
    from app.models import Usuario

    app = create_app('testing')
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    app.config['INSTAGRAM_ACCESS_TOKEN'] = ''
    app.config['INSTAGRAM_IG_USER_ID'] = ''

    with app.test_client() as client:
        with app.app_context():
            db.create_all()
            admin = Usuario(matricula='admin', nome='Admin', tipo='ADMIN')
            admin.set_senha('admin123')
            db.session.add(admin)
            db.session.commit()
        yield client
        with app.app_context():
            db.drop_all()


@pytest.fixture
def insta_auth_headers(insta_client):
    response = insta_client.post('/auth/api/login', json={
        'matricula': 'admin',
        'senha': 'admin123'
    })
    assert response.status_code == 200
    token = response.get_json()['access_token']
    return {'Authorization': f'Bearer {token}'}


class TestInstagramAPI:

    def test_status_not_configured(self, insta_client, insta_auth_headers):
        response = insta_client.get('/api/v1/instagram/status', headers=insta_auth_headers)
        assert response.status_code == 200
        data = response.get_json()
        assert data['configured'] is False
        assert data['access_token'] is False
        assert data['ig_user_id'] is False

    def test_status_requires_auth(self, insta_client):
        response = insta_client.get('/api/v1/instagram/status')
        assert response.status_code in (401, 422)

    def test_publish_without_file(self, insta_client, insta_auth_headers):
        response = insta_client.post('/api/v1/instagram/publish', headers=insta_auth_headers)
        assert response.status_code == 400

    def test_publish_invalid_type(self, insta_client, insta_auth_headers):
        response = insta_client.post(
            '/api/v1/instagram/publish',
            headers=insta_auth_headers,
            data={'image': (io.BytesIO(b'hello'), 'card.txt'), 'caption': 'teste'},
            content_type='multipart/form-data',
        )
        assert response.status_code == 400

    def test_publish_not_configured(self, insta_client, insta_auth_headers):
        png = b'\x89PNG\r\n\x1a\n' + b'0' * 100
        response = insta_client.post(
            '/api/v1/instagram/publish',
            headers=insta_auth_headers,
            data={'image': (io.BytesIO(png), 'card.png'), 'caption': 'teste'},
            content_type='multipart/form-data',
        )
        assert response.status_code == 502
        assert 'não configurado' in response.get_json()['message']

    def test_deny_operador(self):
        from app import create_app, db
        from app.models import Usuario

        app = create_app('testing')
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False

        with app.test_client() as client:
            with app.app_context():
                db.create_all()
                op = Usuario(matricula='operador', nome='Operador', tipo='OPERADOR')
                op.set_senha('operador123')
                db.session.add(op)
                db.session.commit()

            login = client.post('/auth/api/login', json={
                'matricula': 'operador', 'senha': 'operador123'
            })
            token = login.get_json()['access_token']
            headers = {'Authorization': f'Bearer {token}'}

            png = b'\x89PNG\r\n\x1a\n' + b'0' * 100
            response = client.post(
                '/api/v1/instagram/publish',
                headers=headers,
                data={'image': (io.BytesIO(png), 'card.png'), 'caption': 'teste'},
                content_type='multipart/form-data',
            )
            assert response.status_code == 403

            with app.app_context():
                db.drop_all()
