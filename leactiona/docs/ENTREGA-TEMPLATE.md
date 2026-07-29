# Template de entrega de módulo (copiar / colar)

Use ao marcar um `module_prompt` como entregue. Cole no chat, no Phanton (notas da entrega) ou em `docs/LOG-DESVIOS.md`.

```
## Entrega — <modulo> — <YYYY-MM-DD>

### Copiar: resumo
- App: leactiona
- Prompt de origem: <nome>
- Endpoints / artefatos principais:
  - …
- Testes: `npm run test:<tag>` — N/N OK

### Copiar: desvios (se houver)
| ID | Tipo | O que | Incorporar em |
|----|------|-------|---------------|
| x.y | LACUNA/CONFLITO/INFRA/CORREÇÃO | … | PRD/SDD/security/prompt/só código |

### Copiar: pendências
- [ ] …

### Fora de escopo respeitado
- …
```

**Phanton**: botão “Copiar entrega” deve preferir este bloco (ou equivalente JSON) para cada módulo `entregue`.
