# ACTIONFINANCE_REV_REVISAO_CADASTROS_012

Identificador: ACTIONFINANCE_REV_REVISAO_CADASTROS_012. Data: 05/10/2026. Revisão independente do prompt 012. Não altera o prompt 011. Aceite e publicação permanecem com analista/proprietário. Nenhuma migration ou importação foi aplicada no RDS público.

## R1 Estado real e reversão

### Achado

O pacote 011 afirmava «RDS público permanece em V12 (V13 ainda não migrada)». Isso contradiz o ADENDO_003 e o histórico Flyway lido neste ciclo.

### Correção / decisão

Levantamento somente leitura em 05/10/2026 via ECS Fargate `actionfinance-dbadmin`, sem expor credenciais.

| Campo | Valor |
|---|---|
| Conta | `253137917703` |
| Região | `us-east-2` |
| Instância | `actionfinance` |
| Host | `actionfinance.czqyam2auctn.us-east-2.rds.amazonaws.com` |
| Banco | `actionfinance` |
| Motor | PostgreSQL 17.9, status `available` |
| Script | `scripts/ops/inspect-flyway-readonly-012.ps1` |
| `query_exit` | 0 |

Versões com `success=true` no destino efetivo (checksum e `installed_on`):

| Versão | Checksum | Aplicada em (UTC do RDS) |
|---|---|---|
| 1 | 1488219560 | 2026-09-30 14:10:45 |
| 2 | -1679030834 | 2026-09-30 14:10:46 |
| 3 | 759528725 | 2026-09-30 14:10:47 |
| 4 | -1274852429 | 2026-09-30 14:10:47 |
| 5 | 649129189 | 2026-09-30 14:10:48 |
| 6 | -1262827641 | 2026-09-30 14:10:48 |
| 7 | 1132211541 | 2026-09-30 14:10:48 |
| 8 | -1867401097 | 2026-10-01 20:35:38 |
| 9 | -1848166565 | 2026-10-01 20:35:39 |
| 10 | -886612604 | 2026-10-01 20:35:39 |
| 11 | 746826402 | 2026-10-01 20:35:40 |
| 12 | -1191140435 | 2026-10-01 20:35:40 |
| 13 | 728072343 | 2026-10-02 11:59:32 |

`has_v13=true`. `has_v14=false`. `has_v15=false`. V16–V18 não existem no origin. A consulta `max(version)` textual devolveu `9` (ordem lexicográfica de VARCHAR); a evidência útil é `installed_rank` / a linha 13. `count(*)` de `financial_title` no origin nesta leitura: **0**.

V14/V15 **não** foram editadas. A correção de integridade é incremental: V16 (FK composta, claim, `connection_key` NOT NULL, FK do match), V17 (grants do claim), V18 (idempotência da linha de importação no lote).

### Rollback

Prioridade: recolher a imagem anterior. V14–V18 só acrescentam colunas/tabelas com default; `POST /catalogs/counterparties {name,role}` e `GET ?compatibleWith=` continuam válidos. Restore do origin **não** está autorizado. Se um restore for pedido depois: interrupção controlada, janela/RPO, captura de escritas posteriores, restore primeiro em banco isolado, reconciliação, só então troca de destino.

`PartyDirectoryIT` cria o próprio Testcontainer e **não** prova cópia restaurada. O ensaio de cópia é `scripts/ops/rehearse-isolated-upgrade-012.ps1` (recusa host RDS público; exige JDBC isolado). `PartyDirectorySchemaUpgradeIT` é upgrade descartável V1→V18, também em container, com a mesma ressalva.

### Prova

Inspect ECS `query_exit=0` em 05/10/2026 ~15:32 UTC. Schema IT e PartyDirectoryIT verdes em Testcontainer (abaixo). Script de ensaio recusou o host público e aceitou `127.0.0.1:55432` em `-CompareOnly` sem migrate.

### Limitação

