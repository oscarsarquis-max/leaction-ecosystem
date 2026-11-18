# GESTAO-006 — Custo pelo valor pago (e catálogo v2): retorno

Branch `feat/gestao-006-valor-pago` (a partir de `feat/gestao-005a-sugestao`). Imagem em produção: `lojadepaes-gestao:006-20261103` (anterior: `005a-20261103`).

## 1. Resumo

- A entrada passa a pedir o **"Valor pago (R$)"**, o total da linha. Embaixo do campo, em cinza, aparece o que será gravado: `= R$ 45,98/kg` e, na embalagem, `= R$ 22,99/emb · R$ 45,98/kg`.
- O cabeçalho da coluna é o seletor **"Valor pago ▾ | Preço por unidade"**. Vale para a entrada toda e para o colar da planilha, e a última escolha fica lembrada neste navegador. O "Não sei" continua deixando o custo do lote desconhecido. O total do rodapé é a soma dos valores pagos.
- **Corrigir custo** no lote (painel do ingrediente e detalhe da entrada): pede o valor pago (ou o preço por unidade) e o motivo, mostra antes e depois, grava o histórico (quem, quando, antes, depois, motivo) e **não mexe no saldo**.
- **Trocar ingrediente** no painel do ingrediente (por item): busca, motivo, histórico; os lotes e o saldo vão junto e os dois saldos se ajustam por um movimento de junção. Nada é trocado sozinho.
- **Catálogo v2** (71 itens) copiado sem alterações; "sarraceno" virou qualificador; Nuvola e farinha para pizza levam a "tipo 0".

Regra do ciclo cumprida: na Loja de Pães só foram feitos os quatro pontos autorizados (SSH só para o meu IP e fechado só a minha regra; rebuild e restart do `gestao-api`; migração aditiva no banco `gestao`; `carregar-catalogo`). Mais o `pg_dump` e a consulta de leitura pedidos na seção 0. Mais nada foi tocado.

## 2. Dados que já existem (seção 0)

- **Nada foi apagado, renomeado ou religado**: ingredientes, itens, lotes, movimentos, entradas, apelidos e decisões de "parecidos" ficaram como estavam. `carregar-catalogo` e as regras da 005A não tocam dados da organização.
- **Migração `0004_valor_pago_correcoes` só aditiva**: duas colunas novas, nulas, em `entrada_linhas` (`valor_pago`, `modo_custo`, com um `CHECK`) e duas tabelas novas (`correcoes_custo`, `trocas_ingrediente`). Nenhuma coluna ou tabela existente foi alterada. O `downgrade` só remove o que a 0004 criou.
- **O custo que já estava gravado mantém o sentido**: o lote já guardava R$ por unidade base (R$/g, R$/ml, R$/un); a coluna antiga "R$ por kg" era dividida por 1000 na entrada. Não há conversão de valor nenhuma, então nenhum número antigo foi reinterpretado.
- **Prova** (produção, mesma consulta somente leitura `scripts/consulta-custos-lotes.sql`, antes e depois do deploy): saída **idêntica** (mesmo SHA-256 `d985d2c7…0c6a`, 19 linhas, 16 lotes). Ver seção 6.
- Backup antes da migração: `pg_dump -Fc` do banco `gestao` em `/opt/lojadepaes-gestao/backups/gestao-pre006.dump` (60.831 bytes, SHA-256 `a8f80dce…f27`, `chmod 600`). Conferi com `pg_restore --list`: 123 linhas, 15 entradas `TABLE DATA`, cabeçalho íntegro.
- **Item ligado ao ingrediente errado**: a ação **"Trocar ingrediente"** existe (busca, motivo, histórico). Eu **não troquei nada** em produção; quem decide é você.

## 3. Testes (só os da área)

| Onde | Resultado |
|---|---|
| Backend (áreas `valor_pago`, `catalogo_v2_sugestao`, `ingrediente_busca`, `estoque`, `sugestao_qualificadores`, `dominio_puro`, `papeis`) | **170 passed**; `ruff check app tests` limpo |
| Frontend | `tsc --noEmit` limpo; `eslint --max-warnings 0` limpo; **73 passed** (eram 57); `npm run build` ok |

