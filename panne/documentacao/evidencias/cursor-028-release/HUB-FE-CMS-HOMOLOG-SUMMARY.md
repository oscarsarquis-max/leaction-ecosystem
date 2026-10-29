# Hub FE CMS publish + panne-demo homolog

## Frontend admin
- Editor URL: https://actionhub.com.br/dashboard/cms/site
- VERSION: 4dcc5cb+3bbe9f0-cms-fe
- GIT_SHA: 3bbe9f0 (includes 4dcc5cb)
- BUILD_ID: FHvqQY066waZoBksrscsw
- Build: local (outside EC2); published .next + npm ci --omit=dev
- Rollback copy: /var/lib/leaction-platform/fe-published-028-cms
- Note: previous live .next was already lost in ENOSPC cleanup (deleted inode); source backup at fe-source-backup-pre-028-cms-publish

## Selector proof (published bundle)
See ops-hub-fe-selector-proof.txt — PanelDX, inove4us, School, Panne Demonstração, Panne Produção

## Homolog panne-demo (reversed)
- Image S3: https://paneldx-cms-assets-2026.s3.amazonaws.com/cms/1788200384012-panne-demo-homolog-marker.png
- Site snapshot S3: s3://paneldx-cms-assets-2026/cms/site/panne-demo.json
- Fallback while gateway stopped: source=cache, login FE 200
- Restored baseline confirmed on Hub + Panne demo
