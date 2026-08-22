# Ficha impressa

A ficha é projeção papel da **ordem** (e da batelada, se partida). Não é a receita viva do laboratório.

## Conteúdo mínimo

- empresa e estabelecimento;
- códigos da ordem e da batelada;
- produto e versão da formulação (número + hash curto do snapshot);
- data e turno;
- quantidades e unidades do snapshot de escala;
- ingredientes na sequência operacional;
- etapas, tempos e temperaturas previstos;
- rendimento e perdas previstos;
- campos em branco para apontamento manual (lote, peso real, hora, rubrica);
- alertas críticos (alergênico, substituição já autorizada, hold);
- responsável previsto;
- instante da emissão e **número da emissão**;
- identificação da versão impressa (hash = snapshot).

Custos e margens **fora** da ficha de chão.

## QR / código curto

Opcional. Se existir, aponta para a ordem + número da emissão (não para a formulação viva). Útil para recusar ficha cancelada ou emissão velha. **Não é obrigatório** — a contingência funciona sem câmera.

## Evitar ficha obsoleta ou cancelada

1. Toda emissão grava número e hash do snapshot.
2. Reimpressão depois de mudança **não existe**: mudança exige nova ordem.
3. Cancelamento: quadro some; nova emissão é recusada; o código curto, se usado, devolve “inválida”.
4. Cabeçalho visual com estado no momento da impressão; se `cancelled` / `completed`, marca “não executar”.
5. Preferir uma ficha por batelada quando a ordem for partida — reduz uso da folha errada.

Digital e papel mostram os mesmos códigos de ordem, batelada, versão e emissão.
