# BLOG-001 — Retorno

Data: 08/11/2026. Somente leitura. Nada foi alterado na Loja, na Gestão, no ActionHub, no Caddy, no DNS ou nos bancos. Sem commit.

O LePain · Bread & Sense é uma aplicação nova em `C:\Projetos\lojadepaes-blog`, com contêiner próprio no mesmo Lightsail e o host `lepain.lojadepaes.com.br`. O blog só lê o CMS do ActionHub.

## 1. O CMS de posts hoje

Tabela `cms_posts` no banco `leaction_hub` (`leaction-platform/shared/database/patch_cms_headless.sql`). A capa passou de `VARCHAR(255)` para `TEXT` em `patch_cms_site_config.sql`, porque a URL do S3 não cabia. `cms_site_config` é outro recurso (a landing em JSON) e não guarda post.

| Campo | Papel |
|---|---|
| `id` | serial |
| `slug` | único no mundo (`uq_cms_posts_slug`), até 255 caracteres; a API normaliza e corta em 240 |
| `titulo` | até 255 |
| `resumo` | texto curto do card; um só |
| `conteudo_html` | corpo inteiro |
| `imagem_capa` | uma URL |
| `sistema_destino` | `hub-publico`, `actionhub`, `inove4us`, `paneldx`, `todos` |
| `status` | `rascunho` ou `publicado` |
| `publicado_em` | preenchido na primeira publicação; permanece se o post volta a rascunho |
| `criado_em` | criação |

Não há `atualizado_em`, idioma, seção, vínculo entre traduções, sentidos, segundo resumo, tipo, data de evento nem validade.

O formulário Novo Post (`CmsPostForm.tsx`) grava esses campos. O rótulo do corpo é "HTML / Markdown", o placeholder é HTML, e o painel do ActionHub injeta `conteudo_html` como HTML. Não há conversor de Markdown nem editor de blocos. Markdown digitado na caixa aparece como texto. A capa é uma imagem, campo de upload `imagem`.

Upload (`cms-upload.js`): `POST /api/admin/cms/upload` (também `/admin/cms/upload` e `/api/admin/upload`), JWT de admin, arquivo no campo `imagem`. Só entra o que o navegador declara como `image/*`, até 5 MB. Vídeo e áudio são recusados. Com `CMS_S3_BUCKET`, o objeto vai para o S3 (`CMS_S3_PREFIX` padrão `cms`, região `CMS_S3_REGION` ou `AWS_REGION`, URL pública `CMS_S3_PUBLIC_URL` ou a URL do bucket). Sem bucket, o arquivo fica em `cms-uploads/images` e é servido em `GET /images/:filename`. A resposta é `{ success, url, public_url, storage }`.

Leitura pública: `GET /api/cms/posts?sistema_destino=&limit=`. Sem autenticação. O gateway usa CORS aberto (`cors()` sem lista de origens). A resposta não manda `Cache-Control`. O filtro é `status = publicado` e, se o destino vier na query, `sistema_destino` igual ao pedido **ou** `todos`. Ordem: `publicado_em` desc, depois `criado_em` desc. `limit` padrão 20, máximo 100. Não há página, nem busca por slug, nem filtro por idioma. Rascunho não sai. A escrita (`POST`/`PUT` e a listagem admin) exige JWT.

O exemplo que já existe é `leaction-platform/examples/cms-consumer-noticias.py` (e o espelho `.js`), o consumidor Flask do PanelDX, no mesmo desenho do Inove4us. Ele chama o gateway com `sistema_destino` e `limit`, guarda a lista na memória por 480 segundos (`CMS_CACHE_TTL_SEC`) e, se o Hub falhar, devolve a cópia anterior. O próprio ActionHub lê `GET /api/cms/posts?sistema_destino=actionhub&limit=4` com `cache: 'no-store'` e mostra título, resumo e o HTML. O middleware do frontend deixa passar `/hub-api/api/cms/posts` mesmo com o site em manutenção.