Os 27 testes novos do backend (`tests/test_valor_pago.py`, 19; `tests/test_catalogo_v2_sugestao.py`, 8) e os 16 do frontend cobrem exatamente a lista pedida:

| Pedido | Teste |
|---|---|
| 0,5 kg com R$ 22,99 = R$ 45,98/kg | `test_meio_quilo_com_22_99_pagos_da_45_98_por_kg`; tela: "o custo é o valor pago por padrão… = R$ 45,98/kg" |
| 1 emb de 500 g com R$ 22,99 = R$ 22,99/emb e R$ 45,98/kg | `test_uma_embalagem_de_500_g_…`; tela: "na embalagem… (o rótulo diz 'embalagem')" |
| "Preço por unidade" continua | `test_modo_preco_por_unidade_continua_funcionando` e `_em_embalagem`; tela: "'Preço por unidade' continua funcionando… e a escolha fica lembrada" |
| O colar respeita o modo | tela: "colar da planilha respeita o modo escolhido"; `entradaForm.test.ts`: "a colagem guarda o custo como veio" |
| Corrigir custo grava histórico e não muda o saldo | `test_corrigir_custo_grava_o_historico_e_nao_muda_o_saldo`, `…pelo_preco_por_unidade…`, `…exige_motivo…`, `…respeita_papel_e_organizacao`; tela: o diálogo mostra antes/depois e manda só `valor_pago` e `motivo` |
| Trocar ingrediente leva os lotes, ajusta os dois saldos, com histórico | `test_trocar_ingrediente_leva_os_lotes_ajusta_os_dois_saldos_e_guarda_historico`, `…grava_quem_quando_e_porque`, `…recusa_unidade_diferente_mesmo_ou_inativo_sem_motivo`, `…respeita_papel` |
| A migração preserva o custo por kg/L dos lotes antigos | `test_migracao_0004_preserva_custos_e_dados_de_lotes_antigos` (migra de verdade 0003 → 0004 → 0003 num banco descartável, compara a mesma consulta antes e depois) |
| "Trigo Sarraceno" sugere "Farinha de trigo sarraceno" e nunca a "especial" | `test_trigo_sarraceno_sugere_farinha_de_trigo_sarraceno_e_nunca_a_especial` (inclui o item já ligado ao ingrediente errado) |
| "Farinha de Trigo Tipo Nuvola" sugere "tipo 0" | `test_farinha_de_trigo_tipo_nuvola_sugere_tipo_0_em_destaque` e `test_nuvola_ganha_da_especial_mesmo_com_a_especial_ja_na_padaria` |

Extras: catálogo v2 com 71 itens, v1 → v2 insere 1 e altera 1, "sarraceno" exclui "Farinha de trigo …" sem o termo, "farinha de trigo" comum ainda sugere a "especial", "farinha para pizza" leva ao "tipo 0".

## 4. Capturas locais (1280 e 390 px)

Ambiente **local**, banco de demonstração (`scripts/seed-demo-gestao-006.py`, `scripts/capture-gestao-006.mjs`). Em `docs/evidence/gestao-006-local/`; as checagens automáticas estão em `capturas-1280.md` e `capturas-390.md`: sem rolagem horizontal e controles com 40 px (44 no celular).

| O que mostra | 1280 | 390 |
|---|---|---|
| Linhas com o custo calculado embaixo (`= R$ 45,98/kg`; `= R$ 22,99/emb · R$ 45,98/kg`) e o seletor "Valor pago ▾" | `entrada-valor-pago-1280.png` | `entrada-valor-pago-390.png` |
| O mesmo no modo "Preço por unidade" | `entrada-preco-por-unidade-1280.png` | `entrada-preco-por-unidade-390.png` |
| Detalhe da entrada: valor pago, custo por kg e "Corrigir custo" | `entrada-detalhe-1280.png` | `entrada-detalhe-390.png` |
| **Diálogo "Corrigir custo"** (antes R$ 45,98/kg, depois R$ 40,00/kg, motivo) | `corrigir-custo-dialogo-1280.png` | `corrigir-custo-dialogo-390.png` |
| Painel do ingrediente: custo do lote, "Corrigir custo" e "Correções de custo" | `ingrediente-custo-e-correcoes-1280.png` | `ingrediente-custo-e-correcoes-390.png` |
| "Trocar ingrediente" (item ligado ao ingrediente errado) | `trocar-ingrediente-dialogo-1280.png` | `trocar-ingrediente-dialogo-390.png` |
| Depois da troca: item, lote e saldo no ingrediente certo; histórico "Troca de ingrediente" | `trocar-ingrediente-resultado-1280.png` | `trocar-ingrediente-resultado-390.png` |

