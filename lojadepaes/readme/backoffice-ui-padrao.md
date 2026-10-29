# Padrão visual do backoffice

Critério de aceite dos prompts de interface da gestão. A casca e as telas novas seguem estas medidas. Um defeito de alinhamento, sobreposição ou medida fora da escala impede a publicação.

## Medidas

Espaçamento só na escala 4, 8, 12, 16, 20, 24, 32, 40 e 48 px. Nenhum valor solto fora de tipografia e borda.

Tipografia só nestes tamanhos: 11, 12, 13, 14, 15, 16, 18, 20, 24 e 28 px. Pesos 400, 500, 600 e 700. DM Sans no admin. Playfair Display só na marca.

Controles: altura de 40 px no desktop e 44 px no celular, para botão, campo, seleção e link-botão lado a lado. Raio de 8 px em controles, 12 px em cartões e 999 px em selos.

Alinhamento: o que está na mesma linha fica centralizado no eixo vertical. Bordas esquerdas de título, filtros, tabela e cartões da mesma página caem na mesma coluna. A barra superior e o conteúdo usam a mesma margem lateral.

Cores só das variáveis de `frontend/src/admin/shell/tokens.css`. Nenhum hex novo fora desse arquivo.

## Estados

Todo elemento interativo tem hover, foco visível, ativo e desabilitado. O foco é um anel de 2 px na cor de acento, sem depender só da cor. Texto com contraste de 4,5:1 ou mais.

## Larguras

Conferir 320, 390, 768, 960, 1280 e 1440 px. Em nenhuma delas pode haver rolagem horizontal da página, texto cortado sem reticências, sobreposição, rótulo de botão em duas linhas ou elemento encostado na borda.

## Revisão antes de publicar

1. Capturar as rotas do prompt nas seis larguras, com dados, incluindo os estados abertos que o prompt pedir (menu, gaveta, painel, foco).
2. Olhar cada imagem e preencher `readme/evidence/<prompt>/revisao-visual.md`: uma linha por captura, com OK ou o defeito e a correção.
3. Rodar no mesmo navegador uma checagem que falhe se `document.documentElement.scrollWidth > innerWidth` ou se um controle visível da entrega tiver altura menor que a mínima da largura.
4. Publicar só com a revisão sem defeito aberto. Defeito do miolo antigo fica listado como pendente para o prompt seguinte, sem correção neste passo.
