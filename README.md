# Baixa.ai

Site público para baixar mídia de links do **Instagram** (post, Reel e Story público), **TikTok**, **X** e **YouTube** (vídeo único ou Short). Não pede login, não usa cookie de conta e não guarda o arquivo: a API lê o link e transmite o download para quem pediu.

O site fica em [baixa.nataliagranato.xyz](https://baixa.nataliagranato.xyz). A API fica em [api.baixa.nataliagranato.xyz](https://api.baixa.nataliagranato.xyz).

## O que este MVP faz

- Aceita `instagram.com`, `tiktok.com`, `x.com`, `twitter.com`, `youtube.com` (incluindo `m.youtube.com`) e `youtu.be`, e só o link de uma publicação ou de um vídeo único (não o perfil, a playlist nem a live).
- Devolve as opções de vídeo ou imagem, inclusive carrossel. No YouTube, além do arquivo progressivo, junta vídeo H.264 e áudio AAC até 1080p e remuxa para MP4 sem recodificar o vídeo. Todo vídeo ganha também a opção **Baixar MP3** (192 kbps). O download segue em stream.
- Limita pedidos por IP, corta busca longa e recusa arquivo maior que o teto configurado.
- Responde em português quando o conteúdo é privado, exige login ou não é compatível.

Stories fechados, contas privadas e qualquer coisa que peça senha não são baixados. O Baixa.ai não contorna login.

## Desenvolvimento local

Pré-requisitos: Python 3.12, Node.js 22 e ffmpeg. O container da API já traz o ffmpeg. No `uvicorn` local, o ffmpeg precisa estar no `PATH` para o MP3 e para o remux do YouTube.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r api/requirements.txt -r api/requirements-dev.txt

cd api
export CORS_ORIGINS=http://localhost:3000
export DOWNLOAD_TOKEN_SECRET=dev-secret
uvicorn app.main:app --reload --port 8000
```

Em outro terminal:

```bash
cd web
cp .env.example .env.local
npm install
npm run dev
```

Abra [http://localhost:3000](http://localhost:3000). O `.env.local` já aponta para `http://localhost:8000`.

Testes e lint da API, sem rede:

```bash
cd api
ruff check . && ruff format --check .
pytest
```

No front:

```bash
cd web
npm run lint
npm run build
npm run typecheck
```

Imagem da API:

```bash
docker build -t baixa-api api
docker run --rm -p 8000:8000 \
  -e CORS_ORIGINS=http://localhost:3000 \
  -e DOWNLOAD_TOKEN_SECRET=dev-secret \
  baixa-api
```

## Variáveis de ambiente

### API

| Variável | Padrão | Função |
| --- | --- | --- |
| `APP_ENV` | `development` | Com `production`, `DOWNLOAD_TOKEN_SECRET` passa a ser obrigatório. |
| `DOWNLOAD_TOKEN_SECRET` | segredo só de desenvolvimento | Assina o link de download. Troque em produção. |
| `CORS_ORIGINS` | `https://baixa.nataliagranato.xyz` | Origens permitidas, separadas por vírgula. |
| `TRUST_PROXY` | `true` | Usa o último IP de `X-Forwarded-For` (o que o Render acrescenta). |
| `RATE_LIMIT_REQUESTS` | `60` | Pedidos por IP na janela. |
| `RATE_LIMIT_WINDOW_SECONDS` | `600` | Tamanho da janela, em segundos. |
| `EXTRACT_TIMEOUT_SECONDS` | `30` | Tempo máximo da busca. |
| `DOWNLOAD_TIMEOUT_SECONDS` | `120` | Tempo máximo do stream. |
| `MAX_FILE_BYTES` | `104857600` | Teto de 100 MB por arquivo. |
| `TOKEN_TTL_SECONDS` | `600` | Validade do botão de download. |
| `SENTRY_DSN` | vazio | Se existir, liga o Sentry. Sem a variável, o SDK não inicia. |
| `SENTRY_ENVIRONMENT` | vazio | Ambiente enviado ao Sentry. |
| `PORT` | `8000` | Porta do uvicorn. O Render define esta variável. |

O limite por IP vive na memória do processo. No plano gratuito há uma instância só; se um dia houver mais de uma, o limite não é compartilhado entre elas.

### Web

| Variável | Função |
| --- | --- |
| `NEXT_PUBLIC_API_URL` | URL da API, sem barra no final. Em produção: `https://api.baixa.nataliagranato.xyz`. |
| `NEXT_PUBLIC_SENTRY_DSN` | Opcional. O navegador só carrega o Sentry quando este valor existe. |

## Deploy

Os dois lados cabem em plano gratuito: API no Render (container) e site na Vercel. Não há banco. O MP3 e o remux do YouTube usam um diretório temporário só durante o pedido; ele é apagado quando o stream termina.

### API no Render

1. Crie um Blueprint a partir deste repositório. O `render.yaml` na raiz descreve o serviço `baixa-api` com o Dockerfile em `api/`.
2. Confirme o plano gratuito. Se a conta não puder usar `plan: free`, escolha o menor plano web no painel e mantenha o mesmo Dockerfile.
3. O Blueprint gera `DOWNLOAD_TOKEN_SECRET`. Não coloque o segredo no Git.
4. `SENTRY_DSN` fica vazio até você criar um projeto no Sentry e colar o DSN.
5. Em **Custom Domains**, adicione `api.baixa.nataliagranato.xyz` e publique o CNAME que o Render mostrar.
6. A checagem de saúde é `GET /healthz`. No plano gratuito o serviço dorme depois de um tempo ocioso; a primeira busca depois disso pode demorar.

### Site na Vercel

1. Importe o repositório. **Root Directory:** `web`. Framework: Next.js.
2. Defina `NEXT_PUBLIC_API_URL=https://api.baixa.nataliagranato.xyz` em Production (e Preview, se quiser).
3. Opcional: `NEXT_PUBLIC_SENTRY_DSN`.
4. Adicione o domínio `baixa.nataliagranato.xyz` e use os registros DNS que a Vercel indicar.

A CORS da API precisa incluir a origem exata do site. O `render.yaml` já libera `https://baixa.nataliagranato.xyz`. Se usar um domínio de preview da Vercel, acrescente essa origem em `CORS_ORIGINS`.

## Atualizar o yt-dlp

O extrator quebra quando o Instagram, o TikTok, o X ou o YouTube mudam a página. A versão está pinada em `api/requirements.txt`.

```bash
pip index versions yt-dlp
# edite a linha yt-dlp==... em api/requirements.txt
pip install -r api/requirements.txt
pytest
```

Suba a API de novo depois de mudar a versão. Não é preciso mudar o front.

## YouTube

Aceitamos `youtube.com`, `m.youtube.com`, `youtu.be` e Shorts (`/shorts/ID`). Só vídeo único: um link de playlist (`list=`) ou de live é recusado antes de chamar o extrator.

A qualidade alta (até 1080p, quando existe H.264 + AAC) junta as duas faixas com ffmpeg em remux (`-c copy`), sem recodificar o vídeo. A opção progressiva, em geral 360p, continua na lista. Todo vídeo, de qualquer plataforma, também ganha **Baixar MP3**: o ffmpeg converte o melhor áudio para MP3 a 192 kbps, em uma thread, e o arquivo temporário é apagado depois do stream. Os dois caminhos respeitam `MAX_FILE_BYTES` e `DOWNLOAD_TIMEOUT_SECONDS`.

O YouTube costuma responder `Sign in to confirm you're not a bot` para IPs de datacenter, como os do Render no plano gratuito. Quando isso acontece, a API devolve uma mensagem em português e não tenta login nem cookies. Não há garantia de que o download do YouTube funcione em produção.

## Nota legal

O Baixa.ai é uma ferramenta de uso pessoal. Baixe só o que você tem direito de guardar. Respeite os direitos autorais e os termos do Instagram, do TikTok, do X e do YouTube. O serviço não se destina a redistribuir conteúdo de terceiros, não pede a senha de ninguém e não armazena as mídias.
