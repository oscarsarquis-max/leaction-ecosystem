# SEGSENSE_URL_001 — Contrato funcional da captura, extração, revisão e retenção

## Controle

| Campo | Valor |
|---|---|
| Identificador | SEGSENSE_URL_001 |
| Versão | 1.1 |
| Data | 15/09/2026 |
| Prompt | SEGSENSE_PRM_020_COR_001 |
| Situação | Executado nesta etapa; não autoaprovado |

## Decisões de versionamento

- Satellite Contract **1.1 permanece intacto**. Proveniência `URL_EXTRACTED` exige **Satellite 1.2**, compatível e opt-in. Jornadas governadas/residenciais continuam em 1.0/1.1.
- Identificador `SEGSENSE_DAT_006` já descreve a V12 de DemonstrationStory. Snapshots de URL estão em **`SEGSENSE_DAT_007`**. V1–V16 não são reescritas; captura usa **V17**.
- Capability agrícola demonstrativa: `DISCOVER_SYNTHETIC_CROP_PROTECTION_PATHS`. Sem prêmio, cobertura, seguradora ou produto. Não é Icatu.
- Extrator desta fatia: `URL_EXTRACTOR_V2` (conteúdo principal + janela local `LOCAL_WINDOW_V1`). `URL_EXTRACTOR_V1` permanece apenas como histórico do PRM_020.

## Matriz operacional

Cada seta: executor → evidência persistida → erro possível → dado que atravessa a fronteira.

### URL digitada → validação

- **Executor:** navegador (campo “URL pública”) + BFF `POST /api/v1/public/demo/url-captures`.
- **Evidência:** tentativa correlacionada (`correlationId`); em falha, `result_code` persistido quando a URL chega ao servidor.
- **Erros:** vazia; malformada; esquema ≠ `http`/`https`; userinfo; porta não permitida (MVP: 80 e 443); comprimento excessivo.
- **Fronteira:** string da URL, sem cookies do visitante.

### validação → resolução DNS

- **Executor:** SegSense (`HostResolver` injetável). Navegador não resolve para captura.
- **Evidência:** host solicitado (sanitizado); não persiste lista de IPs privados observados.
- **Erros:** `DNS_BLOCKED` (falha de resolução, host sem endereço público, loopback, link-local, privado, multicast, unspecified, metadata/cloud, IPv4-mapeado em IPv6).
- **Fronteira:** hostname canônico.

### resolução DNS → conexão/redirect

- **Executor:** SegSense (`SafeUrlFetcher`). `followRedirects=NEVER`; no máximo N saltos (padrão 3); revalidação completa em cada `Location`.
- **Evidência:** URL solicitada vs URL final; quantidade de saltos.
- **Erros:** `REDIRECT_BLOCKED` (salto inseguro, excesso, Location opaca); `TIMEOUT`; destino rebinding (conjunto de IPs muda ou torna-se bloqueado entre duas resoluções).
- **Fronteira:** método GET, `User-Agent` genérico da demo, `Accept` textual. Sem `Authorization`, cookie, token, referer sensível ou IP do visitante.

### conexão/redirect → resposta HTTP

- **Executor:** transporte TLS/HTTP do SegSense. TLS inválido não é ignorado.
- **Evidência:** `http_status`, `content_type`.
- **Erros:** `HTTP_ERROR` (4xx/5xx); `UNSUPPORTED_CONTENT` (MIME fora de `text/html`, `application/xhtml+xml`, `text/plain`); `TIMEOUT`.
- **Fronteira:** cabeçalhos de conteúdo, sem cabeçalhos internos da stack.

### resposta HTTP → bytes recebidos

- **Executor:** leitura em stream com corte (`max-bytes`, padrão 1048576 / 1 MiB).
- **Evidência:** `bytes_sha256` dos bytes efetivamente lidos (cortados, se houver corte).
- **Erros:** `TOO_LARGE` se `Content-Length` ou bytes lidos excedem o limite.
- **Fronteira:** buffer limitado; HTML bruto **não** vai à UI nem ao Git.

### bytes recebidos → extração

- **Executor:** `URL_EXTRACTOR_V2` (texto inerte; sem JS remoto, sem headless). Bytes integrais → `bytes_sha256`. Seleção principal (`main`/`article`/`role=main`/`#mw-content-text`/`#bodyContent`/`#content`; fallback `STRIP_CHROME_BODY_FALLBACK`). Texto normalizado do principal → `text_sha256`.
- **Evidência:** título, idioma se detectável, estratégia de seleção, texto principal, `text_sha256`, elementos com regra, offsets e trecho de evidência na **mesma janela de parágrafo** do evento.
- **Erros:** `NO_MEANINGFUL_TEXT` se o principal não for isolável com confiança mínima; não usa chrome (nav, login, sumário) como texto de revisão; não inventa autoria, data de publicação ou associação distante.
- **Fronteira:** texto principal truncado para persistência; cultura/região/período só com relação local ao evento.

### extração → snapshot

