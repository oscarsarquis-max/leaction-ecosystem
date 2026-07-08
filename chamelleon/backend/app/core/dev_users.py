"""Utilizadores e credenciais padrao de desenvolvimento."""

from __future__ import annotations

import os
import uuid

from app.core.rbac.constants import ROLE_EXECUTOR, ROLE_LED, ROLE_SYSADMIN

# Tenant da equipe (sysadmin, executor)
DEV_TEAM_TENANT_ID = uuid.UUID("00000000-0000-4000-8000-000000000001")

# Lead demo telecom (sistema@...)
DEV_LEAD_TENANT_ID = uuid.UUID("00000000-0000-4000-8000-000000000006")

# Lead demo construcao civil / engenharia
DEV_LEAD_CONSTRUCAO_TENANT_ID = uuid.UUID("00000000-0000-4000-8000-000000000007")

DEV_USER_SYSADMIN_ID = uuid.UUID("00000000-0000-4000-8000-000000000003")
DEV_USER_LEAD_ID = uuid.UUID("00000000-0000-4000-8000-000000000002")
DEV_USER_LEAD_CONSTRUCAO_ID = uuid.UUID("00000000-0000-4000-8000-000000000008")
DEV_USER_EXECUTOR_ID = uuid.UUID("00000000-0000-4000-8000-000000000005")

DEV_FRAMEWORK_ID = "educacao-v1"
DEV_FRAMEWORK_TELECOM_ID = "telecomunicacoes-v1"
DEV_FRAMEWORK_CONSTRUCAO_ID = "construcao-civil-v1"
DEV_DEFAULT_SECTOR = "construcao"

EMAIL_SYSADMIN = "sysadmin@leaction.com.br"
EMAIL_LEAD_TEST = "sistema@paneldx.com.br"
EMAIL_LEAD_CONSTRUCAO = "engenharia@paneldx.com.br"
EMAIL_EXECUTOR_TEST = "executor@paneldx.com.br"

SYSADMIN_PASSWORD = os.getenv("CHAMELLEON_SYSADMIN_PASSWORD", "LeAction1!")
EXECUTOR_PASSWORD = os.getenv("CHAMELLEON_EXECUTOR_PASSWORD", "PanelDX1!")
LEAD_ACCESS_CODE = os.getenv("CHAMELLEON_DEV_LEAD_ACCESS_CODE", "LA-PANEL1")
LEAD_CONSTRUCAO_ACCESS_CODE = os.getenv("CHAMELLEON_DEV_LEAD_CONSTRUCAO_CODE", "LA-ENG1")

SECTOR_PROFILES = {
    "telecom": {
        "framework_id": DEV_FRAMEWORK_TELECOM_ID,
        "tenant_id": DEV_LEAD_TENANT_ID,
        "user_id": DEV_USER_LEAD_ID,
        "email": EMAIL_LEAD_TEST,
        "access_code": LEAD_ACCESS_CODE,
        "tenant_name": "Telecom Demo (Dev)",
        "user_name": "Cliente Telecom Dev",
    },
    "construcao": {
        "framework_id": DEV_FRAMEWORK_CONSTRUCAO_ID,
        "tenant_id": DEV_LEAD_CONSTRUCAO_TENANT_ID,
        "user_id": DEV_USER_LEAD_CONSTRUCAO_ID,
        "email": EMAIL_LEAD_CONSTRUCAO,
        "access_code": LEAD_CONSTRUCAO_ACCESS_CODE,
        "tenant_name": "Engenharia Demo (Dev)",
        "user_name": "Cliente Engenharia Dev",
    },
}

# Compatibilidade com referencias antigas
MVP_TENANT_ID = DEV_TEAM_TENANT_ID
MVP_USER_ID = DEV_USER_LEAD_ID
