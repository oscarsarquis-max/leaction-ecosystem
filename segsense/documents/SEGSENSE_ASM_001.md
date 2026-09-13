# SEGSENSE_ASM_001 — Checkpoint estratégico e teto de personalização contextual

## Controle

- Projeto: SegSense
- Categoria: ASM — assessment
- Versão: 1.0
- Data: 12/09/2026
- Natureza: análise de produto; não é especificação executável nem parecer jurídico
- Fontes de origem: textos iniciais “Spider aplicada ao domínio de seguros” e “O setor bancário na última década…” fornecidos pelo usuário; `SEGSENSE_ARQ_001`, `SEGSENSE_PLN_001`, `SEGSENSE_REV_010`, `SEGSENSE_INT_001`
- Situação: proposta para incorporar ao índice oficial no próximo prompt após aprovação

## 1. Síntese executiva

O diferencial defendido pela inspiração original não é fabricar seguros automaticamente. É **reduzir a distância entre um risco percebido em um contexto real e uma jornada de proteção compreensível, governada e executável por participantes autorizados**.

Uma oferta pode ser **novíssima na experiência e na composição comercial** sem ser um produto securitário novo. O SegSense pode orquestrar apresentação, coleta progressiva e seleção entre configurações permitidas; não pode, por conta própria, ampliar cobertura, fixar prêmio, garantir elegibilidade ou emitir apólice.

## 2. O que da inspiração já virou SegSense

| Ideia original | Estado verificável em 12/09/2026 |
|---|---|
| Cooperação tecnológica com players tradicionais, via integração desacoplada | Direção arquitetural adotada. SegSense é aplicação independente, integrável à Spider e a provedores futuros, não substitui a seguradora. |
| Entrar no momento em que a necessidade se torna perceptível | Oportunidade editorial versionada, governança e link contextual opaco estão implementados. |
| Evitar oferta genérica | Contexto do publicador e página pública contextual existem; a personalização ainda é editorial/não pessoal. |
| Confiança, transparência e explicabilidade | Notice versionado, manifestação local, retirada e estados honestos existem; conformidade jurídica não está concluída. |
| Plataforma reutilizável/API | BFF e fronteiras estão organizados; o Satellite Contract externo da Spider ainda não existe. |
| IA interpreta, Spider decide e executa | Continua como princípio e arquitetura-alvo. **Não opera no SegSense hoje** por ausência do contrato público da Spider. |
| Composição de capabilities e integração com seguradora | Não implementada. Nenhum produto, cotação, elegibilidade, provider mock ou Icatu real foi conectado. |
| Prova comercial visual | PRM_011 em andamento como âncora demonstrativa não oficial, sem simulação operacional. |

Nota arquitetural: a frase inicial “não criar outra arquitetura independente” significa não duplicar o motor de decisão/execução da Spider. A decisão posterior de manter **SegSense, Spider e provider mock fisicamente independentes** permanece correta e prevalece.

## 3. O contexto do link: ponto de partida, não perfil do usuário

Uma fonte fixa — artigo, página, aplicativo ou ambiente cadastrado — fornece **contexto editorial verificável**: tema, canal, posição, versão, publicador e valores não pessoais declarados. Ela não prova que o visitante seja agricultor, empresário, segurável ou interessado em comprar.

