# Reformulação UX — Módulo de Importações

## Passo 0 — auditoria

### Textos visíveis (antes)

- Título: “Importar aulas e eventos”
- Ajuda: “Envie um JSON ou CSV…”
- Campo: “Arquivo (.json ou .csv)”
- Ajuda técnica: `id_externo`, `titulo`, `vinculo_pai_id_externo`
- Botões: “Importar arquivo”, “Relatório detalhado”, “Ver na agenda”
- Histórico: lista com “ok / erro”; tabela Linha / id_externo / Status / Mensagem

### Schema do arquivo (antes)

`id_externo` (obrig.), `titulo`, `data`, `tipo`, horários, instituição/curso/disciplina, `vinculo_pai_id_externo`, `observacoes`

### Fluxo (antes)

Único passo: enviar arquivo → grava direto. Sem pré-visualização.

### Campo Assunto / tema

- Grafo já lia `meta_json.tema` (nullable).
- **Decisão:** coluna física `inove_agenda_eventos.tema` (migration `012`) + espelho em `meta_json.tema` para o grafo.
- Importação: coluna “Assunto” → `tema`; linhas com mesmo assunto (+ mesma disciplina quando houver) encadeiam por data → `id_evento_pai`.
- `id_externo` deixa de ser pedido; gerado por hash estável `(id_clie, instituição, data, título, disciplina)`.

### API (depois)

| Método | Rota | Função |
|--------|------|--------|
| POST | `/api/importacoes/pre-visualizar` | Interpreta arquivo, **não grava** |
| POST | `/api/importacoes/confirmar` | Grava linhas já conferidas |
| POST | `/api/importacoes/aulas-eventos` | Mantido (compat / smoke): grava direto |
| GET | `/api/importacoes` | Histórico |
| GET | `/api/importacoes/:id` | Detalhe do lote (pendências) |

## Status da entrega

- Migration `012_inove_agenda_tema.sql`: coluna `tema` compartilhada (importação + grafo) — aplicada no DB local.
- Helpers: `backend/import_friendly.py` (mensagens + aliases + hash de identificador interno).
- FE: fluxo em 3 passos, associação de colunas, reordenação por arraste, edição inline, histórico em cartões.
- Glossário técnico removido da UI do professor.
- Endpoint legado `/aulas-eventos` permanece para smoke/compat.
- Exemplo amigável: `exemplos/importacao-planilha-amigavel.csv` (colunas com nomes diferentes).

### Validação local (2026-07-25)

- Pré-visualizar: 4 linhas, mapeamento automático (`Nome da aula`→título, `Dia`→data, `Assunto`→assunto).
- Confirmar: 3 aulas + 1 evento; 3 linhas com Assunto “Fotossíntese” encadeadas por data (`id_evento_pai` no primeiro).
- Legado `/aulas-eventos`: continua retornando 3 sucesso / 1 erro no exemplo técnico.
