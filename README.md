# Baixa.ai

Site para baixar mídia pública a partir de um link do Instagram, do TikTok, do X (Twitter) ou do YouTube. A pessoa cola o endereço no site; a API consulta o yt-dlp, lista as opções e transmite o arquivo. Não há cadastro. A API não envia cookie, usuário nem senha ao extrator.

A origem de produção gravada no código é `https://baixa.nataliagranato.xyz` (`metadataBase` em `web/app/layout.tsx`, CORS padrão e `render.yaml`). O workflow de CI compila o front com `NEXT_PUBLIC_API_URL=https://api.baixa.nataliagranato.xyz`. O `render.yaml` não declara esse hostname da API.

## O que o código faz

- Aceita só `http` e `https`, sem usuário ou senha na URL, sem IP no lugar do host e só nas portas 80, 443 ou na porta implícita. O host precisa ser o domínio permitido ou um subdomínio dele.
- Instagram: `/p/`, `/reel/`, `/reels/`, `/tv/`, `/stories/{usuário}/{id}` e `/share/(p|reel|reels|tv)/`. Perfil e `/stories/{usuário}/` sem o id numérico são recusados.
- TikTok: `/@{usuário}/video/{id}`, `/@{usuário}/photo/{id}`, `/t/{código}`, `/embed/v2/{id}`, além dos encurtadores `vm.tiktok.com` e `vt.tiktok.com`. O perfil (`/@usuário`) é recusado. `t.co` não entra na lista.
- X: `/{usuário}/status/{id}` ou `statuses`, `/i/status/{id}`, com `/photo/{n}` ou `/video/{n}` opcional. Vale `x.com` e `twitter.com` (inclusive subdomínio, como `mobile.twitter.com`). O perfil é recusado.
- YouTube: `youtube.com` (inclusive `m.` e `music.`), `youtu.be`, `/watch?v=`, `/shorts/`, `/embed/` e `/v/`, com id de 11 caracteres. Playlist (`list=` ou caminho `/playlist`), live (`/live`, `is_live` ou `live_status` de ao vivo/agendado) e canal são recusados antes ou logo depois da extração. No YouTube a busca usa `noplaylist`.
- Devolve vídeo, imagem ou áudio. Quando o extrator devolve várias entradas, como um carrossel, cada uma pode gerar as próprias opções. O corte é `MAX_EXTRACT_ENTRIES` (padrão 20). O yt-dlp também para em 20 (`playlistend`). Playlist do YouTube não vira carrossel: é recusada.
- Formato progressivo (vídeo e áudio já no mesmo arquivo HTTP): até três alturas. Vídeo H.264 (`avc1` ou `h264`) só de vídeo, até 1080p, junto com áudio AAC (`mp4a` ou `aac`) só de áudio: até três alturas, remuxadas para MP4. VP9 não é recodificado para MP4. HLS e DASH (`m3u8`, `dash`) ficam de fora.
- Se a lista já tem algum vídeo, e existe áudio de origem cuja estimativa cabe em `MAX_FILE_BYTES`, entra a opção MP3. O rótulo na API é `MP3`; o botão do site mostra `Baixar MP3`.
- O arquivo direto é transmitido sem gravar em disco. MP3 e remux passam por um diretório temporário.
- Conteúdo privado, removido ou que peça login vira mensagem em português. A API não tenta contornar isso.
- `POST /api/extract`, `GET /api/download` e `GET /api/thumbnail` entram no limite por IP, na memória do processo. `GET /healthz` não entra. Busca e download têm tempo máximo. Arquivo acima de `MAX_FILE_BYTES` é recusado.

O texto de ajuda do formulário pede um post, Reel ou Story público, um vídeo do TikTok, um post do X ou um vídeo único do YouTube, e diz que vídeos também podem ser baixados em MP3. A página descreve o uso como pessoal, sem conta e sem guardar o arquivo.

## Estrutura do repositório

Não há `package.json` na raiz. API e site são dois projetos. Não há `LICENSE`, `CONTRIBUTING.md`, modelo de issue nem `vercel.json`.