- **Executor:** persistência V17 `demo_url_capture` (append-only de linha; sem UPDATE do texto).
- **Evidência:** registro imutável da captura (hashes, URLs, horário UTC, resultado).
- **Erros:** persistência indisponível (falha visível; sem sucesso vazio).
- **Fronteira:** `captureId` opaco.

### snapshot → revisão humana

- **Executor:** UI pública. Mostra título, domínio, URL final, captura UTC, **texto principal** (não menus), cartões com origem, trecho e ação de remover/corrigir.
- **Evidência:** o que a pessoa viu é o trecho persistido do conteúdo principal; nenhum HTML remoto.
- **Erros:** captura falhou — estado visível, sem chamar Spider; isolamento falhou — pedir colar trecho.
- **Fronteira:** JSON de revisão sem markup.

### revisão humana → contexto confirmado

- **Executor:** `POST .../url-captures/{id}/confirmations` com `confirmedKeys`. Validação server-side: `URL_EXTRACTED` só se existir no snapshot, com evidência/offsets e extrator versionado.
- **Evidência:** `demo_url_capture_confirmation` append-only. Correções = contribuição futura `USER_DECLARED`; original `URL_EXTRACTED` permanece no snapshot mesmo se removido da confirmação.
- **Erros:** captura inexistente; captura sem texto significativo; tentativa de confirmar resultado de falha; atributo não sustentado é omitido, não vira fato da fonte.
- **Fronteira:** `confirmationId` + elementos confirmados sustentados.

### contexto confirmado → intenção

- **Executor:** pessoa, campo livre, independente da URL.
- **Evidência:** texto de intenção só no pedido da jornada (não vira tema da captura).
- **Erros:** intenção vazia ou não compreendida — Spider não é chamada.
- **Fronteira:** intenção `USER_DECLARED`.

### intenção → Spider

- **Executor:** BFF `POST /api/v1/public/demo/protection-journeys` somente com `captureId` confirmado + intenção suficiente. Envelope Satellite **1.2**.
- **Evidência:** jornada V13+; fingerprint v4 inclui `captureId`/`confirmationId`/`textSha256`.
- **Erros:** contexto não confirmado; mistura indevida com simulador residencial (ambiguidade).
- **Fronteira:** contribuições `URL_EXTRACTED` + intenção; hashes/referência; **não** `SATELLITE_GOVERNED`; **não** `scenarioKey` como esconderijo de texto.

### Spider → capability

- **Executor:** `DemoSliceRules`. Quebra de safra + intenção de entender opções → `DISCOVER_SYNTHETIC_CROP_PROTECTION_PATHS`. Residencial permanece `GENERATE_SYNTHETIC_HOME_QUOTE`. Sem capability → `NO_COMPATIBLE_CAPABILITY` (200, sem provider).
- **Evidência:** `capabilityId` na decisão.
- **Erros:** tema agrícola + `SIMULATE_HOME_QUOTE` → `AMBIGUOUS` (não cai no residencial).
- **Fronteira:** `scenarioKey` = `sourceId|objective` (ids curtos, não o artigo).

### capability → provider

- **Executor:** Spider → mock via Provider Contract. SegSense **não** chama o mock.
- **Evidência:** `providerRequestId` (`preq-…`); `recentExecutions` no health do mock.
- **Erros:** provider down → `PROVIDER_UNAVAILABLE`; sem cartão anterior na UI.
- **Fronteira:** inputs minimizados (`scenarioKey`); sem HTML da página; sem R$ agrícola.

### provider → possibilidades exibidas

- **Executor:** UI renderiza **somente** itens do `resultSummary` desta execução.
- **Evidência:** `mockResultId` / `providerReference`; códigos e títulos iguais aos do mock.
- **Erros:** canônico incompleto se READY sem retorno do mock.
- **Fronteira:** cartões demonstrativos; sem hardcode no SegSense.

## Resultados de captura

`FETCHED` · `UNSUPPORTED_CONTENT` · `TOO_LARGE` · `TIMEOUT` · `DNS_BLOCKED` · `REDIRECT_BLOCKED` · `HTTP_ERROR` · `NO_MEANINGFUL_TEXT` · `INVALID_URL`

Códigos ficam em detalhes técnicos. Superfície pública usa linguagem humana (`SEGSENSE_FUN_005`). Threat model: `SEGSENSE_SEC_005`.

## Retenção e minimização (MVP)

- Não persistir HTML bruto nem scripts.
- Persistir texto normalizado truncado (32 KiB), trecho de revisão (2 KiB), hashes SHA-256, URLs (podem conter identificadores — retenção **7 dias** documental; sem job automático nesta fatia).
- Logs: host + `result_code` + `correlationId`; sem corpo; sanitizar quebras de linha.
- Segredos encontrados na página não são gravados nem devolvidos (redação de padrões `Authorization`, `api_key`, `Bearer`).

## Exemplos governados

Permanece `POST /context-sources/resolve` só para URLs do registro local. Falha de URL pública **não** seleciona exemplo governado.
