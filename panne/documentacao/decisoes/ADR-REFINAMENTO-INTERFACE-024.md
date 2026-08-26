# ADR — Refinamento visual e funcional (CURSOR-024)

## Decisão

Refinar a interface da Panne para representar o produto existente: quadro como central do turno, assistente global em gaveta temporária, tela de acesso em três colunas e tokens bege/marrons/grafite. Sem nova regra soberana e sem migração `0021`.

## Contexto

Os ciclos 022 e 023 entregaram relatórios e estoque/compras. A UI ainda misturava formulário permanente de filtros no quadro, assistentes em superfícies concorrentes e login centrado sem preparação editorial.

## Consequências

- O contexto operacional (data, estabelecimento, turno, área) é escolhido antes do uso e persiste só em `sessionStorage` por organização e usuário.
- Filtros temporários ficam na URL e em painel recolhível.
- O assistente global não é chat e não chama Bedrock nos fluxos comuns.
- O conteúdo editorial da entrada usa porta genérica e provider estático. O adaptador ActionHub fica documentado, sem URL nem credencial.

## Fora de escopo

Autenticação OIDC/PKCE, regras de produção/estoque/custo/conformidade/relatórios, barra lateral permanente, ranking individual e CURSOR-025.
