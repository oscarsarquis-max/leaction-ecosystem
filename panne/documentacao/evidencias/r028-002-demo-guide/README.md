# R028-002 — Guia completo da Panne Demo

## Causa

Em `/entrar`, “Ajuda para entrar” só explicava a fronteira do CMS (“O conteúdo ao lado não altera o login…”), sem roteiro de homologação. A demo dependia de conhecimento externo.

## Solução

- Linguagem humana na caixa de `/entrar` + bloco **Como avaliar esta demonstração**
- Página pública `/demonstracao` (somente com `demoMode`)
- Contrato `GET /api/v1/public/demo-guide` (somente `PANNE_ENV=demo`), contagens org-scoped fixas por slug, fallback versionado, sem UUID/email/segredo
- Gigio atualizado (entrada + pós-login)
- Menu do usuário: **Guia da demonstração**
- R028-001: zeros fiscais/produtos com frase humana (“Nenhuma entrada…”)
- Impressão / mobile (seções recolhíveis + CSS)

## Contrato

`GET /api/v1/public/demo-guide`

- 404 fora de `PANNE_ENV=demo`
- Sem auth; query `organization_id` ignorada
- Contagens live quando DB disponível; senão fallback (`source: fallback`)
- Ausência de métrica → `null` → UI “Não informado”

## Limitações apresentadas no guia

1. Criação de nova separação ainda pode estar indisponível na tela.
2. Integração fiscal real depende de certificado A1 — não configurado nesta demo.
3. Combos, mistos e sub-receitas avançadas seguem o estado real do recorte.
4. Dados podem ser alterados por outros homologadores a qualquer momento.
5. Restauração/reset da demo, quando houver, é operação de equipe.

## Testes locais

- FE: `npm test -- --run src/demo-guide-r028.test.tsx` — 7 passed
- FE build: `VITE_HOMOLOG_DEMO=1 VITE_DEMO_MODE=1 VITE_AUTH_PROVIDER=fake npm run build` — ok
- BE: `pytest tests/test_demo_guide.py` — 3 passed

## Publicação

Somente demo (`panne_demo` / `demo.panne.ia.br`). Produção e banco `panne` congelados. Sem reseed.