```text
.
├── .github/workflows/ci.yml   # lint e testes da API; lint, build e typecheck do site
├── render.yaml                # Blueprint do Render para a API
├── api/
│   ├── Dockerfile             # Python 3.12, ffmpeg, usuário não-root
│   ├── .dockerignore
│   ├── .env.example
│   ├── pyproject.toml         # projeto baixa-api; pytest e ruff
│   ├── requirements.txt
│   ├── requirements-dev.txt
│   ├── app/
│   │   ├── main.py            # rotas HTTP
│   │   ├── config.py          # leitura do ambiente
│   │   ├── urls.py            # allowlist de links
│   │   ├── ytdlp_runner.py    # chamada ao yt-dlp
│   │   ├── media.py           # escolha dos formatos
│   │   ├── streaming.py       # proxy do arquivo direto
│   │   ├── transcode.py       # MP3 e remux com ffmpeg
│   │   ├── tokens.py          # token HMAC do download
│   │   ├── cache.py           # cache em memória da extração
│   │   ├── ratelimit.py       # limite por IP
│   │   └── errors.py          # mensagens em português
│   └── tests/                 # pytest, sem rede
└── web/
    ├── package.json
    ├── package-lock.json
    ├── .env.example
    ├── next.config.ts
    ├── app/                   # página, layout, downloader, Sentry, CSS e ícone
    ├── lib/api.ts             # cliente da API
    ├── eslint.config.mjs
    └── tsconfig.json
```

O `web/README.md` só aponta para este arquivo e registra que, na Vercel, o diretório raiz do projeto é `web/`. `web/AGENTS.md` é um aviso gerado pelo Next.js para agentes; não descreve o produto.

## Pré-requisitos

- Python `>= 3.12`, como em `api/pyproject.toml`. A imagem Docker e o CI usam 3.12.
- Node.js 22, que é a versão do job `web` no CI. O `package.json` não declara `engines`.
- npm, com o lockfile `web/package-lock.json`. O CI instala com `npm ci`.
- ffmpeg no `PATH` para gerar MP3 e para o remux. A imagem da API instala o ffmpeg. Os testes de transcode substituem a execução do comando, então o `pytest` não precisa do binário.
- Para o container local: Docker.

As dependências da API e do site não incluem banco de dados nem fila.

## Desenvolvimento local

A API lê só o ambiente do processo. Ela não carrega `api/.env.example` sozinha. O exemplo lista as variáveis; exporte as que quiser mudar.

Na raiz do repositório:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r api/requirements.txt -r api/requirements-dev.txt

cd api
export CORS_ORIGINS=http://localhost:3000
export DOWNLOAD_TOKEN_SECRET=dev-secret
uvicorn app.main:app --reload --port 8000
```

O comando precisa rodar em `api/`, porque o pacote importado é `app`. Com `APP_ENV` diferente de `production`, um segredo vazio faz a API usar o valor de desenvolvimento definido em `api/app/config.py`. Não use esse modo em produção.

Em outro terminal:

```bash
cd web
cp .env.example .env.local
npm install
npm run dev
```

O `web/.env.example` define `NEXT_PUBLIC_API_URL=http://localhost:8000`. Se a variável não existir, `web/lib/api.ts` usa esse mesmo endereço e remove uma barra final. O `api/.env.example` libera `http://localhost:3000` no CORS. Abra o site nessa origem, ou acrescente em `CORS_ORIGINS` a origem em que o `next dev` ficou.

### Container da API

O contexto do build é `api/`. A imagem não inclui o site nem os testes.

```bash
docker build -t baixa-api api
docker run --rm -p 8000:8000 \
  -e CORS_ORIGINS=http://localhost:3000 \
  -e DOWNLOAD_TOKEN_SECRET=dev-secret \
  baixa-api
```

O processo escuta em `0.0.0.0` na porta `${PORT:-8000}`.

### Verificação

Os mesmos comandos do CI, em `.github/workflows/ci.yml`. O workflow roda em todo `push` e em todo `pull_request`.

API, a partir de `api/`:

```bash
ruff check . && ruff format --check .
pytest
```

O `api/tests/conftest.py` bloqueia `socket.create_connection` e `socket.getaddrinfo`. Os testes não alcançam Instagram, TikTok, X, YouTube nem outro host. O Ruff está em `api/pyproject.toml`: linha de 100, alvo Python 3.12, regras `E`, `F`, `I`, `UP` e `B`.

Site, a partir de `web/`:

```bash
npm ci
npm run lint
npm run build
npm run typecheck
```

No CI, o build recebe `NEXT_PUBLIC_API_URL=https://api.baixa.nataliagranato.xyz`. `npm run start` existe (`next start`) e não faz parte do CI.

## API

