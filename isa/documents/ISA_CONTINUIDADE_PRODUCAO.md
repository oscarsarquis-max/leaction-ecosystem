# Continuidade dos dados da ISA

Diretriz expressa do proprietário em 17/10/2026: o piloto recebe informações reais de produção. O fim do piloto não encerra nem reinicia as contas ou os registros.

- Preservar identidades, proprietários, contas, lançamentos, importações, anexos existentes, compromissos, planos, sugestões de IA e decisões, com seus vínculos e histórico.
- Evoluir por migrações compatíveis, sem recriar a base, reatribuir proprietários, exigir recadastro ou reimportação. Mudança de infraestrutura precisa transportar os dados existentes e verificar sua integridade antes da troca.
- Não implementar expiração de dados vinculada ao piloto. A retenção de sete dias das cópias é a janela de recuperação das cópias, não um prazo de validade dos registros na base ativa.
- Dados sintéticos e identidades de demonstração ficam isolados da produção. Não executar limpeza, seed, reset ou demonstração sobre a base real.
- Manter cópia anterior a migrações, recuperação verificável e retorno da aplicação compatível com os dados. Um retorno de versão não deve apagar registros recebidos depois da publicação.
- Exclusão solicitada pelo titular e regras explícitas de retenção continuam respeitadas; continuidade não é autorização para impedir a exclusão.

A alteração visual 0.6.1, a jornada de planejamento 0.6.2, o Início 0.6.3 e o acabamento 0.6.4 usam o mesmo banco, schema 4, identidades e serviço. A organização por contas 0.6.5 acrescenta o schema 5, sem apagar contas, lançamentos, importações ou compromissos já gravados. Nenhuma dessas versões recria usuários nem pede reimportação. Esta diretriz não equivale a garantia de ausência absoluta de interrupções; mudanças futuras devem preservar a continuidade funcional e os dados.
