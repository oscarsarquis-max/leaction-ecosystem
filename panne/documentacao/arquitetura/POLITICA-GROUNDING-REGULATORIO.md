# Política de grounding regulatório

Classe: `RegulatoryGroundingPolicy` em `app/modules/compliance/grounding.py`.

Para fundamentar requisito obrigatório ativo ou conclusão regulatória, a fonte precisa ser:

- privada da organização avaliadora **ou** global `released`;
- autoridade e jurisdição compatíveis;
- versão `reviewed`;
- vigente na data avaliada;
- com estado normativo correto;
- fragmento citável;
- hashes de versão e fragmento preservados;
- licença quando for norma técnica privada.

## Classes

| Classe | Origem típica | Fundamenta obrigação vigente? |
|---|---|---|
| `in_force_act` | normativa oficial `in_force` | sim |
| `future_act` | normativa `future` | não |
| `revoked_or_superseded` | `revoked` / `superseded` | não |
| `proposal` | `draft`, `public_consultation`, minuta, AIR | não |
| `official_guidance` | guia, manual, Q&A oficial | auxilia; não substitui fundamento |
| `private_standard` | técnica/interna licenciada e classificada | sim, se licenciada |
| `non_normative_technical` | conteúdo técnico sem licença | não |

Consulta pública, AIR, minuta ou notícia sobre proposta **jamais** sustenta obrigação vigente. Orientação oficial não substitui o ato normativo.

Citações de IA futura devem ser revalidadas por esta política. Ausência de grounding é falha fechada.