FastAPI, com OpenAPI, Swagger e ReDoc desligados (`docs_url`, `redoc_url` e `openapi_url` são `None`). Toda resposta recebe `X-Content-Type-Options: nosniff`, `Referrer-Policy: no-referrer` e, se ainda não houver, `Cache-Control: no-store`.

CORS: origens de `CORS_ORIGINS`, métodos `GET`, `POST` e `OPTIONS`, cabeçalhos `Content-Type` e `Accept`, sem credenciais.

| Método e caminho | Função |
| --- | --- |
| `GET /healthz` | `{"status": "ok"}`. Não entra no limite por IP. |
| `POST /api/extract` | Corpo JSON `{"url": "..."}`, de 1 a 2048 caracteres. Devolve a prévia e os caminhos de download. |
| `GET /api/download?token=` | Transmite um item. Exige token de arquivo. |
| `GET /api/thumbnail?token=` | Transmite a miniatura, `Content-Disposition: inline`. |

A resposta de `/api/extract` traz `provider`, `title`, `author`, `thumbnail_path` e `items`. Cada item tem `index`, `type` (`video`, `image` ou `audio`), `ext`, `label`, `filesize` e `download_path`. A URL do CDN não vai no JSON: o teste `test_extract_returns_download_options_without_leaking_cdn_urls` cobre isso. O caminho é relativo (`/api/download?token=...`). O site junta com `NEXT_PUBLIC_API_URL`.

Erro classificado: JSON `{"error", "message"}`, com a mensagem de `api/app/errors.py`, em português. O texto cru do extrator não entra nessa mensagem.

| `error` | Situação verificada no código |
| --- | --- |
| `invalid_url` | URL malformada, ou corpo inválido fora de `/api/download` e `/api/thumbnail`. |
| `unsupported_host` | Host fora da allowlist. O extrator não é chamado. |
| `unsupported_content` | Caminho incompatível, live, playlist do YouTube, ou nenhum formato aceito. |
| `private_content` | O texto do extrator casa com um marcador de `api/app/errors.py`, como `private`, `login`, `sign in` ou `cookie`. |
| `not_found` | Conteúdo removido, ou a opção do token não existe mais. |
| `too_large` | Acima de `MAX_FILE_BYTES`. |
| `timeout` | Busca, download local ou ffmpeg estouraram o tempo. |
| `upstream_blocked` | O YouTube pediu confirmação de que o cliente não é um robô. |
| `extraction_failed` | Falha genérica, inclusive destino que não é um IP público. |
| `rate_limited` | Limite do IP. A resposta inclui `Retry-After`. |
| `invalid_token` | Token ausente, adulterado ou vencido. |

### Formatos

A escolha está em `api/app/media.py`.

- Progressivo: protocolo HTTP, com `vcodec` e `acodec`, sem `m3u8`, `dash` ou `mhtml`. Até três alturas.
- Remux: faixas separadas, vídeo H.264 até 1080p e áudio AAC, as duas por HTTP. Até três alturas. O `ffmpeg` copia os fluxos (`-c copy`) e grava `+faststart`. Não usa `libx264`. O código não restringe esse caminho ao YouTube; o teste que fixa o resultado usa um info de YouTube.
- Se a mesma altura existe no remux e no progressivo, o rótulo do progressivo ganha o sufixo ` direto`.
- Imagem (`jpg`, `jpeg`, `png`, `webp`, `gif`): só quando não há vídeo, a de maior largura (no empate, a de maior tamanho). Uma imagem se chama `Imagem`. Várias se chamam `Imagem 1`, `Imagem 2`, e assim por diante.
- MP3: só se já existe um vídeo. A fonte é o áudio de maior `abr`, ou o progressivo de maior `abr` se não houver faixa só de áudio. A estimativa de tamanho é a duração em segundos multiplicada por `192000 / 8`, mais 1024 bytes. Sem duração numérica positiva, a estimativa não é aplicada. Se a estimativa passa de `MAX_FILE_BYTES`, a opção não entra. O `ffmpeg` converte com `libmp3lame`, 192 kbps, dois canais, uma thread (`-threads 1`), sem faixa de vídeo (`-vn`).
- O yt-dlp também corta a playlist em 20 entradas (`playlistend`). `MAX_EXTRACT_ENTRIES` corta de novo depois, no valor configurado (padrão 20).

