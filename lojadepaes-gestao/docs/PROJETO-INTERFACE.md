# Projeto de interface — Loja de Pães · Gestão

Documento de referência da interface da Gestão. Os próximos prompts citam este arquivo.
Desenhado em GESTAO-003; vale para toda tela nova.

## 1. Casca (shell)

A casca é a da Loja, no padrão 108A:

- Espaçamento numa escala de **4 a 48 px** (4, 8, 12, 16, 24, 32, 48). Nada fora dela.
- Controles (botão, campo, seletor, link de menu) com **40 px** de altura no desktop e **44 px** no celular.
- Anel de foco de 2 px em todo controle.
- Revisão em **seis larguras: 320, 390, 768, 960, 1280 e 1440 px**. Até 959 px a tela é "estreita"
  (menu em gaveta, barra de cima do celular); a partir de 960 px é "larga" (menu fixo à esquerda).
- Nenhuma rolagem horizontal em nenhuma largura.

## 2. Menu lateral

```
Hoje
FLUXO DA PADARIA
  1 Entradas       ●  O que chegou?
  2 Ingredientes   ●  O que eu tenho?
  3 Produtos       ○  O que eu vendo?     (em breve)
  4 Receitas       ○  Como eu faço?       (em breve)
  5 Produção       ○  O que faço hoje?    (em breve)
GESTÃO
  Custos (em breve) · Locais · Usuários
```

- Cada etapa do fluxo mostra um **ponto** e uma **frase curta** (por exemplo, "2 vencem em 7 dias").
- Etapa "em breve" não é link: aparece apagada, com a pergunta e o rótulo "em breve", e ponto vazio.
- "Usuários" só aparece para quem pode gerenciar usuários (o dono).
- No topo do menu, a logo (cerca de 40 px de altura) leva para **Hoje**.

### Estados da etapa

| Estado | Ponto | Quando |
|---|---|---|
| **Em dia** | verde | nada pendente |
| **Atenção** | âmbar | há algo a olhar |
| **Falta** | vermelho | falta o básico da etapa |
| *em breve* | vazio | etapa ainda não existe |

Regras:

- **Entradas**: em dia = nada pendente; atenção = há entrada pendente (por exemplo, lote sem validade); falta = não há nenhuma entrada.
- **Ingredientes**: atenção = algum ingrediente sem saldo, ou lote que vence em até 7 dias, ou par de ingredientes parecidos sem decisão; falta = nenhum ingrediente com saldo.
- Uma etapa **não fica "em dia"** se a anterior está em "falta".
- O estado vem do servidor (`GET /fluxo`); o menu nunca calcula sozinho.

## 3. Celular

- A barra de cima mostra a logo (cerca de 32 px) e um botão com **a etapa atual**, com o seu ponto. Tocar nele abre a lista de etapas (a gaveta).
- Na segunda linha da barra ficam o **nome da organização** e o **CNPJ**, sempre inteiros (o CNPJ nunca é cortado).
- A gaveta traz a logo e "Gestão" lado a lado, as etapas, o grupo Gestão e, embaixo, a pessoa, a troca de organização (se houver mais de uma) e **Sair**.
- Painéis laterais viram **tela cheia**. Esc e o botão de fechar fecham; o foco fica preso no painel.

## 4. Barra de cima (desktop)

À esquerda a trilha ("Fluxo da padaria / Entradas"). À direita, lado a lado:
**"Loja de Pães – Boulangerie · CNPJ 00.000.000/0000-00"** e o menu da pessoa (nome, papel, trocar de organização, Sair).
O CNPJ é mostrado com máscara; no banco fica sem máscara (aceita o CNPJ alfanumérico).

Conta de administrador da plataforma, sem organização: não há menu nem dados. A tela diz
"Sua conta não opera nenhuma organização" e oferece só **Sair**.

## 5. Esqueleto de toda tela

1. **Título** da tela.
2. **Pergunta** que a tela responde, em uma linha ("O que chegou?").
3. **Uma** ação principal (botão verde cheio). Ações secundárias são botões de contorno.
4. **Chips de filtro** (Todas, Com nota, Sem nota, Pendentes…).
5. **Lista em linhas**: nome · o número que importa · estado.
6. **Detalhe em painel lateral** (tela cheia no celular). Ações do detalhe ficam no rodapé do painel.

Formulários longos (Entrada sem nota) usam o mesmo esqueleto, com um rodapé fixo que resume
(itens, a decidir, incompletos, total) e traz o botão **Gravar**. O botão fica desligado, com o motivo escrito ao lado.

## 6. Vocabulário

Use: **Entrada, Ingrediente, Item, Lote, Saldo, Validade**.
Nunca: "insumo", "componente", "recebimento".

- **Ingrediente** é o que a receita usa (Farinha de trigo). **Item** é como se compra (Farinha de trigo 25 kg, Dona Benta). Vários itens para um ingrediente.
- **Lote** é uma chegada de um item, com validade e custo. **Saldo** é o que sobra, somado dos lotes.
- Embalagem conta pelo **conteúdo**; nunca converte massa em volume.
- Custo em branco é "sem custo", não zero: o total diz "sem custo não soma".
- Mensagens em português simples. Nada de códigos, siglas internas ou identificadores na tela.

## 7. Logo

- Original: `frontend/images/Loja de Pães logo.png` (2000×2000, fundo creme `#FFF4EA`). **Não se altera.**
- Derivadas em `frontend/src/assets/` (geradas por `scripts/gerar-logos.py`): `logo-loja-de-paes.png` e `logo-loja-de-paes-transparente.png`.
- Não redesenhar, recolorir, distorcer nem cortar o "RECIPES".
- Posições: topo do menu (~40 px, leva para Hoje), barra do celular (~32 px), login centralizado (~72 px) e toda página nova.
- Texto alternativo: **"Loja de Pães"**. Título da aba: **"Loja de Pães · Gestão"**.
- Ícone da aba: o "L" sobre creme, em 32 px e 180 px (`frontend/public/icone-32.png`, `icone-180.png`).

## 8. Como verificar

`scripts/capture-evidence.mjs` captura e confere, nas seis larguras (uma delas a 2x):

- login e menu lateral (logo, foco, rolagem horizontal, altura dos controles);
- o portão de aceite: topbar com organização e CNPJ, e a conta sem organização;
- no modo completo (só em ambiente local), Hoje, Entradas, Entrada sem nota e Ingredientes a 1280 e 390 px.
