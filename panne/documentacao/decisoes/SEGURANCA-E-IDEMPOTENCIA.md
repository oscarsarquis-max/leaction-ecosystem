# Segurança e idempotência

O backend autoriza todas as ações. A UI esconde controles sem permissão, mas não confia só na próxima ação da leitura. Sem HTML cru. Cache e rascunhos limpos na troca de organização e no logout. Token só em memória. Polling para ao sair. Sem stack, SQL ou token nos erros.
