# ACTIONFINANCE_REV_PRE_PUBLICACAO_CADASTROS_015

Identificador: ACTIONFINANCE_REV_PRE_PUBLICACAO_CADASTROS_015. Data: 05/10/2026. Documento independente. O parecer de interface do 014 permanece encerrado. Aceite do proprietário e publicação **não** atribuídos. RDS não migrado. Serviço público não alterado.

Provas 012/013/014 preservadas. Viewport 640 do 014 foi reescrito como largura CSS, não zoom real de 200%.

## Tabela

| Item | Resultado | Evidência |
|---|---|---|
| Identidade da candidata | **Aprovado no ensaio** (manifesto) | `evidence/pre-publicacao-cadastros-015/identidade-candidata.json` — 25 arquivos SHA-256. Sem imagem publicada desta fatia. `0.1.0` não é identidade. |
| Rollback da imagem anterior | **Aprovado no ensaio** | Imagem publicada = `actionfinance-web:11` · `sha256:06e067e772f65d37a0cf43c53022e32d9e0a76eb9841cfebaf75d684b28f953c`. Local `actionfinance:sair-cognito-010-4e556ecd` tem o mesmo digest e o mesmo JAR `79dd27b0…`. ECS em 05/10/2026: `actionfinance-web:11` desired=1 running=1 COMPLETED. |
| Cópia restaurada do origin | **Não executado** | Sem dump. Pedido único: `operations/ACTIONFINANCE_PEDIDO_COPIA_CADASTROS_015.md`. |
| Procedimento sintético de cópia | **Aprovado no ensaio** | `rehearse-isolated-restore-015.ps1 -Synthetic`. Não é a cópia do origin. |

Nenhum item desta tabela foi **reprovado**.

## 1. Identidade da candidata

HEAD `d69e0f4e` mais working tree não identificava o conjunto. Não houve commit único desta fatia: o working tree mistura alterações alheias (Pay, Terraform, outros prompts). A identidade reproduzível é o **manifesto de hashes** dos arquivos pertinentes, sem segredos.

- Migrations da fatia: V14–V19. V13 incluída no manifesto porque o checksum local é `728072343`, o mesmo do origin.
- Backend/frontend da fatia: serviços de diretório, importação, páginas e grade.
- Build: JAR e `dist` desta candidata **não** foram gerados neste ciclo. Imagem desta candidata **não** existe e **não** foi publicada.
- Artefato vigente no serviço público continua o da revisão 010, abaixo.

## 2. Resultado do rollback

Versão anterior efetiva:

| Campo | Valor |
|---|---|
| Tarefa | `actionfinance-web:11` |
| Imagem | `253137917703.dkr.ecr.us-east-2.amazonaws.com/actionfinance@sha256:06e067e772f65d37a0cf43c53022e32d9e0a76eb9841cfebaf75d684b28f953c` |
| JAR | `79dd27b0bb00a349cf596d6fe22a6ed417da747f8ff0addabf72d41d32302830` |
| Flyway no JAR | V1–V12 |
| Web em produção | `ACTIONFINANCE_FLYWAY_ENABLED=false` (migrate é outra família) |

Equivalência da tag local comprovada por `RepoDigests` e pelo hash do JAR extraído. O ensaio **não** substituiu o serviço público.

Destino: volume `actionfinance_rehearsal_015`, não o RDS, não `actionfinance_pgdata_17`. Rede interna, sem secret Spider/OIDC. Schema levado a V19 com os SQL da candidata.

| Modo | Flyway | Resultado real |
|---|---|---|
| Web (como produção) | desligado | Subiu. Leu 2 cadastros. `POST` nome+papel criou `27f8cc28-0968-4de5-b640-416da6433a55`. `PATCH` no fornecedor demo. Documento `77000000000116` e claim=1 intactos após a edição. |
| Migrate da imagem anterior | ligado | Flyway validou, avisou «schema 19 newer than latest available migration 12», não aplicou nada e o processo subiu. Não foi usado `ignore-missing-migrations`. |

INSERT com colunas antigas continua sem valor como prova de rollback. Aqui a imagem anterior de fato inicializou e escreveu.

Restore **não** é a alternativa automática: escritas posteriores e RPO continuam requisito separado. A alternativa compatível testada é recolher só a tarefa web (Flyway desligado), que é o arranjo já vigente.

Log: `rollback-ensaio.json`, `rollback-web-flyway-off.log`, `rollback-migrate-flyway-on.log`.

## 3. Procedimento de cópia

`rehearse-isolated-restore-014.ps1` só imprime instruções. O executável é `rehearse-isolated-restore-015.ps1`.

Antes de escrever, o script recusa: hostname RDS, resolução DNS/CNAME para `rds.amazonaws.com`, `data_directory` de RDS, volume `actionfinance_pgdata_17`, e destino sem o identificador de instância esperado. URL sem `rds.amazonaws.com` não basta.

Ensaio sintético (dados locais, mesmos V14–V19 da candidata):

- Antes: 1 contraparte, 1 título, vínculo e `amount_minor=2500` em V13.
- Depois: V1–V19; checksum V13 `728072343`; mesmos IDs e valor; `document_pending`; runtime sem DELETE; `connection_key` sem nulos.
- Dump do origin: não usado.

`restore-sintetico.json`. Isso não verifica o destino real.

## 4. Autorização efetivamente necessária

Para a **cópia do origin**, falta um sim do proprietário ao [pedido único](../operations/ACTIONFINANCE_PEDIDO_COPIA_CADASTROS_015.md): dump somente leitura, destino isolado, proteção/retenção do arquivo, sem custo de infra nova. Credenciais fora do chat.

Não falta autorização para o desenho 014, para o manifesto, para o rollback isolado já corrido, nem para o ensaio sintético já corrido.

Não se atribui ao proprietário autorização que ele não deu. Não se infere publicação do aceite técnico de interface.
