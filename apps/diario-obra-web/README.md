# Diário de Obra — Web (PWA mobile-first)

Frontend Gemba para o RDO. Porta **6173**, proxy `/api` → backend **6010**.

```powershell
cd C:\Projetos\apps\diario-obra-web
npm install
npm run dev
```

Abra `http://localhost:6173` (layout mobile centralizado no desktop).

## Fluxo

1. Selecionar canteiro (`GET /api/rdo/sites`)
2. Criar canteiro via modal (`POST /api/rdo/sites`)
3. Preencher clima manhã/tarde + observações
4. Salvar rascunho (`POST /api/rdo/logs`)

Cor predominante: **verde** (emerald).
