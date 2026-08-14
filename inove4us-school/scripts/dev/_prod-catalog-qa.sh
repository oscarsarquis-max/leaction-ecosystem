#!/bin/bash
set -euo pipefail
set -a
# shellcheck disable=SC1091
. /var/www/inove4us-school/.env
set +a
export PGPASSWORD="$DB_PASS"
export PGSSLMODE="${DB_SSLMODE:-require}"
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -v ON_ERROR_STOP=1 <<'SQL'
\pset pager off

SELECT
  count(*) AS total,
  count(*) FILTER (WHERE origem='padrao') AS padrao,
  count(*) FILTER (WHERE origem<>'padrao') AS nao_padrao,
  count(*) FILTER (WHERE coalesce(nome,'')='' OR coalesce(descricao,'')='') AS sem_nome_ou_desc,
  count(*) FILTER (WHERE passos_execucao IS NULL OR jsonb_typeof(passos_execucao)<>'array' OR jsonb_array_length(passos_execucao)=0) AS passos_vazios,
  count(*) FILTER (WHERE descricao ILIKE '%lorem%' OR nome ILIKE '%lorem%' OR descricao ILIKE '%placeholder%' OR descricao ILIKE '%a detalhar%' OR descricao ILIKE '%ipsum%') AS placeholder,
  count(*) FILTER (WHERE length(coalesce(descricao,'')) < 20) AS desc_curta,
  count(*) FILTER (WHERE ativo IS NOT TRUE) AS inativas
FROM school_metodologias_catalogo;

SELECT nome, count(*) AS n
FROM school_metodologias_catalogo
GROUP BY nome
HAVING count(*) > 1
ORDER BY n DESC, nome;

SELECT categoria, count(*) AS n
FROM school_metodologias_catalogo
WHERE origem='padrao'
GROUP BY categoria
ORDER BY categoria;

SELECT
  codigo,
  nome,
  categoria,
  length(descricao) AS desc_len,
  jsonb_array_length(coalesce(passos_execucao,'[]'::jsonb)) AS passos,
  ativo
FROM school_metodologias_catalogo
WHERE origem='padrao'
ORDER BY categoria, nome;
SQL
