# Payload canônico da ficha

`GET .../orders/{id}/sheets/{issue_id}` devolve o JSON persistido em `production_sheet_issue.canonical_payload`.

Inclui emissão, ordem/batelada, produto via snapshot da ordem, versões e hashes, materiais, etapas, política, estado na emissão, finalidade e emissão anterior.

Não gera HTML, PDF ou QR. Não consulta cadastro vivo para reconstruir.