## 2. O que falta para o LePain

Dá para fazer com o que existe, sem migração:

- Um ensaio em um idioma: título, slug próprio, resumo do card, capa e corpo HTML.
- No HTML: imagem, galeria (várias imagens), citação (`blockquote`), link, e vídeo ou áudio **por endereço** (`video`, `audio` ou um link). O blog, ao renderizar, aceita só essas marcas; o resto do HTML não é executado.
- Desenho, se for uma imagem já enviada.
- Ignorar, no blog, as linhas `sistema_destino = todos`. A API mistura `todos` em todo filtro. Sem esse descarte, o que for "Todos os sistemas" apareceria no LePain.

Exige mudança no Hub (não feita):

- Destino `lepain` no `CHECK`, no conjunto `DESTINOS` da API e no select do formulário. Hoje um valor fora da lista é rejeitado. Usar `todos` publicaria o post em todos os satélites.
- `secao`: `insights` ou `right_now`.
- `idioma` (`pt` ou `en`) e `grupo_id` ligando as duas versões. O slug continua único e diferente em cada idioma. A unicidade passa a ser `(grupo_id, idioma)`.
- `sentidos`: um ou mais entre olhar, toque, aroma, sabor, som, memória.
- `resumo_instagram`, separado de `resumo`.
- No Right Now: `right_now_tipo` (`promocao`, `evento`, `noticia`), `data_evento` e `valido_ate`. Ficam nulos em Insights. `publicado_em` não serve de data do evento.
- Leitura: `GET` por slug e filtros `secao` e `idioma`, com paginação. A lista atual para em 100.
- Arquivo de vídeo ou áudio: outro upload, outro limite e outro tipo. O S3 já guarda objeto; o que barra é o filtro `image/*` e os 5 MB. Até lá, vídeo e áudio entram por link dentro do HTML.

Proposta mínima, só escrita aqui:

```sql
ALTER TABLE cms_posts DROP CONSTRAINT chk_cms_posts_destino;
ALTER TABLE cms_posts ADD CONSTRAINT chk_cms_posts_destino CHECK (
  sistema_destino IN ('hub-publico','actionhub','inove4us','paneldx','todos','lepain')
);
ALTER TABLE cms_posts
  ADD COLUMN secao VARCHAR(20) NULL,
  ADD COLUMN idioma VARCHAR(2) NULL,
  ADD COLUMN grupo_id INTEGER NULL,
  ADD COLUMN sentidos TEXT[] NULL,
  ADD COLUMN resumo_instagram TEXT NULL,
  ADD COLUMN right_now_tipo VARCHAR(20) NULL,
  ADD COLUMN data_evento DATE NULL,
  ADD COLUMN valido_ate DATE NULL;
```

Mais as checagens de valor, o índice único `(grupo_id, idioma)` e o `grupo_id` apontando para o post irmão. O corpo continua HTML. Não criar tabela de blocos neste passo.

## 3. Renderização e SEO

A Gestão é um SPA Vite servido pelo FastAPI. O Caddy dela manda `X-Robots-Tag: noindex, nofollow`. Isso serve um painel fechado e não serve um blog.

| Caminho | HTML que o buscador e o WhatsApp recebem | Quando o CMS muda |
|---|---|---|
| SPA Vite, como a Gestão | A casca vazia. Título, `hreflang` e Open Graph nascem no navegador. Redes sociais não executam essa página. | A página pede o Hub de novo. O índice não enxerga o texto. |
| Vite com pré-render | Um HTML por URL, bom para `hreflang`, sitemap e Open Graph. | O Hub não avisa ninguém. O post novo só existe depois de outro build e outra imagem. |
| SSR no FastAPI | Cada URL já sai com título, resumo, `hreflang`, canônico e Open Graph. | O processo lê o Hub de novo. Não há rebuild. |

