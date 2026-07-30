"""Testes do LinearExporter com httpx mockado."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.linear_exporter import (
    LinearExporter,
    LinearExporterError,
    format_issue_description,
)


def test_format_issue_description_header():
    text = format_issue_description(
        "Implemente POST /login com JWT.",
        epic_title="Autenticação",
        issue_type="backend",
    )
    assert "Micro-Prompt Gerado pelo Phanton" in text
    assert "Autenticação" in text
    assert "`backend`" in text
    assert "POST /login" in text


def test_exporter_requires_env(monkeypatch):
    monkeypatch.delenv("LINEAR_API_KEY", raising=False)
    monkeypatch.delenv("LINEAR_TEAM_ID", raising=False)
    with pytest.raises(LinearExporterError, match="LINEAR_API_KEY"):
        LinearExporter(api_key="", team_id="team-1")
    with pytest.raises(LinearExporterError, match="LINEAR_TEAM_ID"):
        LinearExporter(api_key="key", team_id="")


def test_export_task_breakdown_creates_project_and_issues(monkeypatch):
    monkeypatch.setenv("LINEAR_API_KEY", "lin_test_key")
    monkeypatch.setenv("LINEAR_TEAM_ID", "team-uuid")

    exporter = LinearExporter(sleep_between_issues=0)

    async def fake_graphql(client, query, variables):
        if "projectCreate" in query:
            assert variables["input"]["name"] == "Habitos SaaS"
            assert variables["input"]["teamIds"] == ["team-uuid"]
            return {
                "projectCreate": {
                    "success": True,
                    "project": {
                        "id": "proj-1",
                        "name": "Habitos SaaS",
                        "url": "https://linear.app/p/1",
                    },
                }
            }
        assert "issueCreate" in query
        assert variables["input"]["projectId"] == "proj-1"
        assert variables["input"]["teamId"] == "team-uuid"
        assert "Micro-Prompt Gerado pelo Phanton" in variables["input"]["description"]
        title = variables["input"]["title"]
        return {
            "issueCreate": {
                "success": True,
                "issue": {
                    "id": f"iss-{title[:8]}",
                    "identifier": "PHA-1",
                    "title": title,
                    "url": "https://linear.app/i/1",
                },
            }
        }

    exporter._graphql = fake_graphql  # type: ignore[method-assign]

    mock_client = MagicMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    with patch("services.linear_exporter.httpx.AsyncClient", return_value=mock_client):
        result = asyncio.run(
            exporter.export_task_breakdown(
                "Habitos SaaS",
                {
                    "epics": [
                        {
                            "title": "Auth",
                            "description": "Login",
                            "issues": [
                                {
                                    "title": "POST /login",
                                    "type": "backend",
                                    "description_micro_prompt": "Use FastAPI + JWT.",
                                    "dependencies": [],
                                },
                                {
                                    "title": "Tela de login",
                                    "type": "frontend",
                                    "description_micro_prompt": "React form + token storage.",
                                    "dependencies": ["POST /login"],
                                },
                            ],
                        }
                    ]
                },
            )
        )

    assert result["issues_created"] == 2
    assert result["epics_count"] == 1
    assert "Projeto criado com 2 issues" in result["summary"]
    assert result["project"]["id"] == "proj-1"
    assert result["failures"] == []


def test_export_rejects_empty_epics(monkeypatch):
    monkeypatch.setenv("LINEAR_API_KEY", "lin_test_key")
    monkeypatch.setenv("LINEAR_TEAM_ID", "team-uuid")
    exporter = LinearExporter(sleep_between_issues=0)
    with pytest.raises(LinearExporterError, match="sem epics"):
        asyncio.run(exporter.export_task_breakdown("X", {"epics": []}))
