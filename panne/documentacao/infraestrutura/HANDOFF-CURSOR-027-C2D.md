# Handoff CURSOR-027-C2D

| Campo | Valor |
|---|---|
| Estado | Diagnóstico **fechado**; acesso bootstrap **revogado** |
| Doc principal | [CURSOR-027-C2D-DIAGNOSTICO.md](CURSOR-027-C2D-DIAGNOSTICO.md) |
| CVEs | [CURSOR-027-C2D-VULNERABILIDADES.md](CURSOR-027-C2D-VULNERABILIDADES.md) |
| Digest | `sha256:87d4cef3…` → **DO_NOT_RUN** |
| C3 | **não** iniciado |

## Gate ao proprietário

- **B1:** imagem nova CRITICAL=0 + bootstrap idempotente corrigido  
- **Rollback controlado:** remover as 4 roles parciais (com autorização)

PanelDX: sem alteração.
