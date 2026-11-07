# GESTAO-014A — retorno

Branch `feat/gestao-014a-foto`, a partir de `86299531`. A foto do produto fica no banco, em WEBP, e o painel deixa de deixar a imagem cobrir o texto.

## Checklist

1. **Feito.** Dump `/opt/lojadepaes-gestao/backups/gestao-pre014a.dump` (119.086 bytes) antes do Alembic. A migração `0010_producao -> 0011_produto_foto` só cria `produto_fotos`. Em produção a tabela ficou com 0 fotos.

2. **Feito.** Backend 288 testes, incluindo `backend/tests/test_fotos_014a.py`. Uma foto de 4000×3000 vira WEBP de 1200×900, sem o EXIF, com menos de 250 KB. HEIC entra. 11 MB responde 413 (“Arquivo maior que 10 MB”). PDF responde 415 (“Formato não aceito”). A enviada vence a URL da Loja, e apagar a enviada devolve essa URL. Outra organização recebe 404. Frontend 83 testes.

3. **Feito.** Capturas em `docs/evidence/gestao-014a-local/`.
   - Focaccia em 1280 e 1920: `focaccia-1280.png` e `focaccia-1920.png`. A foto fica na caixa 4:3. Abaixo, separada, “Importado da Loja em 06/11”, e depois “Estrutura”. A medição do navegador não achou sobreposição.
   - Levain sem foto: `levain-vazio-1280.png`, com a inicial e “Adicionar foto”.
   - Modal com a prévia recortada: `modal-previa-1280.png`.
   - Levain com a foto e a lista em 390: `levain-foto-390.png` (“Foto enviada em 07/11”) e `levain-lista-390.png`, com a miniatura na linha.

4. **Feito.** Imagem `lojadepaes-gestao:014a-20261107`. `https://gestao.lojadepaes.com.br/` responde 200 e serve `index-B6kBQ5h6.js`, SHA-256 `a3a0adf4460f28516ff5f856a9f0d521085219f6d71d9dca2b2803c6aa10654f`, igual ao pacote da imagem. `https://lojadepaes.com.br` responde 200. A contagem da Loja ficou igual antes e depois: `media_assets` 17/0/0, `product_variants` 16/6/6, `products` 16/35/6, `showcase_slots` 10/16/0. Nenhuma foto de teste em produção.

5. **Feito.** Este arquivo e as capturas entram no mesmo commit. A regra de SSH aberta para este ciclo foi fechada; ficaram as 29 que já existiam. 80 e 443 seguem públicos.

A imagem anterior, para voltar, é `lojadepaes-gestao:014-20261107`. O banco volta pelo dump.
