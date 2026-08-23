# Modelo de dados — rotulagem

Migração `0017_labeling_compliance`. UUID, `timestamptz`, `numeric`. FKs compostas por organização. Índices únicos, sem `UniqueConstraint`.

Tabelas: `labeling_dossier`, `labeling_dossier_version`, `labeling_applicability_profile`, `labeling_assessment`, `labeling_finding`, `labeling_evidence`, `labeling_review`, `labeling_nutrition_candidate`, `labeling_nutrition_line`, `labeling_front_of_pack`, `labeling_ingredient_candidate`, `labeling_warning_candidate`, `labeling_mandatory_item`, `labeling_label_candidate`, `labeling_invalidation`, `labeling_command`.

Avaliações, achados, evidências e decisões são append-only. Exclusão física bloqueada. Nova avaliação gera nova versão. Perfil novo não reescreve o snapshot antigo.
