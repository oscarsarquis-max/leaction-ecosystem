# Documentação da Spider (snapshot)

Conteúdo estruturado da aba **Documentação**. A UI só renderiza estes módulos; não lê o filesystem em runtime.

## Como atualizar

1. Inventariar código, testes, migrations e configuração reais.
2. Editar os manifestos em `components.js`, `protocols.js`, `schema.js`, `architecture.js`, `environment.js`.
3. Ajustar `snapshot.js` (`generatedAt` e nota).
4. Rodar `npm run docs:validate` em `spider/frontend` — falha se houver id duplicado, relação órfã, tabela sem migration, dependência sem fonte ou arquivo de evidência inexistente.
5. Rodar `npm test`, `npm run lint` e `npm run build`.
6. Não afirmar roadmap (CAP-021, Reconciliation Workbench, agente/composer) como implementado.

O gerador/validador é determinístico, sem rede e sem alterar fontes da aplicação.