O nome do arquivo usa a rede `instagram`, `tiktok`, `x` ou `youtube`. MP4 com altura vira `baixa-{rede}-{altura}p.mp4`. MP3 vira `baixa-{rede}-{n}.mp3`. Os outros ficam `baixa-{rede}-{n}.{ext}`. O `n` é o `index` do item mais um. `jpeg` vira `jpg`. Extensão fora do mapa `EXT_CONTENT_TYPES`, em `api/app/media.py`, vira `bin`.

### Download e o que fica retido

O arquivo direto sai por `api/app/streaming.py`, que não grava o corpo em disco. O cliente HTTP não segue redirecionamento sozinho; o código segue no máximo três. O host e todos os endereços em que ele resolve precisam ser públicos: não vale privado, loopback, link-local, multicast, reservado nem não especificado. Cabeçalhos encaminhados, se existirem, ficam em `user-agent`, `referer`, `accept`, `accept-language` e `origin`. `Cookie` não entra.

MP3 e remux usam um diretório de `tempfile` com prefixo `baixa-`. `prepare_local_media` apaga esse diretório se a preparação levanta erro. No caminho feliz, `cleanup()` apaga o diretório quando o stream termina. O yt-dlp baixa uma faixa por id, com `max_filesize` igual a `MAX_FILE_BYTES`, `cachedir` desligado e sem cookie.

O resultado da extração fica num cache em memória (`api/app/cache.py`), para a prévia e os downloads seguintes reaproveitarem a mesma busca. O TTL é `CACHE_TTL_SECONDS`. O máximo de 64 entradas está fixo no construtor, não é variável de ambiente. O processo descarta as mais antigas.

O limite por IP (`api/app/ratelimit.py`) também é só deste processo. O comentário do módulo associa isso a uma única instância. Com mais de um processo, cada um conta à parte. Com `TRUST_PROXY` ligado (o padrão), o IP é o último item de `X-Forwarded-For`. Sem o cabeçalho, ou com `TRUST_PROXY` desligado, vale o host da conexão.

O token (`api/app/tokens.py`) é HMAC-SHA256 do payload `url`, `kind`, `index`, `format_id` e `exp`. A validade é `TOKEN_TTL_SECONDS`.

## Configuração

Valores abaixo são os de `Settings.from_env` quando a variável está ausente ou vazia. Inteiro ou número inválido faz a API falhar na subida com `RuntimeError`. `CORS_ORIGINS` precisa ter ao menos uma origem; várias se separam por vírgula.

`TRUST_PROXY` é verdadeiro para `1`, `true`, `yes` ou `on` (qualquer caixa). Qualquer outro texto não vazio é falso. Vazio usa o padrão.

### API

| Variável | Padrão no código | Função |
| --- | --- | --- |
| `APP_ENV` | `development` | Com `production`, `DOWNLOAD_TOKEN_SECRET` é obrigatório e não pode ser o segredo de desenvolvimento. |
| `DOWNLOAD_TOKEN_SECRET` | segredo de desenvolvimento, se vazio e fora de produção | Assina o token. O `render.yaml` pede `generateValue: true`. |
| `CORS_ORIGINS` | `https://baixa.nataliagranato.xyz` | Origens permitidas. O `.env.example` da API usa `http://localhost:3000`. |
| `TRUST_PROXY` | `true` | Lê o último IP de `X-Forwarded-For`. |
| `RATE_LIMIT_REQUESTS` | `60` | Pedidos por IP na janela. O mínimo aceito pelo limitador é 1. |
| `RATE_LIMIT_WINDOW_SECONDS` | `600` | Janela, em segundos. Precisa ser positiva. |
| `EXTRACT_TIMEOUT_SECONDS` | `30` | Tempo da busca. O handler espera esse valor mais 1 segundo. |
| `DOWNLOAD_TIMEOUT_SECONDS` | `120` | Tempo do stream direto e da preparação local. |
| `MAX_FILE_BYTES` | `104857600` | Teto de `100 * 1024 * 1024` bytes. |
| `TOKEN_TTL_SECONDS` | `600` | Validade do token, em segundos. |
| `CACHE_TTL_SECONDS` | `180` | Tempo do cache em memória da extração. Não está no `.env.example`. |
| `MAX_EXTRACT_ENTRIES` | `20` | Máximo de entradas de um carrossel. Não está no `.env.example`. |
| `SENTRY_DSN` | vazio, SDK não inicia | Liga o Sentry da API. `traces_sample_rate` fica 0 e `send_default_pii` fica falso. |
| `SENTRY_ENVIRONMENT` | vazio | Ambiente enviado ao Sentry, se o DSN existir. |
| `PORT` | `8000` no comando do container | Lida pelo `CMD` do Dockerfile, não por `Settings`. O `render.yaml` não a define. |