Assim, o link pode iniciar uma hipótese de necessidade, por exemplo “este conteúdo discute continuidade financeira da família”, mas não autoriza inferir profissão, renda, saúde, patrimônio ou intenção pessoal. O clique não é consentimento para compartilhar dados. Informações individuais adicionais, se realmente necessárias, devem ser solicitadas progressivamente, com finalidade clara e base jurídica validada. A ANPD explica que dados usados para perfil comportamental de pessoa identificada podem ser pessoais e que consentimento, quando escolhido como base, exige manifestação livre, informada e inequívoca. [ANPD — Perguntas Frequentes](https://www.gov.br/anpd/pt-br/acesso-a-informacao/perguntas-frequentes/perguntas-frequentes), [ANPD — Consentimento](https://www.gov.br/anpd/pt-br/acesso-a-informacao/participacao-social/outras-acoes/documentos/ts_04_24_corrigido.pdf).

## 4. Escada de customização

| Nível | O que pode mudar | Dono da decisão | Situação SegSense |
|---|---|---|---|
| 1. Contextualização da apresentação | Texto, ponto de entrada, explicação, linguagem e ordem de perguntas, dentro de conteúdo aprovado | SegSense/publicador | Base implementada |
| 2. Diagnóstico orientado por objetivo | Perguntas adicionais e entendimento do objetivo, sem recomendar produto prematuramente | SegSense coleta; Spider interpretaria/decidiria pelo contrato futuro | Coleta local parcial; Spider bloqueada |
| 3. Configuração de produto existente | Escolha entre coberturas, capitais, assistências, vigência e serviços **somente quando o plano e o canal permitirem** | Seguradora/corretor/representante conforme papéis e contrato; Spider apenas orquestra regras autorizadas | Não implementado; catálogo e regras não disponíveis |
| 4. Composição de programa comercial | Apresentar conjuntamente contratos e serviços distintos, cada qual com preço, condições, responsável e aceite próprios | Participantes autorizados + jurídico/compliance | Possibilidade arquitetural, não oferta real |
| 5. Produto securitário realmente novo | Nova cobertura, combinação contratual inédita, subscrição, tarifação ou condições não existentes | Seguradora, atuária, jurídico e governança regulatória; registro/aprovação conforme categoria | **Fora do poder autônomo do SegSense** |

O teto operacional de curto prazo é o **nível 3**, mas apenas após catálogo contratual, APIs autorizadas, regras de elegibilidade/subscrição, papéis comerciais e contrato Spider. O nível 4 pode gerar uma proposta de valor percebida como nova sem fundir juridicamente contratos distintos. O nível 5 exige criação formal pela seguradora; a SUSEP descreve condições gerais, especiais e particulares e o registro de produtos antes da comercialização, com aprovação prévia para certas categorias. [SUSEP — Seguro de Pessoas](https://www.gov.br/susep/pt-br/copy_of_planos-e-produtos/seguros/seguro-de-pessoas), [SUSEP — Seguro de Danos](https://www.gov.br/susep/pt-br/copy_of_planos-e-produtos/seguros/seguro-de-danos), [SUSEP — Registro Eletrônico de Produto](https://www.gov.br/susep/pt-br/servicos/mercado/realizar-registro-eletronico-de-produto).

## 5. O que a Icatu permite afirmar agora

Páginas públicas da Icatu apresentam atuação em seguro de vida, previdência e capitalização. Há descrição pública de coberturas de vida com opções de escolha e de assistências atreladas a seguro de vida contratado. Isso **não demonstra** quais combinações, preços, elegibilidade, canal, endpoints ou direitos comerciais estarão disponíveis ao SegSense. O catálogo público de APIs acessado nesta análise não expôs operações detalhadas sem acesso autorizado. [Icatu — portal institucional](https://portal.icatuseguros.com.br/), [Icatu — Seguro de Vida Essencial](https://portal.icatuseguros.com.br/seguro-de-vida/essencial), [Icatu — Assistências Vida](https://portal.icatuseguros.com.br/assistenciasvida), [Icatu — Portal de APIs](https://portal-api.icatuseguros.com.br/apis).

**Atenção ao exemplo da quebra de safra:** o artigo é ótimo para demonstrar entrada contextual, mas não há evidência aqui de produto Icatu para perda de safra. Não associar essa necessidade à Icatu na vitrine comercial. Para um cenário Icatu demonstrativo, escolher um contexto alinhado a vida/proteção familiar, e ainda assim sem insinuar produto disponível para aquela pessoa ou contratação possível.

## 6. Exemplo conceitual de “oferta novíssima” sem produto inventado

Uma pessoa lê conteúdo sobre a continuidade financeira da família em caso de imprevisto. O SegSense apresenta um convite contextual e pergunta, voluntariamente, qual objetivo ela deseja explorar: proteção de renda, proteção de dependentes ou organização de longo prazo. **Não** infere perfil pelo artigo.

No futuro, com contratos autorizados, a Spider poderia avaliar o objetivo e consultar apenas opções existentes e permitidas da Icatu, explicando separadamente: cobertura de vida, eventuais assistências vinculadas ao plano e, se fizer sentido, uma jornada distinta de previdência. O resultado seria uma **experiência composta**, não uma apólice híbrida criada pelo SegSense. Cada item exigiria confirmação de disponibilidade, condições, preço, elegibilidade, papel comercial e aceite próprios. Sem essas confirmações, a interface apresenta “ainda não disponível” — jamais simula cotação.

## 7. Modelo de composição a perseguir

```text
Contexto editorial versionado
  → hipótese de necessidade (não perfil)
  → objetivo declarado pelo visitante
  → dados mínimos e fundamento de tratamento validado
  → compreensão/preview da Spider, quando houver contrato
  → catálogo de componentes autorizados pela seguradora
  → regras de compatibilidade, elegibilidade e canal
  → proposta explicável de opções existentes
  → aceite separado por contrato/serviço
  → execução e resultado confirmados
```

O SegSense define UX, contexto editorial e regras de apresentação; a Spider governará compreensão, policy, plano e execução; seguradora e participantes habilitados respondem por produtos, subscrição, preço e emissão. A composição deve ser **determinística depois da interpretação**: matriz de compatibilidade, exclusões, dependências, vigência, canal e autorização não podem ficar a cargo livre de IA.

## 8. Condições para um piloto real

1. Escolher uma necessidade que coincida com portfólio real e canal autorizado da Icatu; não usar quebra de safra como hipótese de produto Icatu sem prova.
2. Obter catálogo versionado de produtos/coberturas/assistências, condições, combinações permitidas, APIs e ambiente de homologação autorizados.
3. Definir papéis: seguradora, corretor/representante/MGA, publicador e SegSense; revisar comercialização e remuneração.
4. Publicação do Satellite Contract externo da Spider e testes de contrato.
5. Modelo jurídico de dados e consentimento/base legal adequado à jornada, inclusive compartilhamento.
6. Revisão atuarial e regulatória caso a proposta ultrapasse simples configuração/composição de ofertas existentes.
7. Provider mock independente para demonstrar **somente** contratos públicos verificáveis, rotulado como simulação não oficial.
8. Métricas de aprendizado: qualidade do contexto, entendimento da necessidade, abandono, transparência compreendida, avanço permitido e resultado confirmado — não apenas cliques.

## 9. Decisão sugerida

Posicionar o SegSense como **camada de distribuição contextual e composição explicável de jornadas de proteção**, cooperando com seguradoras e intermediários autorizados. Vender primeiro o ganho de contexto, governança e conversão qualificada, não a promessa de “criar qualquer seguro”. A ambição de produto inédito permanece como **co-desenvolvimento com seguradora**, não função automática da plataforma.

Este assessment não altera o PRM_011 em execução. Na próxima revisão documental, incorporar `SEGSENSE_ASM_001` ao índice e transformar a escada de customização em backlog de descoberta, sem antecipar API ou produto fictício.
