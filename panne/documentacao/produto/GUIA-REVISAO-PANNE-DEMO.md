# Guia de revisão — Panne Demonstração

Este é um ambiente de **demonstração**. Os dados são sintéticos. Não há conexão com padaria real, norma oficial, pagamento ou nuvem.

## Como iniciar

Na pasta da Panne, em um terminal:

```
powershell -File scripts/dev/start-demo.ps1
```

O script só aceita o banco `panne_demo`. Se a demo já estiver no ar, ele só confirma os endereços.

## Endereço

Abra no navegador: [http://127.0.0.1:5180/entrar](http://127.0.0.1:5180/entrar)

A API responde em [http://127.0.0.1:5080/health](http://127.0.0.1:5080/health).

Não há senha. Não copie nenhum endereço que contenha usuário ou senha de banco.

## Aviso

A tela mostra **Ambiente de demonstração**. O botão **Entrar em desenvolvimento** usa um provedor falso, só neste computador.

## Como escolher o perfil

No centro da tela, em **Perfil de demonstração**, escolha quem você quer ser e clique em **Entrar em desenvolvimento**.

| Perfil | O que consegue ver |
|---|---|
| Proprietário | Quase tudo: quadro, receitas, conformidade, custos, estoque, compras, relatórios e troca de organização |
| Gestor de produção | Turno, planos, ordens, execução e o que o chão de fábrica precisa |
| Técnico / formulador | Ingredientes, receitas e o assistente de formulação |
| Padeiro | Quadro, ordens e execução. Sem preço de compra |
| Revisor regulatório | Dossiês e avaliações de rotulagem |
| Comercial / compras | Necessidades, requisições, cotações, pedidos e recebimentos |
| Leitor | Só leitura do que o perfil permite |

## Roteiro de 20 a 30 minutos

1. Entre como **Proprietário**.
2. No **Quadro**, mude a visão (dia / estação / fluxo) e veja ordens com nome de produto, não código.
3. Abra uma ordem e a execução (pesagem, etapas, ficha).
4. Em **Componentes**, abra ingredientes e uma receita publicada.
5. Em **Conformidade**, compare o dossiê completo com o incompleto. Nada vira certificado sozinho.
6. Em **Gestão → Custos**, veja previsto, realizado e uma simulação. Preço só muda com confirmação humana.
7. Em **Estoque**, veja posição, lotes (disponível, bloqueado, quarentena) e reservas.
8. Em **Compras**, percorra necessidades, requisições, duas cotações, pedido recebido em parte e pedido recebido, depois a devolução.
9. Em **Relatórios**, abra a visão executiva, um relatório com detalhe e o snapshot.
10. Clique no avatar redondo (canto inferior) e confirme que o texto fala da tela atual.
11. Troque para **Padaria Horizonte Demo** no seletor de organização: a farinha da outra casa some.
12. Saia e entre como **Padeiro** e como **Leitor** para ver menus a menos.

## Menus

- **Produção:** quadro, planejamento, ordens, rastreabilidade
- **Componentes:** ingredientes, estoque, lotes, fornecedores, fontes técnicas
- **Receitas:** lista, atelier, assistente de receitas
- **Conformidade:** visão geral, dossiês, avaliações, rótulos, fontes
- **Gestão:** custos, compras, inventários, relatórios

## Trocar organização

No alto da tela, escolha **Panne Demonstração** ou **Padaria Horizonte Demo**. O assistente e as listas devem limpar o que era da casa anterior.

## Abrir o assistente

O círculo da marca no canto inferior abre a gaveta. Não existe botão escrito “Assistente” minimizado. No login, o mesmo círculo oferece ajuda para entrar. Em telas de estoque ou custos, “Abrir no assistente” reusa a mesma gaveta.

## O que é dado sintético

Farinhas, receitas, ordens, lotes, cotações e preços foram inventados para o cenário do dia 24/08/2026. Nada veio de fornecedor real nem de legislação colada da internet.

## Limitações conhecidas

- Não há compra automática nem envio ao fornecedor.
- Não há certificação de rótulo nem publicação sozinha.
- Não há ligação com Action Hub, Bedrock ou login corporativo.
- Alguns cadastros auxiliares ficam vazios de propósito.
- O turno da noite usa o código interno `night`.

## Como encerrar

```
powershell -File scripts/dev/stop-demo.ps1
```

Isso encerra só a Panne Demonstração neste computador.
