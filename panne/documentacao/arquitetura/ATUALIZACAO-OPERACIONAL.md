# Atualização dos dados no modo operacional

A tela `/producao/ordens/:orderId/executar` atualiza:

- manualmente, pelo recarregamento após conflito 409;
- automaticamente após comando concluído com sucesso;
- por polling leve de 20 s, somente nesta tela.

O polling:

- para quando `document.hidden` é verdadeiro;
- é cancelado ao sair da rota ou trocar de organização;
- não sobrescreve formulário com `dirty`;
- não corre enquanto houver comando pendente;
- não é substituto de integração em tempo real.

Não há WebSocket nem SSE.
