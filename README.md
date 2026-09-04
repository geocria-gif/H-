# SISPM - Sistema de Escalas CPR-CN

Sistema web profissional para gestão de escalas de hora extra (HE), vale-transporte (VD) e serviço ordinário (SO) do Comando de Policiamento Rodoviário - Centro Norte (CPR-CN).

## 🚀 Tecnologias

- **Backend**: Flask 3.0, SQLAlchemy 2.0, Flask-Migrate (Alembic)
- **Banco de Dados**: PostgreSQL 16 (produção) / SQLite (desenvolvimento)
- **Autenticação**: Flask-Login + Flask-JWT-Extended (JWT)
- **Segurança**: Flask-Talisman (CSP, HSTS), Flask-Limiter (Rate Limit), CSRF Protection
- **Cache**: Flask-Caching com Redis
- **Servidor**: Gunicorn + Nginx
- **Containerização**: Docker + Docker Compose
- **Frontend**: Bootstrap 5.3, Chart.js, Leaflet.js
- **Testes**: pytest, pytest-cov (cobertura ≥ 80%)
- **CI/CD**: GitHub Actions
- **Deploy**: Render, Railway, Fly.io, DigitalOcean, VPS Ubuntu

## 📋 Funcionalidades

### Core
- ✅ Dashboard com indicadores e gráficos (Chart.js)
- ✅ Gestão de Eventos (HE/VD/SO) com múltiplas OPMs
- ✅ Escala Geral Mensal com busca por matrícula/nome
- ✅ Escala P2 (modelo oficial) com legendas e metadados
- ✅ Escalas Salvas (snapshots) para cálculo de relatórios
- ✅ Relatório de Horas com exportação CSV
- ✅ Tabela de Valores por Posto/Graduação (diurno/noturno)
- ✅ Ocorrências com mapa (Leaflet) e estatísticas
- ✅ Viaturas e Municípios

### Administração
- ✅ Usuários com roles (ADMIN, SUPERVISOR, OPERADOR, VISITANTE)
- ✅ Cargos/Postos e OPMs
- ✅ Backup/Restore PostgreSQL (pg_dump/psql)
- ✅ Logs estruturados (access, error, database, security)
- ✅ Upload de arquivos (PDF, Excel, Word, Imagens)

### API REST
- ✅ CRUD completo para todas as entidades
- ✅ Autenticação JWT (Access + Refresh tokens)
- ✅ Paginação, filtros, ordenação, busca
- ✅ Documentação OpenAPI/Swagger
- ✅ Publicação de cards no Instagram (Meta Graph API)

### Integração Instagram
- ✅ Serviço de publicação via Meta Graph API (imagem + legenda)
- ✅ Página administrativa (`/instagram`) com status e upload manual
- ✅ Endpoint API `POST /api/v1/instagram/publish` (multipart: `image` + `caption`)
- ✅ Endpoint API `GET /api/v1/instagram/status`
- ✅ Botão "Publicar no Instagram" nos cards de Ocorrências (index.html, index2.html, NOVO/index2.html)
- 📖 Guia de configuração das credenciais em [INSTAGRAM_API.md](INSTAGRAM_API.md)

## 🏗️ Estrutura do Projeto

```
SISPM/
├── app/
│   ├── __init__.py          # App factory + extensões
│   ├── config.py            # Configurações (dev/prod/test)
│   ├── models/              # SQLAlchemy Models
│   ├── routes/              # Blueprints (views)
│   ├── services/            # Camada de serviços
│   ├── repository/          # Repository Pattern
│   ├── forms/               # WTForms
│   ├── auth/                # Autenticação (Login, JWT, Roles)
│   ├── api/                 # API REST v1
│   ├── dashboard/           # Dashboard Blueprint
│   ├── templates/           # Jinja2 Templates
│   └── static/              # CSS, JS, Images
├── migrations/              # Alembic migrations
├── tests/                   # Unit + Integration tests
├── instance/                # Instance folder (SQLite dev)
├── uploads/                 # Arquivos uploadados
├── backups/                 # Backups PostgreSQL
├── logs/                    # Logs da aplicação
├── config.py                # Configuração principal
├── requirements.txt         # Dependências Python
├── Dockerfile               # Imagem Docker otimizada
├── docker-compose.yml       # Orquestração completa
├── gunicorn.conf.py         # Config Gunicorn produção
├── .env.example             # Variáveis de ambiente
├── Procfile                 # Render/Railway
├── runtime.txt              # Python version
├── README.md                # Este arquivo
└── .github/workflows/       # CI/CD
```

