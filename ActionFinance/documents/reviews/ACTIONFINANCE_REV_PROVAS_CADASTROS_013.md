# ACTIONFINANCE_REV_PROVAS_CADASTROS_013

Identificador: ACTIONFINANCE_REV_PROVAS_CADASTROS_013. Data: 05/10/2026. Revisão independente do prompt 013. Não é adendo ao 012. Aceite e publicação permanecem com analista/proprietário. Nenhuma migration ou importação foi aplicada no RDS público.

As correções do 012 permanecem: origin em **V13** (inspect 05/10/2026), Testcontainer ≠ cópia restaurada, FKs compostas e `connection_key` NOT NULL existem, validador contém DV oficial. Os **17 testes** do 012 continuam evidência relatada por aquele executor.

## Capturas 012 que não provavam o estado anunciado

Preservadas em `documents/reviews/screenshots/revisao-cadastros-012/`. Não apagadas.

| Arquivo 012 | Por que não prova |
|---|---|
| `360-cadastro-completo.png`, `768-cadastro-completo.png`, `1280-cadastro-completo.png` | Mostram «Este documento já identifica outro cadastro nesta empresa» e permanecem em Cadastrar. Não há ID persistido nem detalhe. |
| `360-detalhe.png`, `768-detalhe.png`, `1280-detalhe.png` | O script 012 fotografou a mesma tela imediatamente após o envio, sem navegar, sem esperar resposta e sem conferir ID. |
| Demais 24 PNGs | Lista, vazio, incompleto, duplicidade, importação e consulta existem; o ensaio não falhava se o estado anunciado faltasse. |

O script 012 usava esperas fixas. `ACTIONFINANCE_UI_URL=:4179` podia servir o bundle antigo. A candidata 013 recusa `:4179` e usa `ACTIONFINANCE_LOCAL_UI_URL` padrão `http://127.0.0.1:5179`.

## R1 Prova de cadastro e detalhe

### Achado

O ensaio 012 não distinguia gravação, recarga e duplicidade. PNG sozinho era tratado como prova.

### Correção / decisão

`frontend/scripts/capture-cadastros-013.mjs` (npm `capture:cadastros-013`) em base local descartável:

1. Dados sintéticos com nome único por execução; CNPJ gerado no ato. Não apaga registro produtivo.
2. Espera POST/PUT; recusa 4xx; exige `id`.
3. Confere GET `/api/v1/catalogs/parties/{id}` (nome, documento, unidade, endereço, contato, fornecimento).
4. Abre o detalhe desse ID, volta à lista, reabre e confere de novo.
5. Duplicidade é caso separado: permanece em `/new`.
6. Cobre mínimo, completo, edição+recarga, duplicidade, somente leitura e cadastro rápido no título.
7. Falha se o estado esperado não existir.

### Teste

Java (Windows, Java 21.0.12, Maven Surefire 3.5.2, Testcontainers PostgreSQL 17.6, perfil `local-demo`):

`mvnw -Dtest="DocumentNumbersTest,PartyDirectoryIT,PartyDirectorySchemaUpgradeIT,PartyDirectoryUpgradeDataIT" test`

**Exit 0. 22 testes, 0 falhas.**

| Classe | Testes | Papel |
|---|---|---|
| `DocumentNumbersTest` | 3 | DV oficial (evidência 012 preservada) |
| `PartyDirectoryIT` | 15 | + `persistsFullPartyReloadsAfterEditAndKeepsTitleQuickCreate`; + `sameNumberDifferentCountryIsNotMirrorAndTwoPrimariesAreRejected` |
| `PartyDirectorySchemaUpgradeIT` | 1 | Schema até V19; checksum V13 `728072343`; FKs e `connection_key` |
| `PartyDirectoryUpgradeDataIT` | 3 | Dados **antes** de V14/V16; conflito com RAISE |

Frontend: Vitest `CounterpartiesPages.test.tsx`, **3 testes, exit 0**.

Captura 05/10/2026 ~17:32 UTC contra `http://127.0.0.1:5179`. Evidência: `documents/reviews/evidence/provas-cadastros-013/capturas.json`. Sem credencial e sem dado pessoal produtivo.

| ID persistido | Estado |
|---|---|
| `8735a1c2-b656-4f64-8fdc-8c5c9276252a` | Cadastro mínimo, documento pendente |
| `ae420007-a34d-4531-a9de-f5d5988c5cef` | Completo (unidade/endereço/contato/fornecimento) + edição `Fantasia 013` |
| `b990fc25-4eae-4456-887d-7d6708d3c52f` | Cadastro rápido no título, documento pendente |

Cliques ocorreram em **1280**. 360 e 768 foram fotografados após redimensionar, salvo o foco do nome em 360 (`clicked-focus-nome`). Cada cena tem `rest`, `scroll` e `full`.

### Limitação

Sessão demo é só memória: a «recarga» é voltar à lista, reabrir o ID e GET na API. `page.reload()` perderia o token. Nenhum registro produtivo foi apagado; execuções anteriores desta máquina deixaram cadastros sintéticos extras.

## R2 Acabamento e linguagem

### Achado

A captura 012 em 360 com `fullPage` mostrou faixa azul no meio do formulário e vazio superior. O desktop era uma coluna longa. Havia frases internas. Importação mostrava `INVALID`, «1 inválidos» e confirmar sempre ativo.

### Correção / decisão

Reproduzido: só `.top` é `position: sticky`. As duas barras de navegação aprovadas não são sticky. A faixa azul no `full` é costura do Playwright do cabeçalho fixo. Em **repouso** e **durante a rolagem** o cabeçalho fica no topo; o campo focado permanece abaixo (`scroll-padding-top` / `scroll-margin-top` 96px).

