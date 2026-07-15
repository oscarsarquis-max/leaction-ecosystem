# Fontes copiadas do PanelDX (somente leitura / cópia)

A aplicação real da Mesa/Oficina do Inovador **não** é a hotpage de marketing.

| Arquivo | Origem PanelDX |
|---------|----------------|
| `inovador_dashboard.ejs` | `LeAction_Sys_FE/views/inovador_dashboard.ejs` |
| `../backend/templates/inovador_dashboard.ejs` | mesma cópia usada em runtime |
| `../backend/paneldx_port/inovador_routes.py` | `LeAction_SysF/routes/inovador_routes.py` |
| `../backend/paneldx_port/sprint_*.py` | deps do mesmo módulo |
| `mesa-do-inovador.ejs` | landing de marketing (legado da cópia inicial) |
| `../frontend/public/js/tracking.js` | sensor PLG |

URL da oficina no inove4us (após login freemium):

```text
http://localhost:5174/inovador/?id_clie=<id>
```

(proxy Vite → Flask `:5010`)