Não houve restore isolado com dump real do origin neste prompt. `titles=0` no RDS público não foi investigado além da contagem lida. Imagem vigente permanece `actionfinance-web:11`. Postgres local desta máquina aplicou V13–V18 só no volume `actionfinance_pgdata_17` — não é o origin.

## R2 Documento fiscal

### Achado

`DocumentNumbers` aceitava CNPJ por `[A-Z0-9]{14}` e CPF por comprimento 11, sem DV. Normalização removia qualquer não-alfanumérico.

### Correção / decisão

Validação oficial: CNPJ 12 alfanuméricos + 2 DVs numéricos (valor = ASCII−48; pesos RFB). CPF 11 dígitos, módulo 11, rejeita repetidos. Vetor oficial `12.ABC.345/01DE-35`. Somente pontuação de apresentação `[.\\-/\\s]`. OTHER 1–32; no BR, 11 dígitos ou 14 com forma de CNPJ não podem ser OTHER. CPF só BR + pessoa física; CNPJ só BR + pessoa jurídica. Sem documento continua permitido. Documento inválido é erro de campo, não aparece como validado. Validade matemática ≠ existência/titularidade.

### Prova

`DocumentNumbersTest`: 3 testes, 0 falhas. Recusa `12*ABC`, DV letra, `12.ABC.345/0001-95`, CPF `111.111.111-11`, CNPJ em pessoa física e CPF em jurídica. `PartyDirectoryIT.rejectsInvalidDocumentAndCrossPartyUnitAddress` devolve 400 para CNPJ inválido.

### Limitação

Não consulta Receita/Serpro. OTHER fora do BR não tem algoritmo nacional neste recorte.

## R3 Integridade entre fornecedor, unidade e endereço

### Achado

V14 ligava endereço a `counterparty_id` e `unit_id` por FKs separadas: mesma empresa, não necessariamente a mesma pessoa.

### Correção / decisão

V16: UNIQUE `(tenant,company,counterparty,id)` na unidade; FK composta do endereço `(tenant,company,counterparty,unit_id)` → unidade. Serviço recusa `unitId` de outra pessoa. `match_counterparty_id` ganhou FK composta à contraparte. Claim de documento é a autoridade na empresa.

### Prova

API: `rejectsInvalidDocumentAndCrossPartyUnitAddress` — endereço da pessoa A com unidade da pessoa B na mesma empresa → 400 `addresses[0].unitId`. Banco: `PartyDirectorySchemaUpgradeIT` tenta o INSERT equivalente e a FK rejeita. Isolamento entre empresas permanece nos ITs de viewer B.

### Limitação

Endereço sem `unit_id` continua permitido (MATCH SIMPLE). Não foi feito teste de exploração pública.

## R4 Unicidade e identidade externa

### Achado

`connection_key` nullable + UNIQUE convencional: dois nulos não colidem. Documento de pessoa e de unidade em índices separados; unidade excluía inativas.

### Correção / decisão

`connection_key` NOT NULL DEFAULT `''`. Ausência de conexão é a chave vazia, não NULL. Claim cobre pessoa, unidade (inclusive inativa persistida) e espelho explícito (`mirrored=true`) só na unidade principal da mesma pessoa. Sem fusão automática por nome ou raiz. Filial permanece unidade; títulos continuam apontando à pessoa, e a unidade específica precisa ser gravada no cadastro para não se perder na origem. PATCH legado `name/active` usa `coalesce` e não zera documento/`personKind`.

### Prova

IT: claim bloqueia outra pessoa com o mesmo CNPJ e permite espelho na principal; duas inserções com `connection_key` ausente (`''`) → 409; duas concorrentes com `connectionKey=conn-012` → 1×200 + 1×409; PATCH legado preserva `33.000.000/0001-40` e `LEGAL`; viewer vê `••••40` em candidatos. Schema IT: segunda identidade `FILE`+`''`+mesmo `external_id` viola UNIQUE.

### Limitação

