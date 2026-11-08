-- GESTAO-006: consulta SÓ LEITURA dos lotes e dos custos gravados (antes e depois do deploy, para comparar).
--
--   docker exec -i infra-db-1 psql -U gestao_app -d gestao -v ON_ERROR_STOP=1 -A -F ' | ' \
--       < consulta-custos-lotes.sql
--
-- Uma linha por lote: organização · lote · item · ingrediente · quantidade comprada (como digitada) ·
-- saldo · custo gravado (R$ por g, ml ou un) · o mesmo custo em R$ por kg, L ou un · o que foi digitado.
-- O custo por kg/L/un é só uma leitura do número gravado (R$/g x 1000); nada é reinterpretado.
-- Usa só colunas que existem ANTES e DEPOIS da migração 0004: a mesma consulta nos dois momentos.
SET default_transaction_read_only = on;

SELECT o.nome_curto AS organizacao,
       l.codigo AS lote,
       i.nome AS item,
       g.nome AS ingrediente,
       g.unidade_base AS base,
       COALESCE((SELECT string_agg(trim(trailing '.' FROM trim(trailing '0' FROM el.quantidade::text)) || ' ' || el.unidade, ' + ' ORDER BY el.posicao)
                 FROM entrada_linhas el WHERE el.lote_id = l.id), '-') AS comprado,
       COALESCE((SELECT sum(el.quantidade_base) FROM entrada_linhas el WHERE el.lote_id = l.id), 0) AS comprado_base,
       COALESCE((SELECT sum(m.quantidade_base) FROM movimentos m WHERE m.lote_id = l.id), 0) AS saldo_base,
       l.custo_unidade_base AS custo_por_unidade_base,
       CASE
         WHEN l.custo_unidade_base IS NULL THEN 'sem custo'
         WHEN g.unidade_base = 'g'  THEN to_char(l.custo_unidade_base * 1000, 'FM999990.00') || ' por kg'
         WHEN g.unidade_base = 'ml' THEN to_char(l.custo_unidade_base * 1000, 'FM999990.00') || ' por L'
         ELSE to_char(l.custo_unidade_base, 'FM999990.00') || ' por un'
       END AS custo_por_kg_l_un,
       COALESCE((SELECT string_agg(
                  CASE
                    WHEN el.custo_informado IS NOT NULL THEN 'digitado ' || el.custo_informado::text || ' por ' || COALESCE(el.custo_por, '?')
                    ELSE 'sem custo'
                  END, ' + ' ORDER BY el.posicao)
                FROM entrada_linhas el WHERE el.lote_id = l.id), '-') AS digitado
FROM lotes l
JOIN itens_estoque i ON i.id = l.item_id
JOIN ingredientes g ON g.id = i.ingrediente_id
JOIN organizacoes o ON o.id = l.organizacao_id
ORDER BY o.nome_curto, g.nome, i.nome, l.codigo;
