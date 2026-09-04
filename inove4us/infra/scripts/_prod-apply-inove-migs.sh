#!/bin/bash
set -euo pipefail
set -a
# shellcheck disable=SC1091
. /tmp/inove-rds.env
set +a
export PGPASSWORD="$DB_PASS"
export PGSSLMODE="${DB_SSLMODE:-require}"
MIG=/tmp/inove-migs

run() {
  psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -v ON_ERROR_STOP=1 "$@"
}

echo "=== probe ==="
run -c "
SELECT
  to_regclass('public.inove_comunicados_escola') AS t021,
  to_regclass('public.inove_avisos_mesa') AS t024,
  to_regclass('public.inove_metodologia_overrides') AS t025,
  to_regclass('public.inove_pei_overrides_base') AS t026,
  to_regclass('public.inove_turmas') AS t027,
  to_regclass('public.inove_curso_disciplinas') AS t033;
"
echo "=== school_disciplina_id column ==="
run -tAc "SELECT column_name FROM information_schema.columns WHERE table_name='inove_disciplinas' AND column_name='school_disciplina_id';"

apply_if_missing() {
  local file="$1"
  local check_sql="$2"
  local present
  present=$(run -tAc "$check_sql" | tr -d '[:space:]')
  if [ -n "$present" ] && [ "$present" != "f" ]; then
    echo "skip $file (already present)"
    return 0
  fi
  echo "==> $file"
  sed -i 's/\r$//' "$MIG/$file"
  run -f "$MIG/$file"
}

# Apply in order; skip when signature object already exists.
apply_if_missing 021_inove_comunicados_escola.sql "SELECT to_regclass('public.inove_comunicados_escola')"
apply_if_missing 022_ctdi_clie_instituicao_b2b.sql "SELECT 1 FROM information_schema.columns WHERE table_name='ctdi_clie' AND column_name='instituicao_b2b_id'"
apply_if_missing 023_inove_agenda_alocacao_escola.sql "SELECT 1 FROM information_schema.columns WHERE table_name='inove_agenda_eventos' AND column_name='is_from_school'"
apply_if_missing 024_inove_avisos_mesa.sql "SELECT to_regclass('public.inove_avisos_mesa')"
apply_if_missing 025_inove_metodologia_overrides.sql "SELECT to_regclass('public.inove_metodologia_overrides')"
apply_if_missing 026_inove_pei_overrides.sql "SELECT to_regclass('public.inove_pei_overrides_base')"
apply_if_missing 027_inove_turmas.sql "SELECT to_regclass('public.inove_turmas')"
apply_if_missing 028_periodo_tipos_quinzenal_mensal.sql "SELECT 1 FROM pg_constraint WHERE conname LIKE '%periodo%quinzenal%' OR conname LIKE '%tipo_periodo%' LIMIT 1"
apply_if_missing 029_school_academic_mirror.sql "SELECT 1 FROM information_schema.columns WHERE table_name='inove_disciplinas' AND column_name='school_disciplina_id'"
apply_if_missing 030_aula_simples_ementa_topico.sql "SELECT 1 FROM information_schema.columns WHERE table_name='inove_aulas_simples' AND column_name='ementa_topico'"
apply_if_missing 031_origem_planejamento_escola.sql "SELECT 1 FROM information_schema.columns WHERE table_name='inove_importacoes_lote' AND column_name='canal'"
apply_if_missing 032_origem_convite_colaborador.sql "SELECT 1 FROM pg_constraint WHERE conname='chk_inove_agenda_eventos_origem' AND pg_get_constraintdef(oid) LIKE '%convite_colaborador%'"
apply_if_missing 033_inove_curso_disciplinas_nn.sql "SELECT to_regclass('public.inove_curso_disciplinas')"
apply_if_missing 034_inove_aula_ocorrencia.sql "SELECT 1 FROM information_schema.columns WHERE table_name='inove_agenda_eventos' AND column_name='ocorrencia_tipo'"
apply_if_missing 035_inove_avisos_mesa_professor.sql "SELECT 1 FROM information_schema.columns WHERE table_name='inove_avisos_mesa' AND column_name='professor_b2c_id'"

echo "=== confirm 034/035 ==="
run -c "
SELECT
  (SELECT 1 FROM information_schema.columns WHERE table_name='inove_agenda_eventos' AND column_name='ocorrencia_tipo') AS c034,
  (SELECT 1 FROM information_schema.columns WHERE table_name='inove_avisos_mesa' AND column_name='professor_b2c_id') AS c035;
"
echo DONE
