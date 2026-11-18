# ACTIONFINANCE — Prompt 055 · Verificação do estado publicado (somente leitura)

## Objetivo
Confirmar o que está servido hoje em actionfinance.actionhub.com.br e comparar com o último registro (054R1: 0.2.11, `actionfinance-web:28`, V25). Devolver um relato curto de divergências. **Não corrigir nada.**

## Regras
- Somente leitura. Proibido: deploy, build de imagem, task de migração, escrita no banco, alterar AWS/DNS/Cognito/ALB, criar dado fictício, `git commit/checkout/reset`.
- Este prompt não tem deploy, então não tem passo 0 (SSH).
- Não rodar testes.
- Não registrar segredos, tokens, e-mails ou valores de clientes no relato.
- Se um comando exigir permissão que você não tem, registre "não verificado: motivo" e siga em frente.

## Passos
1. **Código local** (`C:\Projetos\ActionFinance`): branch, HEAD, `git status --short` (só contar os arquivos), se `5be64152` está no histórico e a lista de arquivos alterados entre `5be64152` e HEAD. Versão em `backend/pom.xml` e `frontend/package.json`.
2. **Público** (sem sessão): `GET /` (nomes de `index-*.js` / `index-*.css`), `GET /actuator/health`, `GET /api/v1/financial-accounts` (esperado 401) e a versão servida, pelo mesmo meio usado no 054R1.
3. **AWS, região us-east-2, só leitura:**
   - Serviço ECS do AF: task definition em uso, desired/running, digest da imagem, rolloutState, data do último deployment.
   - `actionfinance-px-tg`: saúde dos alvos. Regra de host com prioridade 6 no `paneldx-alb`: presente e apontando para esse TG.
   - RDS `actionfinance`: status, engine, classe, Multi-AZ, retenção de backup, último snapshot automático. O snapshot `actionfinance-pre-v25-20261022` ainda existe?
4. **Logs** (CloudWatch do serviço web, últimos 7 dias): quantidade de ERROR e de respostas 5xx e as 5 mensagens de erro distintas mais frequentes (resumidas, sem dados pessoais).

## Entrega
- `documents/reviews/ACTIONFINANCE_REV_ESTADO_PUBLICADO_055.md` contendo:
  - uma tabela **Item | Registrado no 054R1 | Encontrado hoje | OK/Divergente**;
  - divergências e riscos em até 10 linhas;
  - a lista "não verificado", com o motivo de cada item.
- Copiar este prompt para `documents/prompts/ACTIONFINANCE_PROMPT_ESTADO_PUBLICADO_055.md`.
- Não alterar outros documentos.

## Aceite
Tabela completa, nenhuma alteração em código, infraestrutura ou banco, e o relato devolvido ao Oscar.
