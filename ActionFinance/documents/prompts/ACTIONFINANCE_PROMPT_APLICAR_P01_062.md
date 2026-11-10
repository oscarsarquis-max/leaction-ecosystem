# ACTIONFINANCE — Prompt 062 · Aplicar o patch P01 (identidade) e publicar

**Pode rodar agora (o 058B já está publicado).** O frontend agora é implementado pelo Claude, que entrega patches. Este prompt só aplica, testa e publica.

## Regras
- Não alterar a Spider, a Loja nem o Hub. Sem mudança de banco.
- Testes: só os do frontend tocados pelo patch (`App.test.tsx` e os do Início do 058B).

## Passos
0. **SSH:** atualizar a regra para o IP público atual (abrir a nova, testar, só então fechar a antiga).
1. **Aplicar** na branch `feat/actionfinance-extrato-032`:
   `git am -3 "C:\Projetos\claude\2026-11-09-actionfinance-corporate-analyser\patches\P01-identidade-loja-gestao.patch"`
   - Base do patch: `446c6124` (0.2.14, já inclui o 058B). Só toca em `ActionFinance/frontend/src`. Deve aplicar sem conflito.
   - **Se houver conflito com o 058B:** resolver mantendo a lógica do 058B e as cores/fontes do P01. Se a dúvida for de desenho, **parar e relatar** (o Claude refaz o patch).
2. **Conferir:** nenhuma cor antiga (`#1603ad`, `#1800ad`, `#24219b`, `#14143d`) sobrando em `.css`/`.tsx`, inclusive no que o 058B criou. Se o 058B criou cores fixas novas, trocar pelos tokens.
3. **Build e testes** da área.
4. **Publicar 0.2.15:** nova task web; retorno para a task do 058B.
5. **Verificar:** health 200; o pacote publicado contém `af-logo-vazado-branco` e `DM Sans`. Se houver sessão, capturas do Início em 1440 e 390.

## Entrega
- `documents/reviews/ACTIONFINANCE_REV_APLICAR_P01_062.md` (curto): patch aplicado (hash), conflitos, versão, task, retorno.
- Copiar este prompt para `documents/prompts/`. Commit, push e deploy.
