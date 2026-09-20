# SEGSENSE_SEC_005 — Threat model da ingestão de URL

## Controle

| Campo | Valor |
|---|---|
| Identificador | SEGSENSE_SEC_005 |
| Versão | 1.1 |
| Data | 15/09/2026 |
| Prompt | SEGSENSE_PRM_020_COR_001 |

`SEGSENSE_SEC_004` permanece o threat model da âncora comercial. Este documento cobre só a captura de URL.

## Ativos

- Rede interna e metadados de nuvem (SSRF).
- Segredos eventualmente presentes na página capturada.
- Integridade da revisão humana (HTML hostil / XSS).
- Ledger da jornada (não misturar fixture governada com URL real).

## Ameaças e controles

| Ameaça | Controle nesta fatia |
|---|---|
| SSRF a loopback, RFC1918, link-local, multicast, unspecified | Resolver todos os endereços antes de conectar e antes de cada redirect; classificar e bloquear. |
| Metadata IPv4 `169.254.169.254`, hostnames de metadata | Bloqueio por IP e por nome canônico conhecido. |
| IPv4 embutido em IPv6 (`:ffff:`) | Desembrulhar e classificar o IPv4. |
| DNS rebinding | Duas resoluções por salto; conjunto deve ser estável e 100% público; senão `DNS_BLOCKED`. |
| Redirect para rede privada | `followRedirects=NEVER`; revalidar `Location` como URL nova; salto inseguro vira `REDIRECT_BLOCKED`. |
| Userinfo / credencial na URL | Rejeitar. |
| Porta interna | Permitir só 80 e 443 na captura pública. |
| TLS inválido | Trust store padrão; sem hostname verifier permissivo. |
| Cookies / Authorization / IP do visitante | Não encaminhar. |
| Resposta ilimitada | Stream com teto configurável. |
| MIME perigoso | Só HTML textual e texto puro. |
| XSS na UI | Texto inerte; sem `dangerouslySetInnerHTML`; sem executar JS da página. |
| Log injection | Sanitizar CR/LF e truncar. |
| Fixture silenciosa | Exemplos governados em UI separada; captura falha não troca a URL. |
| Segredo na página | Não devolver corpo bruto; redação de padrões óbvios no texto persistido. |
| Chrome da página como “texto da fonte” | `URL_EXTRACTOR_V2` seleciona `main`/`article` (fallback documentado); `NO_MEANINGFUL_TEXT` se o principal não for isolável. |
| Associação factual de termos distantes | Janela `LOCAL_WINDOW_V1` (mesmo parágrafo); BFF recusa `URL_EXTRACTED` sem evidência/offsets no snapshot. |

## Fora desta fatia

- Browser headless e execução de JavaScript remoto.
- Crawling, sitemap, múltiplas páginas.
- Pinning TCP ao IP com SNI de hostname (limitação do `HttpClient` documentada): mitigação é dupla resolução + bloqueio de destino privado.

## Superfície pública

Não expor enum de firewall, stack, IP interno, regra ou segredo. Detalhes técnicos (IDs, hashes, versões) no recorte “Detalhes técnicos desta tentativa”.
