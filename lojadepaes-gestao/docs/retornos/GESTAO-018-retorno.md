# GESTAO-018 — Preparos da casa rendem em peso

Base: `feat/gestao-017-receita-entrada` (`bf34044e`). Branch: `feat/gestao-018-rendimento-peso`. Sem migração (`GESTAO_SEM_BANCO=1`). Sem pull request.

## Checklist

1. **Feito.** `git apply --check` do patch `GESTAO-018-rendimento-em-peso.patch` saiu limpo (código 0) e o `git apply` aplicou. Os avisos foram só de espaço no fim de linha do teste novo. Front: `npx vitest run src/pages/receitas018.test.tsx src/pages/receitas017.test.tsx src/pages/receitas015.test.tsx` — 3 arquivos, 15 testes passando. Backend, só o arquivo novo: `pytest tests/test_rendimento_018.py` — 4 passando.

2. **Feito.** Capturas locais, com o backend em `127.0.0.1:8090` e o Postgres de teste, o Vite em `127.0.0.1:5185` encaminhando `/api` para esse backend. Levain igual ao teste (420 g, inóculo 100 g, processo 5 %). Em `docs/evidence/gestao-018-local/`: `rendimento-1280.png`, `revisar-1280.png`, `rendimento-390.png`, `revisar-390.png`. As quatro mostram rende 399 g de 420 g, reserva 100 g, disponível 299 g, custo R$ 17,53 parcial e hidratação 50 % (131 g de água para 263 g de farinha; a tela arredonda a grama, a API guarda 131,25 e 262,5).

3. **Feito.** Imagem `lojadepaes-gestao:018-20261112`. O deploy imprimiu `banco: nada a fazer neste deploy (GESTAO_SEM_BANCO=1)`. Só o `gestao-api` foi recriado e ficou healthy. `https://gestao.lojadepaes.com.br/` responde 200 e serve `index-CztlpCWp.js`, SHA-256 `41e0b941988cfd5059bcf8b73c928e90b489a36a9c36d93da12ea0c2a0d78596`, o mesmo nome que o build da imagem. `/api/v1/health` e `/api/v1/ready` respondem 200. `https://lojadepaes.com.br` responde 200, com o JavaScript da vitrine que já estava no ar (`index-BPpk5tJI.js`, SHA-256 `beab198e074276d845df53ed9ac88704cd1f1d3b84ba01c540d2ba2621e79251`). A porta 22 deste ciclo foi fechada (`regras_22` 0). Não havia regra antiga. O grupo do Hub não foi alterado. Continuam no ar: `gestao-api`, `infra-api-1`, `lepain`, `infra-caddy-1`, `infra-db-1`.

4. **Feito**, no sentido pedido: não entrei na conta de produção. A conferência no Levain real fica com o Oscar.

## O que o detalhe passa a devolver

- `modo_rendimento` é `massa` quando o produto é componente e não é venda. Nos outros casos é `unidades`, e o pão segue o cálculo em peças.
- No modo massa, `rendimento_massa` traz a massa com o inóculo, o percentual de processo, o que rende (`floor` da massa já com a perda), a reserva do inóculo, o disponível e o custo por kg. O custo por kg é o custo das linhas que não são inóculo, dividido pelo disponível e levado a 1 kg. Fica vazio se o disponível não é positivo. A marca de parcial continua a de sempre.
- 5,24 ÷ 299 × 1000 dá 17,525… A tela e o teste mostram **17,53**, meia para cima em centavos. O 17,52 do enunciado corta o meio centavo.
- Ao gravar em modo massa, peso por peça, formato, unidades e cocção ficam vazios. O rendimento gravado é o que rende, em gramas. Publicar não acusa rendimento vazio quando isso é maior que zero.
- O custo por grama, usado quando o preparo entra em outra receita, passa a ser esse custo por kg ÷ 1000. A perda de 5 % entra no custo do pão.
- `sem_fermento` só aparece no modo unidades e quando o produto não é cultura viva. O preparo da casa não recebe essa pendência.
- `hidratacao` vale nos dois modos: farinha, água e o percentual com uma casa. Some as linhas diretas, a farinha e a água de dentro do componente publicado, e o inóculo da própria cultura no equilíbrio do resto. Sem farinha, o campo fica vazio.
- Inóculo de 500 g neste Levain deixa 279 g disponíveis (820 g × 0,95 = 779; 779 − 500). Não bloqueia. A pendência `reserva_maior` aparece quando a reserva passa do que rende; o teste usa 6.500 g e a publicação responde 422.

## Como voltar

No host, `GESTAO_IMAGE=lojadepaes-gestao:017-20261111` em `/opt/lojadepaes-gestao/deploy/.env` e recriar só o `gestao-api`. A imagem 017 segue no host. O banco não mudou de esquema.