Índice único da unidade ativa permanece o de V14; a autoridade cruzada é o claim. Não há conector Panne. Agregar a pessoa não substitui identificar a filial no título/compra futuros — decisão de modelo a registrar antes dessa integração.

## R5 Provas de interface e importação

### Achado

Reuso de CSS não prova jornada. Hash do arquivo sozinho resume só `PREVIEW`. Linha só com nome não pode fundir.

### Correção / decisão

Prévia do mesmo hash só enquanto `PREVIEW`. Após `CONFIRMED`, reenvio é lote novo (V18 + chave `batchId:sha:line`). Homonímia sem documento → `DUPLICATE` desmarcada, mensagem de revisão. Versão da prévia divergente → `REJECTED` «mudou desde a prévia». Documento mascarado na lista, candidatos, detalhe (consulta), linhas de importação e campo de documento do viewer. Frontend mostra coluna Documento da prévia já mascarada.

### Prova — testes

Ambiente: Windows, Java 21.0.12, Maven Surefire 3.5.2, Testcontainers PostgreSQL 17.6, perfil `local-demo`. Comando: `mvnw -Dtest=DocumentNumbersTest,PartyDirectoryIT,PartyDirectorySchemaUpgradeIT test`. **Exit 0.**

| Classe | Testes | Falhas | Erros | Tempo (s) |
|---|---|---|---|---|
| `DocumentNumbersTest` | 3 | 0 | 0 | 0,105 |
| `PartyDirectoryIT` | 13 | 0 | 0 | 16,698 |
| `PartyDirectorySchemaUpgradeIT` | 1 | 0 | 0 | 5,313 |
| **Total** | **17** | **0** | **0** | — |

Frontend: Vitest 4.1.11 + jsdom, `CounterpartiesPages.test.tsx`, **2 testes, exit 0**.

IT cobre: cadastro mínimo/sem documento, duplicidade, concorrência de documento, inativação com título, isolamento/viewer, importação por linha + idempotência do lote, endereço cruzado, claim/espelho, PATCH legado + máscara, identidade externa vazia e com conexão (concorrente), reenvio após confirmação, prévia obsoleta.

### Prova — interface local

Backend/Postgres locais em `127.0.0.1:8091` / `:5179` / `:5439` após `start-local` (Flyway local V13–V18 no volume de desenvolvimento; **não** é o RDS). Script `frontend/scripts/capture-cadastros-012.mjs` contra `http://127.0.0.1:5179` (não usar a preview `:4179`, que ainda serve o bundle antigo). **24 PNGs** em 05/10/2026, dados sintéticos, evidência em `documents/reviews/evidence/revisao-cadastros-012/capturas.json`.

| Largura | Telas |
|---|---|
| 360, 768, 1280 | lista, cadastrar sem busca, incompleto, completo/detalhe, duplicidade, importação com 1 inválido, lista em consulta |

Lista nova: busca, **Importar arquivo**, **Cadastrar**, «Documento pendente», relação em português. Viewer sem botões de escrita. Importação: «1 inválidos», gravação por linha, XLSX recusado no texto. Sem dado pessoal produtivo.

### Limitação

A preview `:4179` (bundle `index-BE46S7oG.js`) ainda mostra o formulário mínimo antigo; não é a candidata 012. Cadastro rápido no título não foi recapturado nesta jornada (compatibilidade coberta pelo IT `POST /catalogs/counterparties`). A tabela da prévia no recorte 768 ficou abaixo do resumo na captura. Aceite visual continua com o analista. Sem apply/import no origin.

## Entrega e o que este ciclo não faz

Candidata local: V14–V18 no repositório; API/serviço/IT revisados; prompt 012 em `documents/prompts`. Pacote 011 atualizado com esta evidência, histórico do erro V12 preservado. Aceite **não** atribuído. Sem migration/importação no RDS, sem Panne, sem pagamento, sem alteração Pay/Spider. Demais ciclos permanecem separados.
