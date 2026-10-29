# Pacote de publicação — reformulação de cadastros 011

Data original: 05/10/2026. Adendo 012 (05/10/2026): evidência Flyway do origin e correções incrementais. Adendo 013 (05/10/2026): provas de cadastro/detalhe, acabamento e V19 incremental. Adendo 015 (05/10/2026): identidade da candidata, rollback isolado e procedimento executável de cópia. Adendo 017 (05/10/2026): cópia real, V14–V19 no origin e publicação de `actionfinance-web:12`. Aceite integral do produto permanece separado.

## O que este pedido não autoriza

Autorizações anteriores de CSS, menus, logout ou imagem web **não** autorizavam, por si, aplicar V14–V19. O ciclo 017 executou a publicação já pedida da fatia. Continua sem importação produtiva em massa, Panne, cobrança, convite ou mensagem. Aceite do desenho/produto continua pendente.

## Histórico do estado Flyway (não apagar)

| Quando | Afirmação | Situação |
|---|---|---|
| Pacote 011 (texto inicial) | «RDS público permanece em V12 (V13 ainda não migrada)» | **Incorreta.** Contradizia relatos de V13 publicada. |
| REV_012 / inspect 05/10/2026 ~15:32 UTC | Destino efetivo em V13 | Conta `253137917703`, região `us-east-2`, instância `actionfinance`, host `actionfinance.czqyam2auctn.us-east-2.rds.amazonaws.com`, banco `actionfinance`. V1–V13 `success=true`. V13 checksum `728072343` em 2026-10-02 11:59:32. V14/V15/V16/V17/V18 **ausentes**. `financial_title` count=0 nesta leitura. Script: `scripts/ops/inspect-flyway-readonly-012.ps1`. Sem credenciais neste documento. |

Imagem vigente até o 015: `actionfinance-web:11`. Publicada em 05/10/2026: `actionfinance-web:12` · digest `sha256:9b90e33984cef1ef0ae4fe6a066a4a89db348c9d594559b5bb2b66b6dcd3d894`. Relato: [REV_017](../reviews/ACTIONFINANCE_REV_CONTINUIDADE_PUBLICACAO_017.md).

## Conteúdo local (controlado)

| Peça | Caminho |
|---|---|
| Prompt 011 (intacto) | `documents/prompts/ACTIONFINANCE_PROMPT_REFORMULACAO_CADASTROS_011.md` |
| Prompt 012 | `documents/prompts/ACTIONFINANCE_PROMPT_REVISAO_CADASTROS_012.md` |
| Prompt 013 | `documents/prompts/ACTIONFINANCE_PROMPT_PROVAS_CADASTROS_013.md` |
| Revisão 011 | `documents/reviews/ACTIONFINANCE_REV_REFORMULACAO_CADASTROS_011.md` |
| Revisão 012 | `documents/reviews/ACTIONFINANCE_REV_REVISAO_CADASTROS_012.md` |
| Revisão 013 | `documents/reviews/ACTIONFINANCE_REV_PROVAS_CADASTROS_013.md` |
| Prancha proposta | `documents/ux/interface-aprovada/04-cadastros-lista-formulario-proposta.png` |
| Migrations 011 | `database/migrations/V14__counterparty_directory.sql`, `V15__counterparty_directory_grants.sql` |
| Migrations 012 (incrementais; V14/V15 não editadas) | `V16__counterparty_directory_integrity.sql`, `V17__counterparty_directory_integrity_grants.sql`, `V18__counterparty_import_line_idem_scope.sql` |
| Migration 013 (incremental; V14–V16 não editadas) | `V19__counterparty_document_claim_backfill.sql` |
| Modelo CSV sintético | `documents/data/samples/modelo-cadastros-011.csv` |
| Ensaio isolado | `scripts/ops/rehearse-isolated-upgrade-012.ps1` |
| Procedimento de cópia (014 imprime; 015 executa sintético) | `scripts/ops/rehearse-isolated-restore-015.ps1` |
| Ensaio de rollback isolado | `scripts/ops/rehearse-isolated-rollback-015.ps1` |

## Validação antes de qualquer apply produtivo

Não usar `PartyDirectoryIT` como prova de cópia restaurada: o IT sobe Testcontainer próprio.

1. Backup lógico do schema `actionfinance` (pg_dump; retenção vigente). Não restaurar por cima do origin.
2. Restaurar o dump em instância isolada (o script de ensaio recusa o host RDS público).
3. Definir interrupção, janela/RPO e captura de escritas posteriores se houver troca de destino no futuro. Nenhuma autorização de restore produtivo aqui.
4. `flyway migrate` até **V19** nessa cópia. Não editar V14/V15/V16 já versionadas no repositório.
5. Conferir: `flyway_schema_history` (V13 checksum `728072343` intacto); títulos e FKs de `counterparty_id`; counterparties legados `document_pending=true`; grants sem DELETE da contraparte; FK composta do endereço; `connection_key` NOT NULL; tabela `counterparty_document_claim`.
6. Rodar SQL de invariantes **na cópia** (títulos, grants, FKs). Opcional: apontar um IT de ensaio com JDBC explícito isolado — distinto do Testcontainer.
7. Só então apresentar o resultado ao analista/proprietário. Sem apply silencioso.

## Rollback compatível (após V14–V19, se autorizado e falhar)

Preferir rollback de **código**: recolher a imagem anterior **depois** de comprová-la em isolado contra o schema expandido. Um `INSERT` com colunas de V2 prova só essa instrução SQL; **não** prova inicialização, Flyway nem edição pelo fluxo antigo da imagem anterior.

Restore só se o rollback de código for comprovadamente insuficiente:

1. Interromper escritas; registrar RPO.
2. Restaurar o backup pré-migration **primeiro em banco isolado**.
3. Reconciliar escritas posteriores; só então considerar troca de destino.
4. Recolocar a imagem web/API anterior.
5. Não apagar cadastros novos para “desfazer” se já houver título apontando para eles.

Nenhuma autorização de restore produtivo é concedida por este pacote.

## Produção pública neste momento

RDS público em **V19** após o ciclo 017 (05/10/2026). Imagem vigente `actionfinance-web:12` · digest `sha256:9b90e33984cef1ef0ae4fe6a066a4a89db348c9d594559b5bb2b66b6dcd3d894`. SPA `index-BYEiixeg.js`. Recuperação de código: `actionfinance-web:11` · `sha256:06e067e7…` (ensaio 015). Sem restore de schema. [REV_017](../reviews/ACTIONFINANCE_REV_CONTINUIDADE_PUBLICACAO_017.md). Pedido 015 permanece histórico. Fechamento de interface: [REV_014](../reviews/ACTIONFINANCE_REV_FECHAMENTO_CADASTROS_014.md).