Dois ajustes que as capturas pediram: (1) a lista do campo Ingrediente ficava **atrás do painel lateral** (z-index 26 contra 30/45), o que só aparece agora que o campo vive dentro de um painel; subi para 55; (2) o × do chip do ingrediente tinha 32 px (40 no celular); agora 40 px (44 no celular).

## 5. `carregar-catalogo` em produção

```
catálogo de ingredientes - versão 2
1 inseridos, 1 alterados, 69 iguais
```

Como esperado: 1 inserido ("Farinha de trigo sarraceno"), 1 alterado ("Farinha de trigo tipo 0", com nuvola e farinha para pizza), versão 2. O YAML no repositório é o v2 do pacote, byte a byte (SHA-256 `F4F6DA19…7B46`, igual dentro da imagem). Migração no mesmo deploy: `Running upgrade 0003_ingrediente_catalogo -> 0004_valor_pago_correcoes`.

## 6. Publicação (procedimento do 002) e conferências

- SSH: porta 22 aberta **só para o meu IP /32** (`189.14.176.74`; a regra não existia) e **fechada em seguida**; conferi que não ficou e que as 29 regras antigas continuam. Chave temporária removida.
- Antes: `pg_dump` + `pg_restore --list` + consulta de custos (ANTES). Depois: `remote-deploy.sh` (migração 0004, catálogo, recriar `gestao-api`).
- `gestao-api` `healthy` com `006-20261103`; `/api/v1/health` **200**, `/api/v1/ready` **200**; o código novo está dentro do contêiner (`custo_duplo` em `entradas.py`); o JavaScript servido (`index-BERUV_e1.js`) tem o mesmo SHA-256 do build local (`8982ed7a…d71b`).
- **`https://lojadepaes.com.br/` 200**, `https://gestao.lojadepaes.com.br/` 200. Loja intocada. **Sem dados de teste em produção.**
- Banco depois: `alembic_version = 0004_valor_pago_correcoes`; `correcoes_custo` 0, `trocas_ingrediente` 0, linhas com `modo_custo` 0 (nada foi gravado pela 006 ainda); catálogo 71 itens, versão máxima 2.

### Antes e depois do custo (idêntico)

Mesma consulta somente leitura, antes e depois: **saída idêntica** (`diff` vazio, SHA-256 `d985d2c7b001460cb9ccf6272dc21d5884964622c6a9352d8c260aaa2f9d0c6a` nos dois, 19 linhas). Saída completa:

```
SET
organizacao | lote | item | ingrediente | base | comprado | comprado_base | saldo_base | custo_por_unidade_base | custo_por_kg_l_un | digitado
boulangerie | E20261103-15 | Farinha de Cevada Integral | Farinha de Cevada | g | 350 g | 350.0000 | 350.0000 | 0.02145000 | 21.45 por kg | digitado 21.4500 por kg
boulangerie | E20261103-16 | Farinha de Cevada Integral | Farinha de Cevada | g | 350 g | 350.0000 | 350.0000 | 0.02145000 | 21.45 por kg | digitado 21.4500 por kg
boulangerie | E20261103-13 | Trigo Sarraceno | Farinha de Trigo sarraceno | g | 500 g | 500.0000 | 500.0000 | 0.02390000 | 23.90 por kg | digitado 23.9000 por kg
boulangerie | E20261103-09 | Nita Centeio — Nita | Farinha de centeio | g | 2 kg | 2000.0000 | 2000.0000 | 0.02199000 | 21.99 por kg | digitado 21.9900 por kg
boulangerie | E20261103-12 | Fubá Orgânico | Farinha de milho | g | 500 g | 500.0000 | 500.0000 | 0.02299000 | 22.99 por kg | digitado 22.9900 por kg
boulangerie | E20261103-10 | Farinha de Trigo Sêmola | Farinha de semolina | g | 2 kg | 2000.0000 | 2000.0000 | 0.03390000 | 33.90 por kg | digitado 33.9000 por kg
boulangerie | E20261103-08 | Nita 100% Integral | Farinha de trigo integral | g | 2 kg | 2000.0000 | 2000.0000 | 0.00699000 | 6.99 por kg | digitado 6.9900 por kg
boulangerie | E20261103-05 | Farinha de Trigo Doppio Zero | Farinha de trigo tipo 0 | g | 1 kg | 1000.0000 | 1000.0000 | 0.02680000 | 26.80 por kg | digitado 26.8000 por kg
boulangerie | E20261103-06 | Farinha de Trigo Doppio Zero | Farinha de trigo tipo 0 | g | 3 kg | 3000.0000 | 3000.0000 | 0.02680000 | 26.80 por kg | digitado 26.8000 por kg
boulangerie | E20261103-07 | Farinha de Trigo Nita 00 | Farinha de trigo tipo 0 | g | 4 kg | 4000.0000 | 4000.0000 | 0.01799000 | 17.99 por kg | digitado 17.9900 por kg
boulangerie | E20261103-01 | Farinha de Trigo Superiore | Farinha de trigo tipo 0 | g | 1 kg | 1000.0000 | 1000.0000 | 0.00549000 | 5.49 por kg | digitado 5.4900 por kg
boulangerie | E20261103-02 | Farinha de Trigo Superiore | Farinha de trigo tipo 0 | g | 1 kg | 1000.0000 | 1000.0000 | 0.00549000 | 5.49 por kg | digitado 5.4900 por kg
boulangerie | E20261103-03 | Farinha de Trigo Superiore | Farinha de trigo tipo 0 | g | 4 kg | 4000.0000 | 4000.0000 | 0.00549000 | 5.49 por kg | digitado 5.4900 por kg
boulangerie | E20261103-04 | Farinha de Trigo Superiore | Farinha de trigo tipo 0 | g | 2 kg | 2000.0000 | 2000.0000 | 0.00549000 | 5.49 por kg | digitado 5.4900 por kg
boulangerie | E20261103-11 | Farinha de Trigo Tipo Nuvola | Farinha de trigo tipo 0 | g | 4 kg | 4000.0000 | 4000.0000 | 0.03790000 | 37.90 por kg | digitado 37.9000 por kg
boulangerie | E20261103-14 | Itapan Melhorador de Farinha | Melhorador de farinha | g | 500 g | 500.0000 | 500.0000 | 0.02604000 | 26.04 por kg | digitado 26.0400 por kg
(16 rows)
```

## 7. Lotes já salvos em produção (somente leitura; nada foi corrigido)

16 lotes da organização `boulangerie`. "Custo gravado" é o número no banco (R$ por g); "equivale a" é o mesmo número por kg; "digitado" é o que foi escrito na entrada (R$ por kg).

