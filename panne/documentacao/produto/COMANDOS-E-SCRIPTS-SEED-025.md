# Comandos e scripts de seed

```
python -m app.seed reference
python -m app.seed demo --anchor-date 2026-08-24
python -m app.seed smoke --scenario application
python -m app.seed inspect
python -m app.seed verify
python -m app.seed coverage
python -m app.seed dry-run
```

PowerShell: `panne/scripts/dev/seed.ps1` (wrapper). Exige `PANNE_SEED_DATABASE_URL` com sufixo `_demo` ou `_smoke`.

`start-demo.ps1` (R026-012) sobe API `:5080` e Vite `:5180` só contra `panne_demo`, com autenticador falso e `VITE_DEMO_MODE=1`. **Por padrão reinicia a instância** (não reutiliza só porque `/health` responde). Opt-in: `-ReuseExisting` (exige `instance_id` coincidente). Não lê `.env`. Encerrar com `stop-demo.ps1` (prova Panne; não mata processo desconhecido). Estado: `.tmp-demo/instance.json`.
