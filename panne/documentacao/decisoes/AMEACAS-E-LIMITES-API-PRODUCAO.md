# Ameaças e limites da API de produção

- Default deny + RLS forçado; testes A/B via HTTP
- Nenhuma rota de negócio usa conexão administrativa
- Mass assignment bloqueado por `extra="forbid"`
- Limites de paginação, texto e cabeçalho de autorização
- Logs e erros sem token, SQL ou stack
- Correlação ponta a ponta (`X-Correlation-Id`)
- Grupos do IdP não autorizam
- Sem WebSocket, SSE, relatórios materializados ou chamadas Cognito/Bedrock reais
