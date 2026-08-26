# Assistente global

O assistente autenticado vive no **shell**, não nas páginas. Minimizado, é um **avatar circular** (`Abrir assistente da Panne`). Não é botão textual. No login, o modo público reduzido usa `Abrir ajuda para entrar`.

Abre em gaveta temporária, minimizável, dispensável e retomável. Não é barra lateral permanente. Não é chat livre. Não chama Bedrock nos fluxos comuns.

## Respostas determinísticas

- Onde estou
- O que a página significa
- O que posso fazer
- O que falta ou bloqueia
- Para onde seguir

## Contrato

- Guia estático: `panne/frontend/src/guide/routes.ts` — fallback por rota.
- Contexto vivo: `panne/frontend/src/assistant/liveContext.ts` — estado da página, entidade, organização, permissões e próxima ação.
- Comparação automática: `collectRouterPaths()` versus `matchGuide()`.
- Sem token, credencial, segredo ou payload integral.

## Integração

Assistentes específicos registram um fluxo na mesma gaveta (`setFlow`) e permanecem como cartão inline. `Voltar à orientação` devolve o mentor global. Próxima ação é orientação, nunca execução automática.
