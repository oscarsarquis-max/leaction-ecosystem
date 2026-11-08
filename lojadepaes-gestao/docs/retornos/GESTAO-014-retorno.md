# GESTAO-014 — retorno

Branch `feat/gestao-014-producao`, a partir de `51a6cb23`. A produção do dia vira ordem no calendário e sai numa comanda, com os ingredientes escalados pelo rendimento. A baixa de estoque e o realizado ficam para o GESTAO-015.

## Checklist

1. **Feito.** Dump `/opt/lojadepaes-gestao/backups/gestao-pre014.dump` (109.789 bytes) antes do Alembic. A migração `0009_perdas -> 0010_producao` só cria `fornadas`, `programacoes` e `ordens_producao`, e semeia "Manhã 05:00" e "Tarde 13:00" nas organizações que já existiam. Nenhuma ordem foi criada em produção: a contagem de `ordens_producao` ficou 0.

2. **Feito.** Backend 284 testes. Frontend 83. Os novos estão em `backend/tests/test_producao_014.py`: geração idempotente de 14 dias sem mexer na ordem impressa, demanda da Loja com item sem vínculo e selo de diferença, 10 pães de 500 g em 5.981 g com a massa-base expandida, arredondamento de 7,3 g e de 1.234 g, pesagem total somando o mesmo ingrediente, e isolamento entre organizações.

3. **Feito.** Capturas locais nas seis larguras, em `docs/evidence/gestao-014-local/`. Nenhuma com rolagem horizontal.
   - Semana: `semana-320.png` até `semana-1440.png`. No sábado, Manhã traz o pãozinho programado (100) e o da Loja (12); Tarde traz o programado (100). "Crie seu pão · Bola · 2 unidades" fica em "Pedidos sem produto na Gestão". No celular a grade some e entra o seletor do dia.
   - Dia: `dia-320.png` até `dia-1440.png`. Peças de 568 g, massas 59.809 g e 7.177 g, botão "Imprimir comanda da fornada".
   - Programações: `programacoes-320.png` até `programacoes-1440.png` e o modal em `programacoes-modal-1280.png`. 100 por fornada, segunda a sábado, sempre, ativa.
   - Comanda A4: `comanda-a4.pdf` e `comanda-a4-320.png` até `comanda-a4-1440.png`. Comanda 80 mm: `comanda-80.pdf` e `comanda-80-320.png` até `comanda-80-1440.png`. Cabeçalho com a logo, sábado 7 de novembro, Manhã 05:00, comanda 1, 2ª via, "impressa em 07/11/2026 11:03 por Pessoa". Ingredientes, modo de fazer, feito e observações. A pesagem total soma a farinha dos dois blocos em 41.045 g.
   - Hoje, fora da lista obrigatória e no mesmo padrão: `hoje-1280.png` e `hoje-390.png`. "Produção de hoje" mostra Manhã 05:00 com 112 unidades e Tarde 13:00 com 100, e o link "Abrir o dia".

4. **Feito.** A leitura da Loja usou a conexão do `gestao_reader` (`GESTAO_LOJA_DATABASE_URL`), a mesma consulta de vínculo sobre as colunas que a tela Hoje já lê. `pg_stat_user_tables` igual antes e depois do dump e de novo antes e depois de recriar o `gestao-api`: `media_assets` 17/0/0, `product_variants` 16/6/6, `products` 16/35/6, `showcase_slots` 10/16/0. A imagem no ar é `lojadepaes-gestao:014-20261107`. `https://gestao.lojadepaes.com.br/` responde 200 e serve `index-PdpJd3Et.js`, SHA-256 `8c4e71e6eed4c61cde776422f2cf5409a29897ac21e72d099c8980d94cf457c6`, igual ao pacote da imagem. `https://lojadepaes.com.br` responde 200. Nenhuma ordem de teste em produção.

5. **Feito.** Este arquivo, as capturas e os dois PDFs entram no mesmo commit. A regra de SSH aberta para este ciclo foi fechada; ficaram as 29 que já existiam. 80 e 443 seguem públicos.

A imagem anterior, para voltar, é `lojadepaes-gestao:013a-20261106`. O banco volta pelo dump.
