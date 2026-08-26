from tests.test_production_api import _cleanup, _headers, _setup_http


def test_board_context_lists_establishments_and_closed_catalogs(engine) -> None:
    ctx = _setup_http(engine, "ctx")
    try:
        prefix = f"/api/v1/organizations/{ctx['org_id']}/production"
        response = ctx["client"].get(
            f"{prefix}/board/context",
            headers=_headers(ctx["token"], ctx["org_id"]),
        )
        assert response.status_code == 200, response.text
        body = response.json()["data"]
        assert body["establishments"]
        assert {row["code"] for row in body["shifts"]} == {"morning", "afternoon", "night"}
        assert {row["code"] for row in body["areas"]} >= {"fornos", "masseira"}
    finally:
        ctx["admin"].close()
        _cleanup(ctx["client"])
