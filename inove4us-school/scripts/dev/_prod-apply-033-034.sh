#!/bin/bash
set -euo pipefail
sed -i 's/\r$//' /tmp/033_school_unidades_enriquecimento.sql /tmp/034_school_curso_disciplina_nn.sql
set -a
# shellcheck disable=SC1091
. /var/www/inove4us-school/.env
set +a
export PGPASSWORD="$DB_PASS"
export PGSSLMODE="${DB_SSLMODE:-require}"

run() {
  psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -v ON_ERROR_STOP=1 "$@"
}

echo "=== counts ==="
run -c "SELECT (SELECT count(*) FROM school_instituicoes) AS inst, (SELECT count(*) FROM school_cursos) AS cursos, (SELECT count(*) FROM school_turmas) AS turmas, (SELECT count(*) FROM school_disciplinas) AS disc;"

echo "==> 033"
run -f /tmp/033_school_unidades_enriquecimento.sql
run -c "INSERT INTO school_schema_migrations(filename) VALUES ('033_school_unidades_enriquecimento.sql') ON CONFLICT DO NOTHING;"

echo "==> 034"
run -f /tmp/034_school_curso_disciplina_nn.sql
run -c "INSERT INTO school_schema_migrations(filename) VALUES ('034_school_curso_disciplina_nn.sql') ON CONFLICT DO NOTHING;"

echo "=== confirm ==="
run -c "SELECT filename FROM school_schema_migrations WHERE filename LIKE '03%' ORDER BY 1;"
run -c "SELECT to_regclass('public.school_curso_disciplinas') AS nn, to_regclass('public.school_unidade_equipe') AS equipe;"
echo "curso_id leftover on disciplinas:"
run -tAc "SELECT column_name FROM information_schema.columns WHERE table_name='school_disciplinas' AND column_name='curso_id';"
echo DONE
