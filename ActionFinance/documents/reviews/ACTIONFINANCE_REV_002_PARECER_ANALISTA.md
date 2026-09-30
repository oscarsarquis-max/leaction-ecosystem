# ACTIONFINANCE_REV_002 — Parecer do analista

Data: 25/09/2026. Revisão estática do código e documentos entregues no PRM_002.

**Resultado: DEVOLVIDO PARA CORREÇÃO. Fundação parcialmente entregue; aceite pendente.** O relato diferencia corretamente testes bloqueados de aprovados, mas alguns critérios e defeitos concretos impedem avançar ao domínio.

Achados:

1. Testcontainers: suites puladas com `disabledWithoutDocker=true`; configuração impõe pipe local. A prova operacional via CLI não substitui o gate automatizado solicitado.
2. Compatibilidade: versão PostgreSQL ainda fora da faixa declarada como testada pelo Flyway utilizado; V1 bem-sucedida não basta para concluir suporte.
3. Restauração: `verify-backup.ps1` não interrompe com segurança em erros nativos/SQL; relatório admite GRANTs falhos e ainda apresenta sucesso. Precisa preservar owners/ACL ou reconstituí-los explicitamente e validá-los.
4. Processos: start não demonstra repetibilidade; stop aceita java/node/npm como ownership, sujeito a PID reutilizado e problemas de wrapper/filhos. Restore remove nome fixo preventivamente sem provar ownership.
5. Segurança: `anyRequest().authenticated()` não é negação de rotas não previstas. Valores default de bind loopback não impedem override público; validator demo não verifica esse caso.
6. Frontend: lint ausente no package.json; auditoria npm pendente de classificação; navegador real ainda não validado.

As vulnerabilidades npm não foram individualmente classificadas nesta revisão, pois não foi entregue seu relatório detalhado. Não há afirmação de exploração ou comprometimento. Compatibilidade externa será validada pelo Cursor contra documentação oficial e testes no corretivo.

Foi realizada leitura de código/configuração/testes/scripts e REV_002. Não foram executados os scripts de parada/restore nem reproduzidos os testes de runtime nesta revisão. Não foram lidos tokens locais.

Próximo e único prompt: ACTIONFINANCE_PRM_002_COR_001. Sem PRM_003 até retorno e revisão do corretivo. Cursor continua como único desenvolvedor; este parecer não alterou código.
