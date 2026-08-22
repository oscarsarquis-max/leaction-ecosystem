# Contingência e operação digital

Não há escolha definitiva de arquitetura offline neste ciclo.

## Comparativo

| Modo | Prós | Riscos |
|---|---|---|
| Sempre conectado | Fonte única imediata, sem fila | Queda de rede para o turno |
| Leitura offline + fila de apontamentos | Continua o trabalho | Relógio, duplicidade, conflito no retorno |
| Terminal compartilhado | Barato | Identidade do operador fraca |
| Tablet individual | Identidade clara | Custo, perda, higiene |
| Tablet por estação | Equilíbrio | Quem estava logado? |
| Ficha impressa de contingência | Já é o hábito | Ficha velha; retrabalho de digitação |

## Pontos a validar com usuários

- conflitos (dois apontamentos do mesmo consumo);
- sincronização (ordem dos eventos);
- identificação do operador no terminal compartilhado;
- relógio do dispositivo vs servidor;
- toque duplo = duplicidade (idempotência por correlação);
- retorno da conexão (fila rejeita comando sobre ordem já cancelada).

A ficha impressa **já** é a contingência oficial. Qualquer offline digital é extra e depende de descoberta em padaria real.
