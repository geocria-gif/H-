# Integração com Instagram (Meta Graph API)

Guia para publicar os cards institucionais automaticamente no Instagram da
SEGMAF (`@segmaf.com.br`) usando a Meta Graph API.

## Pré-requisitos

- Conta **Instagram Business** (ou Creator) para a SEGMAF.
- Conta **Facebook** vinculada à página da SEGMAF.
- Acesso ao painel **Meta for Developers**.

> A API oficial do Instagram **não permite** publicar em perfis pessoais.
> O perfil deve ser do tipo **Business** ou **Creator** e vinculado a uma
> Página no Facebook.

## 1. Converter o Instagram para Business/Creator

1. Abra o app do Instagram (celular).
2. **Configurações → Tipo de conta → Mudar para conta profissional**.
3. Escolha **Criador** (Creator) ou **Empresa** (Business) e conecte/associe
   uma **Página do Facebook** da SEGMAF.
4. Confirme e aguarde a conversão.

## 2. Criar o App na Meta

1. Acesse https://developers.facebook.com/apps/ e faça login.
2. Clique em **Criar app** → escolha **Empresa** → **Seguinte**.
3. Dê um nome (ex.: `SEGMAF Instagram`) e adicione o e-mail de contato.
4. Crie o app. No painel, localize **ID do app** (APP_ID) e **Segredo do app**
   (APP_SECRET) em **Configurações → Básico**.

## 3. Adicionar o produto Instagram

1. Dentro do app, em **Adicionar produto**, localize **Instagram** e clique em
   **Configurar**.
2. Vá em **Instagram → Configurações → Instagram para API** e clique em
   **Conectar conta do Instagram**.
3. Autorize o acesso com a conta Business da SEGMAF.

## 4. Obter o Access Token (long-lived)

A forma mais simples para automação é usar o **System User**:

1. Em **Configurações → Usuários do sistema** (System Users), clique em
   **Adicionar**.
2. Nome: `SEGMAF Bot`, função (role): **Analista**.
3. Clique em **Gerar novo token**:
   - **App**: selecione o app criado.
   - **Validade**: 365 dias.
   - Marque as permissões:
     - `instagram_basic`
     - `instagram_content_publish`
     - `pages_show_list`
     - `pages_read_engagement`
     - `business_management`
4. Copie o token gerado (válido por 60 dias; pode ser renovado antes de expirar).

### Alternativa (Access Token padrão do app)

1. Em **Ferramentas → API Graph Explorer** (https://developers.facebook.com/tools/explorer/).
2. Selecione o app e o **Instagram Business Account**.
3. Clique em **Gerar token de acesso**.
4. Marque as permissões acima e gere o token curto.
5. Troque por um token de longa duração (60 dias) chamando:
   `GET https://graph.facebook.com/v21.0/oauth/access_token?grant_type=fb_exchange_token&client_id=APP_ID&client_secret=APP_SECRET&fb_exchange_token=SHORT_TOKEN`

## 5. Obter o Instagram Business Account ID

Chame com o token obtido:

```
GET https://graph.facebook.com/v21.0/me/accounts?access_token=TOKEN
```

Localize a **Página da SEGMAF** e copie o `id`. Depois:

```
GET https://graph.facebook.com/v21.0/{PAGE_ID}?fields=instagram_business_account&access_token=TOKEN
```

O valor retornado em `instagram_business_account.id` é o **IG_USER_ID**
(Instagram Business Account ID) usado na publicação.

## 6. Configurar no SISPM

Adicione no arquivo `.env` (e em produção):

```env
INSTAGRAM_ACCESS_TOKEN=token_gerado_acima
INSTAGRAM_IG_USER_ID=numero_do_instagram_business_account
INSTAGRAM_APP_ID=id_do_app_meta
INSTAGRAM_APP_SECRET=segredo_do_app_meta
PUBLIC_BASE_URL=https://seu-dominio.com
```

> `PUBLIC_BASE_URL` é obrigatório: a Meta baixa a imagem do card a partir de uma
> URL pública. Em desenvolvimento use um túnel (ngrok/cloudflared) apontando
> para a aplicação.

## 7. Testar a conexão

1. Faça login no SISPM como ADMIN/SUPERVISOR.
2. Acesse **Administração → Instagram**.
3. A página mostrará se as credenciais estão configuradas e permitirá publicar
   uma imagem de teste.
4. Ou chame a API:
   `GET /api/v1/instagram/status` com o token JWT.

## 8. Publicar os cards

- **Página web (cards):** no painel de Ocorrências, clique em
  **Publicar no Instagram** — o card atual é enviado ao backend e publicado.
- **API:** `POST /api/v1/instagram/publish` (multipart: `image` + `caption`).
- **Admin:** página `Administração → Instagram`, upload manual da imagem.

## Permissões e limites

- Só perfis **Business/Creator** podem usar a API.
- O token deve incluir `instagram_content_publish`.
- Limite padrão: ~50 publicações de imagem por 24h por conta.
- A imagem deve ter proporção entre 1.91:1 e 4:5 (os cards `feed` 1080×1440 e
  `reels/story` 1080×1920 são aceitos).

## Solução de problemas

| Erro | Causa / solução |
|------|-----------------|
| `(#10) Application does not have permission` | Falta permissão `instagram_content_publish` no token |
| `(#100) The image cannot be downloaded` | `PUBLIC_BASE_URL` inacessível externamente; verifique túnel/HTTPS |
| `(#24) Cannot retrieve the number of instagram` | Instagram não é Business/Creator ou não está vinculado à Página |
| Token expirou | Renove no **Usuários do sistema** (System User) |

## Referência

- https://developers.facebook.com/docs/instagram-platform/instagram-api-with-instagram-login
- https://developers.facebook.com/docs/instagram-platform/instagram-api-with-facebook-login/content-publishing
