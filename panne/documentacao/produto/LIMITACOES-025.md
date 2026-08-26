# Limitações CURSOR-025

- Turnos do produto são manhã, tarde e noite. Madrugada usa o código `night`.
- Áreas do quadro continuam fornos, masseira, bancada e embalagem.
- Trial do laboratório só conhece planned/in_progress/completed/cancelled.
- Algumas jornadas de estoque/IA/custos podem ficar em lacuna se um comando de domínio recusar o recorte; o manifesto registra o motivo.
- No `panne_demo` desta execução, compras (requisição/pedido) ficaram em `estoque:compras:recurso_nao_encontrado`. Lotes e reservas persistiram.
- O banco lógico `panne` não recebe demo.
- Não há migração `0021`.
- CURSOR-026 não foi iniciado.
