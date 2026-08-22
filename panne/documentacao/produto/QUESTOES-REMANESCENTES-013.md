# Questões remanescentes após CURSOR-013

1. Um papel por associação: conferente continua sendo o mesmo papel do padeiro, só com ator distinto.
2. `scrapped` na batelada segue sem comando.
3. Conversão automática entre unidades de massa (g↔kg) não foi implementada; a unidade precisa ser de dimensão massa, comparada na quantidade informada.
4. APIs, quadro, PDF da ficha e estoque ficam para ciclos futuros (CURSOR-014+), sem antecipação aqui.
5. Ordens liberadas antes da 0011 sem política não executam até haver ordem substituta com política — sem backfill.