| Lote | Item | Ingrediente | Quantidade | Custo gravado | Equivale a | Digitado |
|---|---|---|---|---|---|---|
| `E20261103-15` | Farinha de Cevada Integral | Farinha de Cevada | 350 g | R$ 0,02145000/g | **21,45/kg** | 21,4500 por kg |
| `E20261103-16` | Farinha de Cevada Integral | Farinha de Cevada | 350 g | R$ 0,02145000/g | **21,45/kg** | 21,4500 por kg |
| `E20261103-13` | Trigo Sarraceno | Farinha de Trigo sarraceno | 500 g | R$ 0,02390000/g | **23,90/kg** | 23,9000 por kg |
| `E20261103-09` | Nita Centeio — Nita | Farinha de centeio | 2 kg | R$ 0,02199000/g | **21,99/kg** | 21,9900 por kg |
| `E20261103-12` | Fubá Orgânico | Farinha de milho | 500 g | R$ 0,02299000/g | **22,99/kg** | 22,9900 por kg |
| `E20261103-10` | Farinha de Trigo Sêmola | Farinha de semolina | 2 kg | R$ 0,03390000/g | **33,90/kg** | 33,9000 por kg |
| `E20261103-08` | Nita 100% Integral | Farinha de trigo integral | 2 kg | R$ 0,00699000/g | **6,99/kg** | 6,9900 por kg |
| `E20261103-05` | Farinha de Trigo Doppio Zero | Farinha de trigo tipo 0 | 1 kg | R$ 0,02680000/g | **26,80/kg** | 26,8000 por kg |
| `E20261103-06` | Farinha de Trigo Doppio Zero | Farinha de trigo tipo 0 | 3 kg | R$ 0,02680000/g | **26,80/kg** | 26,8000 por kg |
| `E20261103-07` | Farinha de Trigo Nita 00 | Farinha de trigo tipo 0 | 4 kg | R$ 0,01799000/g | **17,99/kg** | 17,9900 por kg |
| `E20261103-01` | Farinha de Trigo Superiore | Farinha de trigo tipo 0 | 1 kg | R$ 0,00549000/g | **5,49/kg** | 5,4900 por kg |
| `E20261103-02` | Farinha de Trigo Superiore | Farinha de trigo tipo 0 | 1 kg | R$ 0,00549000/g | **5,49/kg** | 5,4900 por kg |
| `E20261103-03` | Farinha de Trigo Superiore | Farinha de trigo tipo 0 | 4 kg | R$ 0,00549000/g | **5,49/kg** | 5,4900 por kg |
| `E20261103-04` | Farinha de Trigo Superiore | Farinha de trigo tipo 0 | 2 kg | R$ 0,00549000/g | **5,49/kg** | 5,4900 por kg |
| `E20261103-11` | Farinha de Trigo Tipo Nuvola | Farinha de trigo tipo 0 | 4 kg | R$ 0,03790000/g | **37,90/kg** | 37,9000 por kg |
| `E20261103-14` | Itapan Melhorador de Farinha | Melhorador de farinha | 500 g | R$ 0,02604000/g | **26,04/kg** | 26,0400 por kg |

Esses números foram digitados na coluna antiga "R$ por kg"; continuam valendo como R$/kg. Se algum deles era na verdade o **valor pago** da compra (ex.: R$ 22,99 pagos por 500 g, digitados como R$ 22,99/kg), o certo é R$ 45,98/kg e a correção é feita lote a lote em **Corrigir custo**. Quais corrigir é decisão sua; eu não corrigi nenhum.

## 8. Rollback

Só se a comparação falhasse (não falhou). No host:

1. `GESTAO_IMAGE=lojadepaes-gestao:005a-20261103` em `/opt/lojadepaes-gestao/deploy/.env` e `docker compose -f deploy/docker-compose.prod.yml --env-file deploy/.env up -d --force-recreate gestao-api` (a imagem 005A segue no host). A migração é aditiva: a imagem antiga ignora as colunas e tabelas novas.
2. Se os dados precisassem voltar: restaurar `/opt/lojadepaes-gestao/backups/gestao-pre006.dump` (`pg_restore`), com o `gestao-api` parado.

## 9. Decisões e pontos para você

- **Precisão do custo do lote**: o banco guarda `NUMERIC(18,8)` (R$/g). Não alarguei a coluna porque só são permitidas migrações aditivas. O valor pago não é arredondado antes de gravar; a tela arredonda a 2 casas.
- **Corrigir custo com valor pago** vale para a quantidade **comprada** no lote (a soma das entradas dele), não para o saldo de hoje. Depois da correção, o `valor_total` das linhas da entrada passa a seguir o custo corrigido; `valor_pago` e o preço digitado ficam como foram escritos.
- **Trocar o modo da coluna** com linhas já digitadas reinterpreta os números; a linha cinza "= R$ …" deixa isso visível antes de gravar.
- **Embalagem sem ingrediente escolhido ainda**: a linha mostra só `= R$ 22,99/emb`; o "por kg" aparece quando o ingrediente (a unidade do conteúdo) está confirmado.
- **Histórico de troca**: a troca gera um movimento de junção de quantidade 0 ligado ao item, e a lista do histórico o mostra como "Troca de ingrediente".
