# Emissão auditável da ficha

Tabela `production_sheet_issue`. Número sequencial por organização (`production_code_counter.kind=sheet`). Payload canônico dos snapshots (ordem, hashes, política, materiais, etapas, bateladas). SHA-256. Finalidade `operational` | `contingency`. Estado da ordem no instante. Reemissão = novo número e `previous_issue_id`. Ordem cancelada recusa nova emissão. Emissão **não** altera a ordem. Sem PDF, HTML, QR, custos ou margens.
