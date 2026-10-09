# Manifesto de release — modelo

Copiar para `manifests/AF-MAJOR.MINOR.PATCH-<estado>.md`. Não preencher com hipótese. Campo desconhecido = «não comprovado».

| Campo | Conteúdo |
|---|---|
| Versão e estado | planejada / candidata / validada / publicada / revertida / retirada |
| Base | AF-BL-023 e revisão |
| Escopo | Prompts e requisitos incluídos; pendências que **continuam abertas** |
| Mudanças | Funções, correções, impacto em dados/contratos |
| Código | Commit completo; tag imutável `af-vMAJOR.MINOR.PATCH` (não mover, não reusar) |
| Artefatos | Digest/hash de cada imagem ou bundle publicado |
| Banco | Flyway anterior → alvo; arquivos; checksums |
| Validação | Testes, evidências, limitações, prova pública |
| Operação | Compatibilidade Hub/Spider (versões **deles**); publicação; recuperação testada |
| Decisões | Autorização de publicar (origem); aceite (origem). Separados. Deploy ≠ aceite |

Regras: tag só no commit da release. Working tree misto não gera candidata. Hub/Spider não recebem o número do Finance.
