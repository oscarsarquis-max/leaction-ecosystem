# Invariantes dos snapshots de produção

1. Gerados só na liberação, na mesma transação do estado `released`.
2. Guardam nome operacional, unidade (código e nome), quantidades líquida/bruta, fator, percentual do padeiro, farinha-base, sequência, algoritmo, versão e modo de arredondamento.
3. Etapas copiam título, instrução, duração, temperatura e unidade (`celsius`).
4. Hashes SHA-256 canônicos: materiais, etapas e combinação.
5. Depois de `released`, update/delete de snapshot é recusado no banco.
6. Mudança no cadastro de ingrediente não altera o snapshot.
7. Alocações de batelada somam exatamente o líquido do snapshot (Decimal, sem float).
8. Cancelamento preserva o snapshot.
