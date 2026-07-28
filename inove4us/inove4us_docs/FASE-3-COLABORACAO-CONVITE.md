# Fase 3/3 — Colaboração por convite pontual

## Passo 0 — auditoria

| Item | Achado |
|------|--------|
| Dono do desafio | `inove_desafios.id_clie` |
| Responsável da execução (antes) | **Implícito** — sempre `inove_agenda_eventos.id_clie` (= mesmo professor). Fase 2 replicava só para o logado. |
| E-mail | `mail.py` + SES (boto3); `EMAIL_DEV_MODE=1` loga no stderr |
| Login | `/acesso` — e-mail + código (`/api/auth/*`); sem deep-link `?next=` até esta fase |
| Auth padrão | 401 sem sessão; 404 se recurso de outro (opaco) |

## Decisões desta fase

1. **`id_clie_responsavel`** em cada aula — explícito; backfill = `id_clie`. Dono do desafio ≠ necessariamente responsável da execução.
2. **Convite pontual** em `inove_desafio_colaboradores` — sem grafo social.
3. **Visibilidade cruzada:**
   - Dono: vê todas as execuções + Kanban de colaboradores em **leitura**.
   - Colaborador: vê **resumo** (progresso + responsável) de todas; abre/edita **só a própria** execução.
4. **Sem IA** no convite/aceite/criação de parte.
5. **Billing:** recurso coerente com cadastro estruturado (Etapas 1–2, plano pago). Gate de cobrança **não** implementado nesta fase — só sinalizado.

Migration: `015_inove_desafio_colaboradores.sql`.
