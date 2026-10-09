# Versionamento do ActionFinance

Instituído em 09/10/2026 pelo Prompt 024. Quatro identificações distintas:

| Identificação | Forma | Não é |
|---|---|---|
| Baseline / requisitos | `AF-BL-023` + revisão (agora **1.0**) | Versão do produto, Flyway ou revisão ECS |
| Produto | `MAJOR.MINOR.PATCH` | Número do prompt ou `V19` do banco |
| Banco | Flyway `V1`…`Vn` + checksum | Semver do produto |
| Implantação | digest, task definition, ambiente, janela, resultado | Versão do produto |

Estados de uma versão de produto: planejada, candidata, validada, publicada, revertida, retirada.

Uma versão planejada não aparece como publicada. Build no registro ≠ implantação. Aceite ≠ deploy.

Hub e Spider têm versionamento próprio; o manifesto do Finance apenas referencia as peças compatíveis daquela entrega.

Vivos (atualizáveis no Git): [INDEX.md](INDEX.md), [CHANGELOG.md](CHANGELOG.md), manifestos em rascunho. Encerrados: não apagar; retificação declara o que corrige.
