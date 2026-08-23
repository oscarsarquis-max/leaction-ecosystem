# Ficha e snapshots

Novas emissões (`schema_version` 2) congelam estabelecimento, organização e responsável (usuário interno, nome e instante). Não há responsável de produção no domínio, então o campo não é inventado.

Emissões antigas permanecem intactas. Reimpressão lê o JSON persistido. Ausências aparecem como “não informado”. O hash inclui os snapshots. Sem backfill.
