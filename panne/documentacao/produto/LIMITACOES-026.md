# Limitações CURSOR-026

- Sem migração `0021`.
- Sem rede, Bedrock, Cognito, CMS, Action Hub ou marketplace.
- Sem certificação de rótulo e sem compra automática.
- Tabelas de governança antiga (`compliance_*`) e alguns auxiliares ficam vazios de propósito.
- O venv local da máquina pode ser Python 3.11; a prova oficial de testes foi Docker 3.12.
- Capturas autenticadas de todas as telas no Chrome dependem de sessão no navegador do revisor; a prova automatizada cobre router, API viva e login em quatro larguras.
- CURSOR-027 não foi iniciado.
