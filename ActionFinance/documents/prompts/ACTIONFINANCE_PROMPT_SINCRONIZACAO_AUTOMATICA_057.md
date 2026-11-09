# ACTIONFINANCE — Prompt 057 · Sincronização automática de recebimentos por loja

## Objetivo
Hoje os recebimentos do ActionHub Pay só entram no Finance quando alguém clica em **Sincronizar recebimentos**. Em 7 dias não houve nenhuma chamada. O Finance passa a sincronizar sozinho, loja por loja, de tempos em tempos. Isso é a base da futura tela do dono (Desenho 001).

## Regras
- **Não alterar a Spider, a Loja de Pães nem o Hub.** Usar exatamente a chamada que já existe (`LIST_EXTERNAL_PAYMENTS`, contrato 1.4).
- Cada loja (empresa) é sincronizada isoladamente: dados, logs e falhas nunca se misturam, e a falha de uma não impede as outras.
- Testes: só os da área de recebimentos integrados/sincronização. Não rodar a suíte inteira.
- Sem dados fictícios em produção.

## Passos
0. **SSH:** atualizar a regra SSH para o IP público atual desta máquina (abrir a nova, testar, só então fechar a antiga).
1. **Investigar antes** (sem alterar): o serviço que o botão Sincronizar usa, o bloqueio que impede duas sincronizações da mesma empresa e onde fica o histórico de execuções ("Última execução"). Registrar no relato.
2. **Implementar no backend:**
   - Um agendador que, a cada `actionfinance.pay-sync.interval` (padrão **30 min**), percorre as empresas com a integração Pay ativa e chama **o mesmo serviço** do botão, uma empresa por vez.
   - Respeitar o bloqueio por empresa: se houver sincronização manual em curso, pular essa empresa no ciclo.
   - Garantir uma única execução do ciclo, mesmo com mais de uma task (lock no PostgreSQL, por exemplo advisory lock).
   - Registrar cada execução com a origem **Automática** ou **Manual**. Se o histórico atual não tiver onde guardar a origem, criar a migração **V26** só com essa coluna, com padrão `MANUAL` para os registros antigos.
   - Desligado por propriedade nos perfis `local-demo` e de teste. Ligado em produção.
3. **Interface (mínimo):** na tela de recebimentos do Pay, "Última execução" passa a mostrar a origem e o horário, por exemplo "Automática · 15:30". Nada mais muda na interface neste prompt.
4. **Testes da área:**
   - o ciclo chama o serviço uma vez por empresa ativa;
   - pula a empresa bloqueada;
   - a falha de uma empresa não interrompe as outras;
   - a origem fica registrada;
   - uma repetição sem novidades não grava nada novo.
5. **Publicar** (versão **0.2.12**):
   - Se houve V26: snapshot RDS `actionfinance-pre-v26-<data>` e task de migração como no 054R1. Flyway continua desligado na web.
   - Nova task definition web (`:29`). Retorno: `:28` (0.2.11). Se houve V26, registrar que reverter a task não remove a coluna.
6. **Verificar em produção** (sem inserir dados):
   - aguardar um ciclo;
   - o log do Finance mostra uma execução automática por empresa, com contadores (incluídos, atualizados, sem mudança);
   - a tela mostra "Automática · hh:mm";
   - health 200.

## Entrega
- `documents/reviews/ACTIONFINANCE_REV_SINCRONIZACAO_AUTOMATICA_057.md`, com o que a investigação achou, o que mudou, a versão, a task, a migração (se houve), o retorno, os testes executados e a evidência do primeiro ciclo.
- Copiar este prompt para `documents/prompts/`.
- Commit, push e deploy.

## Aceite
Sincronização automática rodando em produção a cada 30 min, isolada por loja, com a origem visível, sem alteração na Spider e sem duplicar recebimentos.
