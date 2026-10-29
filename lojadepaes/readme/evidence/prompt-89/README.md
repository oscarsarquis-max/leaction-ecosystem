# Prompt 89 — Gigio no Criador (jornada pública)

08/10/2026. Verificação na jornada real, sem login admin e sem URL interna de teste. Sem pedido, e-mail ou pagamento real.

## Produção conferida

| Peça | Valor |
|---|---|
| HTTPS | https://lojadepaes.com.br/ |
| Rota pública | `#criacao` — rótulo do menu **Crie seu pão** (não “Faça seu pão”) |
| Título da seção | Criador de Pães |
| Imagem | `lojadepaes:prod-20261008b` (rollback de app: `prod-20261008a`) |
| Bundle | `/assets/index-DGjt2ALe.js` · `/assets/index-BhvDXrCQ.css` |
| Backup | `/opt/lojadepaes/backups/lojadepaes-20261008T121410Z.sql.gz` |
| Regras | `88` |
| Gigio | `enabled` / `ready` / Bedrock Claude |

## Causa

A integração existia. O bloco só montava depois do formato, sem texto enquanto a escolha faltava, e ficava abaixo das cartas com **Combinar o encontro** visível. O painel flutuante **Conversar com Gigio** não é essa dica.

## Correção publicada

No passo **A forma**, o bloco **Uma dica do Gigio para o seu pão** aparece assim que farinha e preparo existem. Sem formato: “Escolha o formato acima para o Gigio comentar a combinação que você montou.” Com formato: busca a dica, mostra carregamento/erro, limpa a dica velha ao mudar a massa, rola o bloco para perto. Sem redesenho das etapas.

## Jornada comprovada (rótulos servidos)

1. https://lojadepaes.com.br/ → **Crie seu pão**.
2. **A essência:** Branca · Fermentação natural curta → **Escolher os sabores**.
3. **Seu toque:** Nozes → **Escolher a forma**.
4. **A forma:** o bloco do Gigio já está visível sem abrir o chat. Escolher **Pão de forma** e esperar.
5. Dica desta sessão: nozes + acidez da fermentação natural; torradas/sanduíches. Botões **Conversar com o Gigio** e **Pedir nova dica**.
6. **Conversar com o Gigio** → “Por que essa combinação funciona?” A resposta usou farinha branca, fermentação natural curta, nozes e pão de forma.
7. Trocar para **Rústico de cesto**: a dica anterior some (“Gigio está olhando a sua massa…”). **Pedir nova dica** devolveu um único bloco, com outro serviço (queijos/geleias).
8. **Combinar o encontro:** 1 pão · 500 g · R$ 70,00 · Branca · Fermentação natural curta · Nozes · Pão de forma. Pedir dica não alterou isso. Não enviar.

Chat a partir da home (**Conversar com Gigio**): proposta válida → **Montar esse pão** → Criador preenchido e editável, aviso “Sugestão do Gigio. Você pode alterar.” Sem sobrescrever sessão vazia.

## Testes (antes de publicar)

- Backend 87 / 88 / data excepcional / Gigio: **31 passed**
- Frontend BreadBuilder + GigioHost: **13 passed**

Fechamento excepcional e caminho convencional não foram alterados. Gigio indisponível não impede montar nem comprar.

## Limitações da prova

Capturas em Chrome headless (emulação 1440 / 390 / 320), não em aparelho físico. A fonte do site às vezes cola as letras na captura; o texto no DOM e nos JSON está com espaços. A tela **REVISÃO** com “Ir para identificação e envio” não foi aberta nesta sessão (calendário exige um **dia de produção aberto**; o encontro já mostrava composição, quantidade e valor). Não houve pedido real.

## Rollback

`LOJADEPAES_API_IMAGE=lojadepaes:prod-20261008a` e recreate da API.
