# GESTAO-017 — retorno

Base: `feat/gestao-014c-numeros` (`879444ce`), a branch publicada. O 014C não foi reaberto. Branch: `feat/gestao-017-receita-entrada`. Sem migração (`GESTAO_SEM_BANCO=1`).

## Checklist

1. **Feito.** `git apply --check` dos dois patches saiu limpo (código 0), e o `git apply` também. O 017 mudou `Receitas.tsx` e criou `receitas017.test.tsx`. O 016B mudou só `fluxo.css`.

2. **Feito.** `npx vitest run src/pages/receitas017.test.tsx src/pages/receitas015.test.tsx src/pages/Produtos.form.test.tsx`: 3 arquivos, 12 testes, todos passaram. Receitas: 4 do 017 e 7 do 015. `Produtos.form`: 1.

2b. **Não feito.** A medida das três caixas em produção. `https://gestao.lojadepaes.com.br/produtos` pede login. A senha de `admin@lojadepaes.com.br` não está gravada (foi digitada uma vez e não ficou em arquivo). Não medi, para não inventar o número.

3. **Não feito.** Os 4 passos no Levain de produção. O mesmo bloqueio: sem a senha não entro, e não alterei a receita.

4. **Feito** o restante. Imagem `lojadepaes-gestao:017-20261111`. O deploy imprimiu `banco: nada a fazer neste deploy (GESTAO_SEM_BANCO=1)`. Só o `gestao-api` foi recriado. `https://gestao.lojadepaes.com.br/` responde 200 e serve `index-BRTlwVJe.js`, SHA-256 `0098510b66c6965d96d7c3db4c4a41a45c619412c5d03ac482b89e33738eced4`. Health e ready respondem 200. `https://lojadepaes.com.br` responde 200, com o JavaScript da vitrine que já estava no ar (`index-BPpk5tJI.js`). A porta 22 aberta neste ciclo foi fechada (`regras_22` 0). O grupo do Hub não foi alterado.

A imagem anterior, para voltar, é `lojadepaes-gestao:014c-20261111`. O banco não foi migrado.