Recomendação: SSR no FastAPI, na mesma família da Gestão (FastAPI, imagem, compose, Caddy), com as páginas em HTML de verdade. Rotas `/pt/insights/{slug}`, `/en/insights/{slug}`, `/pt/right-now/{slug}`, `/en/right-now/{slug}`. Em cada página:

- `link rel="alternate" hreflang="pt"` e `hreflang="en"` para as duas slugs do `grupo_id`, e `hreflang="x-default"` na versão em português;
- `sitemap.xml` com as mesmas alternâncias;
- Open Graph por post: título, `resumo` na descrição, `imagem_capa`, `og:locale` `pt_BR` ou `en_US`, URL canônica.

O Hub não envia webhook e não manda `Cache-Control`. O blog guarda a lista em memória por poucos minutos (o exemplo dos satélites usa 8) e, se o Hub falhar, mostra a última cópia boa. Um post publicado aparece na próxima leitura, sem nova imagem e sem mexer no Caddy. Imagem nova só quando mudar código ou fonte. Um webhook no Hub fica para um ciclo posterior.

## 4. Publicação

A Gestão subiu assim (GESTAO-002), sem recriar a Loja:

- Imagem própria, compose próprio (`name: lojadepaes-gestao`), rede externa `infra_default`.
- Serviço `gestao-api`, porta só na rede (`expose` 8090), `mem_limit` 256m, `cpus` 0.75, sistema de arquivos só leitura.
- `deploy/caddy-add.sh` acrescenta o bloco no **final do mesmo arquivo** montado em `infra-caddy-1` (`/opt/lojadepaes/app/infra/Caddyfile`), valida e faz `caddy reload`. Não troca o inode e não reinicia o contêiner do Caddy. `caddy-remove.sh` apaga só o trecho entre os marcadores.
- DNS na Route 53: um `A` de `gestao.lojadepaes.com.br` para a instância, TTL 300.

O mesmo para o LePain, quando houver autorização. Contêiner `lepain` no projeto `lojadepaes-blog`, rede `infra_default`, `expose` 8091, limite 256 MB e 0,5 CPU. O bloco do Caddy **não** leva `noindex`. Acrescentar com o mesmo método (cópia, `>>`, validar, reload, desfazer se a validação falhar). O `A` de `lepain.lojadepaes.com.br` aponta para a mesma instância. Não publicar porta no host, não recriar `infra-caddy-1`, `infra-api-1`, `infra-db-1` nem `gestao-api`. O blog não abre o banco da Loja; só chama o `GET` público do Hub.

Desfazer: o script irmão apaga só o trecho `>>> lepain` … `<<< lepain` e recarrega o Caddy; `docker compose stop` e `rm` apenas do `lepain`; apagar o `A` na Route 53. A Loja e a Gestão seguem.

Instância `lojadepaes-app`, região `us-east-2`, estado `running`, plano `small_3_0`: 2 GB de RAM, 2 vCPU, disco de sistema de 60 GB. Nas horas lidas em 08/11, a CPU ficou em torno de 2% de média; o maior ponto da janela foi 13,7% em 07/11 às 11h.

A API do Lightsail não informa memória livre nem disco livre. A última medição **no host** é de 02/11, no GESTAO-002: cerca de 985 MB disponíveis (de 1906 MB) e 22 GB livres. Não é a folga de hoje. Cabe o limite proposto (256 MB e 0,5 CPU) no tamanho do plano, e a CPU medida está folgada. Antes de criar o contêiner, medir de novo no host e só seguir se a memória disponível passar de 500 MB e o disco livre passar de 3 GB, o mesmo portão da Gestão.

Bloco proposto:

```
# >>> lepain >>>
lepain.lojadepaes.com.br {
	encode gzip
	header {
		Referrer-Policy no-referrer
		X-Content-Type-Options nosniff
		Strict-Transport-Security "max-age=31536000"
	}
	reverse_proxy lepain:8091
}
# <<< lepain <<<
```

## 5. Card do Instagram

