# Revisão humana e versionamento

Revisão (`accepted`, `rejected`, `needs_changes`) é evento append-only e não certifica. Após revisão, o candidato daquela versão fica imutável. Nova avaliação cria nova versão. Invalidação é evento auditável. Impressão é GET e não altera dados.
