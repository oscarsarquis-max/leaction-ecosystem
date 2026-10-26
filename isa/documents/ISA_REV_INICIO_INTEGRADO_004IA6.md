# ISA — Início integrado

26/10/2026. A proposta `ISA_INICIO_INTEGRADO_004IA6.html` orientou a composição. Ela usa dados fictícios e não é aceite do proprietário. Esta publicação também não é aceite visual.

## O que a pessoa encontra

https://isa.actionhub.com.br abre o Início em **isa-piloto 0.6.9**, schema 9, task `isa-web:18`. A imagem linux/amd64 é `sha256:5981566fb1ed1dbfc1360a28fb2553d58fd0221e4eb97bbafea6f52f09be84a8`. O retorno da aplicação é `isa-web:17`, versão 0.6.8. Não houve schema novo, então a 0.6.8 continua lendo as mesmas contas, saldos, lançamentos e compromissos.

O título é **Seu dinheiro**, com o apoio “O que já aconteceu e o que vem pela frente.” Há um só navegador de mês. O histórico separado “O que já aconteceu”, com o próprio “Próximo mês”, saiu do Início. No celular, o Registrar do cabeçalho local fica oculto porque o menu inferior já o traz.

Sem saldo e sem movimento, a orientação é uma só: **Vamos reunir suas informações**, com importar o extrato ou informar manualmente.

Quando há referência, a situação mostra o rótulo da origem. **Disponível hoje** só aparece se as contas consideradas têm saldo na data de hoje. Saldo anterior fica **Último saldo conhecido**. Soma com conta sem referência fica **Total conhecido** e não libera margem global. A reserva já incluída no saldo não é somada de novo. Investimento sem liquidez fica fora do utilizável.

O mês mostra realizado e previsto restante na mesma lista, com a situação de cada registro. Mês futuro não é chamado de histórico. Um lançamento com data futura não entra no realizado de hoje. Selecionar um dia muda a lista; os totais continuam do mês.

A leitura da ISA não é chamada ao abrir nem ao trocar o mês. O botão **Atualizar a leitura** continua manual. Os números vêm do motor.

## Fontes de saldo suportadas

- Declaração manual por conta, com data e reserva protegida. A origem aparece como “Informado por você”.
- Soma das contas em Real quando cada conta considerada tem declaração e a data cobre hoje.
- Saldo de extrato reconhecido como disponível **não** foi acrescentado. Importar movimentos não cria saldo. Se o arquivo não trouxer um saldo interpretável, a tela pede a lacuna em vez de inventar o valor.
- Saldo calculado a partir de um saldo antigo mais movimentos posteriores completos **não** foi automatizado. Sem cobertura até hoje, o rótulo permanece o último saldo conhecido e a margem de gasto fica “ainda não calculada”.

## Cenário de 26/10/2026

No SQLite de laboratório, com a data fixa 26/10/2026, o teste `server/test_inicio_004ia6.py` conferiu:

- Todas em Real: R$ 1.000 no Banco do Brasil e R$ 200 na poupança, reserva de R$ 200 já dentro do total de R$ 1.200.
- Outubro realizado: entradas R$ 4.000 e saídas R$ 3.100, sem somar de novo esses R$ 900 ao saldo.
- Trajetória a partir de hoje: R$ 1.200, R$ 750, −R$ 150 em 28/10 e R$ 1.350 em 30/10. Falta R$ 150 no dia 28. Para a reserva, R$ 350. Margem para gastar hoje: R$ 0.
- Novembro: mínimo R$ 650 e fechamento R$ 1.850. A margem de hoje continua R$ 0; o mínimo de novembro não vira autorização de gasto hoje.
- Só o Banco do Brasil: R$ 1.000, sem reutilizar os R$ 1.200.
- Poupança sem referência: total conhecido R$ 1.000, margem de hoje bloqueada.
- Saldo de 14/10: último saldo conhecido, sem o rótulo de disponível hoje.
- Lançamento com data futura: não entra no realizado.

## Lentidão

O que o código fazia: a entrada esperava `/api/health`, depois `/api/workspace` — e essa consulta também materializava lançamentos — e ainda o rascunho de importação, com um temporizador de 1,5 s. O Início pedia `/api/home` outra vez e podia disparar a leitura de IA.

O que mudou: a estrutura aparece sem esperar o rascunho. O rascunho de importação carrega depois. A materialização dos lançamentos saiu da leitura do workspace e ficou na gravação da importação. A leitura de IA não dispara sozinha. Resposta antiga de outra conta é ignorada pelo identificador da consulta, e o cache local é limpo quando a pessoa do laboratório muda.

Medição no SQLite vazio, 20 chamadas de `home()`: p50 2,0 ms e p95 2,2 ms. Isso não é o piloto, não inclui rede, autenticação nem base real. As metas de 100 ms, 500 ms e 800 ms no ambiente publicado **não foram medidas** e não estão declaradas como atingidas. O gargalo que ainda falta medir é a abertura autenticada em produção, com a base real e a rede do proprietário.

## Prova visual

Capturas em `documents/reviews/inicio-004ia6/`, em 1440, 1280, 768, 390 e 360, no estado vazio do laboratório. Mostram o título, a orientação única, a situação sem saldo e a agenda do mesmo mês. Não mostram o cenário de R$ 1.200, porque esse cenário ficou no teste automatizado e não foi gravado na base publicada.

O zoom de 200% do navegador não foi aplicado nesta entrega. A tentativa anterior, no Chrome com janela, não alterou a escala. Não está aprovado.

## Publicação

A cópia anterior à troca da imagem está em `backups/20261026T144942+0000/`, task `isa-backup:7`, saída 0. Não houve migration. O ActionFinance permanece em `actionfinance-web:28`.

`/api/workspace` sem sessão continua 401. Não houve sessão do proprietário para percorrer o Início publicado com os dados reais. Saúde 200 não substitui essa leitura.

O commit desta entrega fica no remoto já usado pela ISA. Não há aceite do proprietário.
