from app.modules.reporting_analytics.models import (
    ReportingDashboardPreference,
    ReportingSavedView,
    ReportingSnapshot,
)


def snapshot_out(row: ReportingSnapshot) -> dict:
    return {
        "id": str(row.id),
        "execution_id": str(row.reporting_execution_id),
        "content_hash": row.content_hash,
        "created_at": row.created_at.isoformat(),
        "auto_recalculated": False,
        "payload": row.payload,
    }


def view_out(row: ReportingSavedView) -> dict:
    return {
        "id": str(row.id),
        "code": row.code,
        "display_name": row.display_name,
        "report_code": row.report_code,
        "filters": row.filters,
        "row_version": row.row_version,
    }


def preference_out(row: ReportingDashboardPreference) -> dict:
    return {
        "id": str(row.id),
        "report_code": row.report_code,
        "layout": row.layout,
        "row_version": row.row_version,
    }
