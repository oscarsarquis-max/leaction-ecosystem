# Handoff — CURSOR-028-RELEASE (demo consolidada)

## Escopo

- CURSOR-028-C Produto · 028-D Entrada fiscal · Fluxo · Gigio · mobile/tablet · CMS `/entrar`
- Action Hub: keys aditivas `panne-demo` / `panne` apenas
- Panne: ambiente **demo** · banco `panne_demo` · CMS ativo `panne-demo`
- **Produção congelada** · DB `panne` intacto · key `panne` não publicada · sem force push · fiscal live=0

## Baseline pré-deploy

`documentacao/evidencias/cursor-028-release/BASELINE-PANNE-DEMO-PRE.md`  
Head: `0022_fiscal_inbound`. Sem reseed/truncate. Pós-deploy: comparar contagens; redução → rollback app.

## Rollback

Hub revisão anterior · API task/digest anterior · FE bundle anterior · CMS fallback estático · `0022` não reverter se íntegra.
