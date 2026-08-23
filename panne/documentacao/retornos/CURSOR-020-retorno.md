# CURSOR-020 — Retorno

Implementação do primeiro recorte de Conformidade e Rotulagem sobre a base versionada `2b478e2d5f12ce89a9e812f36414a37697075c67`. Sem commit, push ou deploy. CURSOR-021 não iniciado.

## 1. Base e HEAD

- Branch `main` alinhada a `origin/main`.
- HEAD permanece `2b478e2d5f12ce89a9e812f36414a37697075c67` (`docs(panne): record recipe and AI checkpoint`).
- Trabalho local não commitado, restrito a `panne/`.
- Lixo local `panne/.tmp-chrome-017/` permanece fora do escopo e não deve ser versionado.

## 2. Isolamento

- Somente `panne/`.
- Sem acesso a MySQL, FTP legado ou aplicações irmãs.
- Sem leitura ou gravação de `.env`.
- Runtime de teste usa `docker exec leaction_db printenv` e arquivo temporário fora do repositório.

## 3. Fontes verificadas (acesso 2026-08-23)

| Código | Força | Vigência considerada |
|---|---|---|
| RDC 429/2020 | ato vigente | 2022-10-09 |
| IN 75/2020 | ato vigente | 2022-10-09 |
| RDC 727/2022 | ato vigente | 2022-09-01 |
| Lei 10.674/2003 | ato vigente | 2003-05-19 |
| Notícia Anvisa 2022-10-09 | orientação oficial | não cria obrigação |

Consulta pública, minuta, AIR e Q&A não fundamentam obrigação. Ver [FONTES-OFICIAIS-ROTULAGEM.md](../regulatorio/FONTES-OFICIAIS-ROTULAGEM.md).

## 4. Reconciliação

- Motor fechado: `compliance.engine` (estados mapeados; vocabulário do motor intacto).
- Nutrição técnica: `nutrition_calculation` / `calculation_engine.nutrition` — sem alteração do algoritmo `technical_nutrition_raw`.
- Grounding: biblioteca de conhecimento existente; orientação ≠ norma.
- Formulação: snapshot de `formula_lab` e tipo `composite`.
- IA: sem avaliação, publicação ou aprovação. Explicação futura exige selo, fontes e confirmação humana.

## 5. Banco e head

Alembic head: `0017_labeling_compliance` (revises `0016_recipe_ai_assistant`).

## 6. Tabelas

`labeling_dossier`, `labeling_applicability_profile`, `labeling_dossier_version`, `labeling_assessment`, `labeling_finding`, `labeling_evidence`, `labeling_review`, `labeling_nutrition_candidate`, `labeling_nutrition_line`, `labeling_front_of_pack`, `labeling_ingredient_candidate`, `labeling_warning_candidate`, `labeling_mandatory_item`, `labeling_label_candidate`, `labeling_invalidation`, `labeling_command`.

UUID, `timestamptz`, `numeric`, FKs compostas por organização, índices únicos.

## 7. Perfil de aplicabilidade

Versionado, explícito e nunca inferido pelo nome do produto ou da organização. Organização e estabelecimento ficam no dossiê; o perfil carrega fatos de embalagem, canal, estado físico, categoria confirmada, área, conteúdo líquido, porções, finalidade e mercado. Campo ausente ou categoria não confirmada → `incomplete` → `insufficient_context`. `not_applicable` só com perfil completo e inaplicabilidade comprovada (não embalado, mesmo estabelecimento ou a pedido, e sem embalagem na ausência do consumidor).

## 8. Cálculo nutricional regulatório

Projeção versionada em cinco camadas: técnico bruto, regulatório, declarado, apresentado e evidência. Valores por 100 g, por porção, medida caseira, porções por embalagem, nutrientes obrigatórios, %VD, arredondamento e notas. Nutriente obrigatório ausente ≠ zero.

## 9. Porção e medida caseira

Catálogo Python da IN 75/2020 Anexo I: `pao` 50 g, `bolo` 60 g, `biscoito` 30 g, `massa` 80 g. Sugestão exige `category_confirmed`. Categoria ambígua ou fora do catálogo deixa o perfil incompleto.

## 10. Rotulagem frontal

Sólidos e semissólidos, `Decimal`: açúcares adicionados ≥ 15 g/100 g; gordura saturada ≥ 6 g/100 g; sódio ≥ 600 mg/100 g. Ausência de qualquer um → conclusão incompleta (não presume ausência de lupa). Gera decisão e representação candidata, não arte-final.

## 11. Ingredientes