Identificação e endereço em grade no desktop (nome na largura útil; documento em três colunas; logradouro em linha própria). Uma coluna em ≤768px. Título, formulário e ações compartilham `max-width: 56rem`. Azul oficial e as duas barras mantidos. Sem Mais, sidebar ou menu suspenso.

Frases internas removidas. Instruções: documento opcional com formatos; endereço completável depois; CSV do modelo. Importação: `INVALID` → «Inválido»; «1 linha», «1 inválido». Confirmar indisponível sem linha elegível, com o motivo visível.

### Teste

Prévia 013 (avaliar nestes recortes, não nos PNG 012 de completo/detalhe):

| Recorte | Arquivo | O que mostra |
|---|---|---|
| 360 repouso, detalhe gravado | `360-cadastro-completo-rest.png` | Cabeçalho + duas barras; ID `CTP-ae420007-…`; sem faixa azul sobre campos |
| 360 rolagem / foco | `360-cadastro-completo-scroll.png`, `360-cadastro-completo-foco-rest.png` | Sticky só no topo; nome visível |
| 360 página longa | `360-cadastro-completo-full.png` | Costura do sticky — não é o estado em repouso |
| 1280 grade | `1280-cadastrar-vazio-rest.png`, `1280-cadastro-completo-rest.png` | Tipo/relação lado a lado; documento em três colunas |
| 360 duplicidade | `360-duplicidade-rest.png` | Permanece em Cadastrar; aviso vermelho |
| 1280 importação | `1280-importacao-erro-rest.png` | «1 inválido», célula «Inválido», confirmar desabilitado |

Vitest cobre «1 linha», «Inválido» e confirmar desabilitado.

### Limitação

Aceite visual continua com o analista. A tabela da prévia no 360 continua oculta (cards/CSS já existente); o resumo «1 inválido» é o texto visível. Local Vite `:5179`, não a preview `:4179`.

## R3 Autoridade de documentos no upgrade

### Achado

V16 usa `ON CONFLICT DO NOTHING`. Colisão pré-existente podia ser descartada em silêncio. Pessoa inserida primeiro impedia registrar o espelho da principal. Serviço/repositório podiam tratar só o número normalizado.

### Correção / decisão

V14–V16 **não** foram editadas. Correção incremental **V19**:

- `UPDATE` do claim para espelho só quando pessoa e **uma** principal compartilham país + tipo + número.
- `RAISE EXCEPTION` com diagnóstico se a união pessoa+unidade tiver mais de um `counterparty_id` para a mesma identidade.

Serviço: `sameIdentity` (país, tipo, normalizado); recusa mais de uma principal. Repositório: `UPDATE` do espelho exige identidade completa e `updated = 1`; senão `ValidationException` explícita. Número igual com país/tipo diferentes não é espelho.

### Teste

`PartyDirectoryUpgradeDataIT.backfillsClaimsFromV15WithoutSilentOwnerChoice`: pessoa só documento; unidade com documento próprio; espelho válido; unidade inativa. Após V19: cobertura, dono e `mirrored` corretos.

`refusesPreexistingDocumentConflictWithoutPickingOwner`: pessoa A + unidade de B com o mesmo CNPJ → `FlywayException` contendo `counterparty_document_claim conflito`. Sem escolha automática de dono.

`PartyDirectoryIT.sameNumberDifferentCountryIsNotMirrorAndTwoPrimariesAreRejected`: BR CNPJ `44.000.000/0001-67` + unidade US OTHER com os mesmos dígitos → 200, unidade US. Duas principais → 400 `fields.units`.

### Limitação

V16 permanece como escrita: o `ON CONFLICT DO NOTHING` histórico não foi reescrito. V19 diagnostica o que V16 calou. Postgres local desta máquina está em **V18** (lido 05/10/2026). V19 existe no repositório e no Testcontainer; **não** no origin.

## R4 Limite da prova de upgrade e reversão

### Achado

`PartyDirectorySchemaUpgradeIT` aplicava o schema e lia títulos da demo. Isso não prova preservação de linhas inseridas em V13.

### Correção / decisão

`preservesV13LinksThenAppliesDirectoryAndOldInsertStillWorks`: para em V13, insere tenant/empresa/contraparte/categoria/título, aplica V14–V19, compara ID do título, `counterparty_id`, `amount_minor=1500`, nome e `document_pending`. Depois executa `INSERT` no formato V2 (colunas antigas) contra o schema expandido — 1 linha. Isso é o ensaio de rollback de **imagem** (código antigo no schema novo), não restore.

Ensaio em cópia restaurada do origin **continua pendente**. `rehearse-isolated-upgrade-012.ps1` recusar o JDBC público ≠ executar dump restaurado. Esta revisão não restaurou, não migrou o RDS e não criou infraestrutura com custo.

### Teste

UpgradeDataIT verde no Testcontainer. SchemaUpgradeIT: latest = 19; V13 checksum `728072343`; V14–V19 presentes.

### Limitação

Testcontainer ≠ cópia do RDS. `financial_title` no origin permanecia 0 na leitura 012. Imagem pública continua `actionfinance-web:11`. Rollback de restore **não** autorizado.

## Entrega e o que este ciclo não faz

Candidata local: V19 incremental; API/serviço/repositório com identidade completa; captura 013 que falha sem estado; prompt 013 em `documents/prompts`. Pacote 011 ganha referência a 013 sem reescrever o histórico V13. Aceite **não** atribuído. Sem apply/import no RDS, sem Panne, sem pagamento, sem alteração Pay/Spider/Cognito. Demais ciclos permanecem separados.
