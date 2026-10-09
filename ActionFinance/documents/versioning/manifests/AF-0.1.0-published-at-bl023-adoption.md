# Manifesto — 0.1.0 publicada na adoção de AF-BL-023

Estado: **publicada** (artefato já no ar). Preenchido só com fato verificado em 09/10/2026 ou lacuna explícita. Não é aceite de produto. Não associa o working tree atual a este deploy.

| Campo | Conteúdo |
|---|---|
| Versão e estado | 0.1.0 · publicada |
| Base | Anterior à AF-BL-023. Requisitos 023 **não** estão neste artefato |
| Escopo | Fundação + títulos/baixas/contas + cadastros-017 + listagem Pay publicada. **Abertas:** 019, 020, 021, tesouraria 023 |
| Mudanças | Nenhuma neste manifesto — fotografia da adoção do controle |
| Código | Tag imutável: **ausente** (limite histórico; não fabricada). Commit da imagem 017 relatado como worktree `4e556ecd` + overlay — **não revalidado** neste ciclo |
| Artefatos | SPA conferida: `index-BYEiixeg.js`. Digest ECS `sha256:9b90e33984cef1ef0ae4fe6a066a4a89db348c9d594559b5bb2b66b6dcd3d894` e `actionfinance-web:12`: **último relato 05/10/2026**, não relidos na AWS em 09/10 |
| Banco | Inspect 05/10/2026: Flyway 1–19, V13 checksum `728072343`. **RDS não lido em 09/10.** V20 não publicada |
| Validação | `GET https://actionfinance.actionhub.com.br/api/v1/system/info` → 200, `version=0.1.0`, OIDC, `RECEIPT_SYNC`. HTML 200. Prova autenticada de 019: **não** |
| Operação | Recuperação 017 documentada em REV_017; **não retestada** aqui |
| Decisões | Publicação 017: autorização do proprietário (prompts 016/017). Aceite integral do produto: **não** (REV_017) |

Retificação futura deve acrescentar parágrafo, sem apagar esta tabela.