## ⚡ Início Rápido

### Pré-requisitos
- Docker 24+ e Docker Compose 2+
- Ou Python 3.11+ e PostgreSQL 16+

### Com Docker (Recomendado)

```bash
# 1. Clone o repositório
git clone https://github.com/seu-usuario/sispm.git
cd sispm

# 2. Configure variáveis de ambiente
cp .env.example .env
# Edite .env com suas configurações

# 3. Suba a stack completa
docker compose up --build -d

# 4. Execute migrações e seed inicial
docker compose exec app flask db upgrade
docker compose exec app flask seed

# 5. Acesse http://localhost:5000
# Login: 30481332 / 30481332 (ADMIN)
```

### Desenvolvimento Local (sem Docker)

```bash
# 1. Crie ambiente virtual
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate  # Windows

# 2. Instale dependências
pip install -r requirements.txt

# 3. Configure variáveis
cp .env.example .env
# Edite .env: FLASK_CONFIG=development

# 4. Inicialize banco
flask db upgrade
flask seed

# 5. Rode a aplicação
flask run --debug
# ou
gunicorn --config gunicorn.conf.py app:app
```

## 🐳 Docker - Produção

### Build da Imagem
```bash
docker build -t sispm:latest .
```

### Docker Compose Produção
```bash
# Com variáveis de produção
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

### Variáveis Obrigatórias Produção
```env
FLASK_CONFIG=production
SECRET_KEY=chave-super-secreta-32-chars-minimo
JWT_SECRET_KEY=jwt-chave-super-secreta-32-chars
DATABASE_URL=postgresql://user:pass@host:5432/db
SESSION_COOKIE_SECURE=True
REMEMBER_COOKIE_SECURE=True
JWT_COOKIE_SECURE=True
```

## 🔧 Comandos Flask CLI

```bash
# Migrações
flask db init          # Inicializa migrações (uma vez)
flask db migrate -m "mensagem"  # Cria migração
flask db upgrade       # Aplica migrações
flask db downgrade     # Reverte última

# Seed / Dados iniciais
flask seed             # Cria admin + dados básicos
flask seed --full      # Inclui dados de exemplo

# Backup
flask backup create    # Cria backup PostgreSQL
flask backup list      # Lista backups
flask backup restore <arquivo>  # Restaura backup

# Testes
pytest                 # Roda todos os testes
pytest --cov=app --cov-report=html  # Com cobertura
pytest -v              # Verboso
```

## 📚 API REST

### Autenticação
```bash
# Login
curl -X POST http://localhost:5000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"matricula": "30481332", "senha": "30481332"}'

# Response: access_token, refresh_token, user

# Usar token
curl -H "Authorization: Bearer <access_token>" \
  http://localhost:5000/api/v1/efetivos
```

### Endpoints Principais

| Módulo | Endpoints |
|--------|-----------|
| **Auth** | `POST /api/v1/auth/login`, `POST /api/v1/auth/refresh`, `GET /api/v1/auth/me` |
| **Usuários** | `GET/POST /api/v1/usuarios`, `GET/PUT/DELETE /api/v1/usuarios/<id>` |
| **Efetivo** | `GET/POST /api/v1/efetivos`, `GET/PUT/DELETE /api/v1/efetivos/<matricula>` |
| **Eventos** | `GET/POST /api/v1/eventos`, `GET/PUT/DELETE /api/v1/eventos/<id>` |
| **Escalas** | `GET/POST /api/v1/escalas`, `GET /api/v1/eventos/<id>/relatorio-horas` |
| **Tabela Valores** | `GET/POST /api/v1/tabela-valores`, `GET/PUT/DELETE /api/v1/tabela-valores/<id>` |
| **Ocorrências** | `GET/POST /api/v1/ocorrencias`, `GET /api/v1/ocorrencias/estatisticas` |
| **Escalas P2** | `GET/POST /api/v1/escalas-p2` |
| **Escalas Salvas** | `GET/POST /api/v1/escalas-salvas`, `POST /api/v1/escalas-salvas/<id>/ativar` |
| **Viaturas** | `GET/POST /api/v1/viaturas` |
| **Municípios** | `GET/POST /api/v1/municipios` |
| **Cargos** | `GET /api/v1/cargos` |
| **OPMs** | `GET /api/v1/opms` |
| **Backup** | `POST /api/v1/backup`, `GET /api/v1/backups` |
| **Instagram** | `POST /api/v1/instagram/publish`, `GET /api/v1/instagram/status` |
| **Health** | `GET /api/v1/health` |

### Paginação e Filtros
```
GET /api/v1/efetivos?page=1&per_page=20&search=joao
GET /api/v1/eventos?tipo_pagamento=HE
GET /api/v1/ocorrencias?data_inicio=2024-01-01&data_fim=2024-12-31
```

## 🧪 Testes

```bash
# Todos os testes
pytest

