# Entrada fiscal de mercadorias (CURSOR-028-D)

## Modelo

A entrada separa quatro verdades:

1. **Documento fiscal** (`fiscal_inbound_*`) — o que a nota declara.
2. **Correspondência** (`fiscal_item_match` / `supplier_item_link`) — amarração ao cadastro Panne.
3. **Conferência física** (`fiscal_physical_line`) — o que realmente chegou.
4. **Estoque e custo** — só após `fiscal.confirm_receipt` (receipt + lote + movimento + rateio).

Encontrar ou importar a nota **jamais** movimenta estoque sozinho.

## Estados

`draft` → `captured` / `awaiting_xml` → `awaiting_match` → `awaiting_check` → `partially_received` | `received` | `divergent` → terminais `cancelled` | `refused` | `superseded`.

## Quatro caminhos na UI

1. Preencher manualmente
2. Importar XML
3. Enviar PDF ou foto (OCR sintético na demo)
4. Buscar documentos da Fazenda — **preparado, desativado**; a demo ofereceerece apenas **Simulação**

## Segurança XML

- `defusedxml` + rejeição de DOCTYPE/ENTITY
- Limite de tamanho (8 MiB), MIME allowlist, limite de itens
- Blob em object store privado (`storage_key` + `sha256`); sem XML integral em log

## Integração Fazenda (preparada / desativada)

### Implementado agora

- Interface `FiscalDocumentDistributionProvider`
- Adaptador `NFeDistribuicaoDFe` (contratos DistDFe: NSU, cStat 137/138/108/656, cancelamento)
- Provedor sintético `FixtureDistributionProvider` com cenários DEMONSTRAÇÃO
- Feature flag global `PANNE_FISCAL_LIVE` (default `0`)
- Contrato `establishment_fiscal_certificate` (secret_ref + metadados; sem material A1)
- Rate limit, backoff, idempotência de chave, isolamento org
- UI: mensagem “Consulta automática preparada, mas ainda não ativada…”

### Simulado na demo

- Documentos DistDFe fictícios (CNPJ `00000000000191`, chaves prefixo `9999`)
- Download/XML sintético, item reconhecido + pendente, divergência qtd/preço, parcial, cancelada, sem novos docs, falha temporária

### Tecnicamente preparado (ainda desligado)

- Habilitação por estabelecimento (`distribution_enabled`)
- Ambientes homologation/production
- Validação de configuração sem rede (`validate_certificate_config`)
- Controle de último NSU / última consulta / diagnóstico sanitizado

### Depende do certificado A1 real

- Segredo no cofre (Secrets Manager)
- mTLS com a SEFAZ
- Consulta DistDFe ao vivo
- Rotação/revogação operacional do certificado

### Deliberadamente desativado

- `PANNE_FISCAL_LIVE=0` na demo
- Sem cadastro de certificado real
- Sem chamada de rede à Fazenda
- Sem custo AWS Textract (`PANNE_OCR_LIVE=0`)

## Ativação futura (procedimento)

1. Provisionar segredo A1 no cofre (nunca no banco/app/.env versionado).
2. Registrar `establishment_fiscal_certificate` com `secret_ref`, CNPJ, validade, ambiente.
3. Validar configuração (teste seco — sem DistDFe).
4. Habilitar `distribution_enabled` no estabelecimento.
5. Subir `PANNE_FISCAL_LIVE=1` somente no ambiente autorizado.
6. Monitorar NSU, rate limit e indisponibilidade.

## Revogação / rotação

1. Marcar certificado `revoked` ou `expired`.
2. Rotacionar `secret_ref` no cofre.
3. Desligar `distribution_enabled` e/ou `PANNE_FISCAL_LIVE`.
4. Entradas manuais/XML/PDF continuam funcionando.

## Desligamento imediato

- `PANNE_FISCAL_LIVE=0` ou `distribution_enabled=false`
- Não afeta captura manual, XML nem scan

## Limitações desta passagem

- Sem contabilidade fiscal completa
- Sem emissão de NF-e
- OCR real (Textract) encapsulado e desligado
- Object store demo em memória/S3 privado conforme deploy

## Roteiro demo

1. `/gestao/compras/entradas` → Registrar entrada
2. Importar XML sintético ou Simulação Fazenda
3. Confirmar correspondências
4. Registrar conferência física
5. Confirmar — só então o estoque sobe
