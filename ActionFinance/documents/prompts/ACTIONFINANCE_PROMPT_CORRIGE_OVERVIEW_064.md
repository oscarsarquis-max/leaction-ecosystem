# ACTIONFINANCE — Prompt 064 · Corrigir o erro do Início em produção (urgente)

Em produção (0.2.15, `actionfinance-web:32`), o Oscar entrou como gestor da Loja de Pães. O Início mostra só **"Não foi possível concluir a operação."**: o `GET /api/v1/overview` falha para essa empresa. O cabeçalho, o CNPJ e a identidade estão certos.

## Regras
- Corrigir só o backend do overview. Não alterar a Spider, a Loja nem o Hub. Sem mudança de banco (se parecer necessária, **parar e relatar**).
- Não mexer no frontend: o Claude cuida dele.
- Testes: só os do overview.

## Passos
0. **SSH:** atualizar a regra para o IP público atual (abrir a nova, testar, só então fechar a antiga).
1. **Diagnosticar** pelo CloudWatch do serviço web, entre 18:00 e 18:10 UTC de hoje: o status e o stack trace do `/api/v1/overview`. Registrar a causa (consulta, dado nulo, conta sem saldo inicial, período, permissão...).
2. **Corrigir** de forma que nenhum bloco derrube os outros: se uma fonte falhar ou não tiver dados, aquele bloco volta como `nao_apurado` e o resto responde normalmente. Logar o erro do bloco, sem dados pessoais.
3. **Teste** que reproduza o caso real: a mesma configuração da Loja (recebimentos integrados, nenhum título, extrato sem linhas, uma conta sem saldo inicial). Mais um teste: a falha de um bloco não derruba a resposta.
4. **Publicar 0.2.16:** nova task web; retorno para `:32`.
5. **Verificar:** chamar o endpoint autenticado não é possível pelo Cursor, então conferir no log, depois que o Oscar abrir o Início, que a resposta saiu 200.

## Entrega
- `documents/reviews/ACTIONFINANCE_REV_CORRIGE_OVERVIEW_064.md`, com a causa, a correção, os testes, a versão, a task e o retorno.
- Copiar este prompt para `documents/prompts/`. Commit, push e deploy.
