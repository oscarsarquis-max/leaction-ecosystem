# Preparação futura para ActionHub

O CMS informado é `actionhub.com.br`. Neste ciclo **não** houve acesso ao domínio, nem endpoint, token, webhook, API ou schema proprietário.

O adaptador futuro conecta-se **atrás** de `LoginEditorialContentProvider`, no mesmo schema fechado. Timeout, cache, allowlist de HTTPS e fallback entram só nesse adaptador.

Não foi adicionada URL nem credencial a `.env.example`. Falha editorial nunca bloqueia o login.