Lista candidata em ordem decrescente; compostos via `parent_ingredient_version_id` e tipo `composite`; aditivos só com função e identidade registradas; lacunas explícitas. Sem invenção de denominação legal.

## 12. Alergênicos, lactose e glúten

`CONTÉM` só com `IngredientAllergen.presence = contains`. Fórmula sem alergênico não prova ausência. `PODE CONTER` e lactose ficam em `insufficient_evidence` sem evidência de processo. Glúten: “contém Glúten” com evidência, ou pendência pela Lei 10.674/2003. Sem “não contém Glúten” automático.

## 13. Informações obrigatórias

Checklist controlado (denominação, ingredientes, advertências, conteúdo líquido, origem, lote, validade, conservação, preparo, responsável, registro). Vazio permanece pendente. Sem texto inventado.

## 14. Alegações

Campo `claim` no item obrigatório. Alegação informada vira candidata com `manual_review_required`. Sem autorização automática de alegações nutricionais, funcionais, de saúde, artesanais, naturais ou de ausência.

## 15. Regras e estados

Motor reutilizado. Achados usam `pass`, `fail`, `insufficient_evidence`, `insufficient_context`, `manual_review_required`, `not_applicable`. Soma dos achados não vira selo. `certified` e `conforme_anvisa` permanecem `false`.

## 16. Evidências e citações

Cada achado registra regra, fato, esperado, encontrado, evidência, fonte, versão, localizador, data, explicação técnica e ação. Fontes apontam à biblioteca; orientação não executa.

## 17. Versões candidatas

Snapshot imutável (produto, tabela, lupa, ingredientes, advertências, obrigatórios, pendências, achados, fontes, decisão). Nova avaliação gera nova versão. Invalidação é evento auditável.

## 18. Revisão humana

Decisões `accepted`, `rejected`, `needs_changes`. Após revisão, edição do candidato é bloqueada. Revisão não certifica.

## 19. Interface

Domínio horizontal **Conformidade**: Visão geral, Dossiês, Avaliações, Rótulos candidatos, Fontes e normas. Sem menu “Cadastros”. Criação guiada, detalhe, perfil, achados, editor controlado, comparação, revisão, visualização e impressão A4 com marca d’água.

## 20. Assistente

Onze etapas determinísticas, progresso, pendências, minimizar/dispensar/retomar, próxima ação. Não bloqueia navegação e não declara aprovação.

## 21. Permissões

`labeling.read`, `labeling.dossier.create`, `labeling.evaluate`, `labeling.candidate.edit`, `labeling.review`, `labeling.render`, `labeling.invalidate`, `regulatory.source.read`. Sem permissão genérica de certificação. Cognito groups e `legacy_role_label` não autorizam.

## 22. RLS

`ENABLE` + `FORCE` em todas as tabelas 0017. Política default deny por `organization_id = panne_current_org_id()`. Isolamento A/B coberto. Runtime sem fallback administrativo. Tabelas não entram em `ORGANIZATIONAL_TABLES`.

## 23. Migrações

`0017_labeling_compliance` reversível. Testes: downgrade/reaplicação, `0001 → head`, head = `0017_labeling_compliance`.

## 24. Testes backend

Python 3.12.14 (`python:3.12-slim-bookworm`): **223 aprovados**, **1 ignorado** (`test_ai_bedrock_live`). Baseline anterior: 215 + 1 ignorado. Sem chamadas externas nos testes comuns.

## 25. Testes frontend

`vitest`: **64 aprovados** (55 + 9 de rotulagem). Typecheck, lint e build deste ciclo já executados no recorte; regressão de testes reconfirmada. Impressão chama `window.print()` sem POST. Sem expressão automática de conformidade.

## 26. Documentação

ADR, fontes, perfil, modelo, regras, tabela, lupa, ingredientes, revisão, RLS, limitações, evidências visuais, prompt e este retorno. `INDICE.md` atualizado. Evidências em `panne/documentacao/evidencias/cursor-020/`.

## 27. Riscos e limitações

- Recorte de sólidos/semissólidos de panificação; líquidos fora da avaliação frontal produtiva.
- Catálogo de porção cobre pão, bolo, biscoito e massa.
- Sem BPF, laboratório, registro, certificação, arte-final ou PDF certificado.
- `PODE CONTER`, lactose e ausência de glúten exigem evidência ainda não modelada de processo.
- Marca d’água e disclaimer não substituem revisão humana responsável.

## 28. Commit, push e deploy

Não houve commit, push nem deploy. CURSOR-021 não foi iniciado.
