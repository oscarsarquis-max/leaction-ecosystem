"""Exportação de task_breakdown → Linear (GraphQL API)."""

from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import Any, Optional

import httpx
from dotenv import load_dotenv

_BACKEND_ENV = Path(__file__).resolve().parent.parent / "backend" / ".env"
load_dotenv(_BACKEND_ENV, override=False)

LINEAR_GRAPHQL_URL = "https://api.linear.app/graphql"

_PROJECT_CREATE = """
mutation ProjectCreate($input: ProjectCreateInput!) {
  projectCreate(input: $input) {
    success
    project {
      id
      name
      url
    }
  }
}
""".strip()

_ISSUE_CREATE = """
mutation IssueCreate($input: IssueCreateInput!) {
  issueCreate(input: $input) {
    success
    issue {
      id
      identifier
      title
      url
    }
  }
}
""".strip()


class LinearExporterError(Exception):
    """Falha de configuração ou da API Linear."""


def _env(name: str, default: str = "") -> str:
    return (os.getenv(name) or default).strip()


def format_issue_description(
    micro_prompt: str,
    *,
    epic_title: str = "",
    issue_type: str = "",
) -> str:
    """Monta descrição Markdown elegante para a Issue no Linear."""
    parts = [
        "🤖 **Micro-Prompt Gerado pelo Phanton**",
        "",
    ]
    meta: list[str] = []
    if epic_title:
        meta.append(f"**Épico:** {epic_title}")
    if issue_type:
        meta.append(f"**Tipo:** `{issue_type}`")
    if meta:
        parts.extend(meta)
        parts.append("")
    parts.append(str(micro_prompt or "").strip() or "_(sem micro-prompt)_")
    return "\n".join(parts).strip()


