"""Serviço de integração com a API do Instagram (Meta Graph API).

Publica imagens (cards institucionais) no Instagram Business/Creator da SEGMAF.

Fluxo da API:
1. POST /{ig-user-id}/media          -> cria container de mídia (image_url)
2. POST /{ig-user-id}/media_publish  -> publica o container criado
"""
import logging
import os
import time
from typing import Dict, Optional, Tuple

import requests

from flask import current_app

logger = logging.getLogger(__name__)


class InstagramError(Exception):
    """Erro retornado pela Meta Graph API."""


class InstagramNotConfiguredError(InstagramError):
    """Credenciais do Instagram não configuradas."""


class InstagramService:
    GRAPH_URL = 'https://graph.facebook.com'
    DEFAULT_API_VERSION = 'v21.0'
    IMAGE_TYPES = {'png', 'jpg', 'jpeg'}

    def is_configured(self) -> bool:
        cfg = self._config()
        return bool(cfg.get('access_token') and cfg.get('ig_user_id'))

    def get_status(self) -> Dict:
        cfg = self._config()
        return {
            'configured': self.is_configured(),
            'access_token': bool(cfg.get('access_token')),
            'ig_user_id': bool(cfg.get('ig_user_id')),
            'api_version': cfg.get('api_version'),
            'ig_user_id_value': cfg.get('ig_user_id'),
        }

    def _config(self) -> Dict:
        return {
            'access_token': current_app.config.get('INSTAGRAM_ACCESS_TOKEN', ''),
            'ig_user_id': current_app.config.get('INSTAGRAM_IG_USER_ID', ''),
            'api_version': current_app.config.get('INSTAGRAM_API_VERSION') or self.DEFAULT_API_VERSION,
            'graph_url': current_app.config.get('INSTAGRAM_GRAPH_URL') or self.GRAPH_URL,
        }

    def _api_url(self, endpoint: str) -> str:
        cfg = self._config()
        return f"{cfg['graph_url']}/{cfg['api_version']}/{endpoint}"

    def _request(self, method: str, url: str, **kwargs) -> Dict:
        try:
            response = requests.request(method, url, timeout=60, **kwargs)
        except requests.RequestException as e:
            logger.exception('Instagram request failed')
            raise InstagramError(f'Falha de conexão com a Meta API: {e}') from e

        try:
            data = response.json()
        except ValueError:
            raise InstagramError(f'Resposta inválida da Meta API (HTTP {response.status_code})')

        if response.status_code >= 400 or data.get('error'):
            error = data.get('error', {})
            code = error.get('code', response.status_code)
            message = error.get('message', 'Erro desconhecido')
            raise InstagramError(f'Meta API erro {code}: {message}')

        return data

    def create_media_container(self, image_url: str, caption: Optional[str] = None) -> str:
        """Passo 1: cria o container de mídia. Retorna o creation_id."""
        if not self.is_configured():
            raise InstagramNotConfiguredError(
                'Instagram não configurado. Preencha INSTAGRAM_ACCESS_TOKEN e INSTAGRAM_IG_USER_ID.'
            )
        cfg = self._config()
        params = {
            'image_url': image_url,
            'access_token': cfg['access_token'],
        }
        if caption:
            params['caption'] = caption

        url = self._api_url(f'{cfg["ig_user_id"]}/media')
        data = self._request('POST', url, params=params)
        creation_id = data.get('id')
        if not creation_id:
            raise InstagramError('Resposta da Meta API sem id (creation_id)')
        return str(creation_id)

    def publish_container(self, creation_id: str) -> str:
        """Passo 2: publica o container criado. Retorna o media_id."""
        cfg = self._config()
        params = {
            'creation_id': creation_id,
            'access_token': cfg['access_token'],
        }
        url = self._api_url(f'{cfg["ig_user_id"]}/media_publish')
        data = self._request('POST', url, params=params)
        media_id = data.get('id')
        if not media_id:
            raise InstagramError('Resposta da Meta API sem id (media_id)')
        return str(media_id)

    def get_media_status(self, container_id: str) -> Dict:
        """Consulta o status de processamento de um container de mídia."""
        cfg = self._config()
        url = self._api_url(container_id)
        data = self._request(
            'GET', url,
            params={'fields': 'status_code,status', 'access_token': cfg['access_token']},
        )
        return data

    def publish_image(self, image_url: str, caption: Optional[str] = None,
                      retries: int = 3, wait_seconds: float = 2.0) -> Dict:
        """Publica uma imagem (via URL pública) no Instagram.

        Retorna {'creation_id': ..., 'media_id': ...}.
        """
        creation_id = self.create_media_container(image_url, caption)

        # Aguarda o processamento da imagem antes de publicar
        for attempt in range(retries):
            try:
                status = self.get_media_status(creation_id)
                if status.get('status_code') == 'FINISHED':
                    break
            except InstagramError:
                pass
            if attempt < retries - 1:
                time.sleep(wait_seconds * (attempt + 1))

        media_id = self.publish_container(creation_id)
        return {'creation_id': creation_id, 'media_id': media_id}

    def publish_image_file(self, image_path: str, caption: Optional[str] = None) -> Dict:
        """Publica um arquivo de imagem local.

        A imagem é servida pelo próprio SISPM (rota pública) para que a Meta
        consiga baixá-la.
        """
        if not os.path.exists(image_path):
            raise InstagramError(f'Arquivo de imagem não encontrado: {image_path}')

        ext = os.path.splitext(image_path)[1].lstrip('.').lower()
        if ext not in self.IMAGE_TYPES:
            raise InstagramError(f'Tipo de imagem não suportado: .{ext}')

        public_url = self._public_url_for(image_path)
        return self.publish_image(public_url, caption)

    def _public_url_for(self, image_path: str) -> str:
        """Constrói a URL pública de um arquivo salvo em uploads/instagram/."""
        cfg = self._config()
        base = current_app.config.get('PUBLIC_BASE_URL', 'http://localhost:5000').rstrip('/')

        uploads_dir = current_app.config.get('UPLOAD_FOLDER', 'uploads')
        insta_dir = os.path.join(uploads_dir, 'instagram')
        abs_path = os.path.abspath(image_path)
        abs_insta = os.path.abspath(insta_dir)

        if os.path.normcase(os.path.commonpath([abs_path, abs_insta])) != os.path.normcase(abs_insta):
            raise InstagramError('Arquivo deve estar em uploads/instagram/ para publicação.')

        filename = os.path.basename(abs_path)
        return f'{base}/media/instagram/{filename}'


instagram_service = InstagramService()
