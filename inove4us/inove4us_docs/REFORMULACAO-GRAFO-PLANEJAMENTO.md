# Reformulação do Grafo de Planejamento

## Passo 0 — auditoria

| Item | Achado |
|------|--------|
| Componente | `MapaRealizacoes.jsx` no topo da Mesa (`/mesa-do-inovador`) — **não** há rota `/grafo` |
| Lib | Nenhuma (SVG próprio). Layout atual = níveis por `id_evento_pai` (árvore esquerda→direita), não d3-force |
| API | `GET /api/agenda-eventos/grafo` → `{ nodes[], edges[] }` |
| Tema/assunto | **Não existe** coluna. Rótulo da cápsula = título do evento raiz da cadeia (`id_evento_pai` nulo no componente). `tema` na API fica nullable (opcional via `meta_json.tema`) |
| Clique | Painel próprio no mapa + `onSelectNode` foca a Agenda. Agenda usa **modal** de edição / navegação Kanban (`handleEventClick`) — não há drawer lateral separado |
| Accent | `brand-600` / `#e11d48` e `bordo` — uma cor de destaque para cápsulas |

## Decisões de UX

1. **Um período letivo por vez** no seletor. Default = primeiro período `em_curso` (rótulo `Instituição · período` se houver vários). Sem período cadastrado → sem seletor; só trilha “Sem disciplina vinculada”.
2. Eventos sem `disciplina_id` no range do período entram na trilha genérica.
3. Clique no nó dispara o **mesmo** `handleEventClick` da Agenda (via `openEventRequest`), não um painel duplicado no mapa.
4. Toggle eixo **semana / mês**: default mês se o período > 45 dias; senão semana.
