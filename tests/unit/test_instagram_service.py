"""Unit tests for Instagram service"""
import os

import pytest


@pytest.fixture
def insta_app(app):
    app.config['INSTAGRAM_ACCESS_TOKEN'] = ''
    app.config['INSTAGRAM_IG_USER_ID'] = ''
    app.config['INSTAGRAM_API_VERSION'] = 'v21.0'
    app.config['INSTAGRAM_GRAPH_URL'] = 'https://graph.facebook.com'
    app.config['PUBLIC_BASE_URL'] = 'https://example.com'
    app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(__file__), '..', 'tmp_uploads')
    return app


class TestInstagramService:

    def test_is_configured_false(self, insta_app):
        from app.services.instagram_service import instagram_service
        with insta_app.app_context():
            assert instagram_service.is_configured() is False

    def test_is_configured_true(self, insta_app):
        from app.services.instagram_service import instagram_service
        insta_app.config['INSTAGRAM_ACCESS_TOKEN'] = 'token'
        insta_app.config['INSTAGRAM_IG_USER_ID'] = '123'
        with insta_app.app_context():
            assert insta_app.config['INSTAGRAM_ACCESS_TOKEN'] == 'token'
            assert instagram_service.is_configured() is True

    def test_get_status(self, insta_app):
        from app.services.instagram_service import instagram_service
        with insta_app.app_context():
            status = instagram_service.get_status()
            assert status['configured'] is False
            assert status['api_version'] == 'v21.0'

    def test_create_media_not_configured(self, insta_app):
        from app.services.instagram_service import (
            instagram_service, InstagramNotConfiguredError
        )
        with insta_app.app_context():
            with pytest.raises(InstagramNotConfiguredError):
                instagram_service.create_media_container('https://example.com/img.png')

    def test_publish_image_file_missing(self, insta_app):
        from app.services.instagram_service import (
            instagram_service, InstagramError
        )
        with insta_app.app_context():
            with pytest.raises(InstagramError):
                instagram_service.publish_image_file('/no/such/file.png')

    def test_publish_image_file_bad_ext(self, insta_app):
        from app.services.instagram_service import (
            instagram_service, InstagramError
        )
        with insta_app.app_context():
            path = os.path.join(insta_app.config['UPLOAD_FOLDER'], 'bad.txt')
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, 'w') as f:
                f.write('x')
            try:
                with pytest.raises(InstagramError):
                    instagram_service.publish_image_file(path)
            finally:
                os.remove(path)