class LinearExporter:
    """Cliente GraphQL para criar Project + Issues a partir do task_breakdown."""

    def __init__(
        self,
        *,
        api_key: Optional[str] = None,
        team_id: Optional[str] = None,
        base_url: str = LINEAR_GRAPHQL_URL,
        timeout: float = 60.0,
        sleep_between_issues: float = 0.5,
    ) -> None:
        self.api_key = (api_key if api_key is not None else _env("LINEAR_API_KEY")).strip()
        self.team_id = (team_id if team_id is not None else _env("LINEAR_TEAM_ID")).strip()
        self.base_url = (base_url or LINEAR_GRAPHQL_URL).rstrip("/")
        self.timeout = timeout
        self.sleep_between_issues = max(0.0, float(sleep_between_issues))

        if not self.api_key:
            raise LinearExporterError(
                "LINEAR_API_KEY não configurada. Defina a Personal API Key em backend/.env"
            )
        if not self.team_id:
            raise LinearExporterError(
                "LINEAR_TEAM_ID não configurado. Defina o ID do time Linear em backend/.env"
            )

    def _headers(self) -> dict[str, str]:
        # Personal API Key do Linear: header sem prefixo "Bearer"
        # (Bearer gera INPUT_ERROR na API GraphQL).
        return {
            "Authorization": self.api_key,
            "Content-Type": "application/json",
        }

    async def _graphql(
        self,
        client: httpx.AsyncClient,
        query: str,
        variables: dict[str, Any],
    ) -> dict[str, Any]:
        response = await client.post(
            self.base_url,
            headers=self._headers(),
            json={"query": query, "variables": variables},
        )
        try:
            payload = response.json()
        except Exception as exc:
            raise LinearExporterError(
                f"Resposta Linear inválida (HTTP {response.status_code}): {exc}"
            ) from exc

        if response.status_code >= 400:
            raise LinearExporterError(
                f"Linear HTTP {response.status_code}: {payload}"
            )

        errors = payload.get("errors")
        if errors:
            raise LinearExporterError(f"Linear GraphQL errors: {errors}")

        data = payload.get("data")
        if not isinstance(data, dict):
            raise LinearExporterError(f"Linear sem data: {payload}")
        return data

    async def create_project(
        self,
        name: str,
        description: str = "",
        *,
        client: Optional[httpx.AsyncClient] = None,
    ) -> dict[str, Any]:
        """Cria um Project no Linear (vinculado ao LINEAR_TEAM_ID)."""
        title = (name or "Phanton Export").strip()[:255] or "Phanton Export"
        variables = {
            "input": {
                "name": title,
                "description": (description or "").strip()[:5000],
                "teamIds": [self.team_id],
            }
        }

        async def _run(http: httpx.AsyncClient) -> dict[str, Any]:
            data = await self._graphql(http, _PROJECT_CREATE, variables)
            result = data.get("projectCreate") or {}
            if not result.get("success"):
                raise LinearExporterError(f"projectCreate falhou: {data}")
            project = result.get("project") or {}
            if not project.get("id"):
                raise LinearExporterError(f"projectCreate sem id: {data}")
            return {
                "id": project["id"],
                "name": project.get("name") or title,
                "url": project.get("url"),
            }

        if client is not None:
            return await _run(client)
        async with httpx.AsyncClient(timeout=self.timeout) as http:
            return await _run(http)

    async def create_issue(
        self,
        team_id: str,
        project_id: str,
        title: str,
        description: str,
        *,
        client: Optional[httpx.AsyncClient] = None,
    ) -> dict[str, Any]:
        """Cria uma Issue no time, vinculada ao Project."""
        issue_title = (title or "Issue").strip()[:255] or "Issue"
        variables = {
            "input": {
                "teamId": team_id or self.team_id,
                "projectId": project_id,
                "title": issue_title,
                "description": description or "",
            }
        }

        async def _run(http: httpx.AsyncClient) -> dict[str, Any]:
            data = await self._graphql(http, _ISSUE_CREATE, variables)
            result = data.get("issueCreate") or {}
            if not result.get("success"):
                raise LinearExporterError(f"issueCreate falhou: {data}")
            issue = result.get("issue") or {}
            if not issue.get("id"):
                raise LinearExporterError(f"issueCreate sem id: {data}")
            return {
                "id": issue["id"],
                "identifier": issue.get("identifier"),
                "title": issue.get("title") or issue_title,
                "url": issue.get("url"),
            }

        if client is not None:
            return await _run(client)
        async with httpx.AsyncClient(timeout=self.timeout) as http:
            return await _run(http)

    async def export_task_breakdown(
        self,
        spec_title: str,
        task_breakdown_json: dict[str, Any] | Any,
        *,
        project_description: str = "",
    ) -> dict[str, Any]:
        """
        1) Cria Project com o nome do Spec/PRD
        2) Itera epics → issues e cria cada Issue no Linear
        """
        if not isinstance(task_breakdown_json, dict):
            raise LinearExporterError("task_breakdown_json deve ser um objeto JSON")

        epics = task_breakdown_json.get("epics")
        if not isinstance(epics, list) or not epics:
            raise LinearExporterError(
                "Artefato task_breakdown sem epics — nada para exportar"
            )

        created_issues: list[dict[str, Any]] = []
        failures: list[dict[str, Any]] = []

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            project = await self.create_project(
                spec_title,
                project_description
                or f"Exportado pelo Phanton a partir de «{spec_title}».",
                client=client,
            )

            for epic in epics:
                if not isinstance(epic, dict):
                    continue
                epic_title = str(epic.get("title") or "Épico").strip()
                issues = epic.get("issues") or []
                if not isinstance(issues, list):
                    continue

                for issue in issues:
                    if not isinstance(issue, dict):
                        continue
                    title = str(issue.get("title") or "").strip()
                    if not title:
                        continue
                    # Prefixo do épico ajuda na triagem no Linear
                    linear_title = f"[{epic_title}] {title}" if epic_title else title
                    micro = (
                        issue.get("description_micro_prompt")
                        or issue.get("description")
                        or issue.get("micro_prompt")
                        or ""
                    )
                    itype = str(issue.get("type") or "").strip()
                    description = format_issue_description(
                        str(micro),
                        epic_title=epic_title,
                        issue_type=itype,
                    )
                    try:
                        created = await self.create_issue(
                            self.team_id,
                            project["id"],
                            linear_title,
                            description,
                            client=client,
                        )
                        created_issues.append(
                            {
                                **created,
                                "epic": epic_title,
                                "type": itype,
                            }
                        )
                    except Exception as exc:
                        failures.append(
                            {
                                "epic": epic_title,
                                "title": linear_title,
                                "error": str(exc),
                            }
                        )
                    if self.sleep_between_issues:
                        await asyncio.sleep(self.sleep_between_issues)

        issue_count = len(created_issues)
        epic_count = sum(1 for e in epics if isinstance(e, dict))
        summary = (
            f"Projeto criado com {issue_count} issue"
            f"{'s' if issue_count != 1 else ''}"
            f" ({epic_count} épico{'s' if epic_count != 1 else ''})"
        )
        if failures:
            summary += f"; {len(failures)} falha(s)"

        return {
            "summary": summary,
            "project": project,
            "issues_created": issue_count,
            "epics_count": epic_count,
            "issues": created_issues,
            "failures": failures,
        }