O PNG é 1080×1350, a partir de `resumo_instagram` (enquanto o campo não existe, de `resumo`). Uma rota `/{idioma}/card/{slug}` entrega a página já no tamanho, com as fontes locais, `noindex`, e um botão "Baixar PNG" que desenha o quadro num canvas depois que as fontes carregaram. Três saídas: português, inglês, ou as duas faixas no mesmo quadro (as duas linhas do `grupo_id`). A publicação continua manual.

Gerar o PNG no servidor (Pillow ou um navegador dentro do contêiner) fica para quando o desenho estabilizar. Pillow já resolve texto simples; o cartaz com Fraunces e Caveat Brush quebra fácil em texto de tamanho variável. A página no navegador usa as mesmas fontes do blog e não coloca outro processo no Lightsail.

No futuro, a API do Meta pede: conta profissional do Instagram ligada a uma Página do Facebook; app com a Instagram Graph API e os usos `instagram_content_publish` (e a leitura da conta e da Página); token de longa duração; a imagem numa URL pública que a Meta consiga buscar; criação do contêiner de mídia (`image_url` e legenda) e, em seguida, a publicação desse contêiner. O retrato 1080×1350 está na proporção 4:5 aceita. Nada disso é ligado agora.

## 6. Estrutura proposta

Ainda não criada, fora desta pasta `docs/retornos`.

```
C:\Projetos\lojadepaes-blog\
  .gitignore
  app\
    main.py
    templates\
    static\
      fonts\          Fraunces, Literata, Caveat Brush, Syne (woff2)
      site.css
  deploy\
    Dockerfile
    docker-compose.prod.yml
    .env.example
    caddy\lepain.caddy
    caddy-add.sh
    caddy-remove.sh
  docs\
    retornos\
```

`.gitignore`: `.env`, `deploy/.env`, `__pycache__/`, `.venv/`, `*.pyc`, `.DS_Store`, `dist/`.

As quatro fontes são servidas pelo próprio site (`@font-face` para os arquivos em `app/static/fonts`). Sem pedido ao CDN do Google. Os arquivos (licença OFL) entram num ciclo seguinte, junto com o código. Não foram baixados aqui.

## Comandos executados

```
aws lightsail get-instance --region us-east-2 --instance-name lojadepaes-app
aws lightsail get-instance-metric-data --region us-east-2 --instance-name lojadepaes-app --metric-name CPUUtilization --period 3600 --start-time 2026-11-07T12:00:00Z --end-time 2026-11-08T13:00:00Z --unit Percent --statistics Average Maximum
```

Leitura de arquivos do CMS, do exemplo PanelDX, do Caddyfile da Loja e de `caddy-add.sh`, `caddy-remove.sh`, `gestao.caddy` e `docker-compose.prod.yml` da Gestão. Nenhum SSH, nenhum SQL, nenhum reload.

## Comandos propostos (não executados)

Medir a folga no host, pelo caminho já usado na Gestão, e parar se não passar do portão:

```
free -m
df -h /
```

Migração do Hub: o `ALTER TABLE` da seção 2, mais `lepain` na API e no formulário, e os filtros de leitura. Não rodar neste ciclo.

Publicar, só com autorização, sem recriar Loja nem Gestão:

```
# Route 53: A lepain.lojadepaes.com.br -> a mesma instância, TTL 300
# no host, depois da imagem carregada:
cd /opt/lojadepaes-blog
sudo -n docker compose --env-file deploy/.env -f deploy/docker-compose.prod.yml up -d
# acrescenta só o bloco lepain e recarrega o Caddy
bash deploy/caddy-add.sh
```

Desfazer:

```
bash deploy/caddy-remove.sh
sudo -n docker compose -f deploy/docker-compose.prod.yml stop lepain
sudo -n docker compose -f deploy/docker-compose.prod.yml rm -f lepain
# apagar o A de lepain.lojadepaes.com.br na Route 53
```
