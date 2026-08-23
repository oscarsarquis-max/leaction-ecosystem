# Payload canônico da ficha

`GET .../orders/{id}/sheets/{issue_id}` devolve o JSON persistido em `production_sheet_issue.canonical_payload`.

Inclui emissão, ordem/batelada, produto via snapshot da ordem, versões e hashes, materiais, etapas, política, estado na emissão, finalidade e emissão anterior.

A partir do `schema_version` 2, novas emissões também congelam:

- estabelecimento: id, código e nome;
- organização: id, slug e nome;
- responsável pela emissão: usuário interno, nome de exibição e instante.

Não há responsável de produção no domínio; o campo não é inventado. Emissões antigas permanecem intactas. Reimpressão lê o JSON persistido. Ausências aparecem como “não informado”. Sem backfill e sem consulta a cadastro vivo.

Não gera HTML, PDF ou QR.
