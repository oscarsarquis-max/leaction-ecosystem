# Perfis demo

E-mails `.invalid`. Sem senha. Subjects estáveis.

| Subject | Rótulo | Papel |
|---|---|---|
| demo-owner | Proprietário | owner |
| demo-manager | Gestor de produção | production_manager |
| demo-formulator | Técnico / formulador | technical_responsible |
| demo-baker | Padeiro | baker_operator |
| demo-reviewer | Revisor regulatório | regulatory_reviewer |
| demo-buyer | Comercial / compras | commercial |
| demo-reader | Leitor | viewer |

O seletor só aparece com `VITE_DEMO_MODE=1` fora do build de produção. Token `panne-demo:<subject>` só com verificador falso e env `local|test|demo`.
