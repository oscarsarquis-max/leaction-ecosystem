# PRM_007 — Continuidade para encerramento da publicação

Data: 30/09/2026. Analista → Cursor. Mesmo PRM_007; não emitir ou iniciar PRM_008.

## Confirmações do proprietário

O proprietário confirmou que o nome **Loja de Pães** ficou visualmente correto na interface autenticada e pediu para prosseguir. Registrar login humano funcional e validação visual do Adendo 003, sem atribuir a essa confirmação prova de logout, CSRF ou recuperação do banco. O Adendo 003 está encerrado pelo analista com a confirmação visual do proprietário.

Não repetir correção de caracteres, migração de ALB ou testes locais já aceitos. Manter `actionfinance.actionhub.com.br` no ALB compartilhado, login `admin@actionhub.com.br` e contato `oscar@oscarsarquis.com.br`. Loja de Pães permanece sem CNPJ.

## 1. Concluir prova de logout e CSRF autenticados

Usar sessão de teste controlada no destino, com acesso autorizado. Não pedir senha, MFA ou cookie pelo chat, não extrair credenciais de perfil pessoal nem registrar tokens em evidências. Se houver necessidade de interação humana, preparar a jornada e pedir apenas que o proprietário execute o passo de entrada no navegador.

Provar, com a mesma configuração efetiva da aplicação publicada:

- Sessão autenticada acessa `/api/v1/access/me` com 200 e identifica a empresa autorizada.
- POST de logout sem token CSRF, e com token inválido, é recusado sem encerrar a sessão; GET autenticado subsequente continua 200.
- POST de logout com token válido encerra a sessão. Reutilizar o cookie anterior, apenas dentro do teste e sem expô-lo, não recupera autenticação: `/me` retorna 401.
- A interface limpa informações protegidas e permite nova entrada; não apresenta sucesso de saída quando o servidor recusou a operação.

Não criar pagamento, recebimento ou lançamento fictício na empresa real para testar CSRF. Logout é suficiente para esta prova residual, somado aos testes financeiros já aceitos. Se houver falha, corrigir somente a causa, executar testes pertinentes e registrar eventual nova imagem/digest.

## 2. Restaurar backup real do RDS em destino isolado

Executar o ensaio de recuperação previsto no PRM_007. Antes, identificar o banco de origem e o backup/snapshot real disponível, confirmar criptografia, rede privada e destino descartável. Restaurar para **nova instância/banco isolado**, nunca sobre o banco da produção, o volume local ou outro produto.

Preparar um plano curto com identificadores não sensíveis, custo transitório estimado, duração prevista, verificações e limpeza. O plano aprovado já prevê restore isolado; não pedir novamente aprovação geral. Se exigir gasto material além do escopo aprovado ou mudança em recurso compartilhado, explicitar somente essa diferença antes de executar.

Provar:

- Restauração concluída a partir de backup do RDS real e ponto temporal identificado, não somente dump do ensaio local.
- Versões/checksums Flyway compatíveis com a origem e integridade dos cadastros, vínculos, auditoria e fatos financeiros presentes no ponto restaurado. Se ainda não houver fatos, registrar zero sem inventar uma jornada em produção.
- Owners/grants corretos; runtime sem DDL e sem DELETE em fatos/auditoria. Não transformar usuário master em runtime para facilitar a prova.
- Invalidação das sessões no **banco restaurado**, preservando dados de negócio. Não invalidar sessões na produção.
- Procedimento reproduzível e tempo observado de recuperação. Distinguir tempo medido neste ensaio de compromisso formal de RTO/RPO.

Impedir que o ambiente restaurado envie mensagens, acione integrações ou seja exposto por DNS público. Usar segredos por canal seguro, sem valores em logs. Comparações com a origem devem considerar o instante do backup e eventuais escritas posteriores, sem exigir igualdade com uma base que continuou mudando.

Após coletar evidências, remover somente os recursos temporários criados para o ensaio, conferindo IDs/tags e dependências. Preservar origem, backups regulares, secrets operacionais, banco, serviço e ingresso de produção. Informar explicitamente que a limpeza terminou e se restou algum custo transitório.

## 3. Retorno para aceite final

Atualizar `ACTIONFINANCE_REV_007.md`, RUN/índice e salvar este texto em documents/prompts. Não criar nova rodada de revisão de todos os ciclos anteriores.

Entregar uma tabela curta: login humano (confirmado pelo proprietário), nome com acentos (confirmado), logout/CSRF autenticados, restore real isolado e limpeza. Para cada linha, resultado, data e evidência. Incluir URL, digest ECR completo efetivamente em uso, estado de backup/monitoramento e qualquer pendência operacional verdadeira, sem segredos.

Quando os dois gates residuais passarem, apresentar **“pronto para aceite final de publicação pelo analista”**. Não atribuir o aceite ao executor. Sem commit/push Git nem PRM_008 neste retorno.

## Próxima prioridade preservada

Após o encerramento do PRM_007, o próximo prompt será a primeira integração **ActionFinance → Spider → ActionHub Pay**, para pagamentos e recebimentos da Loja de Pães. ActionHub Pay executa pagamentos de todas as origens; ActionFinance centraliza gestão e acompanhamento; Panne origina compras e mantém estoque físico. Não implementar essa integração antecipadamente durante estas provas de publicação.
