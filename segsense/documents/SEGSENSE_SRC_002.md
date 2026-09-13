# SEGSENSE_SRC_002 — Matriz de evidências públicas Icatu (12/09/2026)

## Controle

| Campo | Valor |
|---|---|
| Identificador | SEGSENSE_SRC_002 |
| Versão | 1.0 |
| Data de consulta | 12/09/2026 |
| Método | Navegação HTTP GET pública; sem login, scraping de operações, cadastro ou cópia extensa |

Consulta complementar a `SEGSENSE_SRC_001`. Marketing institucional **não** é cobertura contratual, canal permitido, elegibilidade, OpenAPI nem autorização de marca.

## Matriz

| URL | Fato (paráfrase) | Acesso | Status | Implicação técnica |
|---|---|---|---|---|
| `https://portal-api.icatuseguros.com.br/` | Hub público: integração autenticada; fala em mais de 100 APIs. | Público | `VERIFICADO` | Identifica o Hub. Não autoriza client, sandbox ou parceria. |
| `https://portal-api.icatuseguros.com.br/apis` | HTTP 200, `text/html`. Busca no HTML público por `openapi`, `swagger`, `paths` e `operationId` não retornou ocorrências. | Público limitado | `VERIFICADO_LIMITADO` | **NÃO VERIFICADO / REQUER ACESSO AUTORIZADO** qualquer operação, schema, payload ou endpoint nomeado. |
| `https://portal-api.icatuseguros.com.br/terms-of-use` | Uso de API condicionado a cadastro e a Parceiro/Fornecedor com contrato vigente; chaves de acesso; sem licença genérica. | Público | `VERIFICADO` | Mock independente **não** é “sandbox Icatu”. |
| `https://portal.icatuseguros.com.br/` | Institucional: vida, previdência e capitalização como linhas de atuação divulgadas. | Público | `VERIFICADO` | Produto institucional divulgado ≠ API, cobertura contratual para o SegSense, canal ou elegibilidade. |
| `https://portal.icatuseguros.com.br/seguro-de-vida/essencial` | Página de produto de vida ao consumidor (coberturas e condições resumidas no site). | Público | `VERIFICADO` (marketing) | Não copiar coberturas para o SegSense. Não afirmar que o cenário demonstrativo oferece esse produto. |

## Lacunas (célula bloqueada)

- OpenAPI, autenticação, homologação, payloads, versionamento, quotas: **REQUER ACESSO AUTORIZADO**.
- Papel do intermediário, base jurídica de compartilhamento, responsabilidade de cotação/emissão: **não publicados para este trabalho**.
- Nada do `SEGSENSE_ASM_001` (escada, composição) se torna atributo real da Icatu.

## Perguntas precisas

### Para Icatu / área comercial

1. Qual documentação de API autorizada (versão, schema, exemplos) pode ser compartilhada com o SegSense?
2. Qual autenticação, ambiente de homologação e quotas se aplicam a um satélite de distribuição contextual — se algum?
3. Qual canal e papel comercial (corretor, representante, outro) seriam permitidos?
4. Consentimento e base jurídica para qualquer dado que cruzasse a fronteira.
5. Quem decide cotação, aceitação e emissão; o que o SegSense **não** pode apresentar.

### Para a Spider

1. Satellite Contract externo executável (`SEGSENSE_REQ_002`).
2. Como um provider mock independente seria alcançado **pela Spider**, sem o SegSense ligar direto.
3. Versionamento, erros e preview sem execução.