# Com cobertura (mínimo 80%)
pytest --cov=app --cov-report=term-missing --cov-fail-under=80

# Apenas unitários
pytest tests/unit

# Apenas integração
pytest tests/integration

# Verboso
pytest -v --tb=short
```

## 📦 Deploy

### Render.com
1. Conecte repositório GitHub
2. **Build Command**: `pip install -r requirements.txt && flask db upgrade`
3. **Start Command**: `gunicorn --config gunicorn.conf.py app:app`
4. Adicione variáveis de ambiente (Settings > Environment)
4. PostgreSQL: Crie banco no Render e use `DATABASE_URL` interna

### Railway
```bash
railway login
railway init
railway add postgresql
railway add redis
railway up
```

### Fly.io
```bash
fly launch
fly postgres create
fly deploy
```

### VPS Ubuntu (com Docker)
```bash
# No servidor
git clone https://github.com/seu-usuario/sispm.git
cd sispm
cp .env.example .env
# Edite .env com valores de produção
docker compose up --build -d
docker compose exec app flask db upgrade
docker compose exec app flask seed

# Configure Nginx + SSL (Let's Encrypt)
# Veja nginx.conf.example
```

## 🔒 Segurança

- **Senhas**: Hash bcrypt (cost=12)
- **CSRF**: Proteção em todos os forms (Flask-WTF)
- **XSS**: CSP rigoroso via Flask-Talisman
- **SQL Injection**: SQLAlchemy ORM + prepared statements
- **Headers**: HSTS, X-Frame-Options, X-Content-Type-Options
- **Rate Limit**: 200 req/min por IP (configurável)
- **Sessões**: HttpOnly, Secure, SameSite=Lax
- **JWT**: Tokens em cookies HttpOnly + CSRF protection

## 📊 Monitoramento

### Logs
```
logs/
├── access.log    # Requisições HTTP
├── error.log     # Erros da aplicação
├── database.log  # Queries lentas/erros SQL
└── security.log  # Tentativas login, acesso negado
```

### Health Check
```bash
curl http://localhost:5000/health
# {"status": "healthy", "service": "SISPM"}
```

## 🔄 Backup & Restore

### Automático (Cron no container worker)
```bash
# Diário às 02:00
0 2 * * * flask backup create && flask backup cleanup
```

### Manual
```bash
# Criar
flask backup create

# Listar
flask backup list

# Restaurar
flask backup restore backup_sispm_20240115_020000.sql
```

## 📝 Licença

Proprietário - CPR-CN / Polícia Militar do Estado da Bahia

## 🤝 Contribuição

1. Fork o projeto
2. Crie branch (`git checkout -b feature/nova-funcionalidade`)
3. Commit (`git commit -m 'feat: nova funcionalidade'`)
4. Push (`git push origin feature/nova-funcionalidade`)
5. Abra Pull Request

## 📞 Suporte

- **Desenvolvedor**: Francisco Rocha Junior
- **Email**: francisco.rocha@pm.ba.gov.br
- **Issues**: GitHub Issues

---

**SISPM v2.0** - Sistema de Escalas do CPR-CN  
Desenvolvido com ❤️ para a Polícia Militar da Bahia