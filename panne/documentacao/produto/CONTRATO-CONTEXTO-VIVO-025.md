# Contrato de contexto vivo do assistente

O guia estático é **fallback**. O estado vivo vem da rota, da organização ativa e do overlay publicado pela página.

## Campos

| Campo | Origem |
|---|---|
| rota e parâmetros | `useLocation` |
| domínio e submenu | guia resolvido |
| título e objetivo | guia + overlay |
| organização | contexto autenticado |
| entidade e rótulo humano | overlay ou guia |
| estado | overlay ou loading/vazio/erro/negado |
| permissões efetivas | sessão |
| ações / pendências / bloqueios / próxima ação | overlay + guia |
| formulário sujo / comando pendente | `setDirty` / `setPendingCommand` |
| contexto operacional | estabelecimento · turno · área |
| conceitos e destinos | glossário e destinos autorizados |

## Regras

- Mudança de rota zera overlay, sujeira e comando pendente.
- Mudança de organização zera overlay e fluxo específico.
- Logout zera tudo.
- Loading, vazio, erro e acesso negado têm contexto próprio (`Feedback` + páginas).
- Nenhum dado de uma organização aparece no texto de outra.
- Nenhum token ou payload integral entra na gaveta.
