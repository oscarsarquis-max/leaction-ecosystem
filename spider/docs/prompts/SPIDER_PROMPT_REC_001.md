# SPIDER — Prompt REC-001 · Reconciliação da rota real Pay → Spider → Finance (somente leitura)

## Objetivo
Descobrir o que está de fato no ar hoje na rota que leva os recebimentos da Loja de Pães (ActionHub Pay → Spider → ActionFinance), e o que existe no Git da Spider. Devolver um relato curto. **Não corrigir nada.**

Motivo: a Spider está publicada em spider.actionhub.com.br. Ela redireciona ao Monitor (`monitor.spider.actionhub.com.br`), com login no Cognito `spider-prod-monitor`. Os dados reais da Loja de Pães já transitam pela Spider de produção. O relatório da Spider de 09/11 está defasado: fala em infraestrutura "não comprovada" e "Demo Only". Precisamos registrar como a produção está montada e como guarda o estado. Ignorar qualquer ambiente sandbox.

## Regras
- Somente leitura. Proibido: deploy, build, alterar AWS/DNS/ALB/Cognito/secrets, chamar endpoint que grave ou dispare sincronização, criar dado, `git commit/checkout/reset`.
- Não tocar na Loja de Pães nem no Hub.
- Não rodar testes.
- Não registrar segredos, tokens, e-mails ou valores de clientes.
- Se faltar permissão para algo, registre "não verificado: motivo" e siga em frente.

## Passos
1. **Git** (`C:\Projetos\spider` e o monorepo `leaction-ecosystem`): branch, HEAD, contagem de `git status --short` e onde fica o código da Spider. Dos documentos citados no relatório (ARCH-014 a 017, SATELLITE-CONTRACT-V1, MONITOR-001, MON-001A, CAP, CTX, SAT-003), quais existem, com caminho e data do último commit.
2. **Código da rota Finance:** localizar no código da Spider o que atende o ActionFinance e o que fala com o ActionHub Pay (controllers, adapters, rotas). Para cada peça, registrar:
   - endpoint e método;
   - autenticação;
   - onde o estado é guardado (memória ou banco);
   - como a idempotência funciona;
   - se usa o Satellite Contract V1 ou um caminho próprio;
   - **isolamento por loja:** como a loja (empresa) é identificada em cada etapa (Pay → Spider → Finance), se credenciais, filas, caches e o estado do Monitor ficam separados por loja, e qualquer ponto em que dados de duas lojas possam se misturar.
3. **AWS, us-east-2, só leitura:**
   - Cluster e serviços da Spider de produção: task definition em uso, imagem e digest, desired/running, último deployment, variáveis de ambiente (só os nomes, sem valores). Confirmar na configuração do Finance o endpoint da Spider que ele usa.
   - Persistência: existe RDS ou volume? O que se perde num restart?
   - DNS e ingresso de `spider.actionhub.com.br`, `api.`, `monitor.` e `callbacks.`: o que resolve e para onde aponta.
4. **Logs** (últimos 7 dias do serviço da rota): quantas chamadas do Finance e quantas ao Pay foram feitas, quantos erros, as 5 mensagens de erro mais frequentes (resumidas) e quantos restarts da task.

## Entrega
- Relato `SPIDER_REV_RECONCILIACAO_ROTA_FINANCE_001.md` na pasta de revisões da Spider (registrar o caminho usado), contendo:
  - um mapa da rota em uma tabela: **Etapa | Componente | Endpoint | Estado guardado em | Evidência**;
  - documentos encontrados e não encontrados;
  - riscos para o uso em produção, em até 10 linhas;
  - a lista "não verificado".
- Copiar este prompt para a pasta de prompts da Spider.

## Aceite
Rota mapeada com evidência, nenhuma alteração feita e o relato devolvido ao Oscar.
