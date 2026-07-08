-- Migração 004: rótulos mais claros no admin após adoção do logotipo em imagem
UPDATE ui_content SET label = 'Logotipo — URL externa (vazio = frontend/public/brand/logo.png)'
WHERE content_key = 'assets.logo';

UPDATE ui_content SET label = 'Logotipo — texto alternativo (acessibilidade)'
WHERE content_key = 'brand.aria_label';

UPDATE ui_content SET label = 'Marca legado — linha superior (só se imagem falhar)'
WHERE content_key = 'brand.linha_superior';

UPDATE ui_content SET label = 'Marca legado — destaque INOV- (só se imagem falhar)'
WHERE content_key = 'brand.pill';

UPDATE ui_content SET label = 'Marca legado — sufixo ativas (só se imagem falhar)'
WHERE content_key = 'brand.sufixo';

UPDATE ui_content SET label = 'Marca legado — linha inferior (só se imagem falhar)'
WHERE content_key = 'brand.linha_inferior';
