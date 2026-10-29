# ACTIONFINANCE_REV_FECHAMENTO_CADASTROS_014

Identificador: ACTIONFINANCE_REV_FECHAMENTO_CADASTROS_014. Data: 05/10/2026. Documento independente. Aceite e publicação **não** atribuídos. RDS público não foi migrado nem restaurado.

Provas 012/013 preservadas. Surefire 013 (15 + 1 + 3 de diretório) permanece. Este ciclo reexecutou `PartyDirectoryIT` (15), `PartyDirectorySchemaUpgradeIT` (1) e `PartyDirectoryUpgradeDataIT` (3): **19 testes, exit 0**.

## Tabela de encerramento

| Item | Resultado | Evidência |
|---|---|---|
| Importação mobile por linha | **Atendido** | Cartões em 360/768 com cliques; só a válida gravada; repetição do lote sem segundo cadastro. IDs abaixo. |
| Alinhamento dos campos de documento | **Atendido** | Grade com a mesma base; CNPJ e Outro; 360/768/1280 e viewport 640 CSS sem rolagem horizontal. A captura `640-documento-zoom-200.png` é viewport de 640 px CSS, não zoom real de 200% no navegador. |
| Código/schema da candidata | **Atendido no local** | HEAD `d69e0f4e` + working tree 014; Flyway local **V19**; `/api/v1/system/info` version `0.1.0` DEMO. Origin continua V13. |
| Recarga real do detalhe | **Atendido** | `page.reload` do ID, reautenticação demo (token local, sem persistir sessão), reabertura do mesmo ID. |
| Rollback da versão anterior | **Não executado** | Artefato local `actionfinance:sair-cognito-010-4e556ecd` existe; `actionfinance-web:11` não foi recolhida. INSERT V2 **não** substitui esta prova. |
| Cópia restaurada do origin | **Não executado** | Sem autorização/acesso ao dump. Procedimento em `scripts/ops/rehearse-isolated-restore-014.ps1`; JDBC público recusado. Não é falha da interface. |

Nenhum item desta tabela foi **reprovado** por teste falho.

## R1 Importação utilizável no celular

### Achado

Em 360 a prévia 013 só mostrava totais: `desktop-table` some abaixo de 1023px e não havia cartões.

### Correção

`ul.catalog-cards.party-import-cards` no mesmo fluxo da tabela. Cada linha: número, nome, documento (já mascarado conforme permissão), classificação, motivo, inclusão permitida e resultado. Confirmação continua por linha; inválida não seleciona; duplicidade/prévia obsoleta/idempotência do lote inalteradas.

### Teste

`capture-cadastros-014.mjs` clicou em **360 e 768**: CSV misto (válida, inválida `12.ABC.345/0001-95`, duplicata da âncora). Motivo da inválida visível. Só a válida marcada. Confirmou. GET: 1 cadastro da válida; 0 da inválida. Segundo POST no **mesmo lote**: `created` permanece 1.

| Largura | ID criado | Lote |
|---|---|---|
| 360 | `027e41ff-2a3c-4c14-bfff-c3fc726213ff` | `aa41f54c-a743-462a-af5d-1952d28ac5db` |
| 768 | `35f918a7-1505-4555-ba45-9311c71239a8` | `cf5dc833-319d-4320-bf8e-6a51499d59ad` |

Prévia visual: `360-importacao-mista-previa.png`, `360-importacao-mista-confirmada.png` (Criado / Não gravada / Não gravada), `768-importacao-mista-selecao.png`. Desktop: `1280-importacao-desktop.png` (tabela).

Vitest `CounterpartiesPages.test.tsx`: 3 testes, exit 0.

### Limitação

Base: volume local de desenvolvimento após V19, não dump do origin. Sem importação produtiva.

## R2 Acabamento dos campos de documento

### Achado

Em 1280-cadastrar-vazio-rest (013), «País do documento» quebrava e deslocava a caixa; «Não informado» cortava. Avisos de pagamento repetiam no formulário.

### Correção

`.party-doc-grid` com colunas `minmax(8.5rem,10rem) minmax(13.5rem,16rem) minmax(12rem,1fr)`, `align-items: end`, rótulos sem quebra. Hint do formulário sem «não autoriza pagamento». A distinção permanece no comportamento e no bloco de completude do detalhe, quando há decisão.

### Teste

`1280-documento-cnpj.png`: três caixas na mesma base, CNPJ visível. Outro em 1280/768/360. Viewport 640 CSS (`640-documento-zoom-200.png`): uma coluna, sem overflow horizontal. Essa captura **não** é zoom real de 200% no navegador; é largura CSS de 640 px. A aprovação visual do alinhamento em 1280/768/360 não é reaberta por essa diferença. Navegação e as duas barras intactas.

### Limitação

Aceite visual continua com o analista.

## R3 Candidata coerente (código + V19)

Jornada 014 rodou em `http://127.0.0.1:5179` após restart local que aplicou Flyway **V19** no volume `actionfinance_pgdata_17`. Identidade: `documents/reviews/evidence/fechamento-cadastros-014/identidade-candidata.json`.

O volume local **não** é descartável. O schema descartável continua sendo `PartyDirectoryUpgradeDataIT` / `PartyDirectorySchemaUpgradeIT` (V19 em Testcontainer). Não se usou a aplicação pública.

## R4 Recarga real

Âncora `8143f765-c05a-4c87-9cc5-237f5de50670`. `page.reload` da URL de detalhe; sessão demo some (memória); login de novo com o token local do arquivo de demonstração (não pedido no chat, não persistido). Busca e reabre o mesmo ID. `1280-recarga-real.png`.

## R5 Rollback da imagem anterior — correção de conclusão

O INSERT com colunas de V2, feito no 013, prova só essa instrução SQL no schema expandido. **Não** prova rollback da imagem anterior. O pacote 011 foi corrigido.

Para provar rollback seria necessário: boot da versão anterior efetiva em isolado, contra schema V19; Flyway/init; leitura e `POST {name,role}`; campos novos intactos após edição pelo fluxo antigo.

Impedimento: `actionfinance-web:11` **não** foi recolhida (proibido neste pedido). Há imagem local `actionfinance:sair-cognito-010-4e556ecd` (ciclo 010, época da web:11). Não foi executada contra V19: o classpath antigo carrega Flyway só até V13; validar um histórico V19 sem as migrations 14–19 no jar é outro ensaio, não feito aqui. INSERT não substitui.

## R6 Cópia restaurada — separado da interface

Requisito pré-publicação. Este pedido não autoriza restore produtivo nem infra com custo. Falta autorização e acesso para obter o dump do origin.

Procedimento exato: `scripts/ops/rehearse-isolated-restore-014.ps1`. Destino isolado (não o RDS, não o volume do desenvolvedor). Dump custom, checksum, restore em base vazia, migrate até V19, invariantes na **cópia**. CompareOnly em `127.0.0.1:55432` aceito; JDBC do host público **recusado**.

Isto não é falha da importação mobile nem do alinhamento.

## Entrega

Prompt 014 em `documents/prompts`. Capturas em `documents/reviews/screenshots/fechamento-cadastros-014/`. Sem Pay, Spider, Panne, Cognito ou operações financeiras. Sem aceite do proprietário e sem publicação.