`api/.env.example` não inclui `CACHE_TTL_SECONDS`, `MAX_EXTRACT_ENTRIES` nem `PORT`.

### Web

| Variável | Função |
| --- | --- |
| `NEXT_PUBLIC_API_URL` | URL da API. Barra final é removida. Sem a variável, o código usa `http://localhost:8000`. `web/lib/api.ts` lê essa variável, inclusive no componente de cliente. No CI ela é definida no passo de build. |
| `NEXT_PUBLIC_SENTRY_DSN` | Opcional. O navegador só importa `@sentry/browser` quando este valor existe. Amostra de traces 0, sem PII. |

O `.env.example` do site deixa o DSN comentado. `web/.gitignore` ignora `.env*` e preserva `.env.example`. O `.gitignore` da raiz ignora `.env` e `.env.local`.

## Deploy

Não há script de deploy no repositório.

### API no Render

O `render.yaml` descreve um serviço web:

- nome `baixa-api`, runtime `docker`, plano `free`, região `oregon`
- Dockerfile `./api/Dockerfile`, contexto `./api`
- caminho de health check `/healthz`
- `APP_ENV=production`
- `CORS_ORIGINS=https://baixa.nataliagranato.xyz`
- `TRUST_PROXY=true`
- `DOWNLOAD_TOKEN_SECRET` gerado pelo Render (`generateValue: true`)
- `SENTRY_ENVIRONMENT=production`
- `SENTRY_DSN` com `sync: false`, então o valor não está no arquivo

Em produção a API recusa subir sem um `DOWNLOAD_TOKEN_SECRET` próprio. Não coloque segredo no Git.

O domínio `api.baixa.nataliagranato.xyz` não está no `render.yaml`. Ele aparece como `NEXT_PUBLIC_API_URL` no CI. Fora do repositório, a origem real do site precisa estar em `CORS_ORIGINS`: o middleware só libera a lista configurada. Uma origem de preview da Vercel só funciona se for acrescentada nessa variável.

### Site

`web/README.md` diz que, na Vercel, o diretório raiz é `web/`. O framework do `package.json` é Next.js 16 (`next` `16.4.3`, React `19.3.0`). Não há `vercel.json` nem configuração de domínio no repositório. A origem usada pelo código é `https://baixa.nataliagranato.xyz`.

Para um build de produção do front, defina `NEXT_PUBLIC_API_URL`. O CI usa `https://api.baixa.nataliagranato.xyz`. `NEXT_PUBLIC_SENTRY_DSN` continua opcional.

## Atualizar o yt-dlp

A versão fica pinada em `api/requirements.txt`. O comentário desse arquivo pede para trocar a versão, rodar os testes e subir de novo. O front não importa o yt-dlp.

Na raiz do repositório, com o ambiente virtual ativo:

```bash
pip index versions yt-dlp
# edite a linha yt-dlp==... em api/requirements.txt
pip install -r api/requirements.txt
cd api && pytest
```

O extrator é chamado sem `cookiefile`, sem `username`, sem `password` e sem cache em disco. Na busca, `skip_download` fica ligado. `noplaylist` fica ligado só para host YouTube.

## Contribuir

Não há guia de contribuição nem licença no repositório. O CI é a verificação automática: em `api/`, `ruff check`, `ruff format --check` e `pytest`; em `web/`, `npm ci`, `npm run lint`, `npm run build` e `npm run typecheck`.

Mantenha os testes sem rede. O fixture global já bloqueia socket; um teste novo não deve chamar Instagram, TikTok, X, YouTube nem outro host de verdade.

Não commite `.env`, `.env.local` nem o valor de `DOWNLOAD_TOKEN_SECRET`. O segredo de produção é gerado no Render, fora do Git.

## Texto do próprio site

O título em `web/app/layout.tsx` é "Baixa.ai — baixar mídia pública". A descrição é: "Cole um link do Instagram, TikTok, X ou YouTube e baixe fotos, vídeos e MP3. Grátis, sem anúncios e sem login."

O rodapé em `web/app/page.tsx` diz:

> Uso pessoal. Respeite os direitos autorais e os termos do Instagram, do TikTok, do X e do YouTube. O Baixa.ai não pede a sua senha e não armazena os arquivos: o download passa pelo servidor e segue direto para o seu aparelho.
