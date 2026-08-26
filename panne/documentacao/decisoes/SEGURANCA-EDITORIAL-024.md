# Segurança editorial

- Texto puro e campos estruturados.
- Bloqueio de script, evento, iframe, estilo arbitrário e protocolos `javascript:`, `data:`, `vbscript:`.
- HTTP aberto e URL protocol-relative são recusados.
- Nenhum segredo no frontend.
- Provider estático não envia dado do usuário.
- Conteúdo não altera autenticação, rotas, permissões nem textos críticos do acesso.
- Provider indisponível devolve laterais vazias e o centro permanece.
